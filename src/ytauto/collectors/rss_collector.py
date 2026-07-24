"""Collect topic ideas from tech news RSS feeds.

WHAT IS RSS? A decades-old, still-everywhere standard: sites publish their
latest articles as a machine-readable XML file. No API key, no login, no
cost — the ideal first data source.

WHY feedparser? RSS in the wild is messy (three format versions, broken
XML, weird encodings). feedparser has parsed all of it for 20 years.
Hand-rolling XML parsing here would be reinventing a wheel badly.
"""

from __future__ import annotations

import feedparser

from ytauto.collectors.relevance import is_relevant
from ytauto.http_client import FetchError, fetch_text
from ytauto.logging_setup import get_logger

log = get_logger(__name__)

# Free, no-key tech feeds. Adding a source = adding one line.
FEEDS = {
    "rss:techcrunch": "https://techcrunch.com/feed/",
    "rss:theverge": "https://www.theverge.com/rss/index.xml",
    "rss:arstechnica": "https://feeds.arstechnica.com/arstechnica/index",
    "rss:hackernews": "https://hnrss.org/frontpage",
    "rss:mittechreview": "https://www.technologyreview.com/feed/",
}

JUNK_PREFIXES = ("The Download:", "Show HN:", "Launch HN:")
def parse_feed(xml_text: str, source: str) -> list[dict]:
    """PURE function: XML text in, idea dicts out. No network. Testable."""
    parsed = feedparser.parse(xml_text)
    ideas = []
    for entry in parsed.entries:
        title = getattr(entry, "title", "").strip()
        if title and is_relevant(title) and not title.startswith(JUNK_PREFIXES):
            ideas.append({"title": title, "source": source})
    return ideas


def collect(feeds: dict[str, str] | None = None) -> list[dict]:
    """Fetch every feed and return all relevant ideas.

    ERROR-HANDLING CHOICE: one dead feed must NOT kill the whole run —
    we catch FetchError PER FEED, log it, and continue with the others.
    Partial success beats total failure in automation.
    """
    ideas: list[dict] = []
    for source, url in (feeds or FEEDS).items():
        try:
            xml_text = fetch_text(url)
        except FetchError:
            log.error("Skipping unreachable feed: %s", source)
            continue
        found = parse_feed(xml_text, source)
        log.info("%s: %d relevant ideas", source, len(found))
        ideas.extend(found)
    return ideas
