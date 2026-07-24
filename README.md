# ytauto — AI-Powered YouTube Automation System

A fully modular, production-style pipeline that automates a faceless YouTube
channel (niche: tech / AI explainers) using free tools and local AI models.

Built milestone-by-milestone as a mentored learning project.

## Project status

| Milestone | Topic | Status |
|-----------|-------|--------|
| 0 | Environment, Git, project skeleton, config, logging | ✅ In progress |
| 1 | Phase 1 begins: trending-topic collector | ⏳ Next |

## Quick start (Windows)

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your local settings file
copy .env.example .env

# 4. Verify everything works
python scripts/verify_setup.py

# 5. Run the tests
pytest
```

## Structure

```
automation_progress/
├── src/ytauto/          # all application code (the package)
│   ├── config.py        # single source of truth for settings
│   └── logging_setup.py # project-wide logging
├── scripts/             # runnable entry points
├── tests/               # pytest test suite
├── data/                # generated data (git-ignored)
├── logs/                # log files (git-ignored)
├── docs/milestones/     # lesson notes for each milestone
├── .env.example         # documented settings template (committed)
└── .env                 # your real secrets (NEVER committed)
```

## Docs

Each milestone's full lesson lives in `docs/milestones/`.
