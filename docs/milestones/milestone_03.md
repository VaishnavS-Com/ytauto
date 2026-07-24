# Milestone 3 — AI Topic Ranking (Ollama + a local LLM)

## 1. Goal

Install Ollama, run a small LLM entirely on your laptop, and let it judge
every collected topic: score 0–10 plus a one-line reason, written back to
the database, moving topics from `new` to `ranked`. Phase 1 of the project
is COMPLETE at the end of this milestone.

## 2. Theory

**Local LLMs and Ollama.** Ollama runs open models (Llama, Gemma, Mistral,
Qwen...) on your own machine and exposes them at `http://localhost:11434`
as a tiny web API. Free, unlimited, private. On a no-GPU laptop, a 3B-
parameter model in 4-bit quantization uses ~2–3 GB RAM and answers in
10–60 seconds. Slow — but ranking runs unattended, so latency is fine.
This is a real engineering tradeoff: cost (free) vs speed (slow) vs
quality (good enough for scoring).

**Quantization in one line:** model weights compressed from 16-bit to
4-bit numbers — ~4x smaller and faster, slightly less accurate; the reason
a 3B model fits in laptop RAM at all.

**Structured output (JSON mode).** The single most important technique for
putting LLMs inside pipelines. Prose answers can't be parsed reliably;
`"format": "json"` constrains generation so only valid JSON can come out.
Pipeline-grade LLM use = JSON in, JSON out, validated after.

**Never trust model output.** Even in JSON mode a model can return
`"score": "eight"`, a score of 42, or missing fields. `parse_verdict`
validates, coerces, clamps, and raises on garbage — the same defensive
posture we used for Reddit's JSON. To the pipeline, an LLM is just another
unreliable external service.

**Dependency injection (the testing star of this milestone).**
`rank_pending(generate=...)` takes the LLM function as a parameter. Real
runs use the Ollama call; tests pass fakes. That's how we test perfect
answers, malformed answers, and total model failure — in milliseconds,
with no model installed. Interviews love this pattern; so do teammates.

**Prompt engineering (see PROMPT_TEMPLATE):** role, explicit criteria,
calibration hints (news = low, evergreen questions = high), exact output
shape, and low temperature (0.2) because scoring needs consistency, not
creativity.

**Schema migration.** Adding `rank_reason` couldn't just go into SCHEMA —
`CREATE TABLE IF NOT EXISTS` ignores existing tables, and your DB already
holds real topics. `_ensure_column()` checks PRAGMA table_info and ALTERs
if needed: the simplest real migration. Production teams use tools like
Alembic; the principle is identical — evolve schema without losing data.

## 3. Folder structure (new)

```
src/ytauto/
├── llm/
│   ├── __init__.py
│   └── ollama_client.py       ← is_available(), generate_json(), LLMError
└── ranking/
    ├── __init__.py
    └── topic_ranker.py        ← prompt, verdict validation, rank_pending()
scripts/rank_topics.py          ← the run command (with --limit)
tests/test_ranker.py            ← 8 tests, zero model calls
```
Also changed: `http_client.py` (+post_json), `database.py` (+migration),
`topic_repository.py` (+set_rank), `config.py`/`.env.example` (+OLLAMA_*).

## 4. Architecture

```
 scripts/rank_topics.py ──── is_available()? ──> fail fast with fix steps
        │
        ▼
 ranking/topic_ranker.rank_pending(limit, generate)
        │   for each 'new' topic:
        │     build_prompt() ──> generate() ──> parse_verdict()
        │           │                │               │
        │         PURE        llm/ollama_client    PURE
        │                     (or a test fake!)
        ▼
 topic_repository.set_rank()  →  score + reason + status='ranked'
```

The LLM sits behind the same wall pattern as the DB (`database.py`) and
the network (`http_client.py`): one gateway file, swappable, mockable.

## 5. Beginner explanation

