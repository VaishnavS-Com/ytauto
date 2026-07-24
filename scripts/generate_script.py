"""Generate a video script for the best ranked topic (or a chosen one).

    python scripts/generate_script.py             # best ranked topic
    python scripts/generate_script.py --topic-id 8

Also exports a readable markdown copy to data/scripts/ so you can read the
result like a human, not a database row.
"""

import argparse

from ytauto.config import settings
from ytauto.database import init_db
from ytauto.generation.script_generator import generate_script
from ytauto.llm.ollama_client import is_available
from ytauto.repositories import script_repository


def export_markdown(script: dict) -> str:
    """Write the script as a markdown file; return its path."""
    out_dir = settings.data_dir / "scripts"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"script_{script['id']}_topic_{script['topic_id']}.md"

    chapters_md = "\n".join(f"{i+1}. {c}" for i, c in enumerate(script["chapters"]))
    path.write_text(
        f"# {script['title']}\n\n"
        f"*Model: {script['model']} | Created: {script['created_at']}*\n\n"
        f"## Hook\n\n{script['hook']}\n\n"
        f"## Chapters\n\n{chapters_md}\n\n"
        f"## Script\n\n{script['body']}\n\n"
        f"## CTA\n\n{script['cta']}\n",
        encoding="utf-8",
    )
    return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a video script")
    parser.add_argument("--topic-id", type=int, default=None,
                        help="specific topic id (default: best ranked)")
    args = parser.parse_args()

    init_db()
    if not is_available():
        print(f"Ollama not reachable or model {settings.ollama_model!r} missing.")
        raise SystemExit(1)

    print("Generating script (6 LLM calls on CPU — expect a few minutes)...")
    script_id = generate_script(topic_id=args.topic_id)

    script = None
    # Fetch what we just saved (topic_id may have been auto-picked).
    from ytauto.database import get_connection
    with get_connection() as conn:
        row = conn.execute("SELECT topic_id FROM scripts WHERE id = ?",
                           (script_id,)).fetchone()
    script = script_repository.latest_script(row["topic_id"])

    words = len(script["body"].split())
    print(f"\nSaved script #{script_id}: {script['title']!r}")
    print(f"Chapters: {len(script['chapters'])} | Body: {words} words "
          f"(~{words // 140} min narration)")
    print(f"Markdown export: {export_markdown(script)}")
    print("\nOpen the markdown file and READ it — exercise 2 needs your verdict.")


if __name__ == "__main__":
    main()
