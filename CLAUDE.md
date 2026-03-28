# Thinkwise Knowledge Agent

RAG-based agent that answers Thinkwise platform questions by searching a local vector database built from docs, community posts, release notes, and personal notes.

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Vector DB | Postgres + pgvector | Self-hosted on Mac Mini |
| Embeddings | Ollama nomic-embed-text | 768 dimensions, runs locally |
| LLM | Claude Sonnet (Anthropic API) | Via API at query time |
| Crawler | crawl4ai (docs), httpx (community) | Sitemap + pagination |
| Interfaces | MCP server, Telegram bot, Web UI (planned) | |

## Architecture

```
DATA SOURCES
  Thinkwise Docs (docs.thinkwisesoftware.com)
  Community Forum (community.thinkwisesoftware.com)
  Release Notes (included in docs blog)
  Personal Notes (notes/ folder)
        |
INGESTION PIPELINE
  Crawler (crawl4ai for docs, httpx for community)
  Chunker (~512 tokens, 50-token overlap, preserve headings)
  Embedder (nomic-embed-text via Ollama)
        |
STORAGE
  pgvector (Postgres) — chunks table
        |
RUNTIME
  Query embedder (same model)
  Top-K retriever (k=8, cosine similarity)
  Claude Sonnet (grounded answer + citations)
        |
INTERFACES
  MCP server — search_thinkwise + search_thinkwise_docs tools
  Telegram bot — text questions, /sources, /note
  Web UI (planned)
```

## Database Schema

```sql
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

1. **Postgres + pgvector setup** — done
2. **Crawler + chunker** — done (crawl4ai for docs sitemap, httpx for community pagination)
3. **Embed + store** — done (Ollama nomic-embed-text, 768 dims)
4. **Basic agent** — done (embed question -> retrieve top-k -> Claude Sonnet -> cited answer)
5. **MCP server** — done (search_thinkwise + search_thinkwise_docs)
6. **Telegram bot** — done (text questions, /sources, /note)
7. **Notes pipeline** — done (file watcher, Telegram /note, CLI)
8. **Cron + launchd** — done (monthly docs, weekly community pending, services auto-start)
9. **Web UI** — planned

## Current Status

- [x] Postgres + pgvector extension installed and verified
- [x] Database + chunks table created
- [x] Ollama + nomic-embed-text installed
- [x] Crawler + chunker built (docs sitemap + community httpx pagination)
- [x] Embeddings pipeline built
- [x] First crawl run (Thinkwise docs) — 241 pages, 3,172 chunks
- [x] First crawl run (community forum) — 3,303 topics, 5,735 chunks
- [x] Basic agent query working end-to-end
- [x] MCP server running
- [x] Telegram bot running (launchd: com.wisey.telegram-bot)
- [x] Notes pipeline (file watcher, /note command, CLI ingest)
- [x] Notes watcher running (launchd: com.wisey.watch-notes)
- [x] Cron: docs monthly (1st of month, 3am)
- [x] Cron: community weekly (Sundays 3am)
- [ ] Web UI

## Personal Notes Strategy

Flat `.md` files in `notes/` folder. Three ways to add:
1. Drop a file in `notes/` — file watcher auto-ingests
2. Telegram `/note <text>` — saves file + ingests immediately
3. CLI: `uv run python -m wisey.ingest notes`

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
- **nomic-embed-text over OpenAI**: runs locally, no API key, good enough for domain-specific retrieval
- **httpx over crawl4ai for community**: plain HTTP avoids rate limiting, site is SSR
- **Private GitHub repo**: internal notes may contain client-specific content
- **MCP server before web UI**: integrates directly into Claude Code workflow

## Environment

- Mac Mini (M1, 16 GB) — local server
- PostgreSQL 17.9 (Homebrew) — `brew services start postgresql@17`
- pgvector 0.8.2 — installed via Homebrew
- Ollama with nomic-embed-text — `brew services start ollama`
- Database: `thinkwise_agent`, user: `mattijsnaus`
- psql path: `/opt/homebrew/opt/postgresql@17/bin/psql`
- Tailscale for remote access
- Anthropic API key in `.env`
- Telegram bot token in `.env`

## Services

| Service | Managed by | Auto-start | Log |
|---|---|---|---|
| PostgreSQL | brew services | Yes | Homebrew |
| Ollama | brew services | Yes | Homebrew |
| Telegram bot | launchd | Yes + auto-restart | ~/wisey-telegram.log |
| Notes watcher | launchd | Yes + auto-restart | ~/wisey-watcher.log |

## SQL Migrations

Numbered files in `sql/`. Run in order against `thinkwise_agent`:

```bash
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
psql -U mattijsnaus -d thinkwise_agent -f sql/001_init.sql
psql -U mattijsnaus -d thinkwise_agent -f sql/002_vector_768.sql
```
