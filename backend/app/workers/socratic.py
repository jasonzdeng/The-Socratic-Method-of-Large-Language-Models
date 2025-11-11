"""Worker orchestrator for Socratic discussions."""
from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Deque, Iterable, List, Protocol

from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.domain.discussion import (
    AgentTurn,
    DiscussionPhase,
    DiscussionSession,
    JudgeVerdict,
    PhaseEvent,
    ToolResult,
)
from backend.app.schemas import models


class AgentAdapter(Protocol):
    """Protocol describing how agents should behave."""

    agent_id: str

    def propose(self, topic: str, context: List[str]) -> str:
        ...

    def reflect(self, prompt: str, response: str) -> Iterable[str]:
        ...


class ToolAdapter(Protocol):
    """Protocol for integrating external tools into the orchestrator."""

    name: str

    def invoke(self, session: DiscussionSession, turn: AgentTurn) -> ToolResult:
        ...


class ReflectionEngine(Protocol):
    """Parlant-style reflection steps interface."""

    def generate(self, agent: AgentAdapter, turn: AgentTurn) -> Iterable[str]:
        ...


class SocraticOrchestrator:
    """Coordinates agents, tools, and judges for a session."""

    def __init__(
        self,
        agents: Iterable[AgentAdapter],
        tools: Iterable[ToolAdapter],
        judges: Iterable["JudgeWorker"],
        reflection_engine: ReflectionEngine,
    ) -> None:
        self.agents: Deque[AgentAdapter] = deque(agents)
        self.tools = list(tools)
        self.judges = list(judges)
        self.reflection_engine = reflection_engine

    def load_or_create_session(self, session_id: str, topic: str) -> DiscussionSession:
        """Return a session aggregate, either from persistence or new."""
        with get_session() as session:
            record = session.get(models.DiscussionSessionRecord, session_id)
            if record:
                return self._hydrate_session(record)
            record = models.DiscussionSessionRecord(id=session_id, topic=topic)
            session.add(record)
            session.flush()
            return DiscussionSession(session_id=session_id, topic=topic)

    def _hydrate_session(self, record: models.DiscussionSessionRecord) -> DiscussionSession:
        """Reconstruct a discussion session aggregate from persistent data."""
        session_model = DiscussionSession(
            session_id=record.id,
            topic=record.topic,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

        session_model.turns.clear()
        for turn_record in sorted(record.turns, key=lambda tr: tr.created_at):
            turn = AgentTurn(
                agent_id=turn_record.agent_id,
                prompt=turn_record.prompt,
                response=turn_record.response,
                reflections=tuple(turn_record.reflections or []),
                created_at=turn_record.created_at,
                completed_at=turn_record.completed_at,
                tool_results=[],
            )
            turn.record_id = turn_record.id  # type: ignore[attr-defined]
            for tool_record in sorted(turn_record.tools, key=lambda tool: tool.created_at):
                tool_result = ToolResult(
                    tool_name=tool_record.tool_name,
                    output=tool_record.output,
                    metadata=tool_record.metadata or {},
                    created_at=tool_record.created_at,
                )
                tool_result.record_id = tool_record.id  # type: ignore[attr-defined]
                turn.tool_results.append(tool_result)
            session_model.turns.append(turn)

        session_model.judge_events.clear()
        for verdict_record in sorted(record.verdicts, key=lambda verdict: verdict.created_at):
            verdict = JudgeVerdict(
                judge_id=verdict_record.judge_id,
                summary=verdict_record.summary,
                open_issues=tuple(verdict_record.open_issues or []),
                metadata=verdict_record.metadata or {},
                created_at=verdict_record.created_at,
            )
            verdict.record_id = verdict_record.id  # type: ignore[attr-defined]
            session_model.judge_events.append(verdict)

        session_model.tool_events.clear()
        for event_record in sorted(record.events, key=lambda event: event.occurred_at):
            session_model.tool_events.append(
                PhaseEvent(
                    phase=DiscussionPhase(event_record.phase),
                    actor=event_record.actor,
                    payload=event_record.payload or {},
                    timestamp=event_record.occurred_at,
                    record_id=event_record.id,
                )
            )

        if session_model.tool_events:
            session_model.current_phase = session_model.tool_events[-1].phase
        elif session_model.judge_events:
            session_model.current_phase = DiscussionPhase.JUDGE_REVIEW

        return session_model

    def run_round(self, session_id: str, topic: str) -> DiscussionSession:
        """Execute a full discussion round across all agents and judges."""
        session_model = self.load_or_create_session(session_id, topic)
        context = [turn.response or "" for turn in session_model.turns]
        agent = self.agents[0]
        prompt = agent.propose(topic, context)
        turn = session_model.start_agent_turn(agent.agent_id, prompt)

        for tool in self.tools:
            result = tool.invoke(session_model, turn)
            session_model.record_tool_result(result)

        response = prompt  # fallback if agent reflection modifies prompt
        reflections = list(self.reflection_engine.generate(agent, turn))
        if hasattr(agent, "respond"):
            response = getattr(agent, "respond")(prompt, context)
        session_model.close_agent_turn(response=response, reflections=reflections)

        for judge in self.judges:
            verdict = judge.review(session_model)
            session_model.add_judge_verdict(verdict)

        self._persist(session_model)
        self._rotate_agents()
        return session_model

    def _persist(self, session_model: DiscussionSession) -> None:
        """Persist session state into the relational schema."""
        with get_session() as session:
            record = session.get(models.DiscussionSessionRecord, session_model.session_id)
            if not record:
                record = models.DiscussionSessionRecord(
                    id=session_model.session_id,
                    topic=session_model.topic,
                    created_at=session_model.created_at,
                    updated_at=session_model.updated_at,
                )
                session.add(record)
            record.topic = session_model.topic
            record.updated_at = datetime.utcnow()

            turn_records = {
                tr.id: tr for tr in session.execute(
                    select(models.AgentTurnRecord).where(models.AgentTurnRecord.session_id == record.id)
                ).scalars()
            }
            for turn in session_model.turns:
                turn_record = turn_records.get(getattr(turn, "record_id", None))
                if not turn_record:
                    turn_record = models.AgentTurnRecord(
                        session_id=record.id,
                        agent_id=turn.agent_id,
                        prompt=turn.prompt,
                    )
                    session.add(turn_record)
                    session.flush()
                    turn.record_id = turn_record.id  # type: ignore[attr-defined]
                turn_record.response = turn.response
                turn_record.reflections = list(turn.reflections)
                turn_record.completed_at = turn.completed_at
                turn_record.created_at = turn.created_at

                existing_tools = {
                    tool.id: tool for tool in session.execute(
                        select(models.ToolResultRecord).where(models.ToolResultRecord.turn_id == turn_record.id)
                    ).scalars()
                }
                for tool_result in turn.tool_results:
                    tool_record = None
                    if hasattr(tool_result, "record_id"):
                        tool_record = existing_tools.get(tool_result.record_id)
                    if not tool_record:
                        tool_record = models.ToolResultRecord(
                            turn_id=turn_record.id,
                            tool_name=tool_result.tool_name,
                            output=tool_result.output,
                            metadata=tool_result.metadata,
                            created_at=tool_result.created_at,
                        )
                        session.add(tool_record)
                        session.flush()
                        tool_result.record_id = tool_record.id  # type: ignore[attr-defined]
                    else:
                        tool_record.output = tool_result.output
                        tool_record.metadata = tool_result.metadata

            existing_verdicts = {
                verdict.id: verdict for verdict in session.execute(
                    select(models.JudgeVerdictRecord).where(models.JudgeVerdictRecord.session_id == record.id)
                ).scalars()
            }
            for verdict in session_model.judge_events:
                verdict_record = None
                if hasattr(verdict, "record_id"):
                    verdict_record = existing_verdicts.get(verdict.record_id)
                if not verdict_record:
                    verdict_record = models.JudgeVerdictRecord(
                        session_id=record.id,
                        judge_id=verdict.judge_id,
                        summary=verdict.summary,
                        open_issues=list(verdict.open_issues),
                        metadata=verdict.metadata,
                        created_at=verdict.created_at,
                    )
                    session.add(verdict_record)
                    session.flush()
                    verdict.record_id = verdict_record.id  # type: ignore[attr-defined]
                else:
                    verdict_record.summary = verdict.summary
                    verdict_record.open_issues = list(verdict.open_issues)
                    verdict_record.metadata = verdict.metadata

            existing_event_ids = {
                evt.id
                for evt in session.execute(
                    select(models.EventRecord.id).where(models.EventRecord.session_id == record.id)
                ).scalars()
            }
            for event in session_model.history():
                if event.record_id in existing_event_ids:
                    continue
                event_record = models.EventRecord(
                    session_id=record.id,
                    phase=event.phase.value,
                    actor=event.actor,
                    payload=event.payload,
                    occurred_at=event.timestamp,
                )
                session.add(event_record)
                session.flush()
                event.record_id = event_record.id
                existing_event_ids.add(event_record.id)

    def _rotate_agents(self) -> None:
        """Rotate the agent queue to ensure turns are round-robin."""
        self.agents.rotate(-1)


class JudgeWorker(Protocol):
    """Protocol for judge workers."""

    judge_id: str

    def review(self, session: DiscussionSession) -> JudgeVerdict:
        ...
