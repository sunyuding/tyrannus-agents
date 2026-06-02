"""FastMCP server for social media content (Module 5)."""

import asyncio
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from core.tools.browser import post_facebook as _browser_post_facebook
from servers.social_media import service, store
from servers.social_media.schemas import DraftStatus

mcp = FastMCP(
    "tyrannus-social",
    instructions="Social media content generation, draft management, and publishing",
)


@mcp.tool()
def generate_post(
    topic: str,
    platforms: list[str] | None = None,
    tone: str = "professional",
    language: str = "zh-TW",
) -> str:
    """Generate social media posts for the given platforms and save as drafts.

    Args:
        topic: The topic or subject for the post
        platforms: Target platforms (default: ["facebook"])
        tone: Writing tone — professional, casual, humorous, etc.
        language: Content language — zh-TW, zh-CN, en
    """
    if platforms is None:
        platforms = ["facebook"]
    drafts = service.generate_post(topic, platforms, tone, language)
    for d in drafts:
        store.save_draft(d)
    lines = [f"Created {len(drafts)} draft(s):"]
    for d in drafts:
        lines.append(f"\n--- {d.platform} (id: {d.id}) ---\n{d.content}")
    return "\n".join(lines)


@mcp.tool()
def generate_video_script(topic: str, language: str = "zh-TW") -> str:
    """Generate a video script with scenes and narration.

    Args:
        topic: The video topic
        language: Script language — zh-TW, zh-CN, en
    """
    script = service.generate_video_script(topic, language)
    lines = [f"Video Script: {script.topic} (id: {script.id})\n"]
    for i, scene in enumerate(script.scenes, 1):
        lines.append(f"Scene {i} [{scene.shot_type}]: {scene.description}")
        lines.append(f"  Narration: {scene.narration}\n")
    lines.append(f"Full narration:\n{script.narration}")
    return "\n".join(lines)


@mcp.tool()
def generate_cover_prompt(topic: str, style: str = "modern") -> str:
    """Generate an AI image prompt for a social media cover image.

    Args:
        topic: The cover image topic
        style: Visual style — modern, minimalist, vibrant, etc.
    """
    return service.generate_cover_prompt(topic, style)


@mcp.tool()
def generate_subtitles(narration_text: str) -> str:
    """Generate SRT-format subtitles from narration text.

    Args:
        narration_text: The full narration text to convert
    """
    return service.generate_subtitles(narration_text)


@mcp.tool()
def list_drafts(status: str | None = None) -> str:
    """List all saved drafts, optionally filtered by status.

    Args:
        status: Filter by status — draft, approved, scheduled, published (default: all)
    """
    drafts = store.list_drafts(status)
    if not drafts:
        return "No drafts found."
    lines = [f"Found {len(drafts)} draft(s):\n"]
    for d in drafts:
        lines.append(
            f"- [{d.status.value}] {d.platform} | {d.topic} | id: {d.id} | {d.created_at:%Y-%m-%d %H:%M}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_draft(draft_id: str) -> str:
    """Get a single draft by ID.

    Args:
        draft_id: The draft identifier
    """
    draft = store.get_draft(draft_id)
    if draft is None:
        return f"Draft '{draft_id}' not found."
    return (
        f"Draft: {draft.id}\n"
        f"Platform: {draft.platform}\n"
        f"Topic: {draft.topic}\n"
        f"Status: {draft.status.value}\n"
        f"Created: {draft.created_at:%Y-%m-%d %H:%M}\n"
        f"---\n{draft.content}"
    )


@mcp.tool()
def approve_draft(draft_id: str) -> str:
    """Mark a draft as approved so it can be published.

    Args:
        draft_id: The draft identifier
    """
    draft = store.get_draft(draft_id)
    if draft is None:
        return f"Draft '{draft_id}' not found."
    if draft.status == DraftStatus.PUBLISHED:
        return f"Draft '{draft_id}' has already been published."

    updated = store.update_draft(draft_id, status=DraftStatus.APPROVED)
    if updated is None:
        return "Failed to approve draft."
    return f"Draft '{draft_id}' approved."


@mcp.tool()
def post_facebook(draft_id: str) -> str:
    """Publish a draft to Facebook via Chrome CDP.

    Args:
        draft_id: The draft ID to publish
    """
    draft = store.get_draft(draft_id)
    if draft is None:
        return f"Draft '{draft_id}' not found."
    if draft.status != DraftStatus.APPROVED:
        return (
            f"Draft '{draft_id}' is {draft.status.value}. "
            "Run approve_draft first before publishing to Facebook."
        )

    result = asyncio.run(_browser_post_facebook(draft.content))
    if "successfully" in result.lower():
        store.update_draft(draft_id, status=DraftStatus.PUBLISHED)
    return result


@mcp.tool()
def schedule_post(draft_id: str, publish_at: str) -> str:
    """Schedule a draft for future publishing (saves timestamp, no cron yet).

    Args:
        draft_id: The draft ID to schedule
        publish_at: ISO 8601 datetime for publishing (e.g. 2025-01-15T10:00:00)
    """
    draft = store.get_draft(draft_id)
    if draft is None:
        return f"Draft '{draft_id}' not found."

    try:
        dt = datetime.fromisoformat(publish_at)
    except ValueError:
        return f"Invalid datetime format: {publish_at}. Use ISO 8601."

    updated = store.update_draft(
        draft_id, status=DraftStatus.SCHEDULED, publish_at=dt
    )
    if updated is None:
        return "Failed to update draft."
    return f"Draft '{draft_id}' scheduled for {dt:%Y-%m-%d %H:%M}."


def main():
    mcp.run()


if __name__ == "__main__":
    main()
