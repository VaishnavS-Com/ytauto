# PROJECT_STATE — ytauto (AI YouTube Automation System)

> Living document. Update after every milestone. If starting a new chat with
> an AI mentor, paste the "Resume prompt" at the bottom.

## The project brief (original goal)

Build a complete, modular, production-quality AI system that automates a
faceless YouTube channel using only free tools, as a mentored learning
project (milestone by milestone, with theory, code, exercises — no
shortcuts). Portfolio-worthy for placement interviews.

**Learner profile:** B.Tech AI & Data Science student, beginner–intermediate
Python, Windows laptop, 8–16 GB RAM, no GPU, Ollama not yet installed.

**Decisions made:**
- Project lives in `automation_progress/` (old web app archived in `_archive_webapp/`)
- Pacing: one milestone per session; exercises before advancing
- Channel niche: tech / AI explainers
- No GPU → small local models (Gemma 2B / Phi-3 class) + free API fallbacks

## The 11 phases (roadmap)

| Phase | What | Status |
|---|---|---|
| 1 | Find trending topics, multi-source collection, topic DB, dedupe, AI ranking | ✅ COMPLETE |
| 2 | LLM generation: title, script, hook, CTA, chapters, description, tags, keywords | ⬜ |
| 3 | Voiceover via free TTS (Edge TTS / Coqui) | ⬜ |
| 4 | AI image generation (free/local) | ⬜ |
| 5 | B-roll: generate or auto-download copyright-free clips | ⬜ |
| 6 | Final video assembly: subtitles, transitions, zooms, music, captions (MoviePy/FFmpeg) | ⬜ |
| 7 | AI thumbnail | ⬜ |
| 8 | SEO optimization | ⬜ |
| 9 | Auto-upload via YouTube API | ⬜ |
| 10 | Analytics collection (CTR, watch time, retention, subs) → DB | ⬜ |
| 11 | Analytics-driven self-improvement loop | ⬜ |
| — | Then: free cloud deployment, scheduling, scaling to 10 channels, monetization | ⬜ |

**Tech stack:** Python, SQLite, MoviePy, FFmpeg, OpenCV, Whisper, Ollama
(Llama/Gemma/Mistral), Stable Diffusion, Coqui TTS, Edge TTS, Pillow,
FastAPI, Gradio, YouTube API, Git.

## Milestones completed

### ✅ Milestone 0 — Foundation (docs/milestones/milestone_00.md)
- venv, Git + GitHub, src layout, `.env` secrets pattern
- `src/ytauto/config.py` — frozen Settings dataclass, single source of truth
- `src/ytauto/logging_setup.py` — console + rotating file logging
- `scripts/verify_setup.py`, 5 passing tests
- Exercises done: debug-level experiment, rotation theory, `MAX_VIDEOS_PER_DAY` setting + test

### ✅ Milestone 1 — Database layer (docs/milestones/milestone_01.md)
- `src/ytauto/database.py` — SQLite schema (`topics` table), idempotent `init_db`
- `topics` schema: UNIQUE normalized title (dedupe at DB level), status
  lifecycle `new→ranked→scripted→produced→published` (+`rejected`) with CHECK,
  nullable `score`, status index
- `src/ytauto/repositories/topic_repository.py` — repository pattern,
  parameterized queries, IntegrityError → duplicate handling
- `scripts/topics_cli.py` — argparse CLI (add / list)
- 12 passing tests (throwaway DBs via tmp_path)

**Milestone 1 exercises — ✅ ALL DONE**
1. ✅ Drove the CLI, added 5 topics, watched duplicate get refused
2. ✅ `pytest -v` → 13 passed, matched each test to its purpose
3. ✅ Peeked at raw rows; explained why the app shouldn't bypass the repository
4. ✅ Wrote `delete_topic()` + test → 13 passed
5. ✅ Thinking: separate `scripts` table (one topic → many drafts)
6. ✅ Committed + pushed

### ✅ Milestone 2 — Trending-topic collector (docs/milestones/milestone_02.md)
- `pyproject.toml` — proper editable install (`pip install -e .`), killed `sys.path` hack
- `src/ytauto/http_client.py` — timeouts, exponential-backoff retries, `FetchError`
- `src/ytauto/collectors/` — RSS (5 feeds) + Reddit (public JSON), relevance filter
- `scripts/collect_topics.py` — one-command idempotent pipeline
- 20 passing tests (zero network calls)

**Milestone 2 exercises — ✅ ALL DONE**
1. ✅ Installed properly, ran collection (32 topics), proved idempotency
2. ✅ Killed sys.path hack from all 5 files, 20 tests still pass
3. ✅ Tuned relevance filter — replaced broad "model" with specific AI terms
4. ✅ Added MIT Tech Review feed (one line = one new source)
5. ✅ Wrote case-insensitivity test → 20 passed
6. ✅ Thinking: recency + title length as cheap RSS quality signals
7. ✅ Committed + pushed

### ✅ Milestone 3 — AI topic ranking (docs/milestones/milestone_03.md) — PHASE 1 COMPLETE
- Ollama installed, llama3.2:3b running locally (~4s/topic on CPU)
- `src/ytauto/llm/ollama_client.py` — JSON mode, health check, LLMError
- `src/ytauto/ranking/topic_ranker.py` — prompt template, verdict validation,
  dependency injection (fake LLMs in tests), per-topic failure isolation
- Schema migration: `_ensure_column` added `rank_reason` to live DB
- Prompt iterated 3x: vague judgment → strict rules (model dodged them) →
  **LLM classifies (`dated_news`), code enforces the score cap** — key lesson
- Junk-prefix filter in rss_collector (policy in code at collection too)
- 31 passing tests; 39 topics ranked with clean bimodal 4/8 separation

## Next up

**Milestone 4 — Phase 2 begins: script generation.** Top-ranked topic →
full video package (hook, script, CTA, chapters) via multi-step prompt
chain with the local LLM; new `scripts` table (one topic → many drafts);
higher temperature for creative generation; status `ranked` → `scripted`.

## Key habits established

- Commit small + often; check `git status` for `.env` before every commit
- Secrets only in `.env` (git-ignored); `.env.example` documents settings
- Every module: `from ytauto.logging_setup import get_logger` — no `print` in library code
- All SQL stays in `repositories/`; always `?` placeholders, never f-strings
- Every milestone ships with tests; tests use throwaway DBs, never real data
- Network code: always set timeouts, retry with backoff, isolate failures
- Separate fetch (network) from parse (pure logic) — test parse, mock fetch
- `pip install -e .` for imports; never use `sys.path` hacks

## Resume prompt (paste into a new chat)

"You are my university-style mentor for an ongoing project. Read
PROJECT_STATE.md and docs/milestones/ in my automation_progress folder for
full context. We are building an AI-powered faceless-YouTube automation
system in phases, one milestone per session, with theory + code + exercises,
production-quality, free tools only. Milestones 0–2 are complete
(foundation; SQLite topic database; trending-topic collector with HTTP
client, RSS/Reddit sources, 20 tests). Check the 'exercises' status in
PROJECT_STATE.md, review my exercise work if pending, then continue with the
next milestone listed under 'Next up'. Never skip steps, teach as you build."
