"""Assemble the final MP4 for a script.

    python scripts/build_video.py --script-id 2
    python scripts/build_video.py --script-id 2 --music data/music/calm.mp3

Prerequisites: voiceover (Milestone 5) and visuals (Milestone 6) already
generated for this script. First run downloads FFmpeg (~80 MB, one time).
CPU encoding takes roughly 1-2x video duration — a 4-min video ≈ 4-8 min.
"""

import argparse
from pathlib import Path

from ytauto.database import init_db
from ytauto.repositories import video_repository
from ytauto.video.video_builder import build_video


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the final video")
    parser.add_argument("--script-id", type=int, required=True)
    parser.add_argument("--music", type=Path, default=None,
                        help="optional background music file (mp3)")
    args = parser.parse_args()

    init_db()
    print("Assembling video (encoding is CPU-heavy — be patient)...")
    video_id = build_video(args.script_id, music_path=args.music)

    row = video_repository.latest_video(args.script_id)
    minutes, seconds = divmod(int(row["duration_s"]), 60)
    size_mb = Path(row["file_path"]).stat().st_size / 1_000_000
    print(f"\nVideo #{video_id}: {row['file_path']}")
    print(f"Duration: {minutes}:{seconds:02d} | Size: {size_mb:.1f} MB")
    print("\nOpen it. You built a YouTube video from a headline. Watch it fully.")


if __name__ == "__main__":
    main()
