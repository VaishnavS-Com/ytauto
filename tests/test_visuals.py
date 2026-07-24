"""Visuals tests — real Pillow rendering (fast + deterministic), fake LLM
and fake image fetcher. Pillow is pure local computation, so unlike the
network and the model, we test it for real.
"""

import pytest
from PIL import Image

from ytauto.database import init_db
from ytauto.http_client import FetchError
from ytauto.llm.ollama_client import LLMError
from ytauto.repositories import asset_repository, script_repository
from ytauto.repositories import topic_repository as topics
from ytauto.visuals.slide_renderer import render_slide
from ytauto.visuals.visual_generator import generate_visuals, parse_slide_text


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return db_path


@pytest.fixture
def script_id(db):
    topic_id = topics.add_topic("What is RAG?", niche="tech", db_path=db)
    return script_repository.save_script(
        topic_id=topic_id, title="What is RAG in AI?",
        hook="Your AI is smarter with a library card.",
        body="Section one text.\n\nSection two text.",
        cta="Subscribe for more.", chapters=["A", "B"],
        model="test-model", db_path=db,
    )


def fake_llm(prompt, temperature=0.3):
    return {"headline": "RAG explained", "support": "Search plus generation",
            "image_prompt": "abstract library of glowing documents"}


# --- renderer ----------------------------------------------------------------

def test_render_slide_produces_full_hd_png(tmp_path):
    out = render_slide(tmp_path / "s.png", headline="Hello world",
                       body_text="Some supporting text", kicker="test")
    img = Image.open(out)
    assert img.size == (1920, 1080)
    assert out.stat().st_size > 1000


def test_render_slide_handles_very_long_text(tmp_path):
    # Must not crash or overflow the canvas — wrapping + line caps handle it.
    out = render_slide(tmp_path / "long.png", headline="word " * 60,
                       body_text="lots of text " * 50)
    assert Image.open(out).size == (1920, 1080)


# --- extraction validator ------------------------------------------------------

def test_parse_slide_text_truncates_not_rejects():
    headline, support, _ = parse_slide_text(
        {"headline": "H" * 200, "support": "s" * 300, "image_prompt": ""})
    assert len(headline) == 80 and len(support) == 120


def test_parse_slide_text_requires_headline():
    with pytest.raises(LLMError):
        parse_slide_text({"support": "no headline"})


# --- full generation -----------------------------------------------------------

def test_generate_visuals_slides_only(db, script_id, tmp_path):
    paths = generate_visuals(script_id, gen_json=fake_llm,
                             visuals_root=tmp_path / "v", db_path=db)
    # hook + 2 sections + cta = 4 slides
    assert len(paths) == 4
    assert all(p.exists() for p in paths)

    slides = asset_repository.get_assets(script_id, kind="slide", db_path=db)
    assert len(slides) == 4


def test_ai_image_failure_is_not_fatal(db, script_id, tmp_path):
    """Garnish policy: a failed AI image is skipped, slides still complete."""
    def broken_fetch(prompt, out_path):
        raise FetchError("image service down")

    paths = generate_visuals(script_id, with_ai_images=True, gen_json=fake_llm,
                             fetch_image=broken_fetch,
                             visuals_root=tmp_path / "v", db_path=db)
    assert len(paths) == 4  # all slides present, zero ai_images
    assert asset_repository.get_assets(script_id, kind="ai_image", db_path=db) == []


def test_regeneration_is_idempotent(db, script_id, tmp_path):
    generate_visuals(script_id, gen_json=fake_llm,
                     visuals_root=tmp_path / "v", db_path=db)
    generate_visuals(script_id, gen_json=fake_llm,
                     visuals_root=tmp_path / "v", db_path=db)
    assert len(asset_repository.get_assets(script_id, db_path=db)) == 4


def test_generate_visuals_empty_body(db, tmp_path):
    """An empty script body still produces hook and cta slides correctly."""
    topic_id = topics.add_topic("Empty topic", niche="tech", db_path=db)
    sid = script_repository.save_script(
        topic_id=topic_id, title="Empty Script",
        hook="Just a hook.", body="", cta="Just a cta.",
        chapters=[], model="test", db_path=db,
    )
    paths = generate_visuals(sid, gen_json=fake_llm, visuals_root=tmp_path / "v", db_path=db)
    assert len(paths) == 2  # hook slide + cta slide
    assert [p.name for p in paths] == ["00_hook_slide.png", "01_cta_slide.png"]

