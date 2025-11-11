"""Domain models for Socratic discussion sessions."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Sequence


class DiscussionPhase(str, Enum):
    """Enumeration of the lifecycle phases inside a discussion round."""

    AGENT_TURN = "agent_turn"
    TOOL_INVOCATION = "tool_invocation"
    JUDGE_REVIEW = "judge_review"


@dataclass(slots=True)
class PhaseEvent:
    """Immutable snapshot describing a transition within a phase."""

    phase: DiscussionPhase
    timestamp: datetime
    payload: dict = field(default_factory=dict)
    actor: Optional[str] = None
    record_id: Optional[int] = None


@dataclass(slots=True)
class ToolResult:
    """Result emitted by a tool invocation during the discussion."""

    tool_name: str
    output: str
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class AgentTurn:
    """Represents a single agent contribution to the discussion."""

    agent_id: str
    prompt: str
    response: Optional[str] = None
    reflections: Sequence[str] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    tool_results: List[ToolResult] = field(default_factory=list)


@dataclass(slots=True)
class JudgeVerdict:
    """A decision produced by a judge or committee of judges."""

    judge_id: str
    summary: str
    open_issues: Sequence[str] = field(default_factory=tuple)
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class DiscussionSession:
    """Aggregate root capturing the state of a multi-phase discussion."""

    session_id: str
    topic: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    current_phase: DiscussionPhase = DiscussionPhase.AGENT_TURN
    turns: List[AgentTurn] = field(default_factory=list)
    tool_events: List[PhaseEvent] = field(default_factory=list)
    judge_events: List[JudgeVerdict] = field(default_factory=list)

    def start_agent_turn(self, agent_id: str, prompt: str) -> AgentTurn:
        """Start a new agent turn and transition the phase."""
        turn = AgentTurn(agent_id=agent_id, prompt=prompt)
        self.turns.append(turn)
        self.current_phase = DiscussionPhase.AGENT_TURN
        self.updated_at = datetime.utcnow()
        self.tool_events.append(
            PhaseEvent(
                phase=self.current_phase,
                timestamp=self.updated_at,
                payload={"agent_id": agent_id, "prompt": prompt},
                actor=agent_id,
            )
        )
        return turn

    def record_tool_result(self, tool_result: ToolResult) -> None:
        """Attach a tool result to the latest agent turn and log the phase transition."""
        if not self.turns:
            raise ValueError("Cannot record tool result without an active turn")
        self.turns[-1].tool_results.append(tool_result)
        self.current_phase = DiscussionPhase.TOOL_INVOCATION
        timestamp = datetime.utcnow()
        self.updated_at = timestamp
        self.tool_events.append(
            PhaseEvent(
                phase=self.current_phase,
                timestamp=timestamp,
                payload={"tool": tool_result.tool_name, "metadata": tool_result.metadata},
                actor=tool_result.metadata.get("invoked_by"),
            )
        )

    def close_agent_turn(self, response: str, reflections: Optional[Sequence[str]] = None) -> None:
        """Finalize the latest agent turn with an agent response and reflections."""
        if not self.turns:
            raise ValueError("No agent turn available to close")
        turn = self.turns[-1]
        turn.response = response
        if reflections:
            turn.reflections = tuple(reflections)
        turn.completed_at = datetime.utcnow()
        self.updated_at = turn.completed_at

    def add_judge_verdict(self, verdict: JudgeVerdict) -> None:
        """Record a judge verdict and update phase tracking."""
        self.judge_events.append(verdict)
        self.current_phase = DiscussionPhase.JUDGE_REVIEW
        self.updated_at = verdict.created_at

    def history(self) -> List[PhaseEvent]:
        """Return a chronological list of phase events for auditing."""
        return sorted(self.tool_events, key=lambda event: event.timestamp)
