# Milestone 8 — Grounding: Research Before Writing

## 1. Goal

Kill hallucinations at the source. Before any script is written, the
system gathers verified notes (Wikipedia summaries chosen by the LLM),
caches them on the topic, injects them into every writing prompt, and
forbids facts from anywhere else. Regenerate the RAG script and watch the
fake definition disappear.

## 2. Theory

**The incident.** Our first real video opened with "RAG stands for
Recurrent Attention Graph" — false — plus an invented statistic. Two
causes: (1) a 3B model writing from parametric memory *fabricates* when it
doesn't know; (2) our own prompt rule "include at least one real number"
*ordered* it to produce specifics it didn't have. We built a confident-
nonsense machine and gave it a quota.

**The cure is retrieval.** Fetch trusted text about the topic, put it in
the prompt, and restrict factual claims to that text. This is Retrieval-
Augmented Generation — the very concept our video lied about, now
implemented in our pipeline. The general principle: **an LLM should
transform trusted input, not be trusted as a source.** You've seen this
before in miniature (the ranker classifies, code decides); grounding is
the same idea for content.

**Why Wikipedia?** Free, keyless, high-editorial-quality summaries, a
stable REST API, and its opening extracts are exactly "the agreed-upon
basics" — which is what an explainer video needs. Later sources can be
added (the RSS article that spawned the topic, arXiv abstracts) — the
notes format already carries source attribution per block.

**The research flow.** LLM proposes 1-3 encyclopedia terms (a small
classification-ish job → temperature 0.2) → wiki search picks pages →
summary extracts, capped at 900 chars each → formatted into a NOTES block.
Notes are cached in `topics.research_notes` (a migration, like rank_reason)
so a topic is researched once, not on every draft.

**Layered fallbacks, never a crash.** Bad term extraction → fall back to
searching the raw title. Wiki finds nothing → empty notes → the prompt
switches to NO_NOTES_FALLBACK: *no numbers, no names, concepts only*.
Research is best-effort; honesty is mandatory either way.

**Prompt changes worth reading side by side (git diff!):** the "include a
real number" rule is GONE — replaced by "facts only from notes; analogies
you may create (illustrations, not facts)". That distinction — the model
may invent *explanatory devices* but never *claims* — is the fine line
grounded content walks.

## 3. Folder structure (new)

```
src/ytauto/research/
├── __init__.py               ← the incident, memorialized
└── wiki_research.py          ← terms prompt, wiki API, format_notes
tests/test_research.py         ← 9 tests, fake LLM + fake wiki
```
Changed: `script_generator.py` (Step 0 research, grounded prompts),
`topic_repository.py` (+set_research_notes), `database.py` (migration),
`tests/test_script_generator.py` (fake_gather injected).

## 4. Architecture

```
 generate_script()
        │
        ├─ Step 0  RESEARCH (new)
        │     cached notes on topic? ── yes ─► use them
        │     no ─► gather_notes():
        │            LLM terms (t=0.2) ─► wiki search ─► summaries
        │            └─ failures degrade gracefully → fewer/empty notes
        │     empty? ─► NO_NOTES_FALLBACK (strict no-specifics mode)
        │     else  ─► cache in topics.research_notes
        │
        ├─ Step 1  PLAN     ← notes injected
        ├─ Step 2  SECTIONS ← notes injected + "facts ONLY from notes"
        └─ Step 3  HOOK+CTA (unchanged — creative, not factual)
```

## 5. Beginner explanation

The scriptwriter used to work from memory and, when memory ran dry, made
things up with total confidence (the worst colleague). Now a librarian
runs ahead: for each topic they photocopy the relevant encyclopedia pages
and staple them to the assignment. New studio rule: anything stated as
fact must be on the photocopies; if it isn't there, explain the idea in
your own words without pretending to know specifics. Analogies remain the
writer's own — those are teaching tools, not claims.

## 6–7. Code (read in this order)

1. `research/wiki_research.py` — the flow, fallback layering, source
   attribution in notes
2. `script_generator.py` — Step 0, both grounded prompts, the fallback
   block; run `git diff` on this file and read the prompt changes
3. `tests/test_research.py` — note `test_grounding_rules_reach_the_prompts`:
   it pins the LESSON itself into the test suite, so no future refactor
   can silently drop the grounding rules

**Why Wikipedia's REST API** (vs the `wikipedia` pip package): two plain
GETs through our existing http_client — timeouts, retries, User-Agent all
inherited; no new dependency for two URL calls.

## 8. Common mistakes

1. **Asking a small model for specifics without sources** — you'll get
   confident fiction. Our own "include a number" rule caused the incident.
2. **Letting research failure kill generation** — best-effort with a
   strict fallback beats a crashed pipeline.
3. **Re-researching on every draft** — cache on the topic (and note the
   provenance question: stale notes are a real thing; see exercise 5).
4. **Dumping 10k chars of source into the prompt** — small models drown;
   cap each extract (900 chars) and the term count (3).
5. **Forbidding everything** — banning analogies too makes scripts dry
   and robotic. Facts restricted, illustrations free.
6. **Grounding the hook** — the hook is curiosity, not claims; it stays
   creative. (But it must not contradict the notes — exercise 4.)

## 9. Exercises

1. `pytest` → 70 passed (61 + 9 research).
2. **The redemption arc.** Reset topic 2's script state and regenerate
   with grounding:
   `python -c "from ytauto.repositories.topic_repository import update_status; update_status(2, 'ranked')"`
   then `python scripts/generate_script.py --topic-id 2`. Open the new
   markdown export next to the old one. Is the RAG definition correct
   now? Are there any invented numbers left? This diff is the milestone.
3. **Inspect the notes:** `python -c "from ytauto.repositories.topic_repository import list_topics; print([r['research_notes'] for r in list_topics() if r['id']==2][0])"`
   — read what the librarian fetched. Would YOU trust these notes?
4. **Write one test:** gather_notes must pass `temperature=0.2` (not the
   default) to the LLM for term extraction — a spy fake that records the
   kwarg. → 71 passed.
5. **Thinking:** research_notes are cached forever, but facts age (a
   model's "latest version" changes). Propose a staleness policy in 2-3
   sentences: when should notes be re-gathered, and what column would
   that need?
6. Then regenerate voiceover + visuals + video for the new script and
   watch the corrected video. Commit + push, update PROJECT_STATE.md.

## 10. Next milestone

**Milestone 9 — attractiveness: motion + captions.** Ken Burns zoom/pan
on every slide, AI images as backgrounds with dark overlays (text stays
crisp on top), and word-timed burned-in captions via faster-whisper.
The regenerated, now-truthful RAG video gets the visual treatment — and
becomes the first candidate for actual upload.
