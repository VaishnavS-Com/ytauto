"""Collect topic ideas from Reddit — no API key needed.

Reddit exposes any listing as JSON by appending `.json` to its URL:
https://www.reddit.com/r/artificial/top.json?t=day&limit=25
Free and public, but be a good citizen: identify yourself (our http_client
sends a User-Agent) and don't hammer it (we fetch a few subreddits once a
day, far below any limit).

Reddit is a great idea source for a different reason than news feeds:
posts show what people are CURIOUS or CONFUSED about — and questions
("Why does ChatGPT make things up?") are ready-made explainer videos.
"""

from __future__ import annotations

from ytauto.collectors.relevance import is_relevant
from ytauto.http_client import FetchError, fetch_json
from ytauto.logging_setup import get_logger

log = get_logger(__name__)

SUBREDDITS = ["artificial", "MachineLearning", "technology", "ArtificialInteligence"]

# Skip low-engagement posts — score is a free quality signal.
MIN_SCORE = 50


def parse_listing(data: dict, source: str, min_score: int = MIN_SCORE) -> list[dict]:
    """PURE function: Reddit's JSON structure in, idea dicts out.

    The structure is data -> children -> [each has 'data' with title/score].
    We use .get() with defaults everywhere because external data can be
    missing fields — defensive parsing, never trust input you don't control.
    """
    ideas = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        title = (post.get("title") or "").strip()
        score = post.get("score", 0)
        if title and score >= min_score and is_relevant(title):
            ideas.append({"title": title, "source": source})
    return ideas


def collect(subreddits: list[str] | None = None) -> list[dict]:
    """Fetch top daily posts from each subreddit. Per-source error isolation."""
    ideas: list[dict] = []
    for sub in subreddits or SUBREDDITS:
        source = f"reddit:{sub}"
        url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=25"
        try:
            data = fetch_json(url)
        except FetchError:
            log.error("Skipping unreachable subreddit: %s", source)
            continue
        found = parse_listing(data, source)
        log.info("%s: %d relevant ideas", source, len(found))
        ideas.extend(found)
    return ideas
