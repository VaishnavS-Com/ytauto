"""Collector tests — NO NETWORK, ever.

We test the PURE parse functions with small hand-made samples. This is why
fetch and parse were separated: network code is slow and flaky in tests,
parsing logic is where the bugs live anyway.
"""


from ytauto.collectors.reddit_collector import parse_listing
from ytauto.collectors.relevance import is_relevant
from ytauto.collectors.rss_collector import parse_feed

# --- relevance filter -------------------------------------------------------

def test_relevant_titles_pass():
    assert is_relevant("OpenAI releases new model")
    assert is_relevant("Why machine learning needs better data")
    assert is_relevant("NVIDIA GPU shortage explained")


def test_irrelevant_titles_fail():
    assert not is_relevant("Best pizza places in Chennai")
    assert not is_relevant("Football transfer news roundup")


def test_word_boundary_no_false_match():
    # "ai" must not match inside other words like "air" or "airlines".
    assert not is_relevant("Air travel prices are falling")


def test_relevant_is_case_insensitive():
    """ALL-CAPS titles from feeds must still be recognized as relevant."""
    assert is_relevant("OPENAI DROPS NEW MODEL")
    assert is_relevant("Deep Learning Breakthrough")


# --- RSS parsing -------------------------------------------------------------

SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Sample</title>
<item><title>New AI chip breaks records</title></item>
<item><title>Celebrity gossip of the week</title></item>
<item><title>What is deep learning really?</title></item>
</channel></rss>"""


def test_parse_feed_filters_and_tags_source():
    ideas = parse_feed(SAMPLE_RSS, source="rss:test")
    titles = [i["title"] for i in ideas]
    assert "New AI chip breaks records" in titles
    assert "What is deep learning really?" in titles
    assert "Celebrity gossip of the week" not in titles     # filtered out
    assert all(i["source"] == "rss:test" for i in ideas)


# --- Reddit parsing ----------------------------------------------------------

SAMPLE_LISTING = {
    "data": {"children": [
        {"data": {"title": "Why does ChatGPT hallucinate?", "score": 900}},
        {"data": {"title": "My cat photos", "score": 5000}},              # irrelevant
        {"data": {"title": "New LLM benchmark released", "score": 10}},   # low score
        {"data": {}},                                                     # missing fields
    ]}
}


def test_parse_listing_filters_relevance_and_score():
    ideas = parse_listing(SAMPLE_LISTING, source="reddit:test", min_score=50)
    assert [i["title"] for i in ideas] == ["Why does ChatGPT hallucinate?"]


def test_parse_listing_handles_empty_input():
    assert parse_listing({}, source="reddit:test") == []
