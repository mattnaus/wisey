"""Ingest markdown files from notes/ and guides/ folders into the vector DB."""

from pathlib import Path

from wisey.chunker import chunk_text
from wisey.db import clear_source, get_connection, insert_chunks
from wisey.embed import embed_texts

NOTES_DIR = Path(__file__).parent.parent / "notes"
GUIDES_DIR = Path(__file__).parent.parent / "guides"

# Map folder name to source_type
FOLDER_SOURCES = {
    "notes": ("notes", NOTES_DIR),
    "guides": ("guides", GUIDES_DIR),
}


def _extract_title(content: str, filename: str) -> str:
    """Extract title from first heading or fall back to filename."""
    title = filename.replace("-", " ").strip()
    for line in content.splitlines():
        if line.startswith("## "):
            title = line.lstrip("# ").strip()
            break
        if line.startswith("# "):
            title = line.lstrip("# ").strip()
            break
    return title


def read_folder(source_type: str, folder: Path) -> list[dict]:
    """Read all .md files from a folder."""
    pages = []
    for md_file in sorted(folder.glob("*.md")):
        content = md_file.read_text().strip()
        if not content:
            continue

        title = _extract_title(content, md_file.stem)
        pages.append({
            "url": f"{folder.name}/{md_file.name}",
            "title": title,
            "markdown": content,
            "source_type": source_type,
        })
    return pages


def _embed_and_store(pages: list[dict], label: str) -> int:
    """Chunk, embed, and store pages. Returns count of chunks stored."""
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

    print(f"[{label}] {len(pages)} files → {len(all_chunks)} chunks")

    if not all_chunks:
        return 0

    texts = [c["content"] for c in all_chunks]
    embeddings = embed_texts(texts)

    rows = [{
        "content": chunk["content"],
        "embedding": str(embedding),
        "source_url": chunk["source_url"],
        "source_type": chunk["source_type"],
        "title": chunk["title"],
    } for chunk, embedding in zip(all_chunks, embeddings)]

    count = insert_chunks(rows)
    print(f"[{label}] Stored {count} chunks in database")
    return count


def ingest_notes(fresh: bool = False) -> int:
    """Ingest notes/ folder."""
    if fresh:
        deleted = clear_source("notes")
        if deleted:
            print(f"[notes] Cleared {deleted} existing chunks")

    pages = read_folder("notes", NOTES_DIR)
    if not pages:
        print("[notes] No notes found")
        return 0

    print(f"[notes] Found {len(pages)} notes")
    return _embed_and_store(pages, "notes")


def ingest_guides(fresh: bool = False) -> int:
    """Ingest guides/ folder."""
    if fresh:
        deleted = clear_source("guides")
        if deleted:
            print(f"[guides] Cleared {deleted} existing chunks")

    pages = read_folder("guides", GUIDES_DIR)
    if not pages:
        print("[guides] No guides found")
        return 0

    print(f"[guides] Found {len(pages)} guides")
    return _embed_and_store(pages, "guides")


def ingest_single_file(filepath: Path) -> int:
    """Ingest a single .md file from notes/ or guides/. Removes old chunks first."""
    folder_name = filepath.parent.name
    source_type = folder_name if folder_name in ("notes", "guides") else "notes"
    source_url = f"{folder_name}/{filepath.name}"

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

    title = _extract_title(content, filepath.stem)
    chunks = chunk_text(content, title=title)
    if not chunks:
        return 0

    embeddings = embed_texts(chunks)

    rows = [{
        "content": c,
        "embedding": str(e),
        "source_url": source_url,
        "source_type": source_type,
        "title": title,
    } for c, e in zip(chunks, embeddings)]

    return insert_chunks(rows)


# Keep backward compat for telegram bot import
ingest_single_note = ingest_single_file


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target in ("notes", "all"):
        ingest_notes(fresh=True)
    if target in ("guides", "all"):
        ingest_guides(fresh=True)
