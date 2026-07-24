"""All database operations for the `voiceovers` table."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ytauto.database import get_connection
from ytauto.logging_setup import get_logger

log = get_logger(__name__)


def save_part(
    script_id: int,
    part_index: int,
    part_name: str,
    file_path: str,
    voice: str,
    db_path: Path | None = None,
) -> int:
    """Record one synthesized audio part."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO voiceovers (script_id, part_index, part_name, file_path, voice)
            VALUES (?, ?, ?, ?, ?)
            """,
            (script_id, part_index, part_name, file_path, voice),
        )
        part_id = cursor.lastrowid
    log.info("Saved voiceover part %s for script %d", part_name, script_id)
    return part_id


def get_parts(script_id: int, db_path: Path | None = None) -> list[sqlite3.Row]:
    """All audio parts for a script, in playback order."""
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT * FROM voiceovers WHERE script_id = ? ORDER BY part_index",
            (script_id,),
        ).fetchall()


def delete_parts(script_id: int, db_path: Path | None = None) -> int:
    """Remove all parts for a script (used before regenerating). Returns count."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM voiceovers WHERE script_id = ?", (script_id,)
        )
        deleted = cursor.rowcount
    if deleted:
        log.info("Deleted %d old voiceover parts for script %d", deleted, script_id)
    return deleted
