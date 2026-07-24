"""Voiceover tests — fake synthesizer, no network, no real audio.

The fake writes a tiny file, which is enough to test everything that can
break: splitting, ordering, DB rows, idempotent regeneration, rollback.
"""

import pytest

from ytauto.database import init_db
from ytauto.repositories import script_repository, topic_repository as topics
from ytauto.repositories import voiceover_repository
from ytauto.tts.edge_client import TTSError
from ytauto.tts.voiceover_generator import generate_voiceover, split_into_parts


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return db_path


@pytest.fixture
def script_id(db):
    """A stored script with 3 body sections."""
    topic_id = topics.add_topic("What is RAG?", niche="tech", db_path=db)
    return script_repository.save_script(
        topic_id=topic_id, title="What is RAG in AI?",
        hook="Your AI is smarter with a library card.",
        body="Section one text.\n\nSection two text.\n\nSection three text.",
        cta="Subscribe for more.", chapters=["A", "B", "C"],
        model="test-model", db_path=db,
    )


def fake_synth(text, out_path, voice=None):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"FAKE_MP3_BYTES")
    return out_path


# --- pure splitting ----------------------------------------------------------

def test_split_into_parts_order_and_names():
    script = {"hook": "H", "body": "S1.\n\nS2.", "cta": "C"}
    parts = split_into_parts(script)
    assert [name for name, _ in parts] == ["hook", "section_01", "section_02", "cta"]
    assert parts[0][1] == "H" and parts[-1][1] == "C"


def test_split_into_parts_single_section():
    script = {"hook": "H", "body": "Single section with no blank lines.", "cta": "C"}
    parts = split_into_parts(script)
    assert [name for name, _ in parts] == ["hook", "section_01", "cta"]



# --- generation with fakes ---------------------------------------------------

def test_generate_voiceover_writes_files_and_rows(db, script_id, tmp_path):
    paths = generate_voiceover(script_id, synth=fake_synth,
                               audio_root=tmp_path / "audio", db_path=db)

    assert len(paths) == 5           # hook + 3 sections + cta
    assert all(p.exists() for p in paths)
    assert paths[0].name == "00_hook.mp3"
    assert paths[-1].name == "04_cta.mp3"

    rows = voiceover_repository.get_parts(script_id, db_path=db)
    assert [r["part_name"] for r in rows] == \
        ["hook", "section_01", "section_02", "section_03", "cta"]


def test_regeneration_is_idempotent(db, script_id, tmp_path):
    generate_voiceover(script_id, synth=fake_synth,
                       audio_root=tmp_path / "audio", db_path=db)
    generate_voiceover(script_id, synth=fake_synth,
                       audio_root=tmp_path / "audio", db_path=db)
    # Second run replaced, not duplicated.
    assert len(voiceover_repository.get_parts(script_id, db_path=db)) == 5


def test_failure_rolls_back_files_and_rows(db, script_id, tmp_path):
    calls = {"n": 0}

    def flaky_synth(text, out_path, voice=None):
        calls["n"] += 1
        if calls["n"] == 3:                      # fail on the 3rd part
            raise TTSError("network died")
        return fake_synth(text, out_path, voice)

    with pytest.raises(TTSError):
        generate_voiceover(script_id, synth=flaky_synth,
                           audio_root=tmp_path / "audio", db_path=db)

    # Nothing half-done survives: no rows, no files.
    assert voiceover_repository.get_parts(script_id, db_path=db) == []
    audio_dir = tmp_path / "audio" / f"script_{script_id}"
    assert not any(audio_dir.glob("*.mp3")) if audio_dir.exists() else True


def test_missing_script_raises(db):
    with pytest.raises(TTSError):
        generate_voiceover(9999, synth=fake_synth, db_path=db)
