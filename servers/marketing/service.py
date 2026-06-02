"""OpenAI-powered marketing strategy and content generation."""

import json
import uuid

from openai import OpenAI

from core.config import settings
from servers.marketing.schemas import (
    AudiencePersona,
    Campaign,
    ContentCalendar,
    ContentItem,
    WeekPlan,
)


def _client() -> OpenAI:
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _chat(system: str, user: str) -> str:
    resp = _client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content or ""


def _parse_json(raw: str) -> dict | list:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())


def analyze_audience(product: str, industry: str) -> AudiencePersona:
    """Analyze target audience for a product/service."""
    system = (
        "You are a marketing strategist. Analyze the target audience. "
        "Return ONLY valid JSON with keys: "
        '"demographics", "pain_points" (list), "channels" (list), "messaging". '
        "No markdown."
    )
    user = f"Product: {product}\nIndustry: {industry}"
    data = _parse_json(_chat(system, user))
    return AudiencePersona.model_validate(data)


def generate_campaign(
    product: str, goal: str, budget: str, duration: str
) -> Campaign:
    """Generate a marketing campaign plan."""
    system = (
        "You are a marketing campaign planner. Create a campaign plan. "
        "Return ONLY valid JSON with keys: "
        '"channels" (list), "kpis" (list), "content_plan" (string summary). '
        "No markdown."
    )
    user = (
        f"Product: {product}\nGoal: {goal}\n"
        f"Budget: {budget}\nDuration: {duration}"
    )
    data = _parse_json(_chat(system, user))
    return Campaign(
        id=uuid.uuid4().hex[:12],
        product=product,
        goal=goal,
        budget=budget,
        duration=duration,
        channels=data["channels"],
        kpis=data["kpis"],
        content_plan=data["content_plan"],
    )


def generate_copy(
    topic: str, platform: str, tone: str = "professional", context: str = ""
) -> str:
    """Generate marketing copy for a specific platform."""
    system = (
        "You are a marketing copywriter. Write compelling copy for the specified "
        "platform and tone. Return ONLY the copy text, nothing else."
    )
    user = (
        f"Topic: {topic}\nPlatform: {platform}\n"
        f"Tone: {tone}\nContext: {context}"
    )
    return _chat(system, user).strip()


def generate_schedule(
    campaign_summary: str, weeks: int = 4
) -> ContentCalendar:
    """Generate a content calendar for a campaign."""
    system = (
        "You are a content strategist. Create a weekly content calendar. "
        "Return ONLY valid JSON with key \"weeks\": list of objects with "
        '"week" (int), "theme" (str), "items" (list of '
        '{"day", "platform", "content_type", "topic", "description"}). '
        "No markdown."
    )
    user = f"Campaign: {campaign_summary}\nWeeks: {weeks}"
    data = _parse_json(_chat(system, user))
    return ContentCalendar(
        weeks=[
            WeekPlan(
                week=w["week"],
                theme=w["theme"],
                items=[ContentItem(**item) for item in w["items"]],
            )
            for w in data["weeks"]
        ]
    )


def optimize_content(metrics_summary: str) -> str:
    """Provide optimization suggestions based on content performance metrics."""
    system = (
        "You are a marketing analytics expert. Based on the performance metrics, "
        "provide actionable optimization suggestions. "
        "Be specific and practical. Return your analysis as plain text."
    )
    return _chat(system, metrics_summary).strip()
