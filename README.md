# Wisey — Thinkwise Knowledge Agent

RAG-based agent that answers Thinkwise platform questions by searching a local vector database built from docs, community posts, release notes, and personal notes.

## Stack

| Layer | Tech | Notes |
|---|---|---|
| Vector DB | PostgreSQL 17 + pgvector 0.8 | Self-hosted on Mac Mini (M1) |
| Embeddings | OpenAI `text-embedding-3-small` | 1536 dimensions |
| LLM | Claude Sonnet (Anthropic API) | Grounded answers with citations |
| Crawler | crawl4ai | Python, handles JS-rendered pages |
| Interfaces | MCP server, Telegram bot (Elvis), Web UI | In build order |

## Architecture

```
DATA SOURCES                      RUNTIME
  Thinkwise Docs                    Query embedder (same model)
  Community Forum        ──►        Top-K retriever (k=8, cosine)
  Release Notes                     Claude Sonnet (answer + citations)
  Personal Notes (notes/)
        │                          INTERFACES
        ▼                            MCP server → Claude Code tool
  INGESTION PIPELINE                 Telegram bot (Elvis)
    Crawler (crawl4ai)               Web UI
    Chunker (~512 tokens)
    Embedder
        │
        ▼
  STORAGE
    pgvector (chunks table)
```

## Prerequisites

- macOS with Homebrew
- PostgreSQL 17 (`brew install postgresql@17`)
- pgvector (`brew install pgvector`)
- OpenAI API key (for embeddings)
- Anthropic API key (for Claude at query time)

## Database Setup

```bash
# Start Postgres
brew services start postgresql@17

# Create database and run schema
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
psql -U $(whoami) -d postgres -c "CREATE DATABASE thinkwise_agent;"
psql -U $(whoami) -d thinkwise_agent -f sql/001_init.sql
```

## Project Structure

```
wisey/
├── sql/            # Database migrations (numbered)
│   └── 001_init.sql
├── notes/          # Personal markdown notes (embedded into vector DB)
├── CLAUDE.md       # Agent instructions
└── README.md
```

## Build Progress

- [x] PostgreSQL 17 + pgvector installed and verified
- [x] Database `thinkwise_agent` created
- [x] `chunks` table with vector index created
- [ ] OpenAI API key configured
- [ ] Crawler + chunker (crawl4ai)
- [ ] Embeddings pipeline
- [ ] Basic agent query (embed → retrieve → Claude → answer)
- [ ] MCP server
- [ ] Telegram bot (Elvis)
- [ ] Web UI
