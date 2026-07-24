"""All database operations for the `videos` table."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ytauto.database import get_connection
from ytauto.logging_setup import get_logger

log = get_logger(__name__)


def save_video(
    script_id: int, file_path: str, duration_s: float,
    db_path: Path | None = None,
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO videos (script_id, file_path, duration_s) VALUES (?, ?, ?)",
            (script_id, file_path, duration_s),
        )
        video_id = cursor.lastrowid
    log.info("Saved video %d for script %d (%.1fs)", video_id, script_id, duration_s)
    return video_id


def latest_video(script_id: int, db_path: Path | None = None) -> sqlite3.Row | None:
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT * FROM videos WHERE script_id = ? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (script_id,),
        ).fetchone()