You've hired a (slightly eccentric) film critic who works from home for
free. For every idea card in the "new" tray, you hand them a strict scoring
form (the prompt). They fill in a number and one sentence (JSON). A clerk
double-checks the form — number actually a number? between 0 and 10? —
because the critic occasionally writes "eleven" or spills coffee on it
(validation). Checked forms get stapled to the card, which moves to the
"ranked" tray. If the critic doesn't answer the door, the card just stays
in "new" for tomorrow.

## 6–7. Code (read in this order)

1. `llm/ollama_client.py` — the API call, JSON mode, health check, LLMError
2. `ranking/topic_ranker.py` — THE file of this milestone: prompt design,
   validation, dependency injection, per-topic failure isolation
3. `database.py` diff — `_ensure_column` migration
4. `repositories/topic_repository.py` — `set_rank` (one atomic UPDATE)
5. `scripts/rank_topics.py` — fail-fast health check, run, leaderboard
6. `tests/test_ranker.py` — fake LLMs: happy, flaky, counting

**Why Ollama** (vs cloud APIs): zero cost at unlimited volume, no key to
leak, works offline; tradeoff is speed and model size. **Why llama3.2:3b**
as default: strong quality-per-RAM for CPU laptops; configurable in `.env`
— try others without touching code.

## 8. Common mistakes

1. **Parsing prose LLM output with string tricks.** Use JSON mode + validate.
2. **Trusting the JSON.** `data["score"]` might be `"eight"`. Validate types,
   clamp ranges, raise on garbage.
3. **Short timeouts for local models.** CPU inference is slow; 10s timeouts
   make everything "fail". We use 120s for POSTs to Ollama.
4. **One model failure killing the batch** — isolate per item; failed items
   stay `new` and retry next run for free.
5. **High temperature for scoring tasks** — same topic, wildly different
   scores. Low temperature for judgment, high for creativity.
6. **Editing SCHEMA and wondering why existing DBs don't change** — schema
   creation is not migration. `_ensure_column` is the difference.
7. **Testing "around" the LLM instead of injecting it** — if your code takes
   the model as a parameter, everything becomes testable.

## 9. Exercises

1. **Install Ollama.** Download from https://ollama.com (Windows installer),
   then in a terminal: `ollama pull llama3.2:3b` (~2 GB download). Sanity
   check: `ollama run llama3.2:3b "say hi in 5 words"` — first token is
   slow (model loading), that's normal. Exit with /bye.
2. **Run the tests first**: `pytest` → 28 passed — before Ollama is even
   involved. Let that sink in: the AI pipeline is fully tested without AI.
3. **Rank for real.** `python scripts/rank_topics.py --limit 10`. Watch the
   log, then study the leaderboard: do YOU agree with the model's scores?
   Find one you disagree with and read its reason.
4. **Tune the judge.** Improve PROMPT_TEMPLATE (e.g., penalize clickbait, or
   reward topics that suit narrated slideshows). Re-run on fresh topics.
   Compare. Prompt iteration IS development now.
5. **Write one test:** a fake LLM returning `{"score": 11, "reason": "!"}`
   must result in a stored score of exactly 10.0 (clamping proof, but this
   time through the full rank_pending flow, not just parse_verdict).
   `pytest` → 29 passed.
6. **Thinking:** we rank topics one per LLM call. Batching 10 titles into
   ONE prompt would be ~10x faster. What NEW failure modes would batching
   introduce? (2–3 sentences; think about what happens to the other 9 when
   one answer is malformed, and whether scores stay independent.)
7. **Commit + push**, update PROJECT_STATE.md (Phase 1: ✅ COMPLETE).

## 10. Next milestone

**Milestone 4 — Phase 2 begins: script generation.** The highest-ranked
topic becomes a full video package: hook, script, CTA, chapters — generated
by your local LLM with a multi-step prompt chain, stored in a new `scripts`
table (exactly the one-to-many design you defended in Milestone 1's
exercise). Longer generations, higher temperature, and the art of making
a 3B model write like it means it.
