# Thinkwise Knowledge Agent

RAG-based agent that answers Thinkwise platform questions by searching a local vector database built from docs, community posts, release notes, and personal notes.

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Vector DB | Postgres + pgvector | Self-hosted on Mac Mini |
| Embeddings | Ollama nomic-embed-text | 768 dimensions, runs locally |
| LLM | Claude Sonnet (Anthropic API) | Via API at query time |
| Crawler | crawl4ai | Python, handles JS-rendered pages |
| Interfaces | MCP server, Telegram bot (Elvis), Web UI | Build in this order |

## Architecture

```
DATA SOURCES
  ├── Thinkwise Docs (docs.thinkwisesoftware.com)
  ├── Community Forum (community.thinkwisesoftware.com)
  ├── Release Notes
  └── Personal Notes (markdown files)
        ↓
INGESTION PIPELINE
  ├── Crawler (crawl4ai, weekly cron)
  ├── Chunker (~512 tokens, 50-token overlap, preserve headings)
  └── Embedder (nomic-embed-text via Ollama)
        ↓
STORAGE
  └── pgvector (Postgres) — chunks table (see schema below)
        ↓
RUNTIME
  ├── Query embedder (same model)
  ├── Top-K retriever (k=8, cosine similarity)
  ├── Reranker (optional, skip initially)
  └── Claude Sonnet (grounded answer + citations)
        ↓
INTERFACES
  ├── MCP server → Claude Code tool: search_thinkwise_docs(query)
  ├── Telegram bot (Elvis)
  └── Web UI
```

## Database Schema

```sql
-- Run on Mac Mini Postgres instance
CREATE DATABASE thinkwise_agent;

\c thinkwise_agent

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
    id          SERIAL PRIMARY KEY,
    content     TEXT NOT NULL,
    embedding   vector(768),
    source_url  TEXT,
    source_type TEXT,   -- 'docs' | 'community' | 'release_notes' | 'notes'
    title       TEXT,
    crawled_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## Build Order

1. **Postgres + pgvector setup** ✅ done
2. **Crawler + chunker** ✅ done — crawl4ai, sitemap for docs, pagination for community
3. **Embed + store** ✅ done — OpenAI text-embedding-3-small, batch embedding pipeline
4. **Basic agent** — embed question → retrieve top-k → call Claude API → return answer
5. **MCP server** — wrap agent as Claude Code tool
6. **Elvis / Telegram** — query from phone while at client
7. **Web UI** — simple internal dev interface

## Current Status

- [x] Postgres + pgvector extension installed and verified
- [x] Database + chunks table created
- [x] Ollama + nomic-embed-text installed (replaces OpenAI embeddings)
- [x] Crawler + chunker built (docs sitemap + community pagination)
- [x] Embeddings pipeline built
- [ ] First crawl run (Thinkwise docs)
- [ ] First crawl run (community forum)
- [ ] Basic agent query working end-to-end
- [ ] MCP server running
- [ ] Elvis bot connected

## Personal Notes Strategy

No centralised note system — bootstrapping from scattered sources:
- Past Claude conversations (mine these first)
- Slack messages where problems were explained
- SQL script comments
- Emails with client solutions

Format: flat `.md` files in `notes/` folder. No special structure needed — the embedder handles it.

Example note format:
```markdown
## [Short title of the problem/solution]
Date: [approx date]
Problem: [what broke or was unclear]
Fix: [what actually worked]
Why: [the reason, if known]
```

## Key Decisions

- **pgvector over Qdrant**: reuse existing Postgres, fewer moving parts
- **text-embedding-3-small**: cheap, accurate, 1536 dims — sweet spot for this use case
- **Private GitHub repo first**: internal notes may contain client-specific content
- **MCP server before web UI**: integrates directly into Claude Code workflow

## Environment

- Mac Mini (M1, 16 GB) — local server
- PostgreSQL 17.9 (Homebrew) — `brew services start postgresql@17`
- pgvector 0.8.2 — installed via Homebrew
- Database: `thinkwise_agent`, user: `mattijsnaus` (default local user)
- psql path: `/opt/homebrew/opt/postgresql@17/bin/psql`
- Tailscale for remote access
- OpenAI API key required for embeddings
- Anthropic API key required for Claude at query time

## SQL Migrations

Numbered files in `sql/`. Run in order against `thinkwise_agent`:

```bash
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
psql -U mattijsnaus -d thinkwise_agent -f sql/001_init.sql
```