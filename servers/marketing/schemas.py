"""Pydantic models for marketing campaigns and content planning."""

from datetime import datetime

from pydantic import BaseModel, Field


class AudiencePersona(BaseModel):
    demographics: str
    pain_points: list[str]
    channels: list[str]
    messaging: str


class ContentItem(BaseModel):
    day: str
    platform: str
    content_type: str
    topic: str
    description: str


class WeekPlan(BaseModel):
    week: int
    theme: str
    items: list[ContentItem]


class ContentCalendar(BaseModel):
    weeks: list[WeekPlan]


class Campaign(BaseModel):
    id: str
    product: str
    goal: str
    budget: str
    duration: str
    channels: list[str]
    kpis: list[str]
    content_plan: str
    created_at: datetime = Field(default_factory=datetime.now)
