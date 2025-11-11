"""Router for dispatching prompts to vendor-specific LLM adapters."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Optional, Tuple, Type

try:  # pragma: no cover - optional dependency
    import redis.asyncio as redis  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    redis = None

try:  # pragma: no cover - optional dependency
    from opentelemetry import trace  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    trace = None

from ..models.llm import LLMResponse, Prompt, ResponseChunk, ResponseUsage
from ..providers import (
    AnthropicAdapter,
    DeepSeekAdapter,
    GeminiAdapter,
    KimiAdapter,
    OpenAIAdapter,
    PerplexityAdapter,
    ProviderAdapter,
    ProviderSettings,
    RateLimit,
)
from .tools import ToolRegistry, default_registry

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    name: str
    settings: ProviderSettings
    rate_limit: Optional[RateLimit]
    cache_ttl: Optional[int] = None


class InMemoryCache:
    """Fallback cache used when Redis is unavailable."""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            value, expires_at = entry
            if expires_at is not None and expires_at < asyncio.get_event_loop().time():
                self._store.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        async with self._lock:
            expiry = None
            if ex is not None:
                expiry = asyncio.get_event_loop().time() + ex
            self._store[key] = (value, expiry)


class LLMRouter:
    """Normalize provider configuration and dispatch requests to adapters."""

    ADAPTERS: Dict[str, Type[ProviderAdapter]] = {
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
        "perplexity": PerplexityAdapter,
        "deepseek": DeepSeekAdapter,
        "gemini": GeminiAdapter,
        "kimi": KimiAdapter,
    }

    def __init__(
        self,
        *,
        redis_url: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
        default_cache_ttl: int = 300,
    ) -> None:
        self.tool_registry = tool_registry or default_registry()
        self.default_cache_ttl = default_cache_ttl
        self._cache = self._init_cache(redis_url)
        self._provider_cache: Dict[str, ProviderConfig] = {}
        self._tracer = trace.get_tracer(__name__) if trace else None

    def _init_cache(self, redis_url: Optional[str]) -> Any:
        if redis_url and redis:
            return redis.from_url(redis_url)
        return InMemoryCache()

    def register_provider(self, name: str, config: Dict[str, Any]) -> None:
        normalized = self.normalize_provider_config(name, config)
        key = normalized.settings.model or name
        self._provider_cache[key] = normalized
        logger.debug("Registered provider config for %s", key)

    def normalize_provider_config(self, name: str, config: Dict[str, Any]) -> ProviderConfig:
        provider_name = name.lower()
        if provider_name not in self.ADAPTERS:
            raise ValueError(f"Unsupported provider: {name}")

        api_key = config.get("api_key") or config.get("key") or config.get("token")
        if not api_key:
            raise ValueError(f"Missing API key for provider {name}")

        model = config.get("model") or config.get("deployment")
        if not model:
            raise ValueError(f"Missing model identifier for provider {name}")

        api_base = config.get("api_base") or config.get("base_url") or config.get("endpoint")
        options = dict(config.get("options", {}))
        headers = dict(config.get("headers", {}))
        request_timeout = config.get("request_timeout")
        rate_per_minute = config.get("rate_limit_per_minute") or config.get("rpm")
        burst = config.get("burst")
        cache_ttl = config.get("cache_ttl")

        settings = ProviderSettings(
            model=model,
            api_key=api_key,
            api_base=api_base,
            options=options,
            request_timeout=request_timeout,
            headers=headers,
        )
        rate_limit = RateLimit(rate_per_minute=rate_per_minute, burst=burst) if rate_per_minute else None
        return ProviderConfig(name=provider_name, settings=settings, rate_limit=rate_limit, cache_ttl=cache_ttl)

    def get_adapter(
        self, provider: str, config: Optional[Dict[str, Any]] = None
    ) -> Tuple[ProviderAdapter, ProviderConfig]:
        provider_name = provider.lower()
        if config is not None:
            normalized = self.normalize_provider_config(provider_name, config)
        else:
            normalized = next(
                (value for key, value in self._provider_cache.items() if value.name == provider_name),
                None,
            )
            if normalized is None:
                raise ValueError(f"Provider {provider} is not registered and no config supplied")
        adapter_cls = self.ADAPTERS[provider_name]
        adapter = adapter_cls(normalized.settings, rate_limit=normalized.rate_limit)
        return adapter, normalized

    async def aroute(
        self,
        *,
        provider: str,
        prompt: Prompt,
        tools: Optional[Any] = None,
        cache_key: Optional[str] = None,
        session_id: Optional[str] = None,
        stream: bool = False,
        use_cache: bool = True,
        response_format: Optional[Dict[str, Any]] = None,
        **options: Any,
    ) -> Any:
        adapter, provider_config = self.get_adapter(provider, options.pop("provider_config", None))
        normalized_tools = self._normalize_tools(tools, session_id)
        payload = adapter.create_payload(
            prompt=prompt,
            tools=normalized_tools,
            stream=stream,
            response_format=response_format,
            **options,
        )
        cache_key = cache_key or ProviderAdapter.cache_key(adapter.settings.model, payload)

        if stream:
            return await self._stream_response(adapter, payload)

        cached = await self._fetch_cache(cache_key) if use_cache else None
        if cached:
            logger.debug("Cache hit for %s", cache_key)
            raw_response = json.loads(cached)
            return self._coerce_response(provider, raw_response)

        span_ctx = self._tracer.start_as_current_span("llm.call") if self._tracer else nullcontext()
        async with span_ctx as span:
            raw_response = await adapter.execute(payload, stream=False)
            response = self._coerce_response(provider, raw_response)
            if use_cache:
                await self._store_cache(provider_config, cache_key, raw_response)
            if span:
                self._enrich_span(span, provider, payload, response)
            return response

    def _normalize_tools(self, tools: Optional[Any], session_id: Optional[str]) -> Optional[Any]:
        if not tools:
            return None
        session_identifier = session_id or "anonymous"
        normalized = []
        for tool in tools:
            if isinstance(tool, str):
                definition = self.tool_registry.get(tool)
                self.tool_registry.ensure_budget(name=definition.name, session_id=session_identifier)
                normalized.append(
                    {
                        "type": "function",
                        "function": {
                            "name": definition.name,
                            "description": definition.description,
                            "parameters": definition.json_schema,
                        },
                        "metadata": definition.metadata,
                    }
                )
            elif isinstance(tool, dict):
                tool_name = tool.get("name") or tool.get("function", {}).get("name")
                if tool_name:
                    self.tool_registry.ensure_budget(name=tool_name, session_id=session_identifier)
                normalized.append(tool)
            else:
                normalized.append(tool)
        return normalized

    async def _stream_response(
        self,
        adapter: ProviderAdapter,
        payload: Dict[str, Any],
    ) -> AsyncGenerator[ResponseChunk, None]:
        stream = await adapter.execute(payload, stream=True)
        index = 0
        async for chunk in stream:
            yield ResponseChunk(index=index, content=chunk if isinstance(chunk, str) else json.dumps(chunk))
            index += 1

    async def _fetch_cache(self, key: str) -> Optional[str]:
        if isinstance(self._cache, InMemoryCache):
            return await self._cache.get(key)
        try:
            return await self._cache.get(key)
        except Exception:  # pragma: no cover - network errors ignored
            logger.warning("Failed to fetch cache key %s", key, exc_info=True)
            return None

    async def _store_cache(self, provider_config: ProviderConfig, key: str, value: Any) -> None:
        ttl = provider_config.cache_ttl or self.default_cache_ttl
        serialized = json.dumps(value)
        if isinstance(self._cache, InMemoryCache):
            await self._cache.set(key, serialized, ex=ttl)
        else:
            try:
                await self._cache.set(key, serialized, ex=ttl)
            except Exception:  # pragma: no cover
                logger.warning("Failed to store cache key %s", key, exc_info=True)

    def _coerce_response(self, provider: str, raw: Any) -> LLMResponse:
        text = ""
        usage = None
        logprobs = None
        tool_calls = []
        frames = []

        if isinstance(raw, dict):
            usage_data = raw.get("usage")
            if usage_data:
                usage = ResponseUsage(
                    input_tokens=usage_data.get("prompt_tokens", usage_data.get("input_tokens", 0)),
                    output_tokens=usage_data.get("completion_tokens", usage_data.get("output_tokens", 0)),
                    cost=usage_data.get("total_cost"),
                )
            if provider == "openai":
                choices = raw.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    text = message.get("content", "")
                    logprobs = message.get("logprobs")
                    tool_calls = message.get("tool_calls", [])
            elif provider == "anthropic":
                content = raw.get("content", [])
                if content:
                    text = "".join(part.get("text", "") for part in content)
            elif provider == "perplexity":
                text = raw.get("output", "") or raw.get("answer", "")
            elif provider == "deepseek":
                choices = raw.get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
                    logprobs = choices[0].get("logprobs")
            elif provider == "gemini":
                candidates = raw.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(part.get("text", "") for part in parts)
            elif provider == "kimi":
                choices = raw.get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
            text = text or raw.get("text", "")
        else:
            text = str(raw)

        return LLMResponse(text=text, raw=raw, usage=usage, logprobs=logprobs, frames=frames, tool_calls=tool_calls)

    def _enrich_span(self, span: Any, provider: str, payload: Dict[str, Any], response: LLMResponse) -> None:
        try:
            span.set_attribute("llm.provider", provider)
            span.set_attribute("llm.model", payload.get("model"))
            span.set_attribute("llm.prompt_tokens", response.usage.input_tokens if response.usage else 0)
            span.set_attribute("llm.completion_tokens", response.usage.output_tokens if response.usage else 0)
            span.set_attribute("llm.cost", response.usage.cost if response.usage else 0)
        except Exception:  # pragma: no cover - tracing is best-effort
            logger.debug("Failed to annotate trace span", exc_info=True)


class nullcontext:
    """Fallback async context manager for when OpenTelemetry is unavailable."""

    async def __aenter__(self) -> None:  # type: ignore[override]
        return None

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None


__all__ = ["LLMRouter", "ProviderConfig"]
