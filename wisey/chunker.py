"""Split markdown text into overlapping chunks suitable for embedding."""

import tiktoken

ENCODER = tiktoken.encoding_for_model("text-embedding-3-small")
CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 50  # tokens


def count_tokens(text: str) -> int:
    return len(ENCODER.encode(text))


def chunk_text(text: str, title: str | None = None) -> list[str]:
    """Split text into chunks of ~CHUNK_SIZE tokens with CHUNK_OVERLAP overlap.

    If a title is provided, it is prepended to each chunk as context.
    Splits on paragraph boundaries first, then falls back to sentences.
    """
    if not text.strip():
        return []

    title_prefix = f"# {title}\n\n" if title else ""
    title_tokens = count_tokens(title_prefix)
    target = CHUNK_SIZE - title_tokens

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = count_tokens(para)

        # If a single paragraph exceeds target, split it by sentences
        if para_tokens > target:
            # Flush current buffer first
            if current_parts:
                chunks.append(title_prefix + "\n\n".join(current_parts))
                current_parts, current_tokens = _overlap_parts(current_parts, target)

            for sentence_chunk in _split_long_paragraph(para, target):
                chunks.append(title_prefix + sentence_chunk)
            continue

        if current_tokens + para_tokens > target and current_parts:
            chunks.append(title_prefix + "\n\n".join(current_parts))
            current_parts, current_tokens = _overlap_parts(current_parts, target)

        current_parts.append(para)
        current_tokens += para_tokens

    if current_parts:
        chunks.append(title_prefix + "\n\n".join(current_parts))

    return chunks


def _overlap_parts(parts: list[str], target: int) -> tuple[list[str], int]:
    """Return the tail of parts that fits within CHUNK_OVERLAP tokens."""
    overlap_parts: list[str] = []
    overlap_tokens = 0
    for p in reversed(parts):
        t = count_tokens(p)
        if overlap_tokens + t > CHUNK_OVERLAP:
            break
        overlap_parts.insert(0, p)
        overlap_tokens += t
    return overlap_parts, overlap_tokens


def _split_long_paragraph(text: str, target: int) -> list[str]:
    """Split a long paragraph into sentence-based chunks."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        st = count_tokens(sentence)
        if current_tokens + st > target and current:
            chunks.append(" ".join(current))
            current = []
            current_tokens = 0
        current.append(sentence)
        current_tokens += st

    if current:
        chunks.append(" ".join(current))
    return chunks
