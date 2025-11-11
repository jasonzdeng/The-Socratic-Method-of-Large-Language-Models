"""Topic-related API routes."""

from typing import List

from fastapi import APIRouter

from common.models import Topic
from ..tasks.topics import create_topic_task

router = APIRouter()


@router.get("/", response_model=List[Topic], summary="List topics")
async def list_topics() -> list[Topic]:
    """Return a placeholder list of topics."""

    return [
        Topic(id="intro-logic", title="Introduction to Logic", description="Logic fundamentals"),
        Topic(id="ethics-101", title="Ethics", description="Exploring ethical frameworks"),
    ]


@router.post("/", response_model=Topic, summary="Create a new topic")
async def create_topic(topic: Topic) -> Topic:
    """Dispatch a background task to persist the topic and echo the request body."""

    create_topic_task.delay(topic.model_dump())
    return topic
