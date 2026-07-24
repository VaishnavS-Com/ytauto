"""Database connection + schema for the whole system.

WHY SQLITE?
-----------
SQLite is a full SQL database that lives in a single file (data/ytauto.db).
No server to install, no password, free forever, and it ships inside Python
itself (`import sqlite3` — stdlib). For a single-machine pipeline like ours
it is the professional choice, not a toy: browsers, phones, and planes run
SQLite in production.

DESIGN RULES USED HERE
----------------------
1. One function (`get_connection`) is the ONLY way the app opens the DB —
   so settings like foreign keys and row factories are applied everywhere.
2. Schema lives in one place (`SCHEMA`) and `init_db()` is idempotent:
   safe to call at every startup, creates tables only if missing.
3. Callers use `with get_connection() as conn:` — the context manager
   COMMITS on success and ROLLS BACK on error automatically. No half-saved
   data, ever. (This is what "transactional" means.)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ytauto.config import settings
from ytauto.logging_setup import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Schema — the shape of our data.
#
# topics: every video idea the system ever sees, from any source.
#   title            what a human reads
#   title_normalized lowercase/trimmed version; UNIQUE = the database itself
#                    refuses duplicates (Phase 1 "remove duplicate ideas" is
#                    enforced at the storage layer, not by fragile app code)
#   source           where the idea came from: manual | reddit | google_trends...
#   niche            channel niche it belongs to
#   status           lifecycle: new -> ranked -> scripted -> produced -> published
#   score            AI ranking score, NULL until Phase 1 ranking runs
#   created_at       set once by SQLite itself
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT NOT NULL,
    title_normalized TEXT NOT NULL UNIQUE,
    source           TEXT NOT NULL DEFAULT 'manual',
    niche            TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'new'
                     CHECK (status IN ('new','ranked','scripted','produced','published','rejected')),
    score            REAL,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_topics_status ON topics(status);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection with our standard settings applied.

    `db_path` is overridable so tests can use a throwaway database
    instead of touching the real one — a key testing technique.
    """
    path = db_path or (settings.data_dir / "ytauto.db")
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    # Rows behave like dicts: row["title"] instead of row[1]. Readable code.
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(
    conn: sqlite3.Connection, table: str, column: str, decl: str
) -> None:
    """Tiny MIGRATION helper: add a column if the table doesn't have it yet.

    Why needed: `CREATE TABLE IF NOT EXISTS` does nothing when the table
    already exists — so adding a column to SCHEMA alone would only affect
    BRAND NEW databases. Existing databases (yours, with real topics in it!)
    must be altered in place. This is the simplest form of what production
    teams do with tools like Alembic: evolve the schema without losing data.
    """
    columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
        log.info("Migration: added column %s.%s", table, column)


def init_db(db_path: Path | None = None) -> None:
    """Create tables if missing, then apply migrations. Idempotent."""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
        # --- migrations (each one idempotent, in the order they were added) ---
        _ensure_column(conn, "topics", "rank_reason", "TEXT")   # Milestone 3
    log.info("Database initialized")
