"""Ingest markdown notes from the notes/ folder into the vector DB."""

import os
from pathlib import Path

from wisey.chunker import chunk_text
from wisey.db import clear_source, insert_chunks
from wisey.embed import embed_texts

NOTES_DIR = Path(__file__).parent.parent / "notes"


def read_notes(notes_dir: Path | None = None) -> list[dict]:
    """Read all .md files from the notes directory."""
    notes_dir = notes_dir or NOTES_DIR
    pages = []
    for md_file in sorted(notes_dir.glob("*.md")):
        content = md_file.read_text().strip()
        if not content:
            continue

        # Extract title from first heading or filename
        title = md_file.stem.replace("-", " ").strip()
        for line in content.splitlines():
            if line.startswith("## "):
                title = line.lstrip("# ").strip()
                break
            if line.startswith("# "):
                title = line.lstrip("# ").strip()
                break

        pages.append({
            "url": f"notes/{md_file.name}",
            "title": title,
            "markdown": content,
            "source_type": "notes",
        })

    return pages


def ingest_notes(fresh: bool = False) -> int:
    """Chunk, embed, and store notes. Returns count of chunks stored."""
    if fresh:
        deleted = clear_source("notes")
        if deleted:
            print(f"[notes] Cleared {deleted} existing chunks")

    pages = read_notes()
    if not pages:
        print("[notes] No notes found")
        return 0

    print(f"[notes] Found {len(pages)} notes")

    all_chunks = []
    for page in pages:
        chunks = chunk_text(page["markdown"], title=page.get("title"))
        for chunk_content in chunks:
            all_chunks.append({
                "content": chunk_content,
                "source_url": page["url"],
                "source_type": page["source_type"],
                "title": page["title"],
            })

    print(f"[notes] {len(pages)} notes → {len(all_chunks)} chunks")

    if not all_chunks:
        return 0

    texts = [c["content"] for c in all_chunks]
    embeddings = embed_texts(texts)

    rows = []
    for chunk, embedding in zip(all_chunks, embeddings):
        rows.append({
            "content": chunk["content"],
            "embedding": str(embedding),
            "source_url": chunk["source_url"],
            "source_type": chunk["source_type"],
            "title": chunk["title"],
        })

    count = insert_chunks(rows)
    print(f"[notes] Stored {count} chunks in database")
    return count


def ingest_single_note(filepath: Path) -> int:
    """Ingest a single note file. Removes old chunks for this file first."""
    from wisey.db import get_connection

    source_url = f"notes/{filepath.name}"

    # Remove old chunks for this specific note
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM chunks WHERE source_url = %s", (source_url,))
        conn.commit()
    finally:
        cur.close()
        conn.close()

    content = filepath.read_text().strip()
    if not content:
        return 0

    title = filepath.stem.replace("-", " ").strip()
    for line in content.splitlines():
        if line.startswith("## "):
            title = line.lstrip("# ").strip()
            break
        if line.startswith("# "):
            title = line.lstrip("# ").strip()
            break

    chunks = chunk_text(content, title=title)
    if not chunks:
        return 0

    embeddings = embed_texts(chunks)

    rows = [{
        "content": c,
        "embedding": str(e),
        "source_url": source_url,
        "source_type": "notes",
        "title": title,
    } for c, e in zip(chunks, embeddings)]

    return insert_chunks(rows)


if __name__ == "__main__":
    ingest_notes(fresh=True)
