"""Niche relevance filter — keep only ideas that fit our channel.

RSS feeds and subreddits carry plenty of off-topic noise (sports deals,
phone reviews...). This first filter is deliberately dumb-but-transparent:
keyword matching. In a later milestone an LLM does smarter relevance
scoring — but you should always build the simple version first and measure,
before reaching for AI. (Optimization lesson: AI calls are 1000x slower
than a keyword check; spend them only where they add value.)
"""

from __future__ import annotations

# Lowercase keywords; a title matches if ANY appears in it.
AI_KEYWORDS = [
    "ai", "a.i.", "artificial intelligence", "machine learning", "deep learning",
    "neural", "llm", "gpt", "chatgpt", "claude", "gemini", "openai", "anthropic",
    "language model", "ai model", "ml model", "foundation model",
    "robot", "automation", "agent", "chip", "gpu", "nvidia",
    "quantum", "algorithm", "data science", "python", "transformer",
    "diffusion", "copilot", "chatbot",
]


def is_relevant(title: str, keywords: list[str] | None = None) -> bool:
    """True if the title looks like it belongs in our tech/AI niche.

    NOTE the word-boundary trick: we pad with spaces and strip punctuation
    so the keyword "ai" matches "AI beats humans" but NOT "air travel".
    Substring matching without boundaries is a classic silent bug.
    """
    words = title.lower()
    for ch in ",.!?:;'\"()[]":
        words = words.replace(ch, " ")
    padded = f" {words} "

    for kw in keywords or AI_KEYWORDS:
        if f" {kw} " in padded or (len(kw) > 4 and kw in words):
            return True
    return False
