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
    """Split a long paragraph into smaller chunks.

    Tries splitting by newlines first (handles tables and lists),
    then falls back to sentence boundaries, then hard splits by tokens.
    """
    import re

    # First try splitting by newlines (covers tables, lists, etc.)
    lines = [line for line in text.split("\n") if line.strip()]
    if len(lines) > 1:
        return _assemble_lines(lines, target, sep="\n")

    # Then try sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) > 1:
        return _assemble_lines(sentences, target, sep=" ")

    # Last resort: hard split by token count
    tokens = ENCODER.encode(text)
    chunks = []
    for i in range(0, len(tokens), target):
        chunks.append(ENCODER.decode(tokens[i : i + target]))
    return chunks


def _assemble_lines(lines: list[str], target: int, sep: str) -> list[str]:
    """Group lines into chunks that fit within target tokens."""
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for line in lines:
        lt = count_tokens(line)
        if current_tokens + lt > target and current:
            chunks.append(sep.join(current))
            current = []
            current_tokens = 0
        current.append(line)
        current_tokens += lt

    if current:
        chunks.append(sep.join(current))
    return chunks
