"""Tests for the topic repository.

KEY TECHNIQUE: `tmp_path` is a built-in pytest fixture — a fresh temporary
folder for every test. Each test gets its own throwaway database, so tests
never touch data/ytauto.db, never see each other's data, and can run in any
order. Isolated tests are trustworthy tests.
"""

import pytest

from ytauto.database import init_db
from ytauto.repositories import topic_repository as topics


@pytest.fixture
def db(tmp_path):
    """A fresh, empty database file for one single test."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return db_path


def test_add_and_list(db):
    topic_id = topics.add_topic("How do LLMs work?", niche="tech", db_path=db)
    assert topic_id is not None

    rows = topics.list_topics(db_path=db)
    assert len(rows) == 1
    assert rows[0]["title"] == "How do LLMs work?"
    assert rows[0]["status"] == "new"       # default from schema
    assert rows[0]["score"] is None         # unranked until Phase 1 ranking


def test_duplicates_are_rejected(db):
    assert topics.add_topic("What is RAG?", niche="tech", db_path=db) is not None
    # Same idea, different formatting -> normalization must catch it.
    assert topics.add_topic("  what is rag?  ", niche="tech", db_path=db) is None
    assert topics.count_topics(db_path=db) == 1


def test_empty_title_raises(db):
    with pytest.raises(ValueError):
        topics.add_topic("   ", niche="tech", db_path=db)


def test_status_lifecycle(db):
    topic_id = topics.add_topic("AI in 2026", niche="tech", db_path=db)
    assert topics.update_status(topic_id, "ranked", db_path=db) is True

    ranked = topics.list_topics(status="ranked", db_path=db)
    assert [r["id"] for r in ranked] == [topic_id]


def test_update_missing_id_returns_false(db):
    assert topics.update_status(9999, "ranked", db_path=db) is False


def test_invalid_status_rejected_by_db(db):
    """The CHECK constraint is the database defending its own integrity."""
    import sqlite3

    topic_id = topics.add_topic("Quantum computing", niche="tech", db_path=db)
    with pytest.raises(sqlite3.IntegrityError):
        topics.update_status(topic_id, "banana", db_path=db)


def test_normalize_title():
    assert topics.normalize_title("  How  AI   Works! ") == "how ai works!"


def test_delete_topic(db):
    """add → delete → count must be 0; deleting missing id returns False."""
    topic_id = topics.add_topic("Throwaway topic", niche="tech", db_path=db)
    assert topics.delete_topic(topic_id, db_path=db) is True
    assert topics.count_topics(db_path=db) == 0
    # Deleting the same id again should return False (already gone).
    assert topics.delete_topic(topic_id, db_path=db) is False

