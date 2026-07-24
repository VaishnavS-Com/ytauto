"""Assemble voiceover parts + slides into one MP4.

THE CORE IDEA — pairing by contract
-----------------------------------
Milestones 5 and 6 both split the script with the SAME split_into_parts,
so voiceover part_index N and slide part_index N describe the same moment.
`pair_parts` joins them and VALIDATES the contract (same count, files
actually on disk) before any expensive rendering starts. Fail fast:
discovering a missing slide 4 minutes into an encode is misery.

RENDERING (MoviePy 2.x)
-----------------------
For each pair: ImageClip(slide).with_duration(audio.duration).with_audio()
— the slide shows for EXACTLY as long as its narration (the whole reason
we made per-part audio). Gentle fade in/out per part = simple transitions.
Optional background music is looped and mixed quietly under everything.
MoviePy drives FFmpeg (bundled via imageio-ffmpeg) to encode H.264 + AAC —
the codecs YouTube expects.

The actual MoviePy work lives in ONE function (_render_moviepy) that
build_video takes as an injectable parameter — same dependency-injection
pattern as the LLM and TTS, so tests never render real video.
(Subtitles/captions come in a later milestone via Whisper.)
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ytauto.config import settings
from ytauto.logging_setup import get_logger
from ytauto.repositories import (
    asset_repository,
    video_repository,
    voiceover_repository,
)
from ytauto.repositories import topic_repository
from ytauto.tts.voiceover_generator import _get_script_by_id

log = get_logger(__name__)

FADE = 0.3          # seconds of fade in/out per part
MUSIC_VOLUME = 0.08  # background music must stay far under narration


class VideoError(Exception):
    """Video assembly failed (missing parts, broken files, encode error)."""


def pair_parts(voice_rows, asset_rows) -> list[tuple[Path, Path]]:
    """PURE-ish: join audio and slides on part_index, validating the contract.

    Returns ordered [(audio_path, image_path), ...]. Raises VideoError on
    any mismatch — BEFORE rendering starts.
    """
    slides = {row["part_index"]: Path(row["file_path"]) for row in asset_rows}
    if not voice_rows:
        raise VideoError("No voiceover parts — run generate_voiceover first")
    if len(slides) != len(voice_rows):
        raise VideoError(
            f"Contract broken: {len(voice_rows)} audio parts but "
            f"{len(slides)} slides — regenerate visuals"
        )

    pairs = []
    for row in voice_rows:
        audio = Path(row["file_path"])
        image = slides.get(row["part_index"])
        if image is None:
            raise VideoError(f"No slide for part {row['part_index']}")
        if not audio.exists():
            raise VideoError(f"Audio file missing on disk: {audio}")
        if not image.exists():
            raise VideoError(f"Slide file missing on disk: {image}")
        pairs.append((audio, image))
    return pairs


def _render_moviepy(
    pairs: list[tuple[Path, Path]],
    out_path: Path,
    music_path: Path | None = None,
) -> float:
    """The only function that imports MoviePy. Returns video duration (s)."""
    from moviepy import (
        AudioFileClip,
        CompositeAudioClip,
        ImageClip,
        afx,
        concatenate_videoclips,
        vfx,
    )

    clips = []
    for audio_path, image_path in pairs:
        audio = AudioFileClip(str(audio_path))
        clip = (
            ImageClip(str(image_path))
            .with_duration(audio.duration)
            .with_audio(audio)
            .with_effects([vfx.FadeIn(FADE), vfx.FadeOut(FADE)])
        )
        clips.append(clip)

    video = concatenate_videoclips(clips, method="chain")

    if music_path is not None and music_path.exists():
        music = (
            AudioFileClip(str(music_path))
            .with_effects([afx.AudioLoop(duration=video.duration),
                           afx.MultiplyVolume(MUSIC_VOLUME)])
        )
        video = video.with_audio(CompositeAudioClip([video.audio, music]))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    video.write_videofile(
        str(out_path),
        fps=24,
        codec="libx264",       # H.264 — what YouTube wants
        audio_codec="aac",
        logger=None,           # MoviePy's bar spams logs; ours suffice
    )
    duration = video.duration
    video.close()
    return duration


def build_video(
    script_id: int,
    music_path: Path | None = None,
    render: Callable[..., float] = _render_moviepy,
    videos_root: Path | None = None,
    db_path: Path | None = None,
) -> int:
    """Full assembly for one script. Returns the videos-table row id.

    On success the TOPIC advances to 'produced' — the lifecycle milestone
    the whole pipeline has been building toward since Milestone 1.
    """
    script = _get_script_by_id(script_id, db_path=db_path)
    if script is None:
        raise VideoError(f"Script id {script_id} not found")

    voice_rows = voiceover_repository.get_parts(script_id, db_path=db_path)
    asset_rows = asset_repository.get_assets(script_id, kind="slide",
                                             db_path=db_path)
    pairs = pair_parts(voice_rows, asset_rows)   # validate BEFORE rendering

    out_path = (videos_root or settings.data_dir / "videos") / f"script_{script_id}.mp4"
    log.info("Rendering %d parts -> %s", len(pairs), out_path.name)
    duration = render(pairs, out_path, music_path)

    if not out_path.exists() or out_path.stat().st_size == 0:
        raise VideoError("Encoder produced no output file")  # trust but verify

    video_id = video_repository.save_video(
        script_id, str(out_path), duration, db_path=db_path)
    topic_repository.update_status(script["topic_id"], "produced",
                                   db_path=db_path)
    log.info("Video %d complete: %.1fs", video_id, duration)
    return video_id
