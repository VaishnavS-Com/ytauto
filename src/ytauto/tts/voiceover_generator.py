"""Turn a stored script into per-part MP3 files.

WHY PER-PART AUDIO, NOT ONE BIG MP3?
------------------------------------
The video builder (Phase 6) will show different visuals for the hook, each
chapter, and the CTA. If narration is one long file, syncing visuals means
guessing timestamps. One file per part makes sync trivial: part N's visual
lasts exactly as long as part N's audio. Design decisions ripple forward —
we're making Phase 6 easy from Phase 3.

FAILURE POLICY: all-or-nothing again (same reasoning as scripts — half a
voiceover can't be used). If any part fails, we delete the files and rows
already produced for this script, then raise. Re-running is always safe:
existing parts for the script are cleared first (idempotent regeneration).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ytauto.config import settings
from ytauto.logging_setup import get_logger
from ytauto.repositories import script_repository, voiceover_repository
from ytauto.tts.edge_client import TTSError, synthesize

log = get_logger(__name__)


def split_into_parts(script: dict) -> list[tuple[str, str]]:
    """PURE: script dict -> ordered (part_name, text) pairs.

    Body sections were joined with blank lines in Milestone 4; we split on
    the same separator. Contract between milestones, in code.
    """
    parts: list[tuple[str, str]] = [("hook", script["hook"])]
    sections = [s.strip() for s in script["body"].split("\n\n") if s.strip()]
    for i, section in enumerate(sections, start=1):
        parts.append((f"section_{i:02d}", section))
    parts.append(("cta", script["cta"]))
    return parts


def generate_voiceover(
    script_id: int,
    synth: Callable[..., Path] = synthesize,
    audio_root: Path | None = None,
    db_path: Path | None = None,
) -> list[Path]:
    """Synthesize every part of one script. Returns the audio file paths."""
    # Find the script (via its topic-agnostic id).
    script = _get_script_by_id(script_id, db_path=db_path)
    if script is None:
        raise TTSError(f"Script id {script_id} not found")

    out_dir = (audio_root or settings.data_dir / "audio") / f"script_{script_id}"
    parts = split_into_parts(script)

    # Idempotent regeneration: clear previous attempt for this script.
    voiceover_repository.delete_parts(script_id, db_path=db_path)

    written: list[Path] = []
    try:
        for index, (name, text) in enumerate(parts):
            path = out_dir / f"{index:02d}_{name}.mp3"
            synth(text, path, settings.tts_voice)
            voiceover_repository.save_part(
                script_id, index, name, str(path), settings.tts_voice,
                db_path=db_path,
            )
            written.append(path)
    except TTSError:
        # All-or-nothing: undo everything from this attempt, then re-raise.
        log.error("Voiceover failed for script %d — rolling back %d parts",
                  script_id, len(written))
        voiceover_repository.delete_parts(script_id, db_path=db_path)
        for path in written:
            path.unlink(missing_ok=True)
        raise

    log.info("Voiceover complete for script %d: %d parts in %s",
             script_id, len(written), out_dir)
    return written


def _get_script_by_id(script_id: int, db_path: Path | None = None) -> dict | None:
    from ytauto.database import get_connection

    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT topic_id FROM scripts WHERE id = ?", (script_id,)
        ).fetchone()
    if row is None:
        return None
    for draft in script_repository.get_scripts_for_topic(
        row["topic_id"], db_path=db_path
    ):
        if draft["id"] == script_id:
            return draft
    return None
