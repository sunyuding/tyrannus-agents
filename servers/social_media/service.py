"""OpenAI-powered content generation for social media."""

import json

from openai import OpenAI

from core.config import settings
from servers.social_media.schemas import Draft, DraftStatus, Scene, VideoScript
from servers.social_media.store import new_draft_id


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


def generate_post(
    topic: str,
    platforms: list[str],
    tone: str = "professional",
    language: str = "zh-TW",
) -> list[Draft]:
    """Generate a post draft for each platform."""
    system = (
        "You are a social media content expert. "
        "Generate platform-specific posts. Return ONLY valid JSON: "
        'a list of objects with "platform" and "content" keys. '
        "No markdown, no code fences."
    )
    user = (
        f"Topic: {topic}\n"
        f"Platforms: {', '.join(platforms)}\n"
        f"Tone: {tone}\n"
        f"Language: {language}\n"
        "Generate one post per platform."
    )
    raw = _chat(system, user)
    # Strip markdown code fences if model adds them
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    items = json.loads(cleaned.strip())

    drafts: list[Draft] = []
    for item in items:
        draft = Draft(
            id=new_draft_id(),
            topic=topic,
            platform=item["platform"],
            content=item["content"],
            status=DraftStatus.DRAFT,
        )
        drafts.append(draft)
    return drafts


def generate_video_script(topic: str, language: str = "zh-TW") -> VideoScript:
    """Generate a video script with scenes."""
    system = (
        "You are a video content strategist. "
        "Generate a video script with scenes. Return ONLY valid JSON with keys: "
        '"scenes" (list of {"description", "narration", "shot_type"}) '
        'and "narration" (full narration text). No markdown.'
    )
    user = f"Topic: {topic}\nLanguage: {language}"
    raw = _chat(system, user)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    data = json.loads(cleaned.strip())

    return VideoScript(
        id=new_draft_id(),
        topic=topic,
        scenes=[Scene(**s) for s in data["scenes"]],
        narration=data["narration"],
    )


def generate_cover_prompt(topic: str, style: str = "modern") -> str:
    """Generate an AI image prompt for a cover image."""
    system = (
        "You are a visual design expert. Generate a detailed AI image generation prompt "
        "for a social media cover image. Return ONLY the prompt text, nothing else."
    )
    user = f"Topic: {topic}\nStyle: {style}"
    return _chat(system, user).strip()


def generate_subtitles(narration_text: str) -> str:
    """Generate SRT-format subtitles from narration text."""
    system = (
        "You are a subtitle editor. Convert the narration into SRT format. "
        "Split into natural segments of 5-10 seconds. "
        "Return ONLY valid SRT content, nothing else."
    )
    return _chat(system, narration_text).strip()
