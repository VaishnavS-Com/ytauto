"""All database operations for the `assets` table."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ytauto.database import get_connection
from ytauto.logging_setup import get_logger

log = get_logger(__name__)


def save_asset(
    script_id: int,
    part_index: int,
    kind: str,
    file_path: str,
    meta: str = "",
    db_path: Path | None = None,
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO assets (script_id, part_index, kind, file_path, meta)
            VALUES (?, ?, ?, ?, ?)
            """,
            (script_id, part_index, kind, file_path, meta),
        )
        asset_id = cursor.lastrowid
    log.info("Saved %s asset for script %d part %d", kind, script_id, part_index)
    return asset_id


def get_assets(
    script_id: int, kind: str | None = None, db_path: Path | None = None
) -> list[sqlite3.Row]:
    query = "SELECT * FROM assets WHERE script_id = ?"
    params: tuple = (script_id,)
    if kind is not None:
        query += " AND kind = ?"
        params = (script_id, kind)
    query += " ORDER BY part_index"
    with get_connection(db_path) as conn:
        return conn.execute(query, params).fetchall()


def delete_assets(script_id: int, db_path: Path | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM assets WHERE script_id = ?", (script_id,))
        deleted = cursor.rowcount
    if deleted:
        log.info("Deleted %d old assets for script %d", deleted, script_id)
    return deleted
