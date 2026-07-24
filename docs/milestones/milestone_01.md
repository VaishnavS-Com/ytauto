# Milestone 1 — The Database Layer (Phase 1 begins)

## 1. Goal

Give the system a permanent memory: a SQLite database that stores every
video idea, enforces "no duplicates" at the storage level, and tracks each
idea's journey from `new` to `published`. By the end you can add and list
topics from the command line, and 12 tests pass.

## 2. Theory

**Why a database instead of a JSON/CSV file?** Files break under exactly the
conditions automation creates: two writes at once corrupt the file, a crash
mid-write loses everything, and "find all unranked topics" means loading and
scanning the whole file yourself. A database gives you transactions (all-or-
nothing writes), constraints (rules the data can never violate), and queries.

**Why SQLite specifically?** It's a real production database that lives in
one file, ships inside Python (stdlib `sqlite3`), needs zero setup, and costs
nothing. Perfect for a single-machine pipeline. If we ever outgrow it, the
repository pattern (below) means only one folder of code changes.

**Schema design decisions in `topics`:**

- `id INTEGER PRIMARY KEY AUTOINCREMENT` — every row gets a permanent unique
  number; every other table we add later (scripts, videos, analytics) will
  point at topics via this id. That's relational design.
- `title_normalized TEXT UNIQUE` — THE key decision. Duplicate prevention is
  enforced by the database itself, not by app code that someone might forget
  to call. Insert a duplicate → SQLite refuses → we catch it gracefully.
- `status CHECK (status IN (...))` — the lifecycle (`new → ranked → scripted
  → produced → published`, plus `rejected`) is a state machine, and the DB
  rejects any state not on the list. Typos become loud errors, not silent
  corruption.
- `score REAL` nullable — NULL means "not ranked yet". NULL is information.
- An index on `status` — the query we'll run most ("give me all `new`
  topics") stays fast even at 100k rows.

**The Repository pattern.** `topic_repository.py` is the only file allowed
to write SQL for the topics table. Everything else calls plain functions:
`add_topic()`, `list_topics()`. Benefits: SQL in one place, testable in
isolation, swappable storage. This is clean architecture in miniature —
layers, with dependencies pointing inward.

**SQL injection (API security lesson #1).** Never build queries with
f-strings. `f"INSERT ... VALUES ('{title}')"` executes attacker-controlled
text as SQL. Parameterized queries (`VALUES (?, ?)` + a tuple of values)
make the database treat input strictly as data. Non-negotiable habit.

## 3. Folder structure (new files)

```
src/ytauto/
├── database.py                  ← connection + schema + init_db()
└── repositories/
    ├── __init__.py
    └── topic_repository.py      ← all SQL for the topics table
scripts/
└── topics_cli.py                ← argparse CLI: add / list
tests/
└── test_topic_repository.py     ← 7 new tests, isolated via tmp_path
data/
└── ytauto.db                    ← created on first run (git-ignored)
```

## 4. Architecture

```
 topics_cli.py          (later: topic collector, ranker, ...)
        │                        │
        ▼                        ▼
 ┌─────────────────────────────────────┐
 │  repositories/topic_repository.py   │   plain functions, no SQL leaks out
 └──────────────────┬──────────────────┘
                    ▼
 ┌─────────────────────────────────────┐
 │  database.py                        │   one way to connect, one schema
 └──────────────────┬──────────────────┘
                    ▼
              data/ytauto.db
```

Rule: arrows only point downward. The CLI never imports sqlite3; the
repository never prints to the screen. Each layer has one job.

## 5. Beginner explanation

The database is a filing cabinet with a strict clerk. You hand the clerk an
idea card; the clerk checks "do I already have this card?" (UNIQUE
constraint) and refuses copies. Each card carries a stamp showing where it
is in its life: new, ranked, scripted, produced, published. You never open
the cabinet yourself — you always go through the clerk (the repository).
And the clerk either files your whole request or none of it (transactions):
no half-filed cards even if the power goes out mid-filing.

## 6–7. Code (read in this order, comments are the lesson)

1. `src/ytauto/database.py` — schema, `get_connection`, idempotent `init_db`
2. `src/ytauto/repositories/topic_repository.py` — parameterized queries,
   expected-error handling (`IntegrityError` → duplicate → return `None`)
3. `scripts/topics_cli.py` — argparse subcommands, dispatch pattern
4. `tests/test_topic_repository.py` — fixtures, `tmp_path`, isolated DBs

**Why each tool:** `sqlite3` (stdlib — zero deps, production-grade),
`argparse` (stdlib — free `--help`, standard CLI pattern),
pytest fixtures (fresh DB per test = trustworthy tests).

## 8. Common mistakes

1. **Building SQL with f-strings.** Injection. Always `?` placeholders.
2. **`except Exception:` around everything.** We catch ONLY
   `IntegrityError` (expected: duplicates). Unexpected errors must crash
   loudly during development. Silent failure is worse than a crash.
3. **Testing against the real database.** Tests then depend on leftover
   data and destroy real data. `tmp_path` gives every test a throwaway DB.
4. **Dedup in Python instead of the schema.** "Check then insert" has a
   race condition (two processes check simultaneously, both insert). The
   UNIQUE constraint cannot be raced.
5. **Forgetting `with` on connections.** Without the context manager, an
   exception can leave a transaction half-open and lock the file.
6. **String statuses scattered everywhere.** Ours are constrained by CHECK;
   later we'll promote them to a Python Enum too.

## 9. Exercises

1. **Drive the CLI.** `python scripts/topics_cli.py add "How do neural
   networks learn?"` then add 4 more ideas for the tech/AI niche, then
   `python scripts/topics_cli.py list`. Add one of them AGAIN with
   different capitalization — watch the duplicate get refused.
2. **Run the tests**: `pytest -v` — 12 passed (5 config + 7 repository).
   Read the `-v` output and match each test name to what it proves.
3. **Look inside the cabinet.** `python -c "import sqlite3; con =
   sqlite3.connect('data/ytauto.db'); [print(r) for r in
   con.execute('SELECT id, title, status FROM topics')]"` — you're reading
   raw rows, no repository. Now say in one sentence why the rest of the app
   should NOT do this.
4. **Write one new repository function** `delete_topic(topic_id, db_path=None)
   -> bool` in `topic_repository.py` (mirror `update_status` — `DELETE FROM
   topics WHERE id = ?`, return `rowcount > 0`). Write one test for it:
   add → delete → `count_topics() == 0`. `pytest` → 13 passed.
5. **Thinking exercise:** we'll later store generated scripts. Should they
   go in a new `scripts` table with a `topic_id` column, or as extra columns
   on `topics`? Pick one and defend it in 2–3 sentences. (Hint: one topic
   might get several script drafts.)
6. **Commit and push** with a message describing WHY this layer exists.

## 10. Next milestone

**Milestone 2 — the trending-topic collector.** First real automation:
fetch trending tech questions/posts from free public sources (RSS feeds,
Reddit's public JSON), through a proper HTTP client with timeouts, retries,
and error handling, and watch the database fill itself. Also: replacing the
`sys.path` hack with a proper editable install (`pip install -e .`).
