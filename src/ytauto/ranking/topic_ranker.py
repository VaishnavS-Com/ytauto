"""Score topics for video-worthiness using an LLM.

PROMPT ENGINEERING NOTES (read the prompt below alongside these):
- We give the model a ROLE ("YouTube strategist") — grounds its judgment.
- We define EACH criterion explicitly — vague asks get vague scores.
- We show the EXACT output shape and nothing else — with JSON mode this
  yields machine-parseable output nearly every time.
- We ask for a one-line reason — costs little, and lets a human audit WHY
  the AI ranked something high (explainability matters in real systems).

DESIGN FOR TESTABILITY (same trick as fetch/parse in collectors):
`rank_pending` takes the LLM function as a PARAMETER (`generate`), with the
real Ollama call as default. Tests pass a fake function instead — so we can
test all the logic, including LLM failures, without any model installed.
This technique is called dependency injection. Simple, and it makes
"AI code" as testable as any other code.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ytauto.llm.ollama_client import LLMError, generate_json
from ytauto.logging_setup import get_logger
from ytauto.repositories import topic_repository as topics

log = get_logger(__name__)

PROMPT_TEMPLATE = """You are a YouTube content strategist for a faceless \
tech/AI explainer channel aimed at curious general viewers.

Score this video topic idea from 0 to 10 for overall video-worthiness:

TOPIC: {title}

Judge it on:
- searchability: will people search for or click this in the next months?
- evergreen: will it still get views in a year, or is it dated news?
- explainability: can it become a clear 5-8 minute explainer with visuals?
- originality: is it a fresh angle, or oversaturated?

Scoring rules (apply strictly, in order):
- If the topic is about one specific dated event, announcement, incident,
  or product launch: score it 4 or below, no exceptions.
- If the topic is a timeless question or concept a curious viewer might
  search any month of the year: score it 7 or above.
- Clickbait phrasing without substance: subtract 2.
- Use the full range, including odd numbers like 3, 5, 7.

Answer with ONLY this JSON, nothing else:
{{"dated_news": <true if this is about one specific recent event,
announcement, launch, or newsletter issue, else false>,
"score": <number 0-10>, "reason": "<one short sentence>"}}"""


def build_prompt(title: str) -> str:
    """PURE: title in, full prompt out. Testable without any model."""
    return PROMPT_TEMPLATE.format(title=title)


def parse_verdict(data: dict) -> tuple[float, str]:
    """PURE: validate the model's JSON. Never trust LLM output blindly.

    Models sometimes return score as a string ("7"), out of range (11),
    or omit fields. We normalize or raise — garbage must not reach the DB.
    """
    try:
        score = float(data["score"])
    except (KeyError, TypeError, ValueError) as exc:
        raise LLMError(f"Bad verdict, no usable score: {data!r}") from exc

    score = max(0.0, min(10.0, score))          # clamp into range
    if data.get("dated_news") is True:
        score = min(score, 4.0)                  # rule enforced in CODE
    reason = str(data.get("reason", "")).strip()[:300]
    return score, reason


def rank_pending(
    limit: int = 10,
    generate: Callable[[str], dict] = generate_json,
    db_path: Path | None = None,
) -> dict:
    """Rank up to `limit` topics with status 'new'. Returns run statistics.

    FAILURE POLICY: one bad LLM answer skips ONE topic (stays 'new', will
    be retried next run) — it never kills the whole batch. Same isolation
    principle as the collectors.
    """
    pending = topics.list_topics(status="new", db_path=db_path)[:limit]
    stats = {"ranked": 0, "failed": 0}

    for row in pending:
        try:
            verdict = generate(build_prompt(row["title"]))
            score, reason = parse_verdict(verdict)
        except LLMError as exc:
            log.error("Ranking failed for topic %d (%r): %s",
                      row["id"], row["title"], exc)
            stats["failed"] += 1
            continue

        topics.set_rank(row["id"], score, reason, db_path=db_path)
        stats["ranked"] += 1

    log.info("Ranking run: %(ranked)d ranked, %(failed)d failed", stats)
    return stats
