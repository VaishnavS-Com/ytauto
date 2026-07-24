"""Script generator tests — the whole chain runs on fake LLMs."""

import pytest

from ytauto.database import init_db
from ytauto.generation.script_generator import (
    generate_script,
    parse_hook_cta,
    parse_plan,
)
from ytauto.llm.ollama_client import LLMError
from ytauto.repositories import script_repository, topic_repository as topics


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return db_path


# --- pure validators ---------------------------------------------------------

def test_parse_plan_valid():
    title, chapters = parse_plan(
        {"title": "How AI designs medicines", "chapters": ["A", "B", "C", "D"]}
    )
    assert title == "How AI designs medicines"
    assert chapters == ["A", "B", "C", "D"]


def test_parse_plan_rejects_bad_shapes():
    with pytest.raises(LLMError):
        parse_plan({"title": "", "chapters": ["A", "B", "C"]})       # no title
    with pytest.raises(LLMError):
        parse_plan({"title": "X", "chapters": ["A"]})                # too few
    with pytest.raises(LLMError):
        parse_plan({"title": "X", "chapters": "not a list"})
    with pytest.raises(LLMError):
        parse_plan({"title": "X", "chapters": ["A","B","C","D","E","F","G"]})  # 7 = too many


def test_parse_hook_cta_rejects_missing():
    with pytest.raises(LLMError):
        parse_hook_cta({"hook": "great hook", "cta": ""})


# --- the full chain with fakes -----------------------------------------------

def fake_json(prompt: str, temperature: float = 0.2) -> dict:
    if '"chapters"' in prompt and '"title"' in prompt and "Design" in prompt:
        return {"title": "How AI finds new medicines",
                "chapters": ["The problem", "Enter AI", "A real case", "What's next"]}
    return {"hook": "What if a computer found your next medicine?",
            "cta": "Subscribe for more explainers."}


def fake_text(prompt: str, temperature: float = 0.7) -> str:
    return "This is a narration section with a friendly explanation. " * 10


def test_generate_script_full_chain(db):
    topic_id = topics.add_topic("AI in drug discovery", niche="tech", db_path=db)
    topics.set_rank(topic_id, 8.0, "evergreen", db_path=db)

    script_id = generate_script(
        gen_json=fake_json, gen_text=fake_text, db_path=db
    )

    saved = script_repository.latest_script(topic_id, db_path=db)
    assert saved["id"] == script_id
    assert saved["title"] == "How AI finds new medicines"
    assert len(saved["chapters"]) == 4
    # Body = one section per chapter, joined.
    assert saved["body"].count("narration section") >= 4
    assert saved["hook"].startswith("What if")

    # Lifecycle advanced: ranked -> scripted.
    assert topics.list_topics(status="scripted", db_path=db)[0]["id"] == topic_id


def test_generate_script_no_ranked_topics(db):
    with pytest.raises(LLMError):
        generate_script(gen_json=fake_json, gen_text=fake_text, db_path=db)


def test_failure_keeps_topic_ranked_and_saves_nothing(db):
    """If step 3 explodes, no script row exists and the topic stays 'ranked'."""
    topic_id = topics.add_topic("AI and quantum computing", niche="tech", db_path=db)
    topics.set_rank(topic_id, 7.0, "good", db_path=db)

    def json_fails_on_hook(prompt: str, temperature: float = 0.2) -> dict:
        if "hook" in prompt:
            raise LLMError("model exploded at the last step")
        return fake_json(prompt, temperature)

    with pytest.raises(LLMError):
        generate_script(gen_json=json_fails_on_hook, gen_text=fake_text, db_path=db)

    assert script_repository.get_scripts_for_topic(topic_id, db_path=db) == []
    assert topics.list_topics(status="ranked", db_path=db)[0]["id"] == topic_id


def test_multiple_drafts_per_topic(db):
    """The one-to-many design: generating twice = two drafts, newest first."""
    topic_id = topics.add_topic("What is RAG really?", niche="tech", db_path=db)
    topics.set_rank(topic_id, 9.0, "great", db_path=db)

    generate_script(topic_id=topic_id, gen_json=fake_json, gen_text=fake_text,
                    db_path=db)
    generate_script(topic_id=topic_id, gen_json=fake_json, gen_text=fake_text,
                    db_path=db)

    drafts = script_repository.get_scripts_for_topic(topic_id, db_path=db)
    assert len(drafts) == 2
