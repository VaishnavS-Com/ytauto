"""Gather grounding notes from Wikipedia (free, keyless, reliable).

Flow: LLM proposes encyclopedia search terms for the topic (a small
classification-style job it's good at) → Wikipedia search API finds pages
→ summary API returns vetted opening extracts → we format them into a
NOTES block for the script prompts.

Wikipedia REST endpoints used (no auth):
  search:  /w/rest.php/v1/search/page?q=<term>&limit=1
  summary: /api/rest_v1/page/summary/<title>

FAILURE POLICY: research is best-effort. A dead endpoint or a topic with
no wiki coverage yields FEWER or EMPTY notes — never a crash. The script
generator compensates: empty notes trigger the strictest no-numbers rule.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Callable

from ytauto.http_client import FetchError, fetch_json
from ytauto.llm.ollama_client import LLMError, generate_json
from ytauto.logging_setup import get_logger

log = get_logger(__name__)

TERMS_PROMPT = """A YouTube explainer video will be made about this topic:

{topic}

Which encyclopedia articles should the writer read first? Answer with ONLY
this JSON — 1 to 3 precise article titles (things, concepts, technologies;
not sentences):
{{"terms": ["<term 1>", "<term 2>"]}}"""

MAX_SUMMARY_CHARS = 900


def parse_terms(data: dict) -> list[str]:
    """PURE: validate the term list; 1-3 non-empty strings."""
    terms = data.get("terms")
    if not isinstance(terms, list):
        raise LLMError(f"Bad terms: {data!r}")
    cleaned = [str(t).strip() for t in terms if str(t).strip()]
    if not cleaned:
        raise LLMError(f"No usable terms: {data!r}")
    return cleaned[:3]


def fetch_wiki_summary(term: str) -> tuple[str, str] | None:
    """(page title, summary extract) for the best match, or None."""
    try:
        search = fetch_json(
            "https://en.wikipedia.org/w/rest.php/v1/search/page?q="
            + urllib.parse.quote(term) + "&limit=1",
            retries=2,
        )
        pages = search.get("pages", [])
        if not pages:
            return None
        title = pages[0]["title"]

        summary = fetch_json(
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + urllib.parse.quote(title),
            retries=2,
        )
        extract = (summary.get("extract") or "").strip()
        return (title, extract[:MAX_SUMMARY_CHARS]) if extract else None
    except (FetchError, KeyError) as exc:
        log.warning("Wiki lookup failed for %r: %s", term, exc)
        return None


def format_notes(summaries: list[tuple[str, str]]) -> str:
    """PURE: (title, extract) pairs -> the NOTES block for prompts."""
    if not summaries:
        return ""
    blocks = [f"[Source: Wikipedia — {title}]\n{extract}"
              for title, extract in summaries]
    return "\n\n".join(blocks)


def gather_notes(
    topic_title: str,
    gen_json: Callable[..., dict] = generate_json,
    fetch_summary: Callable[[str], tuple[str, str] | None] = fetch_wiki_summary,
) -> str:
    """Full research pass for one topic. Returns notes text ('' if nothing)."""
    try:
        terms = parse_terms(
            gen_json(TERMS_PROMPT.format(topic=topic_title), temperature=0.2)
        )
    except LLMError as exc:
        log.warning("Term extraction failed (%s) — falling back to raw title", exc)
        terms = [topic_title]

    summaries = []
    for term in terms:
        result = fetch_summary(term)
        if result is not None:
            summaries.append(result)
            log.info("Research: got summary for %r", result[0])

    notes = format_notes(summaries)
    if not notes:
        log.warning("Research found NOTHING for %r — script will be "
                    "generated in strict no-facts mode", topic_title)
    return notes
