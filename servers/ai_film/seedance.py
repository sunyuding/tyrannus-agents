"""Ark SDK wrapper for Seedance 2.0 video generation."""

import time
import urllib.request
from pathlib import Path

from volcenginesdkarkruntime import Ark

from core.config import settings


def _client() -> Ark:
    if not settings.ARK_API_KEY:
        raise RuntimeError("ARK_API_KEY environment variable is not set")
    return Ark(api_key=settings.ARK_API_KEY, base_url=settings.ARK_BASE_URL)


def create_video_task(
    prompt: str,
    *,
    image_urls: list[str] | None = None,
    video_urls: list[str] | None = None,
    audio_urls: list[str] | None = None,
    ratio: str = "16:9",
    duration: int = 5,
    generate_audio: bool = False,
    watermark: bool = False,
) -> str:
    """Submit a video generation task. Returns the provider task ID."""
    client = _client()

    content_parts: list[dict] = [{"type": "text", "text": prompt}]
    for url in image_urls or []:
        content_parts.append({"type": "image_url", "image_url": {"url": url}, "role": "reference_image"})
    for url in video_urls or []:
        content_parts.append({"type": "video_url", "video_url": {"url": url}, "role": "reference_video"})
    for url in audio_urls or []:
        content_parts.append({"type": "audio_url", "audio_url": {"url": url}, "role": "reference_audio"})

    resp = client.content_generation.tasks.create(
        model=settings.SEEDANCE_MODEL,
        content=content_parts,
        ratio=ratio,
        duration=duration,
        generate_audio=generate_audio,
        watermark=watermark,
    )
    return resp.id


def get_task_status(provider_task_id: str) -> dict:
    """One-shot status check. Returns {status, video_url?, error?}."""
    client = _client()
    resp = client.content_generation.tasks.get(task_id=provider_task_id)

    result: dict = {"status": resp.status}

    content = getattr(resp, "content", None)
    if content:
        result["video_url"] = getattr(content, "video_url", None)

    error = getattr(resp, "error", None)
    if error:
        result["error"] = f"{getattr(error, 'code', 'unknown')}: {getattr(error, 'message', '')}"

    return result


def poll_video_task(provider_task_id: str) -> dict:
    """Blocking poll until terminal state or timeout. Returns {status, video_url?, error?}."""
    deadline = time.monotonic() + settings.SEEDANCE_POLL_TIMEOUT

    while time.monotonic() < deadline:
        result = get_task_status(provider_task_id)
        if result["status"] in ("succeeded", "failed"):
            return result
        time.sleep(settings.SEEDANCE_POLL_INTERVAL)

    return {"status": "timeout", "error": f"Timed out after {settings.SEEDANCE_POLL_TIMEOUT}s"}


def download_video(video_url: str, task_id: str) -> str:
    """Download video to local storage. Returns the local file path."""
    videos_dir = Path.home() / "Downloads" / "ai_film"
    videos_dir.mkdir(parents=True, exist_ok=True)
    local_path = videos_dir / f"{task_id}.mp4"
    urllib.request.urlretrieve(video_url, local_path)
    return str(local_path)
