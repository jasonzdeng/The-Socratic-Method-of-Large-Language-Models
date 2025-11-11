"""DeepSeek provider adapter."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import HTTPProviderAdapter
from ..models.llm import Prompt


class DeepSeekAdapter(HTTPProviderAdapter):
    name = "deepseek"
    supports_logprobs = True
    tool_call_format = "json_schema"

    def create_payload(
        self,
        *,
        prompt: Prompt,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        reasoning: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **options: Any,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.settings.model,
            "messages": prompt.compile(self.name, include_scratchpads=True),
        }
        if reasoning:
            payload["reasoning"] = reasoning
        if tools:
            payload["tools"] = [self.normalize_tool_spec(tool) for tool in tools]
        if max_tokens is not None:
            payload["max_output_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        payload.update(options)
        payload["stream"] = stream and self.supports_streaming
        return payload
