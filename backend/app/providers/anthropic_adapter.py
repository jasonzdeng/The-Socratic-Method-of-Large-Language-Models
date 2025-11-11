"""Anthropic provider adapter."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import HTTPProviderAdapter
from ..models.llm import Prompt


class AnthropicAdapter(HTTPProviderAdapter):
    name = "anthropic"
    tool_call_format = "json_schema"

    def build_auth_headers(self, settings) -> Dict[str, str]:
        headers = super().build_auth_headers(settings)
        headers["x-api-key"] = headers.pop("Authorization").split(" ")[-1]
        headers["anthropic-version"] = settings.options.get("anthropic_version", "2023-06-01")
        return headers

    def create_payload(
        self,
        *,
        prompt: Prompt,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        **options: Any,
    ) -> Dict[str, Any]:
        system = system_prompt
        messages = []
        for message in prompt.compile(self.name, include_scratchpads=True):
            if message["role"] == "system" and system is None:
                system = message["content"]
                continue
            messages.append({"role": message["role"], "content": message["content"]})
        payload: Dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
        }
        if system:
            payload["system"] = system
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        if tools:
            payload["tools"] = [self.normalize_tool_spec(tool) for tool in tools]
        payload.update(options)
        payload["stream"] = stream and self.supports_streaming
        return payload
