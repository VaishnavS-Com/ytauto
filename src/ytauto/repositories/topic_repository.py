"""All database operations for the `topics` table.

TWO NON-NEGOTIABLE HABITS TAUGHT HERE
-------------------------------------
1. PARAMETERIZED QUERIES. We write  VALUES (?, ?, ?)  and pass values
   separately. NEVER build SQL with f-strings — that is how SQL injection
   happens (user input like  '); DROP TABLE topics;--  executing as code).
   The `?` placeholders make injection impossible.

2. ERRORS ARE HANDLED, NOT HIDDEN. A duplicate insert is an EXPECTED event
   (Phase 1 will re-see the same trending topic daily), so we catch it,
   log it, and return None. Unexpected errors are NOT caught — they should
   crash loudly so we see them. Catching everything is a classic beginner
   bug that turns crashes into silent data loss.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ytauto.database import get_connection
from ytauto.logging_setup import get_logger

log = get_logger(__name__)


def normalize_title(title: str) -> str:
    """Canonical form used for duplicate detection.

    'How AI Works!' and '  how ai works ' are the same idea. Lowercasing,
    trimming, and collapsing inner whitespace catches most real duplicates.
    (Phase 1 later adds smarter, meaning-based dedup on top of this.)
    """
    return " ".join(title.lower().split())


def add_topic(
    title: str,
    niche: str,
    source: str = "manual",
    db_path: Path | None = None,
) -> int | None:
    """Insert a topic. Returns its new id, or None if it's a duplicate."""
    title = title.strip()
    if not title:
        raise ValueError("Topic title cannot be empty")

    try:
        with get_connection(db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO topics (title, title_normalized, source, niche)
                VALUES (?, ?, ?, ?)
                """,
                (title, normalize_title(title), source, niche),
            )
            topic_id = cursor.lastrowid
        log.info("Added topic %d: %r (source=%s)", topic_id, title, source)
        return topic_id
    except sqlite3.IntegrityError:
        # UNIQUE constraint on title_normalized fired -> duplicate idea.
        log.info("Skipped duplicate topic: %r", title)
        return None


def list_topics(
    status: str | None = None,
    db_path: Path | None = None,
) -> list[sqlite3.Row]:
    """Return topics, optionally filtered by status, newest first."""
    query = "SELECT * FROM topics"
    params: tuple = ()
    if status is not None:
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY created_at DESC, id DESC"

    with get_connection(db_path) as conn:
        return conn.execute(query, params).fetchall()


def update_status(topic_id: int, status: str, db_path: Path | None = None) -> bool:
    """Move a topic through its lifecycle. Returns False if id doesn't exist.

    The CHECK constraint in the schema rejects invalid status strings at
    the database level — a second line of defense below this function.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE topics SET status = ? WHERE id = ?",
            (status, topic_id),
        )
        updated = cursor.rowcount > 0

    if updated:
        log.info("Topic %d -> status %s", topic_id, status)
    else:
        log.warning("update_status: topic id %d not found", topic_id)
    return updated


def count_topics(db_path: Path | None = None) -> int:
    """Total number of stored topics."""
    with get_connection(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]


def delete_topic(topic_id: int, db_path: Path | None = None) -> bool:
    """Remove a topic by id. Returns False if id doesn't exist."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM topics WHERE id = ?",
            (topic_id,),
        )
        deleted = cursor.rowcount > 0

    if deleted:
        log.info("Deleted topic %d", topic_id)
    else:
        log.warning("delete_topic: topic id %d not found", topic_id)
    return deleted

