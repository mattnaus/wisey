"""Embed text chunks using OpenAI text-embedding-3-small."""

import os
from openai import OpenAI

MODEL = "text-embedding-3-small"
BATCH_SIZE = 100  # OpenAI supports up to 2048 inputs per request


def get_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required")
    return OpenAI(api_key=api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts, batching as needed. Returns list of 1536-dim vectors."""
    client = get_client()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        response = client.embeddings.create(model=MODEL, input=batch)
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

        if (i + BATCH_SIZE) < len(texts):
            print(f"[embed] Embedded {i + len(batch)}/{len(texts)} chunks")

    return all_embeddings
