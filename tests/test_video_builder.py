"""Video builder tests — a FAKE renderer, so no MoviePy/FFmpeg needed.

We test everything AROUND rendering: contract validation (pair_parts),
the happy path, fail-fast behavior, and the lifecycle advance to
'produced'. The one function we don't test (_render_moviepy) is exercised
by actually building a video on your machine — some things an integration
run covers better than a slow, brittle unit test.
"""

import pytest

from ytauto.database import init_db
from ytauto.repositories import (
    script_repository,
    topic_repository as topics,
    video_repository,
    voiceover_repository,
)
from ytauto.repositories import asset_repository
from ytauto.video.video_builder import VideoError, build_video, pair_parts


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return db_path


@pytest.fixture
def ready_script(db, tmp_path):
    """A script with matching voiceover parts and slides on 'disk'."""
    topic_id = topics.add_topic("What is RAG?", niche="tech", db_path=db)
    topics.set_rank(topic_id, 8.0, "x", db_path=db)
    script_id = script_repository.save_script(
        topic_id=topic_id, title="T", hook="H", body="S1.\n\nS2.",
        cta="C", chapters=["A", "B"], model="m", db_path=db)
    topics.update_status(topic_id, "scripted", db_path=db)

    for i, name in enumerate(["hook", "section_01", "section_02", "cta"]):
        audio = tmp_path / f"{i:02d}_{name}.mp3"
        audio.write_bytes(b"AUDIO")
        voiceover_repository.save_part(script_id, i, name, str(audio), "v",
                                       db_path=db)
        slide = tmp_path / f"{i:02d}_{name}_slide.png"
        slide.write_bytes(b"PNG")
        asset_repository.save_asset(script_id, i, "slide", str(slide),
                                    db_path=db)
    return script_id, topic_id


def fake_render(pairs, out_path, music_path=None):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"FAKE_MP4")
    return 123.4  # pretend duration


# --- pair_parts contract validation -------------------------------------------

def test_pair_parts_happy(db, ready_script):
    script_id, _ = ready_script
    pairs = pair_parts(
        voiceover_repository.get_parts(script_id, db_path=db),
        asset_repository.get_assets(script_id, kind="slide", db_path=db),
    )
    assert len(pairs) == 4
    assert pairs[0][0].name == "00_hook.mp3"


def test_pair_parts_rejects_count_mismatch(db, ready_script, tmp_path):
    script_id, _ = ready_script
    extra = tmp_path / "extra.mp3"
    extra.write_bytes(b"AUDIO")
    voiceover_repository.save_part(script_id, 9, "extra", str(extra), "v",
                                   db_path=db)
    with pytest.raises(VideoError, match="Contract broken"):
        pair_parts(
            voiceover_repository.get_parts(script_id, db_path=db),
            asset_repository.get_assets(script_id, kind="slide", db_path=db),
        )


def test_pair_parts_rejects_missing_file(db, ready_script, tmp_path):
    script_id, _ = ready_script
    (tmp_path / "00_hook.mp3").unlink()      # delete one audio from disk
    with pytest.raises(VideoError, match="missing on disk"):
        pair_parts(
            voiceover_repository.get_parts(script_id, db_path=db),
            asset_repository.get_assets(script_id, kind="slide", db_path=db),
        )


def test_pair_parts_rejects_missing_slide_file(db, ready_script, tmp_path):
    script_id, _ = ready_script
    (tmp_path / "00_hook_slide.png").unlink()  # delete one slide from disk
    with pytest.raises(VideoError, match="missing on disk"):
        pair_parts(
            voiceover_repository.get_parts(script_id, db_path=db),
            asset_repository.get_assets(script_id, kind="slide", db_path=db),
        )



def test_pair_parts_rejects_empty(db):
    with pytest.raises(VideoError, match="No voiceover"):
        pair_parts([], [])


# --- build_video ---------------------------------------------------------------

def test_build_video_full_flow(db, ready_script, tmp_path):
    script_id, topic_id = ready_script
    video_id = build_video(script_id, render=fake_render,
                           videos_root=tmp_path / "vid", db_path=db)

    row = video_repository.latest_video(script_id, db_path=db)
    assert row["id"] == video_id
    assert row["duration_s"] == 123.4

    # THE moment: topic reaches 'produced'.
    assert topics.list_topics(status="produced", db_path=db)[0]["id"] == topic_id


def test_build_video_verifies_output_exists(db, ready_script, tmp_path):
    script_id, _ = ready_script

    def liar_render(pairs, out_path, music_path=None):
        return 99.0   # claims success, writes nothing

    with pytest.raises(VideoError, match="no output"):
        build_video(script_id, render=liar_render,
                    videos_root=tmp_path / "vid", db_path=db)
    # And nothing was recorded.
    assert video_repository.latest_video(script_id, db_path=db) is None


def test_build_video_missing_script(db):
    with pytest.raises(VideoError, match="not found"):
        build_video(9999, render=fake_render, db_path=db)
