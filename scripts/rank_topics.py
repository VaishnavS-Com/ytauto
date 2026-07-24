"""Rank 'new' topics with the local LLM.

    python scripts/rank_topics.py            # rank up to 10
    python scripts/rank_topics.py --limit 30

Requires Ollama running with the model pulled (see milestone_03.md).
The script checks first and tells you exactly what to do if not.
"""

import argparse

from ytauto.config import settings
from ytauto.database import init_db
from ytauto.llm.ollama_client import is_available
from ytauto.ranking.topic_ranker import rank_pending
from ytauto.repositories import topic_repository as topics


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-rank pending topics")
    parser.add_argument("--limit", type=int, default=10,
                        help="max topics to rank this run (default 10)")
    args = parser.parse_args()

    init_db()

    # Fail fast with a helpful message — don't let 10 topics each time out.
    if not is_available():
        print(f"Ollama is not reachable, or model {settings.ollama_model!r} "
              "is not pulled.")
        print("Fix: install from https://ollama.com, then run:")
        print(f"    ollama pull {settings.ollama_model}")
        raise SystemExit(1)

    print(f"Ranking up to {args.limit} topics with {settings.ollama_model} "
          "(CPU inference — expect ~10-60s per topic; this is normal)...")
    stats = rank_pending(limit=args.limit)

    print(f"Done: {stats['ranked']} ranked, {stats['failed']} failed.")

    ranked = topics.list_topics(status="ranked")
    ranked_sorted = sorted(ranked, key=lambda r: r["score"] or 0, reverse=True)
    print("\nTop ideas so far:")
    for row in ranked_sorted[:10]:
        print(f"  {row['score']:>4.1f}  {row['title']}")
        print(f"        ↳ {row['rank_reason']}")


if __name__ == "__main__":
    main()
