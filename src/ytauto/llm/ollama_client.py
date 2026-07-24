"""Client for a locally running Ollama server.

WHAT IS OLLAMA? A free program that downloads and runs open LLMs (Llama,
Gemma, Mistral...) on YOUR machine and exposes them over a tiny local web
API at http://localhost:11434. No API key, no cost, no data leaving your
laptop. We talk to it with plain HTTP POSTs — the same skill as any API.

WHY JSON MODE? LLMs produce prose by default; prose is unparseable. Passing
`"format": "json"` makes Ollama constrain the model so output is always
valid JSON. Structured output is THE key technique for using LLMs inside
pipelines — the difference between a chatbot and a system component.
"""

from __future__ import annotations

import json

from ytauto.config import settings
from ytauto.http_client import FetchError, fetch_json, post_json
from ytauto.logging_setup import get_logger

log = get_logger(__name__)


class LLMError(Exception):
    """The LLM could not produce a usable answer (server down, bad output...)."""


def is_available() -> bool:
    """Health check: is Ollama running and is our model pulled?"""
    try:
        tags = fetch_json(f"{settings.ollama_url}/api/tags", retries=1, timeout=5)
    except FetchError:
        return False
    models = [m.get("name", "") for m in tags.get("models", [])]
    # "llama3.2:3b" should match "llama3.2:3b" exactly or as a prefix.
    return any(name.startswith(settings.ollama_model) for name in models)


def generate_json(prompt: str, temperature: float = 0.2) -> dict:
    """Send a prompt, get back a parsed JSON dict.

    Low temperature (0.2): we want consistent scoring, not creativity.
    (For script WRITING in Phase 2 we'll turn temperature up.)
    """
    try:
        response = post_json(
            f"{settings.ollama_url}/api/generate",
            {
                "model": settings.ollama_model,
                "prompt": prompt,
                "format": "json",       # constrain output to valid JSON
                "stream": False,        # one complete answer, not chunks
                "options": {"temperature": temperature},
            },
        )
    except FetchError as exc:
        raise LLMError(
            f"Ollama unreachable at {settings.ollama_url}. "
            "Is it running? Start it, or install from https://ollama.com, "
            f"then: ollama pull {settings.ollama_model}"
        ) from exc

    raw = response.get("response", "")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        # Even JSON mode can occasionally emit garbage (e.g. empty string).
        log.error("Model returned unparseable output: %.200r", raw)
        raise LLMError("Model output was not valid JSON") from exc


def generate_text(prompt: str, temperature: float = 0.7) -> str:
    """Send a prompt, get back plain prose (no JSON constraint).

    Added in Milestone 4 for script WRITING: constraining creative prose
    to JSON hurts its quality, and higher temperature (0.7) gives the
    varied, natural writing a narration script needs.
    """
    try:
        response = post_json(
            f"{settings.ollama_url}/api/generate",
            {
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature},
            },
        )
    except FetchError as exc:
        raise LLMError(
            f"Ollama unreachable at {settings.ollama_url}. Is it running?"
        ) from exc

    text = (response.get("response") or "").strip()
    if not text:
        raise LLMError("Model returned empty text")
    return text
