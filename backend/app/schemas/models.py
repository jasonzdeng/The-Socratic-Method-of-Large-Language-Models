"""SQLAlchemy models representing discussion data."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DiscussionSessionRecord(Base):
    __tablename__ = "discussion_sessions"

    id = Column(String, primary_key=True)
    topic = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    turns = relationship("AgentTurnRecord", back_populates="session")
    verdicts = relationship("JudgeVerdictRecord", back_populates="session")
    events = relationship("EventRecord", back_populates="session")


class AgentTurnRecord(Base):
    __tablename__ = "agent_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("discussion_sessions.id"), nullable=False)
    agent_id = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text)
    reflections = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)

    session = relationship("DiscussionSessionRecord", back_populates="turns")
    tools = relationship("ToolResultRecord", back_populates="turn")


class ToolResultRecord(Base):
    __tablename__ = "tool_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    turn_id = Column(Integer, ForeignKey("agent_turns.id"), nullable=False)
    tool_name = Column(String, nullable=False)
    output = Column(Text, nullable=False)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    turn = relationship("AgentTurnRecord", back_populates="tools")


class JudgeVerdictRecord(Base):
    __tablename__ = "judge_verdicts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("discussion_sessions.id"), nullable=False)
    judge_id = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    open_issues = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("DiscussionSessionRecord", back_populates="verdicts")


class EventRecord(Base):
    __tablename__ = "discussion_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("discussion_sessions.id"), nullable=False)
    phase = Column(String, nullable=False)
    actor = Column(String)
    payload = Column(JSON, default=dict)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    causal_turn_id = Column(Integer, ForeignKey("agent_turns.id"))
    causal_tool_id = Column(Integer, ForeignKey("tool_results.id"))
    causal_verdict_id = Column(Integer, ForeignKey("judge_verdicts.id"))

    session = relationship("DiscussionSessionRecord", back_populates="events")
    turn = relationship("AgentTurnRecord")
    tool = relationship("ToolResultRecord")
    verdict: Optional[JudgeVerdictRecord] = relationship("JudgeVerdictRecord")
