"""Core agent: embed question → retrieve chunks → ask Claude → return answer."""

import os

from dotenv import load_dotenv

load_dotenv()

import anthropic

from wisey.db import get_connection
from wisey.embed import embed_texts

CLAUDE_MODEL = "claude-sonnet-4-20250514"
TOP_K = 8

SYSTEM_PROMPT = """\
You are Wisey, a knowledgeable assistant for the Thinkwise low-code platform.
You answer questions using the retrieved documentation and community posts below.

Rules:
- Base your answer ONLY on the provided context. If the context doesn't contain \
enough information, say so honestly.
- Cite your sources using [title](url) markdown links.
- Be concise and practical. Thinkwise users are typically developers or consultants.
- If the question is about a specific version, note which version the docs refer to.
- For code or SQL examples, use fenced code blocks.
"""


def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    """Embed the query and retrieve the most similar chunks."""
    query_embedding = embed_texts([query])[0]

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Disable index scan when table is small; IVFFlat needs data to work well
        cur.execute("SET enable_indexscan = off")
        cur.execute(
            """
            SELECT content, source_url, source_type, title,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (str(query_embedding), str(query_embedding), top_k),
        )
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    return [
        {
            "content": row[0],
            "source_url": row[1],
            "source_type": row[2],
            "title": row[3],
            "similarity": row[4],
        }
        for row in rows
    ]


def format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context block for Claude."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source_label = chunk["source_type"].replace("_", " ").title()
        parts.append(
            f"--- Source {i} [{source_label}]: {chunk['title']} ---\n"
            f"URL: {chunk['source_url']}\n"
            f"Similarity: {chunk['similarity']:.4f}\n\n"
            f"{chunk['content']}\n"
        )
    return "\n".join(parts)


def ask(question: str, top_k: int = TOP_K) -> str:
    """Full agent pipeline: retrieve context, ask Claude, return answer."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is required")

    chunks = retrieve(question, top_k=top_k)
    if not chunks:
        return "No relevant documents found. The vector database may be empty."

    context = format_context(chunks)
    user_message = f"## Context\n\n{context}\n\n## Question\n\n{question}"

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ask Wisey a Thinkwise question")
    parser.add_argument("question", nargs="+", help="Your question")
    parser.add_argument("--retrieve-only", action="store_true",
                        help="Only show retrieved chunks, don't call Claude")
    parser.add_argument("--top-k", type=int, default=TOP_K,
                        help=f"Number of chunks to retrieve (default: {TOP_K})")
    args = parser.parse_args()

    question = " ".join(args.question)
    print(f"Q: {question}\n")

    if args.retrieve_only:
        chunks = retrieve(question, top_k=args.top_k)
        for i, c in enumerate(chunks, 1):
            label = c["source_type"].replace("_", " ").title()
            print(f"{i}. [{c['similarity']:.4f}] [{label}] {c['title']}")
            print(f"   {c['source_url']}")
            print(f"   {c['content'][:150]}...")
            print()
    else:
        answer = ask(question, top_k=args.top_k)
        print(answer)
