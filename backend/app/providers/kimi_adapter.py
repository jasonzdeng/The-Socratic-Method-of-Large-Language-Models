"""Moonshot Kimi provider adapter."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import HTTPProviderAdapter
from ..models.llm import Prompt


class KimiAdapter(HTTPProviderAdapter):
    name = "kimi"
    supports_logprobs = False
    tool_call_format = "markdown"

    def create_payload(
        self,
        *,
        prompt: Prompt,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
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
            payload["plugins"] = [self.normalize_tool_spec(tool) for tool in tools]
        payload.update(options)
        payload["stream"] = stream and self.supports_streaming
        return payload
