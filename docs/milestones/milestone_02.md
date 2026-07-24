# Milestone 2 — The Trending-Topic Collector (first real automation)

## 1. Goal

Run one command and watch the database fill itself with fresh, relevant,
deduplicated video ideas from live sources (tech RSS feeds + Reddit) — with
production-grade networking: timeouts, retries with exponential backoff, and
per-source failure isolation. Also: proper packaging (`pip install -e .`)
kills the `sys.path` hack.

## 2. Theory

**Editable installs.** `pyproject.toml` describes our package; `pip install
-e .` links (not copies) `src/ytauto` into the environment. Imports work
from anywhere, code edits apply instantly. This is how every professional
Python project is set up.

**Networks fail — plan for it.** Three defenses, all in `http_client.py`:

- *Timeout* (10s): `requests.get` with no timeout can hang forever. An
  unattended pipeline that hangs is worse than one that crashes — it does
  nothing and tells nobody.
- *Retries with exponential backoff* (2s → 4s → 8s): most network failures
  are transient. Waiting longer each time gives a struggling server room to
  recover — retrying instantly can make an overloaded server worse.
- *Failure isolation*: one dead feed is logged and skipped; the other
  sources still deliver. Partial success beats total failure.

**Fetch/parse separation (the testability trick).** Every collector splits
network I/O (`collect`) from pure logic (`parse_*`). Pure functions get
tested with tiny hand-made samples — fast, deterministic, no network in
tests, ever. If you remember one design idea from this milestone, this is it.

**The collector contract.** Every collector returns `list[dict]` with keys
`title` and `source`. The pipeline doesn't know or care where ideas came
from. Adding a Google-Trends collector later = one new file, zero changes
elsewhere. Contracts are what "modular" actually means.

**Idempotency.** Running collection twice adds nothing twice — the UNIQUE
constraint from Milestone 1 absorbs re-seen topics. Safe re-runs are a core
property of reliable automation (schedulers WILL double-fire someday).

**Filter cheap before you filter smart.** The keyword relevance filter is
deliberately dumb. An LLM will re-rank topics in a later milestone, but LLM
calls are ~1000x more expensive than a string check — so the cheap filter
runs first and the smart one only sees survivors. That layered-filter
pattern is everywhere in production AI systems.

## 3. Folder structure (new)

```
pyproject.toml                       ← package definition (pip install -e .)
src/ytauto/
├── http_client.py                   ← fetch_text/fetch_json + FetchError
└── collectors/
    ├── __init__.py                  ← the contract, documented
    ├── relevance.py                 ← keyword niche filter
    ├── rss_collector.py             ← 4 tech feeds, no keys needed
    └── reddit_collector.py          ← public .json endpoints, no keys
scripts/collect_topics.py            ← run everything, store, report
tests/test_collectors.py             ← 6 tests, zero network
```

## 4. Architecture

```
 scripts/collect_topics.py
      │  ideas = rss.collect() + reddit.collect()
      ▼
 ┌───────────────┐   ┌──────────────────┐
 │ rss_collector │   │ reddit_collector │     each: fetch → parse → filter
 └──────┬────────┘   └────────┬─────────┘
        │    both use          │
        ▼                      ▼
 ┌─────────────────────────────────────┐
 │ http_client.py  (timeout/retry/UA)  │ ← only file that imports requests
 └─────────────────────────────────────┘
        then ideas flow down into
 ┌─────────────────────────────────────┐
 │ topic_repository.add_topic()        │ ← UNIQUE constraint eats duplicates
 └─────────────────────────────────────┘
```

## 5. Beginner explanation

Imagine hiring two scouts. One reads tech newspapers (RSS), one hangs out
in discussion clubs (Reddit). Each morning both bring back headline lists.
A doorman (relevance filter) turns away anything off-topic. The clerk from
Milestone 1 files what remains, refusing duplicates. If one scout's route
is blocked, the other still reports — and sending the scouts out twice
changes nothing, because the clerk already has those cards.

## 6–7. Code (read in this order)

1. `pyproject.toml` — what packaging is, why editable installs
2. `src/ytauto/http_client.py` — timeout, backoff, custom exception, User-Agent
3. `src/ytauto/collectors/relevance.py` — word-boundary matching (why "ai" ≠ "air")
4. `src/ytauto/collectors/rss_collector.py` — pure parse + isolated fetch
5. `src/ytauto/collectors/reddit_collector.py` — defensive `.get()` parsing
6. `scripts/collect_topics.py` — the pipeline run
7. `tests/test_collectors.py` — sample-data testing, no network

**Why each library:** `requests` (the Python HTTP standard; clean API,
proper exceptions), `feedparser` (20 years of handling broken real-world
RSS; hand-parsing XML here would be reinventing a wheel badly).

## 8. Common mistakes

1. **`requests.get(url)` with no timeout** — can hang forever. Always set one.
2. **Retrying instantly in a tight loop** — hammers a struggling server;
   backoff exists for their benefit and yours.
3. **One `try/except` around the whole run** — one dead feed then kills all
   sources. Isolate failures at the smallest sensible unit.
4. **Testing with live network calls** — slow, flaky, breaks offline. Split
   fetch from parse; test parse.
5. **Substring keyword matching** — "ai" matching "air travel" quietly fills
   your database with garbage. Word boundaries matter.
6. **Trusting external data shapes** — Reddit posts CAN miss fields. `.get()`
   with defaults everywhere; never `data["key"]` on data you don't control.
7. **No User-Agent** — anonymous default agents get blocked or rate-limited.

## 9. Exercises

1. **Install properly.** In your venv: `pip install -r requirements.txt`
   then `pip install -e .` — then run `pytest` from the project root:
   19 passed. Then `python scripts/collect_topics.py` — watch your database
   fill with real, current headlines. Run it AGAIN immediately: mostly
   "duplicates skipped". Explain to yourself why that's the designed behavior.
2. **Kill the hack.** Delete the `sys.path.insert(...)` lines (and their
   `sys`/`Path` imports if now unused) from `verify_setup.py`,
   `topics_cli.py`, and all three test files. `pytest` again — still 19
   passed. That's the editable install doing its job.
3. **Tune the doorman.** Look at `topics_cli.py list` output. See noise?
   Missing things you'd want? Adjust `AI_KEYWORDS`, re-run collection,
   compare. (Real data work is exactly this loop.)
4. **Add a source.** Add one line to `FEEDS` — e.g. MIT Tech Review:
   `https://www.technologyreview.com/feed/` — recollect, and check `list`.
   One line = new source. That's the contract paying off.
5. **Write one test:** `is_relevant` must be case-insensitive —
   `is_relevant("OPENAI DROPS NEW MODEL")` is True. Add it, run pytest: 20.
6. **Thinking:** Reddit's `score` filters low-quality posts. What could be
   a similar cheap "quality signal" for RSS items, where there are no
   upvotes? (No right answer — 2–3 sentences.)
7. **Commit + push**, and tick this milestone off in PROJECT_STATE.md.

## 10. Next milestone

**Milestone 3 — AI enters the pipeline.** Install Ollama, pull a small
model that fits your no-GPU laptop (Gemma 2B / Phi-3-mini class), and build
the topic RANKER: the LLM scores each `new` topic for video-worthiness
(searchability, evergreen value, explainability) and writes `score` back to
the database — moving topics from `new` to `ranked`. Prompt engineering,
structured LLM output (JSON mode), and handling model failures gracefully.
