"""Parlant-inspired reflection helpers."""
from __future__ import annotations

from typing import Iterable

from backend.app.domain.discussion import AgentTurn
from backend.app.workers.socratic import AgentAdapter, ReflectionEngine


class DefaultReflectionEngine(ReflectionEngine):
    """Reflection engine that defers to the agent when possible."""

    def generate(self, agent: AgentAdapter, turn: AgentTurn) -> Iterable[str]:
        if hasattr(agent, "reflect"):
            yield from agent.reflect(turn.prompt, turn.response or "")
        else:
            yield from ()
