"""Watch the notes/ folder and auto-ingest new or changed notes."""

import logging
from pathlib import Path

from watchfiles import Change, watch

from wisey.ingest_notes import NOTES_DIR, ingest_single_note

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info(f"Watching {NOTES_DIR} for changes...")

    for changes in watch(NOTES_DIR):
        for change_type, path_str in changes:
            path = Path(path_str)

            if not path.suffix == ".md":
                continue

            if change_type in (Change.added, Change.modified):
                logger.info(f"{'New' if change_type == Change.added else 'Updated'}: {path.name}")
                try:
                    count = ingest_single_note(path)
                    logger.info(f"Ingested {path.name} → {count} chunks")
                except Exception as e:
                    logger.error(f"Failed to ingest {path.name}: {e}")

            elif change_type == Change.deleted:
                logger.info(f"Deleted: {path.name} — removing from DB")
                try:
                    from wisey.db import get_connection
                    source_url = f"notes/{path.name}"
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM chunks WHERE source_url = %s", (source_url,))
                    deleted = cur.rowcount
                    conn.commit()
                    cur.close()
                    conn.close()
                    logger.info(f"Removed {deleted} chunks for {path.name}")
                except Exception as e:
                    logger.error(f"Failed to clean up {path.name}: {e}")


if __name__ == "__main__":
    main()
