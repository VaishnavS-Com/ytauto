"""All database operations for the `scripts` table.

Chapters are a Python list in the app but a JSON string in SQLite —
serialization happens HERE, at the storage boundary, and nowhere else.
Callers never see JSON strings; they see lists.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ytauto.database import get_connection
from ytauto.logging_setup import get_logger

log = get_logger(__name__)


def save_script(
    topic_id: int,
    title: str,
    hook: str,
    body: str,
    cta: str,
    chapters: list[str],
    model: str,
    db_path: Path | None = None,
) -> int:
    """Store one complete script draft. Returns its new id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO scripts (topic_id, title, hook, body, cta, chapters, model)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (topic_id, title, hook, body, cta, json.dumps(chapters), model),
        )
        script_id = cursor.lastrowid
    log.info("Saved script %d for topic %d (%d words)",
             script_id, topic_id, len(body.split()))
    return script_id


def get_scripts_for_topic(
    topic_id: int, db_path: Path | None = None
) -> list[dict]:
    """All drafts for a topic, newest first, chapters deserialized."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM scripts WHERE topic_id = ? "
            "ORDER BY created_at DESC, id DESC",
            (topic_id,),
        ).fetchall()
    return [_to_dict(row) for row in rows]


def latest_script(topic_id: int, db_path: Path | None = None) -> dict | None:
    """Most recent draft for a topic, or None."""
    drafts = get_scripts_for_topic(topic_id, db_path=db_path)
    return drafts[0] if drafts else None


def _to_dict(row: sqlite3.Row) -> dict:
    """Row -> plain dict, with chapters back as a Python list."""
    d = dict(row)
    d["chapters"] = json.loads(d["chapters"])
    return d
