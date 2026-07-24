"""Generate a complete video script with a PROMPT CHAIN.

WHY A CHAIN, NOT ONE BIG PROMPT?
--------------------------------
Ask a 3B model for "a complete 8-minute script with hook, chapters and CTA"
in one go and you get mush: it loses the plan halfway through. Small models
do much better with small jobs. So we decompose, exactly like Milestone 3's
lesson (classification is easier than judgment → here: a section is easier
than an essay):

    Step 1  PLAN     (JSON, temp 0.4)  → title + 4 chapter titles
    Step 2  SECTIONS (prose, temp 0.7) → one call per chapter, ~150 words
    Step 3  HOOK+CTA (JSON, temp 0.8)  → the most creative parts last,
                                          written with the full plan known

Each step's output feeds the next prompt — that's the "chain". Notice the
temperatures: facts/structure cold, creativity warm. And notice both LLM
functions are injected parameters again, so every test runs modelless.

QUALITY GUARDRAIL: YouTube's 2026 "inauthentic content" policy punishes
template-y, low-variation output. The chain design fights this: every
video's structure comes from a fresh plan, and prose sections are written
against that plan — not one reusable madlib.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ytauto.config import settings
from ytauto.llm.ollama_client import LLMError, generate_json, generate_text
from ytauto.logging_setup import get_logger
from ytauto.repositories import script_repository, topic_repository

log = get_logger(__name__)

PLAN_PROMPT = """You are planning a faceless YouTube explainer video for a \
tech/AI channel (curious general audience, 5-8 minutes, narrated slideshow).

TOPIC: {topic}

Design the video with LASER FOCUS on this specific topic — do not widen
it into a survey of related concepts. All 4 chapters must directly explain
the stated topic, nothing adjacent.

Answer with ONLY this JSON:
{{"title": "<clear, honest, searchable video title - no clickbait>",
"chapters": ["<chapter 1 title>", "<chapter 2 title>",
"<chapter 3 title>", "<chapter 4 title>"]}}"""

SECTION_PROMPT = """You are writing narration for a faceless YouTube \
explainer video titled "{title}".

Full chapter plan: {chapters}

Write ONLY the narration for the chapter: "{chapter}"

Rules:
- around 150 words, spoken style: short sentences, no headings, no lists
- explain like a friendly expert; one concrete example or analogy
- include at least one real number, statistic, or named example
- VARY your sentence openings — never start two consecutive sentences
  with the same word or phrase (especially avoid repeating "So", "This",
  "That", "Now", "And")
- do not greet the viewer, do not say "in this chapter", just narrate
- do not repeat other chapters' content"""

HOOK_CTA_PROMPT = """A faceless YouTube explainer video titled "{title}" \
covers these chapters: {chapters}

Write its opening hook and closing call-to-action. Answer with ONLY this JSON:
{{"hook": "<2-3 spoken sentences that make a curious viewer stay. Open with
a surprising fact, a number, or a tension — NOT 'Did you know', NOT
'Today we', NOT 'Welcome back'. No channel name.>",
"cta": "<1-2 spoken sentences asking to subscribe for more explainers,
friendly not pushy>"}}"""


def parse_plan(data: dict) -> tuple[str, list[str]]:
    """Validate step 1 output. Same defensive posture as parse_verdict."""
    title = str(data.get("title", "")).strip()
    chapters = data.get("chapters")
    if not title or not isinstance(chapters, list) or not (3 <= len(chapters) <= 6):
        raise LLMError(f"Bad plan: {data!r}")
    chapters = [str(c).strip() for c in chapters if str(c).strip()]
    if len(chapters) < 3:
        raise LLMError(f"Bad plan, too few usable chapters: {data!r}")
    return title, chapters


def parse_hook_cta(data: dict) -> tuple[str, str]:
    hook = str(data.get("hook", "")).strip()
    cta = str(data.get("cta", "")).strip()
    if not hook or not cta:
        raise LLMError(f"Bad hook/cta: {data!r}")
    return hook, cta


def generate_script(
    topic_id: int | None = None,
    gen_json: Callable[..., dict] = generate_json,
    gen_text: Callable[..., str] = generate_text,
    db_path: Path | None = None,
) -> int:
    """Run the full chain for one topic. Returns the saved script id.

    Picks the best ranked topic when topic_id is None. On success the
    topic advances to 'scripted'. On ANY LLM failure we raise — nothing
    half-done is saved, and the topic stays 'ranked' for a retry.
    """
    if topic_id is None:
        row = topic_repository.best_ranked_topic(db_path=db_path)
        if row is None:
            raise LLMError("No ranked topics available — run rank_topics first")
        topic_id, topic_title = row["id"], row["title"]
    else:
        match = [r for r in topic_repository.list_topics(db_path=db_path)
                 if r["id"] == topic_id]
        if not match:
            raise LLMError(f"Topic id {topic_id} not found")
        topic_title = match[0]["title"]

    log.info("Generating script for topic %d: %r", topic_id, topic_title)

    # --- Step 1: plan (cold) -------------------------------------------------
    title, chapters = parse_plan(
        gen_json(PLAN_PROMPT.format(topic=topic_title), temperature=0.4)
    )
    log.info("Plan: %r with %d chapters", title, len(chapters))

    # --- Step 2: one section per chapter (warm) -------------------------------
    sections = []
    for chapter in chapters:
        text = gen_text(
            SECTION_PROMPT.format(title=title, chapters=chapters, chapter=chapter),
            temperature=0.7,
        )
        sections.append(text)
        log.info("Section %r: %d words", chapter, len(text.split()))
    body = "\n\n".join(sections)

    # --- Step 3: hook + CTA (warmest, written knowing the whole plan) ---------
    hook, cta = parse_hook_cta(
        gen_json(HOOK_CTA_PROMPT.format(title=title, chapters=chapters),
                 temperature=0.8)
    )

    # --- Persist, then advance the topic's lifecycle --------------------------
    script_id = script_repository.save_script(
        topic_id=topic_id, title=title, hook=hook, body=body, cta=cta,
        chapters=chapters, model=settings.ollama_model, db_path=db_path,
    )
    topic_repository.update_status(topic_id, "scripted", db_path=db_path)
    return script_id
