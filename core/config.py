"""Shared configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    OPENAI_API_KEY: str = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY", "")
    )
    DATABASE_URL: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus",
        )
    )
    CHROMA_PERSIST_DIR: str = field(
        default_factory=lambda: os.environ.get("CHROMA_PERSIST_DIR", "./data/chroma")
    )
    CHROME_CDP_PORT: int = field(
        default_factory=lambda: int(os.environ.get("CHROME_CDP_PORT", "9333"))
    )
    CHROME_PROFILE_DIR: str = field(
        default_factory=lambda: os.environ.get(
            "CHROME_PROFILE_DIR",
            os.path.expanduser(
                "~/Library/Application Support/Google/Chrome/SocialMCP/"
            ),
        )
    )


settings = Settings()
