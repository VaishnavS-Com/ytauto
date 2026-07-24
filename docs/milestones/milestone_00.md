# Milestone 0 — Foundation: Environment, Git, Skeleton, Config, Logging

## 1. Goal

Before writing a single line of AI code, we build the foundation every
production system stands on: an isolated Python environment, version control,
a clean folder structure, centralized configuration, and real logging.
By the end you can run `python scripts/verify_setup.py` and `pytest` and both
succeed, with your work committed to Git.

## 2. Theory

**Virtual environments.** Python installs packages globally by default. Two
projects needing different versions of the same library then break each other.
A virtual environment (`venv`) is a private, per-project copy of Python.
Production rule: one project = one venv, always.

**Version control (Git).** Git records snapshots ("commits") of your project.
It lets you undo mistakes, understand why code changed, and prove your work to
interviewers. A repo with 200 small, well-messaged commits over months is
portfolio gold — it shows how you think.

**The src layout.** Application code lives in `src/ytauto/` instead of the
project root. Why: it forces you to *install/import* your package the same way
a user would, catching packaging bugs early, and it cleanly separates code
(`src/`) from tests, scripts, data, and docs. This layout is the modern Python
packaging standard.

**Configuration and secrets.** Hard-coding an API key in code and pushing to
GitHub is the classic beginner disaster — bots scrape GitHub for keys within
minutes. The professional pattern is: secrets in a git-ignored `.env` file →
loaded into environment variables → read by one `config.py` → imported
everywhere else. `.env.example` (committed, no real values) documents which
settings exist.

**Logging.** An automation pipeline runs unattended. When it fails at 3 AM,
`print()` output is gone; log files are your flight recorder. Python's
`logging` module gives you timestamps, severity levels (DEBUG < INFO <
WARNING < ERROR), per-module names, and file rotation so logs never fill
your disk.

## 3. Folder structure

```
automation_progress/           ← project root, also the Git repo root
├── src/
│   └── ytauto/                ← the Python package (all real code)
│       ├── __init__.py        ← marks the folder as a package
│       ├── config.py          ← settings, loaded once, imported everywhere
│       └── logging_setup.py   ← one function: get_logger(__name__)
├── scripts/
│   └── verify_setup.py        ← runnable entry point for this milestone
├── tests/
│   └── test_config.py         ← pytest suite (4 tests)
├── docs/milestones/           ← these lesson files
├── data/                      ← generated data (git-ignored, .gitkeep only)
├── logs/                      ← app.log lands here (git-ignored)
├── _archive_webapp/           ← your old web app, preserved, git-ignored
├── .env.example               ← committed template
├── .env                       ← YOUR secrets — you create this, never committed
├── .gitignore
├── requirements.txt
└── README.md
```

## 4. Architecture

```
              ┌────────────────────┐
              │  .env  (secrets)   │
              └─────────┬──────────┘
                        │ loaded once by python-dotenv
                        ▼
              ┌────────────────────┐
              │ config.py          │  single source of truth
              │  → settings object │  (frozen dataclass)
              └───┬────────────┬───┘
                  │            │
                  ▼            ▼
        ┌──────────────┐  ┌──────────────────┐
        │ logging_setup│  │ every future     │
        │  get_logger()│  │ module (Phase 1+)│
        └──────────────┘  └──────────────────┘
```

Dependency direction matters: everything depends on `config`, `config`
depends on nothing inside the project. Later phases (topic finder, script
generator, video builder) will each be a module under `src/ytauto/` importing
`settings` and `get_logger` the exact same way. That uniformity IS the
modularity you asked for.

## 5. Beginner explanation

Think of the project as a restaurant kitchen being set up before opening day.
The venv is your own set of knives no other chef touches. Git is the logbook
recording every change to the menu. `config.py` is the recipe binder — one
place everyone checks, so no two cooks use different salt amounts. Logging is
the CCTV camera: when something burns overnight, you replay the tape.
Nothing gets cooked today — but nothing cooked later works without this.

## 6–7. Code (with comments)

The code is already in place — read these files top to bottom, comments
included; they are the lesson:

1. `src/ytauto/config.py` — dataclass, `frozen=True`, `pathlib`, dotenv
2. `src/ytauto/logging_setup.py` — handlers, formatter, rotation, the
   run-once guard
3. `scripts/verify_setup.py` — entry-point pattern, `if __name__ == "__main__"`
4. `tests/test_config.py` — pytest basics, testing immutability

**Why each library was chosen:**

| Library | Why this one |
|---|---|
| `python-dotenv` | The de-facto standard for `.env` loading; tiny, zero magic. |
| `pathlib` (stdlib) | Object-oriented paths that work on Windows AND Linux. String paths with `\` break the moment you deploy to a cloud server (Linux) — which we will. |
| `logging` (stdlib) | Built in, thread-safe, industry standard. Fancy loggers (loguru) exist, but employers expect you to know stdlib logging. |
| `pytest` | Simplest test syntax in Python (plain `assert`), massive ecosystem, the industry default. |

## 8. Common mistakes

1. **Committing `.env`.** Once a secret touches Git history it is compromised
   forever, even if you delete it in the next commit. Our `.gitignore` guards
   this — verify with `git status` before your first commit: `.env` must NOT
   appear.
2. **Skipping the venv** and installing into global Python. Works today,
   collides with another project next month.
3. **`import config` from the wrong directory.** Always run commands from the
   project root. The `sys.path` lines in scripts/tests handle the rest (we
   replace that hack with a proper editable install in a later milestone).
4. **Using `print()` for status messages.** From today, every module logs.
5. **Mutable global config** — code silently changing settings at runtime.
   `frozen=True` makes that a loud error instead of a silent bug.
6. **Giant first commit.** Commit small and often, with messages that say
   *why*, not just *what*.

## 9. Exercises (do these before the next session)

1. **Set up and verify.** On your laptop, from the project folder:
   `python -m venv .venv` → `.venv\Scripts\activate` →
   `pip install -r requirements.txt` → `copy .env.example .env` →
   `python scripts/verify_setup.py` → `pytest` (4 tests must pass).
2. **First Git commits.** Install Git if needed (git-scm.com), then:
   `git init`, `git add .`, check `git status` (confirm `.env` absent!),
   `git commit -m "Milestone 0: project skeleton, config, logging"`.
   Then create a free GitHub account, make a repo, and push.
3. **Break it on purpose.** Set `LOG_LEVEL=DEBUG` in `.env`, add a
   `log.debug("...")` line to `verify_setup.py`, run it, and confirm the
   debug line appears. Set it back to INFO and confirm it disappears.
   This teaches you what log levels actually do.
4. **Prove rotation exists.** Read `logging_setup.py` and answer in your own
   words: what happens when `app.log` reaches 1 MB? Where do old logs go?
5. **Stretch:** add a new setting `MAX_VIDEOS_PER_DAY=1` to `.env.example`,
   `.env`, and `config.py` (as an `int` — careful: `os.getenv` returns
   strings!). Write one pytest for it.

## 10. Next milestone

**Milestone 1 — SQLite database layer + first real data.** We design the
`topics` table (database design: schemas, primary keys, uniqueness
constraints for duplicate prevention), write a small repository module with
full error handling, and store our first hand-entered video ideas. That sets
up Milestone 2, where the trending-topic collector starts filling the
database automatically.
