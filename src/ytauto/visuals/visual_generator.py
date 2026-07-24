"""Create the visual assets for every part of a script.

For each part (same split contract as voiceovers):
- hook  -> title slide (video title + hook line)
- section_N -> content slide: LLM distills the narration into a headline
  + 2 key words worth showing (structured extraction — the model READS,
  the renderer DRAWS; content drives visuals automatically)
- cta   -> outro slide

Optionally (--ai), each section also gets a free AI image from
pollinations.ai — an open image-generation service that works as a plain
GET: https://image.pollinations.ai/prompt/<url-encoded prompt>
The LLM writes the image prompt from the narration. AI images are garnish;
slides are the guaranteed baseline (see slide_renderer's docstring).
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from pathlib import Path

from ytauto.config import settings
from ytauto.http_client import FetchError, fetch_bytes
from ytauto.llm.ollama_client import LLMError, generate_json
from ytauto.logging_setup import get_logger
from ytauto.repositories import asset_repository
from ytauto.tts.voiceover_generator import split_into_parts, _get_script_by_id
from ytauto.visuals.slide_renderer import render_slide

log = get_logger(__name__)

SLIDE_TEXT_PROMPT = """Here is narration from a tech explainer video:

{section}

Distill it for an on-screen slide. Answer with ONLY this JSON:
{{"headline": "<max 8 words, the ONE idea of this narration>",
"support": "<max 15 words expanding the headline, plain language>",
"image_prompt": "<a vivid text-to-image prompt for an illustrative, \
abstract-tech style image about this idea, no text in image>"}}"""


def parse_slide_text(data: dict) -> tuple[str, str, str]:
    """Validate extraction. Truncate rather than reject (a long headline
    is a nuisance; a failed part is a hole in the video)."""
    headline = str(data.get("headline", "")).strip()
    if not headline:
        raise LLMError(f"No headline in: {data!r}")
    support = str(data.get("support", "")).strip()
    image_prompt = str(data.get("image_prompt", "")).strip()
    return headline[:80], support[:120], image_prompt[:400]


def fetch_ai_image(prompt: str, out_path: Path) -> Path:
    """Download one free AI image from pollinations.ai."""
    url = ("https://image.pollinations.ai/prompt/"
           + urllib.parse.quote(prompt)
           + "?width=1920&height=1080&nologo=true")
    data = fetch_bytes(url)
    if len(data) < 10_000:  # sanity: real images are bigger than error pages
        raise FetchError("Suspiciously small image response")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    return out_path


def generate_visuals(
    script_id: int,
    with_ai_images: bool = False,
    gen_json: Callable[..., dict] = generate_json,
    fetch_image: Callable[..., Path] = fetch_ai_image,
    render: Callable[..., Path] = render_slide,
    visuals_root: Path | None = None,
    db_path: Path | None = None,
) -> list[Path]:
    """Render every part's slide (and optionally AI images). Returns paths.

    FAILURE POLICY — different from voiceover, deliberately:
    - slides are the guaranteed baseline -> any slide failure aborts all
    - AI images are OPTIONAL garnish -> per-image failure is logged and
      skipped, never fatal. Match strictness to how essential the output is.
    """
    script = _get_script_by_id(script_id, db_path=db_path)
    if script is None:
        raise LLMError(f"Script id {script_id} not found")

    out_dir = (visuals_root or settings.data_dir / "visuals") / f"script_{script_id}"
    parts = split_into_parts(script)
    asset_repository.delete_assets(script_id, db_path=db_path)  # idempotent

    written: list[Path] = []
    for index, (name, text) in enumerate(parts):
        slide_path = out_dir / f"{index:02d}_{name}_slide.png"

        if name == "hook":
            render(slide_path, headline=script["title"],
                   body_text=text, kicker="explained")
            meta = script["title"]
        elif name == "cta":
            render(slide_path, headline="Thanks for watching",
                   body_text=text, kicker="subscribe for more")
            meta = "cta"
        else:
            headline, support, image_prompt = parse_slide_text(
                gen_json(SLIDE_TEXT_PROMPT.format(section=text), temperature=0.3)
            )
            render(slide_path, headline=headline, body_text=support,
                   kicker=script["title"])
            meta = f"{headline} | {support}"

            if with_ai_images and image_prompt:
                img_path = out_dir / f"{index:02d}_{name}_ai.png"
                try:
                    fetch_image(image_prompt, img_path)
                    asset_repository.save_asset(
                        script_id, index, "ai_image", str(img_path),
                        meta=image_prompt, db_path=db_path)
                    written.append(img_path)
                except FetchError as exc:
                    log.warning("AI image skipped for part %s: %s", name, exc)

        asset_repository.save_asset(script_id, index, "slide", str(slide_path),
                                    meta=meta, db_path=db_path)
        written.append(slide_path)

    log.info("Visuals complete for script %d: %d files", script_id, len(written))
    return written
