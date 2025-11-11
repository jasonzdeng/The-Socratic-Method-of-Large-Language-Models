"""Registry of function calling tools available to the LLM router."""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class ToolDefinition:
    name: str
    description: str
    json_schema: Dict[str, Any]
    cost_per_call: float = 0.0
    global_budget: Optional[float] = None
    per_session_budget: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolBudgetExceeded(Exception):
    """Raised when invoking a tool would exceed the configured budget."""


class ToolRegistry:
    """In-memory tool registry with budget enforcement."""

    def __init__(self) -> None:
        self._definitions: Dict[str, ToolDefinition] = {}
        self._global_consumption: Dict[str, float] = {}
        self._session_consumption: Dict[Tuple[str, str], float] = {}
        self._lock = Lock()

    def register(self, definition: ToolDefinition) -> None:
        with self._lock:
            self._definitions[definition.name] = definition
            self._global_consumption.setdefault(definition.name, 0.0)

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._definitions[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def list(self) -> Iterable[ToolDefinition]:
        return list(self._definitions.values())

    def ensure_budget(self, *, name: str, session_id: str, cost: Optional[float] = None) -> None:
        definition = self.get(name)
        computed_cost = cost if cost is not None else definition.cost_per_call
        key = (name, session_id)
        with self._lock:
            total = self._global_consumption.get(name, 0.0) + computed_cost
            if definition.global_budget is not None and total > definition.global_budget:
                raise ToolBudgetExceeded(
                    f"Global budget exceeded for {name}: {total:.2f} > {definition.global_budget:.2f}"
                )
            session_total = self._session_consumption.get(key, 0.0) + computed_cost
            if definition.per_session_budget is not None and session_total > definition.per_session_budget:
                raise ToolBudgetExceeded(
                    f"Session budget exceeded for {name}: {session_total:.2f} > {definition.per_session_budget:.2f}"
                )
            self._global_consumption[name] = total
            self._session_consumption[key] = session_total

    def remaining_budget(self, *, name: str, session_id: str) -> Dict[str, Optional[float]]:
        definition = self.get(name)
        with self._lock:
            global_remaining = (
                None
                if definition.global_budget is None
                else max(definition.global_budget - self._global_consumption.get(name, 0.0), 0.0)
            )
            session_key = (name, session_id)
            session_remaining = (
                None
                if definition.per_session_budget is None
                else max(definition.per_session_budget - self._session_consumption.get(session_key, 0.0), 0.0)
            )
        return {"global": global_remaining, "session": session_remaining}


def default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="search",
            description="Perform web search across curated sources.",
            json_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
                },
                "required": ["query"],
            },
            cost_per_call=0.01,
            global_budget=10.0,
            per_session_budget=1.0,
        )
    )
    registry.register(
        ToolDefinition(
            name="alphavantage",
            description="Query AlphaVantage financial time-series data.",
            json_schema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "function": {"type": "string", "enum": ["TIME_SERIES_DAILY", "TIME_SERIES_INTRADAY"]},
                    "interval": {"type": "string", "default": "5min"},
                },
                "required": ["symbol", "function"],
            },
            cost_per_call=0.05,
            global_budget=25.0,
            per_session_budget=2.0,
        )
    )
    registry.register(
        ToolDefinition(
            name="quant_sandbox",
            description="Execute quantitative experiments in a sandboxed runtime.",
            json_schema={
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "Python script to execute"},
                    "timeout": {"type": "number", "default": 30},
                    "memory_limit": {"type": "number", "default": 512},
                },
                "required": ["script"],
            },
            cost_per_call=0.5,
            global_budget=50.0,
            per_session_budget=5.0,
            metadata={"sandbox": True},
        )
    )
    return registry


__all__ = ["ToolDefinition", "ToolBudgetExceeded", "ToolRegistry", "default_registry"]
