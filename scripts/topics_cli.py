"""Tiny command-line tool to manage topics by hand.

Usage (from project root, venv active):

    python scripts/topics_cli.py add "How do neural networks learn?"
    python scripts/topics_cli.py add "What is RAG?" --source manual
    python scripts/topics_cli.py list
    python scripts/topics_cli.py list --status new

WHY argparse? It's stdlib, and it gives you --help for free. Every
professional CLI you've used (git, pip) follows this subcommand pattern.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ytauto.config import settings
from ytauto.database import init_db
from ytauto.repositories import topic_repository as topics


def cmd_add(args: argparse.Namespace) -> None:
    topic_id = topics.add_topic(args.title, niche=settings.channel_niche, source=args.source)
    if topic_id is None:
        print(f"Duplicate — already in database: {args.title!r}")
    else:
        print(f"Added topic #{topic_id}: {args.title!r}")


def cmd_list(args: argparse.Namespace) -> None:
    rows = topics.list_topics(status=args.status)
    if not rows:
        print("No topics found.")
        return
    print(f"{'id':>4}  {'status':<10} {'score':>6}  title")
    print("-" * 60)
    for row in rows:
        score = f"{row['score']:.2f}" if row["score"] is not None else "-"
        print(f"{row['id']:>4}  {row['status']:<10} {score:>6}  {row['title']}")
    print(f"\nTotal: {len(rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage video topic ideas")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add a topic idea")
    p_add.add_argument("title", help="The topic/idea text (quote it)")
    p_add.add_argument("--source", default="manual", help="Where the idea came from")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List stored topics")
    p_list.add_argument("--status", default=None,
                        help="Filter: new|ranked|scripted|produced|published|rejected")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    init_db()          # idempotent — safe at every startup
    args.func(args)    # dispatch to the chosen subcommand


if __name__ == "__main__":
    main()
