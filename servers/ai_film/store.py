"""JSON file-based video task storage in ~/.tyrannus/ai_film/."""

import os
import uuid
from datetime import datetime
from pathlib import Path

from core.config import settings
from servers.ai_film.schemas import VideoTask


def _tasks_dir() -> Path:
    path = Path(settings.AI_FILM_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def new_task_id() -> str:
    return uuid.uuid4().hex[:12]


def save_video_task(task: VideoTask) -> str:
    """Save a video task to disk. Returns the task ID."""
    path = _tasks_dir() / f"{task.id}.json"
    tmp_path = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    tmp_path.write_text(task.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp_path, path)
    return task.id


def get_video_task(task_id: str) -> VideoTask | None:
    """Load a single video task by local ID."""
    path = _tasks_dir() / f"{task_id}.json"
    if not path.exists():
        return None
    return VideoTask.model_validate_json(path.read_text(encoding="utf-8"))


def find_by_provider_id(provider_task_id: str) -> VideoTask | None:
    """Find a video task by its provider (Ark) task ID."""
    for path in _tasks_dir().glob("*.json"):
        try:
            task = VideoTask.model_validate_json(path.read_text(encoding="utf-8"))
            if task.provider_task_id == provider_task_id:
                return task
        except Exception:
            continue
    return None


def resolve_task(id_or_provider_id: str) -> VideoTask | None:
    """Resolve by local ID first, then by provider task ID."""
    task = get_video_task(id_or_provider_id)
    if task is not None:
        return task
    return find_by_provider_id(id_or_provider_id)


def list_video_tasks(status: str | None = None) -> list[VideoTask]:
    """List all video tasks, optionally filtered by status."""
    tasks: list[VideoTask] = []
    for path in _tasks_dir().glob("*.json"):
        try:
            task = VideoTask.model_validate_json(path.read_text(encoding="utf-8"))
            if status is None or task.status.value == status:
                tasks.append(task)
        except Exception:
            continue
    return sorted(tasks, key=lambda t: t.created_at, reverse=True)


def update_video_task(task_id: str, **updates) -> VideoTask | None:
    """Update fields on an existing video task. Returns updated task or None."""
    task = get_video_task(task_id)
    if task is None:
        return None
    data = task.model_dump()
    data.update(updates)
    data["updated_at"] = datetime.now()
    updated = VideoTask.model_validate(data)
    save_video_task(updated)
    return updated
