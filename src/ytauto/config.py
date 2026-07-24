"""Central configuration for the whole system.

WHY THIS FILE EXISTS
--------------------
Every module (topic finder, script writer, video builder...) needs settings:
paths, API keys, log level. If each module read them its own way, changing
one setting would mean hunting through the whole codebase. Instead, ALL
configuration lives here, loaded exactly once, and every other module does:

    from ytauto.config import settings

This is the "single source of truth" principle.

HOW SECRETS ARE HANDLED
-----------------------
Secrets (API keys) are NEVER written in code. They live in a `.env` file
that is git-ignored. `python-dotenv` copies them into environment
variables at startup, and we read them with `os.getenv`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Locate the project root, no matter where the code is run from.
# This file is at  <root>/src/ytauto/config.py  → three .parent hops up.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Load <root>/.env into environment variables (silently skips if missing).
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """All application settings in one immutable object.

    `frozen=True` makes instances read-only — nothing can accidentally
    mutate configuration at runtime, which prevents a whole class of bugs.
    """

    # --- General ---
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # --- Channel ---
    channel_niche: str = field(
        default_factory=lambda: os.getenv("CHANNEL_NICHE", "tech_ai_explainers")
    )

    max_videos_per_day: int = field(
        default_factory=lambda: int(os.getenv("MAX_VIDEOS_PER_DAY", "1"))
    )

    # --- Local LLM ---
    ollama_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    )

    # --- Paths (derived, not from .env) ---
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    logs_dir: Path = PROJECT_ROOT / "logs"

    # --- API keys (empty until later milestones) ---
    youtube_api_key: str = field(
        default_factory=lambda: os.getenv("YOUTUBE_API_KEY", "")
    )

    def ensure_dirs(self) -> None:
        """Create data/ and logs/ if they don't exist yet (safe to re-run)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


# The one shared instance the rest of the app imports.
settings = Settings()
