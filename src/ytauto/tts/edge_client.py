"""Text-to-speech via Edge TTS (Microsoft's free neural voices).

WHY EDGE TTS? It uses the same neural voices as Microsoft Edge's
read-aloud feature: near-human quality, dozens of voices, completely free,
no API key. Tradeoff: it needs internet (voices run on Microsoft's
servers). Coqui TTS (offline) is the fallback if that ever becomes a
problem — the gateway pattern means swapping = editing this one file.

FIRST CONTACT WITH ASYNC PYTHON
-------------------------------
edge-tts is an async library: `await communicate.save(...)`. Async lets a
program do other work while waiting on the network. Our pipeline is a
simple sequential batch job though, so we wrap the async call in
`asyncio.run(...)` — one sync function the rest of the app calls without
caring. Bridging async libraries into sync code is an everyday skill.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from ytauto.config import settings
from ytauto.logging_setup import get_logger

log = get_logger(__name__)


class TTSError(Exception):
    """Speech synthesis failed (network down, bad voice name, empty audio)."""


async def _synthesize_async(text: str, out_path: Path, voice: str) -> None:
    import edge_tts  # lazy import: only needed when actually synthesizing

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def synthesize(text: str, out_path: Path, voice: str | None = None) -> Path:
    """Turn text into an MP3 file. Returns the path. Sync wrapper."""
    text = text.strip()
    if not text:
        raise TTSError("Cannot synthesize empty text")

    voice = voice or settings.tts_voice
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        asyncio.run(_synthesize_async(text, out_path, voice))
    except TTSError:
        raise
    except Exception as exc:  # edge-tts raises assorted network errors
        raise TTSError(f"TTS failed for {out_path.name}: {exc}") from exc

    # Trust but verify: an "successful" call can still produce a 0-byte file.
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise TTSError(f"TTS produced no audio for {out_path.name}")

    log.info("Synthesized %s (%d bytes, voice=%s)",
             out_path.name, out_path.stat().st_size, voice)
    return out_path
