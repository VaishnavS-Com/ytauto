"""One HTTP client for the whole system — with timeouts and retries.

WHY THIS FILE EXISTS
--------------------
The internet fails constantly: slow servers, dropped connections, rate
limits. Beginner code does `requests.get(url)` bare — which can hang
FOREVER (no default timeout!) or crash the pipeline on one bad response.
Production code always sets a timeout and retries transient failures with
increasing waits ("exponential backoff": 2s, 4s, 8s...) so a hiccup doesn't
kill an unattended 3 AM run.

Every module that needs the network uses fetch_text() / fetch_json().
Nobody else imports `requests` directly — same single-gateway idea as
database.py.
"""

from __future__ import annotations

import time

import requests

from ytauto.logging_setup import get_logger

log = get_logger(__name__)

# Sites block anonymous default user agents ("python-requests/2.31").
# Identifying yourself honestly is both polite and practical.
USER_AGENT = "ytauto/0.1 (educational project; contact: your-email@example.com)"

DEFAULT_TIMEOUT = 10  # seconds — never wait longer than this for a response


class FetchError(Exception):
    """Raised when a URL could not be fetched after all retries.

    A custom exception lets callers do `except FetchError` — handling
    network failure specifically, without accidentally swallowing bugs.
    """


def fetch_text(url: str, retries: int = 3, timeout: int = DEFAULT_TIMEOUT) -> str:
    """GET a URL and return its body as text. Retries transient failures."""
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": USER_AGENT},
            )
            # 4xx/5xx don't raise by default in requests — force it:
            response.raise_for_status()
            return response.text

        except requests.RequestException as exc:
            last_error = exc
            wait = 2 ** attempt  # 2s, 4s, 8s — exponential backoff
            log.warning(
                "Fetch failed (attempt %d/%d) for %s: %s — retrying in %ds",
                attempt, retries, url, exc, wait,
            )
            if attempt < retries:
                time.sleep(wait)

    log.error("Giving up on %s after %d attempts", url, retries)
    raise FetchError(f"Could not fetch {url}") from last_error


def fetch_json(url: str, retries: int = 3, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """GET a URL and parse the body as JSON."""
    import json

    return json.loads(fetch_text(url, retries=retries, timeout=timeout))
