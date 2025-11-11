"""FastAPI routes for orchestrating Socratic discussions."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, List

from fastapi import APIRouter, FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from backend.app.core.database import get_session as db_session
from backend.app.domain.discussion import AgentTurn, DiscussionSession, ToolResult
from backend.app.schemas import api as api_schemas, models
from backend.app.workers.judges import CommitteeJudge, JudgeCommitteeConfig, LLMClient, RuleValidator
from backend.app.workers.reflection import DefaultReflectionEngine
from backend.app.workers.socratic import SocraticOrchestrator

router = APIRouter()


class EchoAgent:
    """Simple agent used for bootstrapping the API."""

    agent_id = "echo-agent"

    def propose(self, topic: str, context: List[str]) -> str:  # type: ignore[override]
        return f"Considering {topic}: {', '.join(filter(None, context))}".strip(", ")

    def reflect(self, prompt: str, response: str) -> List[str]:  # type: ignore[override]
        return [f"Reflecting on prompt: {prompt[:50]}"]

    def respond(self, prompt: str, context: List[str]) -> str:
        return f"Response to {prompt}"


class EchoTool:
    name = "echo-tool"

    def invoke(self, session: DiscussionSession, turn: AgentTurn) -> ToolResult:  # type: ignore[override]
        return ToolResult(
            tool_name=self.name,
            output=f"Echoing {turn.prompt}",
            metadata={"invoked_by": turn.agent_id},
        )


class SimpleLLM(LLMClient):
    def __init__(self, model: str = "gpt-sim") -> None:
        self.model = model

    def generate_summary(self, session: DiscussionSession) -> str:
        if not session.turns:
            return "No turns yet."
        latest = session.turns[-1]
        return f"Agent {latest.agent_id} discussed {session.topic}."

    def identify_issues(self, session: DiscussionSession) -> List[str]:
        return ["verify-data-integrity"] if not session.turns else []


class NonEmptyValidator(RuleValidator):
    def __init__(self, name: str = "non-empty") -> None:
        self.name = name

    def evaluate(self, session: DiscussionSession) -> List[str]:
        if any(turn.response for turn in session.turns):
            return []
        return ["no-agent-response"]


_orchestrator: SocraticOrchestrator | None = None


def get_orchestrator() -> SocraticOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        agent = EchoAgent()
        tool = EchoTool()
        judge = CommitteeJudge(
            JudgeCommitteeConfig(
                committee_id="default-committee",
                llm_clients=[SimpleLLM()],
                validators=[NonEmptyValidator()],
            )
        )
        _orchestrator = SocraticOrchestrator(
            agents=[agent],
            tools=[tool],
            judges=[judge],
            reflection_engine=DefaultReflectionEngine(),
        )
    return _orchestrator


@router.post("/sessions", response_model=api_schemas.DiscussionSessionView)
def create_session(payload: api_schemas.CreateSessionRequest) -> api_schemas.DiscussionSessionView:
    orchestrator = get_orchestrator()
    session_model = orchestrator.load_or_create_session(payload.session_id, payload.topic)
    return serialize_session(session_model)


@router.post("/sessions/{session_id}/round", response_model=api_schemas.DiscussionSessionView)
def run_round(session_id: str, payload: api_schemas.RoundRequest) -> api_schemas.DiscussionSessionView:
    orchestrator = get_orchestrator()
    session_model = orchestrator.run_round(session_id=session_id, topic=payload.topic)
    return serialize_session(session_model)


@router.get("/sessions/{session_id}", response_model=api_schemas.DiscussionSessionView)
def get_session(session_id: str) -> api_schemas.DiscussionSessionView:
    orchestrator = get_orchestrator()
    with db_session() as session:
        record = session.get(models.DiscussionSessionRecord, session_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Session not found")
        topic = record.topic
    session_model = orchestrator.load_or_create_session(session_id, topic=topic)
    return serialize_session(session_model)


async def stream_session(session_id: str) -> AsyncIterator[api_schemas.DiscussionSessionView]:
    orchestrator = get_orchestrator()
    while True:
        await asyncio.sleep(1)
        session_model = orchestrator.load_or_create_session(session_id, topic="")
        yield serialize_session(session_model)


@router.websocket("/ws/sessions/{session_id}")
async def session_updates(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    try:
        async for snapshot in stream_session(session_id):
            await websocket.send_json(snapshot.dict())
    except WebSocketDisconnect:
        return


def serialize_session(session_model: DiscussionSession) -> api_schemas.DiscussionSessionView:
    return api_schemas.DiscussionSessionView(
        session_id=session_model.session_id,
        topic=session_model.topic,
        current_phase=session_model.current_phase,
        created_at=session_model.created_at,
        updated_at=session_model.updated_at,
        turns=[
            api_schemas.AgentTurnView(
                agent_id=turn.agent_id,
                prompt=turn.prompt,
                response=turn.response,
                reflections=list(turn.reflections),
                created_at=turn.created_at,
                completed_at=turn.completed_at,
                tool_results=[
                    api_schemas.ToolResultView(
                        tool_name=result.tool_name,
                        output=result.output,
                        metadata=result.metadata,
                        created_at=result.created_at,
                    )
                    for result in turn.tool_results
                ],
            )
            for turn in session_model.turns
        ],
        judge_events=[
            api_schemas.JudgeVerdictView(
                judge_id=verdict.judge_id,
                summary=verdict.summary,
                open_issues=list(verdict.open_issues),
                metadata=verdict.metadata,
                created_at=verdict.created_at,
            )
            for verdict in session_model.judge_events
        ],
    )


app = FastAPI(title="Socratic Method Service")
app.include_router(router)


__all__ = ["app", "router"]
