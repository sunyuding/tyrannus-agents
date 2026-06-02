"""Pydantic models for social media drafts and video scripts."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DraftStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"


class Draft(BaseModel):
    id: str
    topic: str
    platform: str
    content: str
    status: DraftStatus = DraftStatus.DRAFT
    publish_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Scene(BaseModel):
    description: str
    narration: str
    shot_type: str = "medium"


class VideoScript(BaseModel):
    id: str
    topic: str
    scenes: list[Scene]
    narration: str
    created_at: datetime = Field(default_factory=datetime.now)
