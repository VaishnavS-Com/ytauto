"""Ranker tests — NO MODEL NEEDED, thanks to dependency injection.

We pass fake `generate` functions into rank_pending. Fakes let us test
things that are impossible to trigger reliably with a real model: perfect
answers, malformed answers, and total failure.
"""

import pytest

from ytauto.database import init_db
from ytauto.llm.ollama_client import LLMError
from ytauto.ranking.topic_ranker import build_prompt, parse_verdict, rank_pending
from ytauto.repositories import topic_repository as topics


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return db_path


# --- pure functions ----------------------------------------------------------

def test_build_prompt_contains_title_and_format():
    prompt = build_prompt("What is a neural network?")
    assert "What is a neural network?" in prompt
    assert '"score"' in prompt          # output shape is specified


def test_parse_verdict_normal():
    assert parse_verdict({"score": 7.5, "reason": "evergreen"}) == (7.5, "evergreen")


def test_parse_verdict_coerces_string_score():
    score, _ = parse_verdict({"score": "8", "reason": "x"})
    assert score == 8.0


def test_parse_verdict_clamps_out_of_range():
    assert parse_verdict({"score": 42, "reason": "x"})[0] == 10.0
    assert parse_verdict({"score": -3, "reason": "x"})[0] == 0.0


def test_parse_verdict_rejects_garbage():
    with pytest.raises(LLMError):
        parse_verdict({"reason": "no score at all"})
    with pytest.raises(LLMError):
        parse_verdict({"score": "banana"})

def test_parse_verdict_caps_dated_news():
    """Policy lives in code: dated news can never score above 4."""
    score, _ = parse_verdict({"dated_news": True, "score": 9, "reason": "x"})
    assert score == 4.0

# --- the ranking run, with fake LLMs ----------------------------------------

def test_rank_pending_happy_path(db):
    topics.add_topic("How do LLMs work?", niche="tech", db_path=db)
    topics.add_topic("What is RAG?", niche="tech", db_path=db)

    def fake_llm(prompt: str) -> dict:
        return {"score": 9, "reason": "great explainer"}

    stats = rank_pending(limit=10, generate=fake_llm, db_path=db)
    assert stats == {"ranked": 2, "failed": 0}

    assert topics.list_topics(status="new", db_path=db) == []
    ranked = topics.list_topics(status="ranked", db_path=db)
    assert len(ranked) == 2
    assert all(r["score"] == 9.0 for r in ranked)


def test_one_bad_answer_does_not_kill_the_batch(db):
    topics.add_topic("Good topic about AI", niche="tech", db_path=db)
    topics.add_topic("Cursed topic about GPUs", niche="tech", db_path=db)

    def flaky_llm(prompt: str) -> dict:
        if "Cursed" in prompt:
            raise LLMError("model exploded")
        return {"score": 6, "reason": "ok"}

    stats = rank_pending(limit=10, generate=flaky_llm, db_path=db)
    assert stats == {"ranked": 1, "failed": 1}
    # The failed topic stays 'new' — it will be retried on the next run.
    assert len(topics.list_topics(status="new", db_path=db)) == 1


def test_limit_is_respected(db):
    for i in range(5):
        topics.add_topic(f"AI topic number {i}", niche="tech", db_path=db)

    calls = []

    def counting_llm(prompt: str) -> dict:
        calls.append(prompt)
        return {"score": 5, "reason": "meh"}

    rank_pending(limit=3, generate=counting_llm, db_path=db)
    assert len(calls) == 3


def test_score_clamped_through_full_flow(db):
    """A fake LLM returning score=11 must be stored as exactly 10.0."""
    topics.add_topic("Overclaimed AI breakthrough", niche="tech", db_path=db)

    def overscoring_llm(prompt: str) -> dict:
        return {"score": 11, "reason": "off the charts"}

    stats = rank_pending(limit=10, generate=overscoring_llm, db_path=db)
    assert stats == {"ranked": 1, "failed": 0}

    ranked = topics.list_topics(status="ranked", db_path=db)
    assert len(ranked) == 1
    assert ranked[0]["score"] == 10.0

