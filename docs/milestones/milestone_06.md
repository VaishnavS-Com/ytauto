# Milestone 6 — Visuals: Slides + AI Images (Phase 4)

## 1. Goal

Every audio part gets a picture. One command renders clean 1920x1080
typographic slides for the whole script (LLM distills each section into a
headline), optionally garnished with free AI images, all recorded in an
`assets` table. After this milestone you have script + audio + visuals —
everything Phase 6's video builder needs.

## 2. Theory

**Reliable first, fancy second.** AI images are slow, occasionally absurd,
and famously bad at rendering text. Typographic slides are instant,
deterministic, and always on-brand — real explainer channels live on them.
So slides are the guaranteed baseline for EVERY part; AI images are
optional garnish. This shapes the failure policy (below).

**Two different failure policies in one function — on purpose.** A failed
slide aborts the run (a hole in the video is unacceptable); a failed AI
image is logged and skipped (garnish). Strictness should match how
essential the output is. Compare: voiceover = all-or-nothing, ranking =
per-item skip, visuals = both at once, each justified.

**LLM as content distiller.** SLIDE_TEXT_PROMPT turns 150 words of
narration into `headline / support / image_prompt` — structured
extraction, temperature 0.3 (a distillation is a fact-job, not a
creative-job). Note `parse_slide_text` TRUNCATES an overlong headline
instead of rejecting: a too-long headline is a nuisance, a failed part is
a hole. Validators should match the cost of being wrong.

**Pillow fundamentals.** Canvas (`Image.new`), drawing (`ImageDraw`),
typography (`ImageFont.truetype` with a cross-platform candidate list),
and pixel-measured word wrapping — character-count wrapping breaks because
'W' is ~3x wider than 'i'. `draw.textlength()` is the fix.

**Free AI images with zero keys.** pollinations.ai renders an image from a
GET request: `image.pollinations.ai/prompt/<encoded prompt>`. It goes
through our `http_client` (new `fetch_bytes` — media needs `.content`
bytes, not `.text`), inheriting timeouts, retries, and the User-Agent.
Note the size sanity check: a 2 KB "image" is an error page in disguise —
trust-but-verify, media edition.

## 3. Folder structure (new)

```
src/ytauto/visuals/
├── __init__.py
├── slide_renderer.py        ← Pillow: fonts, wrapping, layout
└── visual_generator.py      ← per-part orchestration, garnish policy
src/ytauto/repositories/asset_repository.py
scripts/generate_visuals.py   ← CLI (--script-id, --ai)
tests/test_visuals.py         ← 7 tests (real Pillow, fake LLM/fetch)
data/visuals/script_<id>/     ← NN_part_slide.png (+ NN_part_ai.png)
```
Changed: `database.py` (assets table), `http_client.py` (+fetch_bytes),
requirements/pyproject (Pillow).

## 4. Architecture

```
 generate_visuals.py (--script-id, --ai)
        ▼
 visual_generator.generate_visuals()
        │ split_into_parts()          ← SAME contract as voiceover
        │ for each part:
        │   hook/cta ──────────────► render_slide()   (no LLM needed)
        │   section ─ gen_json() ──► parse_slide_text() ► render_slide()
        │             │ optional --ai:
        │             └─► fetch_ai_image() via http_client.fetch_bytes()
        │                  FetchError → log + skip (garnish policy)
        ▼
 assets rows (kind: slide | ai_image, meta = text/prompt)
```

## 5. Beginner explanation

A design intern joins the studio. For every recorded scene, they read the
narration and write one bold sentence on a poster board (LLM distillation
→ slide). The posters are guaranteed — the intern never fails. Sometimes
you also ask a moody freelance artist for a painting per scene (AI image);
if the artist doesn't deliver, the show still ships on posters. The studio
logbook (assets table) records every poster and painting, and which scene
each belongs to.

## 6–7. Code (read in this order)

1. `visuals/slide_renderer.py` — Pillow, font discovery, pixel wrapping
2. `visuals/visual_generator.py` — the two failure policies, distillation
   prompt, pollinations integration
3. `http_client.py` diff — fetch_bytes and why media ≠ text
4. `repositories/asset_repository.py`
5. `tests/test_visuals.py` — note we test Pillow FOR REAL (local, fast,
   deterministic) but fake the LLM and the image service. What to fake is
   a judgment call: fake what's slow/flaky/external, test the rest.

**Why Pillow** (vs matplotlib, HTML-to-image): direct pixel control, tiny
dependency, and it's the same library we'll use for thumbnails in Phase 7.
**Why pollinations.ai**: the only genuinely free, keyless image API; local
Stable Diffusion on a no-GPU laptop takes 5-10 min/image — not viable.

## 8. Common mistakes

1. **Wrapping text by character count** — measure pixels with textlength.
2. **One failure policy for everything** — baseline strict, garnish lenient.
3. **Trusting downloaded bytes** — check size; error pages masquerade as
   images.
4. **`response.text` for binary data** — corrupts it; use `.content`.
5. **Hard-coding one font path** — candidate list, cross-platform.
6. **Letting the LLM write slide text unconstrained** — cap words in the
   prompt AND truncate in code (both layers, as always).
7. **AI-generating text-heavy slides** — models butcher rendered text; put
   words on typographic slides, let AI images be textless.

## 9. Exercises

1. `pip install -r requirements.txt` → `pytest` → 52 passed.
2. **See your video's look:** `python scripts/generate_visuals.py
   --script-id 2`, open the PNGs in order next to the markdown script.
   Do the headlines actually capture each section?
3. **Try the garnish:** rerun with `--ai`. Judge the AI images honestly:
   keep, or slides-only for launch? (Both are respectable channels.)
4. **Brand it.** Change ACCENT/BG colors and (if you like) the font in
   slide_renderer.py — make it YOURS. Regenerate. This is your channel's
   look now; note the hex codes somewhere, they'll reappear in thumbnails.
5. **Write one test:** `render_slide` with an empty `body_text` must still
   produce a 1920x1080 file (hook/cta path). → 53 passed.
6. **Thinking:** slides are re-rendered from scratch on regeneration, but
   AI images cost 30s+ each. Sketch (2-3 sentences) how you'd cache AI
   images across regenerations — what would the cache KEY have to include
   to stay correct when the prompt changes?
7. Commit + push, update PROJECT_STATE.md (Phase 4 ✅).

## 10. Next milestone

**Milestone 7 — Phase 6 (the big one): video assembly.** MoviePy + FFmpeg
stitch it all together: each part's slide (or AI image) displayed for
exactly its audio's duration, crossfade transitions, subtle Ken Burns
zoom, background music ducked under narration, and an MP4 you can
actually upload. The `videos` table, and topic status finally moves to
`produced`. (Phase 5 B-roll folds in later as an enhancement — slides
first, exactly like this milestone.)
