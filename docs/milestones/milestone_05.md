# Milestone 5 — Voiceover with Edge TTS (Phase 3)

## 1. Goal

One command turns a stored script into a folder of MP3 files — hook, one
per section, CTA — spoken by a free neural voice, recorded in a new
`voiceovers` table. Play `00_hook.mp3` and hear your channel speak.

## 2. Theory

**Edge TTS.** Microsoft's read-aloud neural voices, exposed by the
`edge-tts` Python package: near-human quality, no API key, no cost.
Tradeoff: synthesis happens on Microsoft's servers, so it needs internet.
The gateway pattern (`tts/edge_client.py`, one file that owns the
dependency) means swapping to offline Coqui TTS later touches one file.

**Async Python, first contact.** `edge-tts` is an async library — its
functions are `async def` and must be `await`ed inside an event loop.
Async exists so a program can make progress while waiting on I/O. Our
batch pipeline doesn't need concurrency, so we bridge with
`asyncio.run(...)` inside a plain sync function. Recognizing "this library
is async, I need a bridge" is an everyday professional skill; full async
pipelines come later if we ever need parallel synthesis.

**Per-part audio is a Phase 6 gift.** One MP3 per part means the video
builder can sync visuals per part with zero timestamp guessing: visual N
lasts exactly as long as audio N. We're designing forward.

**Idempotent regeneration + rollback.** Re-running clears old parts first
(safe to regenerate with a new voice), and any mid-run failure deletes the
files AND rows already written — the unit of value is the complete
voiceover, so the unit of failure is too. Note the rollback cleans TWO
stores (filesystem + database): keeping them consistent is why "databases
hold facts, filesystems hold media, the DB row points at the file" is the
standard pattern.

**Trust but verify (media edition).** A TTS call can "succeed" yet write a
0-byte file. `edge_client` checks size > 0 — the same never-trust-output
posture as `parse_verdict`, applied to audio.

## 3. Folder structure (new)

```
src/ytauto/
├── tts/
│   ├── __init__.py
│   ├── edge_client.py           ← synthesize(), TTSError, async bridge
│   └── voiceover_generator.py   ← split_into_parts(), generate_voiceover()
├── repositories/voiceover_repository.py
scripts/generate_voiceover.py
tests/test_voiceover.py           ← 5 tests, fake synth, zero network
data/audio/script_<id>/           ← 00_hook.mp3 ... NN_cta.mp3
```
Changed: `database.py` (voiceovers table), `config.py`/`.env.example`
(TTS_VOICE), requirements/pyproject (edge-tts).

## 4. Architecture

```
 generate_voiceover.py (CLI, --script-id)
        ▼
 tts/voiceover_generator.generate_voiceover()
        │ split_into_parts()  hook | section_01.. | cta   (PURE)
        │ delete_parts()      ← idempotent regeneration
        │ for each part:
        │    synth() ──────────► tts/edge_client.synthesize()
        │    save_part()          (or a test fake!)         │
        │                                            asyncio.run bridge
        │ on TTSError: delete rows + files, re-raise        ▼
        ▼                                             Microsoft servers
 data/audio/script_<id>/*.mp3  +  voiceovers rows (path, voice, order)
```

## 5. Beginner explanation

Your script goes to a recording studio. The narrator records each scene as
its own take (per-part files), labeled and numbered, and the studio logbook
(voiceovers table) records where every take is stored and who voiced it.
If the narrator loses their voice mid-session, the studio shreds the
incomplete session entirely — no half-recorded episodes on the shelf — and
you simply book another session (retry is always safe).

## 6–7. Code (read in this order)

1. `tts/edge_client.py` — async bridge, lazy import, 0-byte check
2. `tts/voiceover_generator.py` — splitting contract, rollback across
   filesystem AND database
3. `repositories/voiceover_repository.py` — save/get/delete parts
4. `tests/test_voiceover.py` — the fake-synth trick; rollback test
5. `scripts/generate_voiceover.py` — CLI

**Why edge-tts** (vs Coqui offline, gTTS): best quality-per-effort at zero
cost; Coqui needs heavy local models (slow on your CPU), gTTS sounds
robotic. Voice is config (`TTS_VOICE`), not code.

## 8. Common mistakes

1. **Calling async functions without an event loop** — `await` outside
   `async def` is a SyntaxError; forgetting `asyncio.run` gives you an
   un-awaited coroutine that silently does nothing.
2. **One giant MP3** — makes Phase 6 sync guesswork. Split at natural
   boundaries.
3. **Storing audio bytes in SQLite** — databases hold facts and paths;
   filesystems hold media.
4. **Trusting the file exists because no exception was raised** — verify
   size > 0.
5. **Rollback that cleans the DB but leaves orphan files** (or vice
   versa) — two stores must stay consistent.
6. **Hard-coding the voice** — it's channel identity; keep it in config so
   ten channels (the end goal!) can each have their own.

## 9. Exercises

1. **Install and test:** `pip install -r requirements.txt` (gets edge-tts),
   then `pytest` → 44 passed — before any real synthesis.
2. **Hear your channel.** `python scripts/generate_voiceover.py --script-id 2`
   (the RAG script). Play the files in order. Verdict: would you watch a
   video narrated by this voice?
3. **Casting call.** List voices with:
   `edge-tts --list-voices | findstr en-`
   Pick 2 alternatives (try en-US-GuyNeural, en-IN-NeerjaNeural), set
   `TTS_VOICE` in `.env`, regenerate (idempotent — safe), compare. Pick
   your channel's permanent voice.
4. **Write one test:** `split_into_parts` on a script whose body has NO
   blank lines (single section) must return exactly
   `["hook", "section_01", "cta"]`. → 45 passed.
5. **Thinking:** synthesis of 6 parts is sequential, ~2s each. Async could
   run them concurrently. What's the risk of firing 6 concurrent requests
   at a free service — and which Milestone 2 concept protects against the
   consequence? (2–3 sentences.)
6. **Commit + push**, update PROJECT_STATE.md (Phase 3 ✅).

## 10. Next milestone

**Milestone 6 — Phase 4: images.** Every part gets a visual: AI-generated
images via free APIs/local Stable Diffusion where feasible on CPU, plus a
programmatic slide renderer with Pillow (title cards, key-point slides) as
the reliable workhorse. An `assets` table, and the LLM writes image
prompts from each section's text — content driving visuals automatically.
