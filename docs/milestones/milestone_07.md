# Milestone 7 — Video Assembly (Phase 6): the MP4

## 1. Goal

One command joins every voiceover part with its slide, adds fades and
optional background music, and encodes a YouTube-ready MP4 (H.264 + AAC).
The topic's lifecycle reaches `produced` — the status we defined back in
Milestone 1 finally gets used. You will watch a video your system made.

## 2. Theory

**Pairing by contract.** Voiceover and visuals were both split with the
same `split_into_parts`, so part_index N in both tables describes the same
moment. `pair_parts` joins them and validates EVERYTHING (counts match,
files exist on disk) before rendering starts. Fail fast matters more than
ever here because rendering is the most expensive step in the pipeline —
discovering a missing slide 4 minutes into an encode is misery.

**MoviePy in one paragraph.** MoviePy is a Python wrapper around FFmpeg
(the universal media engine — it downloads automatically on first run via
imageio-ffmpeg). Building blocks: `ImageClip` (a still shown for a
duration), `AudioFileClip`, `.with_duration()/.with_audio()` to bind them,
effects like `FadeIn/FadeOut`, `concatenate_videoclips` to chain parts,
and `write_videofile` to encode. Our core trick: each slide's duration IS
its narration's duration — the entire reason Milestone 5 made per-part
audio. No timestamp math anywhere.

**Audio mixing.** Background music is looped to the video's length
(`AudioLoop`) and multiplied down to 8% volume (`MultiplyVolume`), then
layered with narration via `CompositeAudioClip`. Music should be felt,
not heard. (Copyright: only use tracks licensed for reuse — YouTube's
Audio Library is the safe free source.)

**Codecs.** H.264 video + AAC audio in an MP4 container is YouTube's
preferred diet: universally decodable, hardware-accelerated everywhere.
FPS is 24 — still slides don't benefit from more.

**Testing strategy: don't unit-test the encoder.** `_render_moviepy` is
the ONLY function that imports MoviePy, and build_video takes it as an
injectable parameter (the same DI pattern as LLM/TTS). Tests use a fake
renderer and cover everything around it: validation, fail-fast, DB rows,
lifecycle. The real encoder is verified by an integration run — your
exercise 2. Knowing what NOT to unit-test is part of testing skill.
Note also the "liar renderer" test: build_video re-checks that the output
file actually exists — never trust a subsystem's return value alone.

## 3. Folder structure (new)

```
src/ytauto/video/
├── __init__.py
└── video_builder.py         ← pair_parts, _render_moviepy, build_video
src/ytauto/repositories/video_repository.py
scripts/build_video.py        ← CLI (--script-id, --music)
tests/test_video_builder.py   ← 7 tests, fake renderer
data/videos/script_<id>.mp4   ← the product
```
Changed: `database.py` (videos table), requirements/pyproject (moviepy).

## 4. Architecture

```
 build_video.py (--script-id, --music)
        ▼
 video_builder.build_video()
        │ voiceover parts ─┐
        │ slide assets ────┴─► pair_parts()   ← validate contract FIRST
        │                          │
        │                    [(audio, image), ...] in order
        ▼                          ▼
     render( pairs )  ──────► _render_moviepy()      (or a test fake)
        │                     ImageClip + AudioFileClip per part
        │                     fades, concat, music mix, H.264 encode
        ▼
 videos row  +  topic status → 'produced'
```

## 5. Beginner explanation

The editing room. Every scene arrives as a poster (slide) and a voice take
(audio) with matching labels. The editor first checks the labels line up —
refusing to start if scene 3's poster is missing (fail fast). Then each
poster is filmed for exactly as long as its take plays, scenes are taped
together with gentle fades, quiet music is laid underneath, and the
projector-ready reel (MP4) goes in the can. The producer stamps the
project folder "PRODUCED".

## 6–7. Code (read in this order)

1. `video/video_builder.py` — pair_parts validation, the MoviePy function,
   injectable renderer, output verification
2. `tests/test_video_builder.py` — fake renderer, the liar-renderer test
3. `repositories/video_repository.py`
4. `scripts/build_video.py`

**Why MoviePy** (vs raw ffmpeg commands): readable Python instead of
inscrutable CLI flag strings; we keep full FFmpeg power underneath. Raw
ffmpeg is worth learning later for performance tuning.

## 8. Common mistakes

1. **Rendering before validating inputs** — expensive failure. Check
   everything cheap first.
2. **Guessing slide durations** — bind them to audio durations; that's
   what per-part audio was for.
3. **Music at narration volume** — 8% or lower; it's texture, not content.
4. **Using copyrighted music** — instant Content ID claim; YouTube Audio
   Library only.
5. **Unit-testing the encoder** — slow, brittle, tests FFmpeg not your
   code. Fake it; integration-test the real thing once.
6. **Trusting the renderer's return value** — verify the file exists and
   is non-empty. (The liar-renderer test exists for this.)
7. **Forgetting `.close()` on clips** — leaks file handles; matters when
   the scheduler runs this daily.

## 9. Exercises

1. `pip install -r requirements.txt` (moviepy) → `pytest` → 60 passed.
2. **THE RUN:** `python scripts/build_video.py --script-id 2`
   (first run downloads FFmpeg ~80 MB; encoding a ~3-min video takes a
   few minutes on CPU). Then watch `data/videos/script_2.mp4` START TO
   FINISH. Note every moment that feels wrong — pacing, voice, slides,
   transitions. That list is gold; bring it.
3. **Add music.** Download one calm track from YouTube Audio Library
   (studio.youtube.com → Audio Library), save as `data/music/calm.mp3`,
   rebuild with `--music data/music/calm.mp3`. Compare with/without.
4. **Write one test:** `pair_parts` must raise VideoError when a SLIDE
   file (not audio) is deleted from disk — mirror the existing missing-
   file test. → 61 passed.
5. **Thinking:** encoding takes minutes and re-runs happen. The videos
   table keeps every render, but old MP4 files pile up on disk. Propose a
   cleanup policy (2-3 sentences): what would you delete, when, and what
   must NEVER be deleted automatically?
6. Commit + push, update PROJECT_STATE.md (Phase 6 core ✅ — B-roll,
   zooms, and captions are enhancement passes coming later).

## 10. Next milestone

**Milestone 8 — the full pipeline + captions.** Two parts: (a) one
`run_pipeline.py` command that chains collect → rank → script → voice →
visuals → video end-to-end with proper logging between stages — your
first taste of true automation; (b) burned-in captions via faster-whisper
(free, CPU-friendly): transcribe each audio part, overlay word-timed
subtitles on the slides. After that: thumbnails (Phase 7), SEO (Phase 8),
upload (Phase 9).
