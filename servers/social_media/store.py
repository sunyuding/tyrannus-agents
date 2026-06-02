"""JSON file-based draft storage in ~/.tyrannus/drafts/."""

import os
import uuid
from datetime import datetime
from pathlib import Path

from core.config import settings
from servers.social_media.schemas import Draft, DraftStatus


def _drafts_dir() -> Path:
    path = Path(settings.DRAFTS_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_draft(draft: Draft) -> str:
    """Save a draft to disk. Returns the draft ID."""
    path = _drafts_dir() / f"{draft.id}.json"
    tmp_path = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    tmp_path.write_text(draft.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp_path, path)
    return draft.id


def get_draft(draft_id: str) -> Draft | None:
    """Load a single draft by ID."""
    path = _drafts_dir() / f"{draft_id}.json"
    if not path.exists():
        return None
    return Draft.model_validate_json(path.read_text(encoding="utf-8"))


def list_drafts(status: str | None = None) -> list[Draft]:
    """List all drafts, optionally filtered by status."""
    drafts: list[Draft] = []
    for path in _drafts_dir().glob("*.json"):
        try:
            draft = Draft.model_validate_json(path.read_text(encoding="utf-8"))
            if status is None or draft.status.value == status:
                drafts.append(draft)
        except Exception:
            continue
    return sorted(drafts, key=lambda d: d.created_at, reverse=True)


def update_draft(draft_id: str, **updates) -> Draft | None:
    """Update fields on an existing draft. Returns updated draft or None."""
    draft = get_draft(draft_id)
    if draft is None:
        return None
    data = draft.model_dump()
    data.update(updates)
    data["updated_at"] = datetime.now()
    updated = Draft.model_validate(data)
    save_draft(updated)
    return updated


def new_draft_id() -> str:
    """Generate a new draft ID."""
    return uuid.uuid4().hex[:12]
