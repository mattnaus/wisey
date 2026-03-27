"""MCP server exposing Wisey as a Claude Code tool."""

import os

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP

from wisey.agent import ask, retrieve

mcp = FastMCP(
    "wisey",
    instructions="Thinkwise Knowledge Agent — search docs, community posts, and notes",
)


@mcp.tool()
def search_thinkwise(query: str) -> str:
    """Search the Thinkwise knowledge base and get an AI-generated answer.

    Searches across Thinkwise documentation, community forum posts, release notes,
    and personal notes. Returns a grounded answer with source citations.

    Use this for any question about the Thinkwise low-code platform, including:
    - Software Factory features and configuration
    - IAM (Intelligent Application Manager) setup
    - Indicium API configuration
    - Deployment (Azure, on-premise, containers)
    - GUI behavior (Universal, Windows, Web)
    - SQL patterns and best practices
    - Release notes and version changes
    """
    return ask(query)


@mcp.tool()
def search_thinkwise_docs(query: str, top_k: int = 8) -> str:
    """Search the Thinkwise knowledge base and return raw source chunks.

    Returns the most relevant documentation chunks without AI summarization.
    Useful when you want to see the raw source material and form your own answer.
    """
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return "No relevant documents found."

    parts = []
    for i, c in enumerate(chunks, 1):
        label = c["source_type"].replace("_", " ").title()
        parts.append(
            f"## {i}. [{label}] {c['title']} (similarity: {c['similarity']:.4f})\n"
            f"URL: {c['source_url']}\n\n"
            f"{c['content']}\n"
        )
    return "\n---\n\n".join(parts)


if __name__ == "__main__":
    mcp.run()
