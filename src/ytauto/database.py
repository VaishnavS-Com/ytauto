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

-- Milestone 4: generated video scripts. One topic -> MANY script drafts
-- (the one-to-many design from Milestone 1's exercise 5). topic_id is a
-- FOREIGN KEY: the database refuses a script pointing at a topic that
-- doesn't exist — referential integrity, enforced by storage again.
CREATE TABLE IF NOT EXISTS scripts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id   INTEGER NOT NULL REFERENCES topics(id),
    title      TEXT NOT NULL,
    hook       TEXT NOT NULL,
    body       TEXT NOT NULL,
    cta        TEXT NOT NULL,
    chapters   TEXT NOT NULL,   -- JSON list of chapter titles
    model      TEXT NOT NULL,   -- which LLM wrote it (provenance!)
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_scripts_topic ON scripts(topic_id);

-- Milestone 5: voiceover audio. One script -> many PARTS (hook, one per
-- chapter section, cta), each its own mp3 file so Milestone 7+ can sync
-- visuals to each part independently. We store the PATH, not the audio:
-- databases hold facts, filesystems hold media. part_index preserves order.
CREATE TABLE IF NOT EXISTS voiceovers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id  INTEGER NOT NULL REFERENCES scripts(id),
    part_index INTEGER NOT NULL,
    part_name  TEXT NOT NULL,        -- hook | section_01.. | cta
    file_path  TEXT NOT NULL,
    voice      TEXT NOT NULL,        -- provenance, like scripts.model
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (script_id, part_index)   -- no duplicate parts per script
);

-- Milestone 6: visual assets. One row per (part, kind): every audio part
-- gets at least a rendered slide; optionally also an AI image. `meta`
-- stores the text/prompt that produced the visual (provenance again).
CREATE TABLE IF NOT EXISTS assets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id  INTEGER NOT NULL REFERENCES scripts(id),
    part_index INTEGER NOT NULL,
    kind       TEXT NOT NULL CHECK (kind IN ('slide', 'ai_image')),
    file_path  TEXT NOT NULL,
    meta       TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (script_id, part_index, kind)
);
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
    # SQLite ignores FOREIGN KEY constraints unless told otherwise (historic
    # quirk). Without this, a script could point at a deleted topic.
    conn.execute("PRAGMA foreign_keys = ON")
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
