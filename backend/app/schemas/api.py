"""Pydantic schemas for API I/O."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from backend.app.domain.discussion import DiscussionPhase


class ToolResultView(BaseModel):
    tool_name: str
    output: str
    metadata: dict
    created_at: datetime


class AgentTurnView(BaseModel):
    agent_id: str
    prompt: str
    response: Optional[str]
    reflections: List[str]
    created_at: datetime
    completed_at: Optional[datetime]
    tool_results: List[ToolResultView]


class JudgeVerdictView(BaseModel):
    judge_id: str
    summary: str
    open_issues: List[str]
    metadata: dict
    created_at: datetime


class DiscussionSessionView(BaseModel):
    session_id: str
    topic: str
    current_phase: DiscussionPhase
    created_at: datetime
    updated_at: datetime
    turns: List[AgentTurnView]
    judge_events: List[JudgeVerdictView]


class CreateSessionRequest(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the session")
    topic: str


class RoundRequest(BaseModel):
    session_id: str
    topic: str
