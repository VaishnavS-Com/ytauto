"""Synthesize the voiceover for a script.

    python scripts/generate_voiceover.py --script-id 2

Needs internet (Edge TTS runs on Microsoft's servers). Output lands in
data/audio/script_<id>/ — play the files and meet your narrator.
"""

import argparse

from ytauto.database import init_db
from ytauto.tts.voiceover_generator import generate_voiceover


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate voiceover MP3s")
    parser.add_argument("--script-id", type=int, required=True,
                        help="which script to voice (see data/scripts/ exports)")
    args = parser.parse_args()

    init_db()
    print(f"Synthesizing script {args.script_id} — a few seconds per part...")
    paths = generate_voiceover(args.script_id)

    total_bytes = sum(p.stat().st_size for p in paths)
    print(f"\nDone: {len(paths)} parts, {total_bytes / 1_000_000:.1f} MB total")
    for p in paths:
        print(f"  {p.name:<22} {p.stat().st_size / 1000:.0f} KB")
    print(f"\nFolder: {paths[0].parent}")
    print("Play 00_hook.mp3 first — that's your channel's voice.")


if __name__ == "__main__":
    main()
