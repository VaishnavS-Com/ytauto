"""Research module tests — fake LLM, fake Wikipedia. No network."""

import pytest

from ytauto.llm.ollama_client import LLMError
from ytauto.research.wiki_research import format_notes, gather_notes, parse_terms


# --- pure functions ------------------------------------------------------------

def test_parse_terms_valid():
    assert parse_terms({"terms": ["RAG", "Language model"]}) == \
        ["RAG", "Language model"]


def test_parse_terms_caps_at_three():
    assert len(parse_terms({"terms": ["a", "b", "c", "d", "e"]})) == 3


def test_parse_terms_rejects_garbage():
    with pytest.raises(LLMError):
        parse_terms({"terms": "not a list"})
    with pytest.raises(LLMError):
        parse_terms({"terms": ["", "  "]})


def test_format_notes():
    notes = format_notes([("RAG", "Retrieval-augmented generation is...")])
    assert "[Source: Wikipedia — RAG]" in notes
    assert "Retrieval-augmented" in notes


def test_format_notes_empty():
    assert format_notes([]) == ""


# --- gather_notes orchestration --------------------------------------------------

def test_gather_notes_happy():
    def fake_llm(prompt, temperature=0.2):
        return {"terms": ["Retrieval-augmented generation"]}

    def fake_summary(term):
        return ("Retrieval-augmented generation",
                "RAG combines retrieval with generation.")

    notes = gather_notes("What is RAG?", gen_json=fake_llm,
                         fetch_summary=fake_summary)
    assert "RAG combines retrieval" in notes


def test_gather_notes_falls_back_to_title_on_bad_terms():
    seen = []

    def bad_llm(prompt, temperature=0.2):
        return {"nonsense": True}          # parse_terms will raise

    def spy_summary(term):
        seen.append(term)
        return (term, "extract")

    gather_notes("Quantum computing", gen_json=bad_llm, fetch_summary=spy_summary)
    assert seen == ["Quantum computing"]   # raw title used as the search term


def test_gather_notes_empty_when_wiki_finds_nothing():
    notes = gather_notes("xyzzy", gen_json=lambda p, temperature=0.2:
                         {"terms": ["xyzzy"]},
                         fetch_summary=lambda term: None)
    assert notes == ""


def test_grounding_rules_reach_the_prompts():
    """The notes must actually appear in PLAN and SECTION prompts."""
    from ytauto.generation.script_generator import PLAN_PROMPT, SECTION_PROMPT

    plan = PLAN_PROMPT.format(topic="T", notes="THE-NOTES")
    section = SECTION_PROMPT.format(title="T", chapters=["A"], chapter="A",
                                    notes="THE-NOTES")
    assert "THE-NOTES" in plan and "THE-NOTES" in section
    assert "NEVER invent" in section       # the incident's lesson, in writing
