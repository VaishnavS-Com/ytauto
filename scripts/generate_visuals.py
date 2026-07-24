"""Render slides (and optionally AI images) for a script.

    python scripts/generate_visuals.py --script-id 2
    python scripts/generate_visuals.py --script-id 2 --ai

Slides need no internet and no model for hook/cta — but section slides use
the LLM to distill headlines, so Ollama must be running.
"""

import argparse

from ytauto.config import settings
from ytauto.database import init_db
from ytauto.llm.ollama_client import is_available
from ytauto.visuals.visual_generator import generate_visuals


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate slides / AI images")
    parser.add_argument("--script-id", type=int, required=True)
    parser.add_argument("--ai", action="store_true",
                        help="also fetch free AI images from pollinations.ai")
    args = parser.parse_args()

    init_db()
    if not is_available():
        print(f"Ollama not reachable or model {settings.ollama_model!r} missing.")
        raise SystemExit(1)

    print("Generating visuals (one LLM call per section)...")
    paths = generate_visuals(args.script_id, with_ai_images=args.ai)

    print(f"\nDone: {len(paths)} files")
    for p in paths:
        print(f"  {p.name}")
    print(f"\nFolder: {paths[0].parent}")
    print("Open the PNGs — this is what your viewers will see.")


if __name__ == "__main__":
    main()
