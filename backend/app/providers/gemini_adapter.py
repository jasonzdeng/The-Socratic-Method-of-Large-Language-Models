"""Google Gemini provider adapter."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import HTTPProviderAdapter
from ..models.llm import Prompt


class GeminiAdapter(HTTPProviderAdapter):
    name = "gemini"
    tool_call_format = "protoc"

    def build_auth_headers(self, settings) -> Dict[str, str]:
        headers = super().build_auth_headers(settings)
        headers["x-goog-api-key"] = headers.pop("Authorization").split(" ")[-1]
        return headers

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
        contents = []
        for message in prompt.compile(self.name, include_scratchpads=True):
            contents.append({
                "role": message["role"],
                "parts": [{"text": message["content"]}],
            })
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {k: v for k, v in {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            }.items() if v is not None},
            "tools": tools or [],
        }
        payload.update(options)
        payload["stream"] = stream and self.supports_streaming
        return payload
