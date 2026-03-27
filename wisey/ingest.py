"""Main ingestion pipeline: crawl → chunk → embed → store."""

import argparse
import asyncio
import json
import os
import sys

from wisey.chunker import chunk_text
from wisey.crawl_community import crawl_community
from wisey.crawl_docs import crawl_docs
from wisey.db import clear_source, insert_chunks
from wisey.embed import embed_texts


def process_crawl_results(pages: list[dict]) -> list[dict]:
    """Chunk crawled pages and return flat list of chunk dicts (without embeddings yet)."""
    all_chunks = []
    for page in pages:
        chunks = chunk_text(page["markdown"], title=page.get("title"))
        for chunk_text_content in chunks:
            all_chunks.append({
                "content": chunk_text_content,
                "source_url": page["url"],
                "source_type": page["source_type"],
                "title": page.get("title", ""),
            })
    return all_chunks


def embed_and_store(chunks: list[dict], batch_label: str = "") -> int:
    """Embed chunks and insert into the database. Returns count stored."""
    if not chunks:
        print(f"[{batch_label}] No chunks to process")
        return 0

    print(f"[{batch_label}] Embedding {len(chunks)} chunks...")
    texts = [c["content"] for c in chunks]
    embeddings = embed_texts(texts)

    rows = []
    for chunk, embedding in zip(chunks, embeddings):
        rows.append({
            "content": chunk["content"],
            "embedding": str(embedding),  # pgvector accepts string format
            "source_url": chunk["source_url"],
            "source_type": chunk["source_type"],
            "title": chunk["title"],
        })

    count = insert_chunks(rows)
    print(f"[{batch_label}] Stored {count} chunks in database")
    return count


async def ingest_docs(fresh: bool = False):
    """Crawl and ingest Thinkwise documentation."""
    if fresh:
        deleted = clear_source("docs") + clear_source("release_notes")
        print(f"[docs] Cleared {deleted} existing chunks")

    pages = await crawl_docs()
    chunks = process_crawl_results(pages)
    print(f"[docs] {len(pages)} pages → {len(chunks)} chunks")
    return embed_and_store(chunks, "docs")


async def ingest_community(fresh: bool = False):
    """Crawl and ingest Thinkwise community forum."""
    if fresh:
        deleted = clear_source("community")
        print(f"[community] Cleared {deleted} existing chunks")

    pages = await crawl_community()
    chunks = process_crawl_results(pages)
    print(f"[community] {len(pages)} pages → {len(chunks)} chunks")
    return embed_and_store(chunks, "community")


async def main():
    parser = argparse.ArgumentParser(description="Ingest Thinkwise content into vector DB")
    parser.add_argument(
        "source",
        choices=["docs", "community", "all"],
        help="Which source to ingest",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Clear existing chunks for this source before ingesting",
    )
    args = parser.parse_args()

    total = 0
    if args.source in ("docs", "all"):
        total += await ingest_docs(fresh=args.fresh)
    if args.source in ("community", "all"):
        total += await ingest_community(fresh=args.fresh)

    print(f"\nDone! Total chunks stored: {total}")


if __name__ == "__main__":
    asyncio.run(main())
