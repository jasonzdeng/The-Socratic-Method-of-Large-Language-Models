"""Provider adapter base classes and shared utilities."""
from __future__ import annotations

import abc
import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, Iterable, Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    """Simple token bucket configuration."""

    rate_per_minute: int
    burst: Optional[int] = None

    def __post_init__(self) -> None:
        if self.burst is None:
            self.burst = self.rate_per_minute


class AsyncTokenBucket:
    """Minimal asynchronous token bucket implementation."""

    def __init__(self, limit: RateLimit) -> None:
        self.limit = limit
        self.tokens = limit.burst or limit.rate_per_minute
        self.updated_at = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self.lock:
            await self._refill()
            while self.tokens <= 0:
                wait_time = 60.0 / float(self.limit.rate_per_minute)
                logger.debug("Rate limit reached. Sleeping for %.2f seconds.", wait_time)
                await asyncio.sleep(wait_time)
                await self._refill()
            self.tokens -= 1

    async def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.updated_at
        refill = int(elapsed * (self.limit.rate_per_minute / 60.0))
        if refill > 0:
            self.tokens = min(self.limit.burst or self.limit.rate_per_minute, self.tokens + refill)
            self.updated_at = now


@dataclass
class ProviderSettings:
    """Normalized configuration for an LLM provider."""

    model: str
    api_key: str
    api_base: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    request_timeout: Optional[float] = None
    headers: Dict[str, str] = field(default_factory=dict)


class ProviderAdapter(abc.ABC):
    """Abstract base class for provider-specific adapters."""

    name: str = "base"
    supports_logprobs: bool = False
    supports_streaming: bool = True
    tool_call_format: str = "json"

    def __init__(
        self,
        settings: ProviderSettings,
        rate_limit: Optional[RateLimit] = None,
    ) -> None:
        self.settings = settings
        self.rate_limiter = AsyncTokenBucket(rate_limit) if rate_limit else None

    async def execute(
        self,
        payload: Dict[str, Any],
        *,
        stream: bool = False,
    ) -> Any:
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        auth_headers = self.build_auth_headers(self.settings)
        request_payload = self.transform_payload(payload, stream=stream)
        headers = {**auth_headers, **self.settings.headers}
        logger.debug("Dispatching request to %s with payload keys: %s", self.name, list(request_payload.keys()))
        return await self.dispatch(request_payload, headers=headers, stream=stream)

    @abc.abstractmethod
    def create_payload(self, **kwargs: Any) -> Dict[str, Any]:
        """Convert normalized request arguments into a vendor payload."""

    @abc.abstractmethod
    async def dispatch(
        self,
        payload: Dict[str, Any],
        *,
        headers: Dict[str, str],
        stream: bool = False,
    ) -> Any:
        """Send a request to the vendor. Subclasses should implement this."""

    def transform_payload(self, payload: Dict[str, Any], *, stream: bool = False) -> Dict[str, Any]:
        """Apply vendor-specific payload transformations."""
        transformed = dict(payload)
        if stream and self.supports_streaming:
            transformed["stream"] = True
        return transformed

    def build_auth_headers(self, settings: ProviderSettings) -> Dict[str, str]:
        """Return default authorization headers."""
        return {"Authorization": f"Bearer {settings.api_key}"}

    def normalize_tool_spec(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize tool schema for the provider."""
        if self.tool_call_format == "json":
            return tool
        # default passthrough for unsupported formats
        return tool

    @staticmethod
    def cache_key(model: str, payload: Dict[str, Any]) -> str:
        serialized = json.dumps({"model": model, "payload": payload}, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class MockStreamingResponse:
    """Utility generator for simulating streaming responses in tests or offline mode."""

    def __init__(self, chunks: Iterable[str]) -> None:
        self.chunks = list(chunks)

    async def __aiter__(self) -> AsyncGenerator[str, None]:
        for chunk in self.chunks:
            await asyncio.sleep(0)
            yield chunk


class HTTPProviderAdapter(ProviderAdapter):
    """Adapter that uses httpx for network IO with graceful degradation."""

    timeout: Optional[float] = None

    async def dispatch(
        self,
        payload: Dict[str, Any],
        *,
        headers: Dict[str, str],
        stream: bool = False,
    ) -> Any:
        try:
            import httpx  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "httpx is required to execute provider calls. Install httpx to continue."
            ) from exc

        timeout = self.settings.request_timeout or self.timeout
        async with httpx.AsyncClient(base_url=self.settings.api_base, timeout=timeout) as client:
            request = client.stream if stream else client.post
            response = await request("/", headers=headers, json=payload)
            response.raise_for_status()
            if stream and response.aiter_text:
                return response.aiter_text()
            return response.json()
