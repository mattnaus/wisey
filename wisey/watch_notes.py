"""Watch notes/ and guides/ folders and auto-ingest new or changed files."""

import logging
from pathlib import Path

from watchfiles import Change, watch

from wisey.ingest_notes import GUIDES_DIR, NOTES_DIR, ingest_single_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info(f"Watching {NOTES_DIR} and {GUIDES_DIR} for changes...")

    for changes in watch(NOTES_DIR, GUIDES_DIR):
        for change_type, path_str in changes:
            path = Path(path_str)

            if path.suffix != ".md":
                continue

            folder_name = path.parent.name
            source_url = f"{folder_name}/{path.name}"

            if change_type in (Change.added, Change.modified):
                logger.info(f"{'New' if change_type == Change.added else 'Updated'}: {source_url}")
                try:
                    count = ingest_single_file(path)
                    logger.info(f"Ingested {source_url} → {count} chunks")
                except Exception as e:
                    logger.error(f"Failed to ingest {source_url}: {e}")

            elif change_type == Change.deleted:
                logger.info(f"Deleted: {source_url} — removing from DB")
                try:
                    from wisey.db import get_connection
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM chunks WHERE source_url = %s", (source_url,))
                    deleted = cur.rowcount
                    conn.commit()
                    cur.close()
                    conn.close()
                    logger.info(f"Removed {deleted} chunks for {source_url}")
                except Exception as e:
                    logger.error(f"Failed to clean up {source_url}: {e}")


if __name__ == "__main__":
    main()
