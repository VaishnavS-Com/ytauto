"""Run all collectors and store new ideas in the database.

    python scripts/collect_topics.py

This is the first script that makes the system feel ALIVE: run it and the
database fills itself. In a later milestone the scheduler runs this daily
with no human involved.

NOTE: no sys.path hack anymore — after `pip install -e .` the ytauto
package imports from anywhere. (Milestone 2 exercise removes the hack from
the older files too.)
"""

from ytauto.collectors import reddit_collector, rss_collector
from ytauto.config import settings
from ytauto.database import init_db
from ytauto.logging_setup import get_logger
from ytauto.repositories import topic_repository as topics

log = get_logger(__name__)


def main() -> None:
    init_db()

    # 1. Gather ideas from every source (each source failure-isolated).
    ideas = rss_collector.collect() + reddit_collector.collect()
    log.info("Collected %d relevant ideas total", len(ideas))

    # 2. Store them. The DB's UNIQUE constraint silently absorbs duplicates —
    #    running this twice a day is completely safe (idempotent pipeline).
    added = 0
    for idea in ideas:
        if topics.add_topic(idea["title"], niche=settings.channel_niche,
                            source=idea["source"]) is not None:
            added += 1

    duplicates = len(ideas) - added
    print(f"Collected: {len(ideas)}  |  new: {added}  |  duplicates skipped: {duplicates}")
    print(f"Database now holds {topics.count_topics()} topics.")
    log.info("Collection run done: %d new, %d duplicates", added, duplicates)


if __name__ == "__main__":
    main()
