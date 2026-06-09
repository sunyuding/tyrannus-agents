"""Pydantic models for video generation tasks."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class VideoTaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMEOUT = "timeout"


class VideoTask(BaseModel):
    id: str
    provider_task_id: str
    prompt: str
    image_urls: list[str] = Field(default_factory=list)
    video_urls: list[str] = Field(default_factory=list)
    audio_urls: list[str] = Field(default_factory=list)
    ratio: str = "16:9"
    duration: int = 5
    generate_audio: bool = False
    watermark: bool = False
    status: VideoTaskStatus = VideoTaskStatus.QUEUED
    video_url: str | None = None
    local_path: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
