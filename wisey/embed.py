"""Embed text chunks using Ollama with nomic-embed-text (768 dimensions)."""

import httpx

OLLAMA_URL = "http://localhost:11434/api/embed"
MODEL = "nomic-embed-text"
BATCH_SIZE = 50  # Ollama handles batches via the input list


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts via Ollama. Returns list of 768-dim vectors."""
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        response = httpx.post(
            OLLAMA_URL,
            json={"model": MODEL, "input": batch},
            timeout=120.0,
        )
        response.raise_for_status()
        batch_embeddings = response.json()["embeddings"]
        all_embeddings.extend(batch_embeddings)

        if (i + BATCH_SIZE) < len(texts):
            print(f"[embed] Embedded {i + len(batch)}/{len(texts)} chunks")

    return all_embeddings
