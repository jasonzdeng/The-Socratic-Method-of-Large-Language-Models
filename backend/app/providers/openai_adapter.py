"""OpenAI provider adapter."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import HTTPProviderAdapter, ProviderSettings
from ..models.llm import Prompt


class OpenAIAdapter(HTTPProviderAdapter):
    name = "openai"
    supports_logprobs = True
    tool_call_format = "json_schema"

    def create_payload(
        self,
        *,
        prompt: Prompt,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **options: Any,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.settings.model,
            "messages": prompt.compile(self.name, include_scratchpads=True),
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        if tools:
            payload["tools"] = [self.normalize_tool_spec(tool) for tool in tools]
        if response_format:
            payload["response_format"] = response_format
        payload.update(options)
        if stream:
            payload["stream_options"] = {"include_usage": True}
        return payload

    def build_auth_headers(self, settings: ProviderSettings) -> Dict[str, str]:
        headers = super().build_auth_headers(settings)
        headers.setdefault("OpenAI-Beta", "assistants=v2")
        return headers
