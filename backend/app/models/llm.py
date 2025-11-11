"""Data structures describing prompts and responses for LLM invocations."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional


class MessageRole(str, Enum):
    """Known conversational roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SCRATCHPAD = "scratchpad"


@dataclass
class DeliberationFrame:
    """Represents an intermediate thought frame in Parlant-style deliberation."""

    name: str
    content: str
    visible: bool = False
    channel: str = "reasoning"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "name": self.name,
            "content": self.content,
            "channel": self.channel,
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        payload["visible"] = self.visible
        return payload


@dataclass
class PromptMessage:
    """Single message exchanged with a model."""

    role: MessageRole
    content: str
    hidden: bool = False
    scratchpad: Optional[str] = None
    frames: List[DeliberationFrame] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_hidden: bool = False) -> Dict[str, Any]:
        if self.hidden and not include_hidden:
            raise ValueError("Hidden messages cannot be serialized without include_hidden=True")
        payload = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        if self.scratchpad:
            payload["scratchpad"] = self.scratchpad
        if self.frames:
            payload["frames"] = [frame.to_dict() for frame in self.frames]
        payload["hidden"] = self.hidden
        return payload

    def render_for_provider(self, provider: str) -> Dict[str, Any]:
        """Render a provider-specific representation of the message."""
        base = {"role": self.role.value}
        if provider in {"openai", "deepseek", "kimi"}:
            base["content"] = self.content if not self.scratchpad else f"{self.content}\n\n{self.scratchpad}"
        elif provider in {"anthropic", "gemini"}:
            base["content"] = self.content
            if self.scratchpad:
                base.setdefault("metadata", {})["scratchpad"] = self.scratchpad
        elif provider == "perplexity":
            base["content"] = self.content
            if self.frames:
                base["frames"] = [frame.to_dict() for frame in self.frames if frame.visible]
        else:
            base["content"] = self.content
        if self.frames and provider in {"openai", "deepseek"}:
            base.setdefault("metadata", {})["frames"] = [frame.to_dict() for frame in self.frames]
        return base


@dataclass
class Prompt:
    """Full prompt payload delivered to the router."""

    messages: List[PromptMessage]
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def visible_messages(self) -> Iterable[PromptMessage]:
        for message in self.messages:
            if not message.hidden:
                yield message

    def hidden_messages(self) -> Iterable[PromptMessage]:
        for message in self.messages:
            if message.hidden:
                yield message

    def compile(self, provider: str, include_scratchpads: bool = False) -> List[Dict[str, Any]]:
        compiled: List[Dict[str, Any]] = []
        for message in self.messages:
            if message.hidden and not include_scratchpads:
                continue
            compiled.append(message.render_for_provider(provider))
        return compiled


@dataclass
class ResponseUsage:
    input_tokens: int
    output_tokens: int
    cost: Optional[float] = None


@dataclass
class ResponseChunk:
    index: int
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Structured response coming back from an LLM provider."""

    text: str
    raw: Any
    usage: Optional[ResponseUsage] = None
    logprobs: Optional[Any] = None
    frames: List[DeliberationFrame] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    chunks: List[ResponseChunk] = field(default_factory=list)

    def add_chunk(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        index = len(self.chunks)
        self.chunks.append(ResponseChunk(index=index, content=content, metadata=metadata or {}))
        self.text += content
