"""Database helpers for storing and querying chunks."""

import os
import psycopg2

DEFAULT_DSN = "dbname=thinkwise_agent user={user} host=localhost".format(
    user=os.environ.get("PGUSER", os.environ.get("USER", "mattijsnaus"))
)


def get_connection(dsn: str | None = None):
    return psycopg2.connect(dsn or os.environ.get("DATABASE_URL", DEFAULT_DSN))


def insert_chunks(rows: list[dict], dsn: str | None = None) -> int:
    """Insert chunk rows into the database. Returns count inserted.

    Each row should have: content, embedding, source_url, source_type, title
    """
    conn = get_connection(dsn)
    cur = conn.cursor()
    inserted = 0
    try:
        for row in rows:
            cur.execute(
                """
                INSERT INTO chunks (content, embedding, source_url, source_type, title)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    row["content"],
                    row["embedding"],
                    row["source_url"],
                    row["source_type"],
                    row["title"],
                ),
            )
            inserted += 1
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return inserted


def clear_source(source_type: str, dsn: str | None = None) -> int:
    """Delete all chunks for a given source_type. Returns count deleted."""
    conn = get_connection(dsn)
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM chunks WHERE source_type = %s", (source_type,))
        count = cur.rowcount
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return count
