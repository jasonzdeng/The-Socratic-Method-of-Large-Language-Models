"""Common data models shared across services."""

from pydantic import BaseModel, Field


class Topic(BaseModel):
    """Represents a learning topic exposed via the API and frontend."""

    id: str = Field(description="Stable identifier for the topic")
    title: str = Field(description="Human-readable title")
    description: str = Field(description="Additional detail about the topic")
