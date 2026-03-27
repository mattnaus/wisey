# Wisey — Thinkwise Knowledge Agent

RAG-based agent that answers Thinkwise platform questions by searching a local vector database built from docs, community posts, release notes, and personal notes.

## Stack

| Layer | Tech | Notes |
|---|---|---|
| Vector DB | PostgreSQL 17 + pgvector 0.8 | Self-hosted on Mac Mini (M1) |
| Embeddings | Ollama `nomic-embed-text` | 768 dimensions, runs locally |
| LLM | Claude Sonnet (Anthropic API) | Grounded answers with citations |
| Crawler | crawl4ai 0.8 | Python, handles JS-rendered pages |
| Interfaces | MCP server, Telegram bot (Elvis), Web UI | In build order |

## Architecture

```
DATA SOURCES                      RUNTIME
  Thinkwise Docs                    Query embedder (same model)
  Community Forum        -->        Top-K retriever (k=8, cosine)
  Release Notes                     Claude Sonnet (answer + citations)
  Personal Notes (notes/)
        |                          INTERFACES
        v                            MCP server -> Claude Code tool
  INGESTION PIPELINE                 Telegram bot (Elvis)
    Crawler (crawl4ai)               Web UI
    Chunker (~512 tokens)
    Embedder
        |
        v
  STORAGE
    pgvector (chunks table)
```

## Data Sources

| Source | URL | Strategy | Est. Pages |
|---|---|---|---|
| Thinkwise Docs | docs.thinkwisesoftware.com | Sitemap -> crawl current version + blog | ~241 |
| Community Forum | community.thinkwisesoftware.com | Paginate categories -> crawl topics | ~6,700 |
| Release Notes | (included in docs blog) | -- | ~24 |
| Personal Notes | `notes/` folder | Direct file read | varies |

## Prerequisites

- macOS with Homebrew
- PostgreSQL 17 (`brew install postgresql@17`)
- pgvector (`brew install pgvector`)
- Python 3.13+ with [uv](https://docs.astral.sh/uv/)
- Ollama (`brew install ollama`) with `nomic-embed-text` model
- Anthropic API key (for Claude at query time)

## Setup

```bash
# Install dependencies
uv sync

# Database
brew services start postgresql@17
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
psql -U $(whoami) -d postgres -c "CREATE DATABASE thinkwise_agent;"
psql -U $(whoami) -d thinkwise_agent -f sql/001_init.sql

# Environment
cp .env.example .env
# Edit .env with your API keys
```

## Ingestion

```bash
# Crawl + chunk + embed + store Thinkwise docs
uv run python -m wisey.ingest docs

# Crawl + chunk + embed + store community forum
uv run python -m wisey.ingest community

# Both at once
uv run python -m wisey.ingest all

# Fresh re-ingest (clears existing chunks first)
uv run python -m wisey.ingest docs --fresh
```

## Project Structure

```
wisey/
  wisey/                  # Python package
    chunker.py            # Text -> overlapping ~512-token chunks
    clean.py              # Strip boilerplate from crawled markdown
    crawl_docs.py         # Docs crawler (sitemap-based)
    crawl_community.py    # Community forum crawler (pagination)
    db.py                 # Postgres/pgvector helpers
    embed.py              # OpenAI embedding client
    ingest.py             # Main pipeline: crawl -> chunk -> embed -> store
  sql/                    # Database migrations
    001_init.sql
  notes/                  # Personal markdown notes
  .env.example            # Required environment variables
  pyproject.toml          # Python project config
  CLAUDE.md               # Agent instructions
```

## Build Progress

- [x] PostgreSQL 17 + pgvector installed and verified
- [x] Database `thinkwise_agent` created with `chunks` table
- [x] Crawler + chunker built (docs + community)
- [x] Embeddings pipeline built
- [ ] First full crawl run (docs)
- [ ] First full crawl run (community)
- [ ] Basic agent query (embed -> retrieve -> Claude -> answer)
- [ ] MCP server
- [ ] Telegram bot (Elvis)
- [ ] Web UI
