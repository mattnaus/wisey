# Wisey — Thinkwise Knowledge Agent

RAG-based agent that answers Thinkwise platform questions by searching a local vector database built from docs, community posts, release notes, and personal notes.

## Stack

| Layer | Tech | Notes |
|---|---|---|
| Vector DB | PostgreSQL 17 + pgvector 0.8 | Self-hosted on Mac Mini (M1) |
| Embeddings | Ollama `nomic-embed-text` | 768 dimensions, runs locally |
| LLM | Claude Sonnet (Anthropic API) | Grounded answers with citations |
| Crawler | crawl4ai (docs), httpx (community) | Sitemap + pagination |
| Interfaces | MCP server, Telegram bot, Web UI (planned) | |

## Architecture

```
DATA SOURCES                      RUNTIME
  Thinkwise Docs                    Query embedder (same model)
  Community Forum        -->        Top-K retriever (k=8, cosine)
  Release Notes                     Claude Sonnet (answer + citations)
  Personal Notes (notes/)
        |                          INTERFACES
        v                            MCP server -> Claude Code tool
  INGESTION PIPELINE                 Telegram bot (Wisey)
    Crawler (crawl4ai / httpx)       Web UI (planned)
    Chunker (~512 tokens)
    Embedder (Ollama)
        |
        v
  STORAGE
    pgvector (chunks table)
```

## Data Sources

| Source | URL | Strategy | Est. Pages |
|---|---|---|---|
| Thinkwise Docs | docs.thinkwisesoftware.com | Sitemap -> crawl current version + blog | ~241 |
| Community Forum | community.thinkwisesoftware.com | Paginate categories -> crawl topics via httpx | ~3,300 |
| Release Notes | (included in docs blog) | -- | ~24 |
| Personal Notes | `notes/` folder | File watcher + Telegram /note | varies |

## Prerequisites

- macOS with Homebrew
- PostgreSQL 17 (`brew install postgresql@17`)
- pgvector (`brew install pgvector`)
- Python 3.13+ with [uv](https://docs.astral.sh/uv/)
- Ollama (`brew install ollama`) with `nomic-embed-text` model
- Anthropic API key (for Claude at query time)
- Telegram bot token (for the Telegram interface)

## Setup

```bash
# Install dependencies
uv sync

# Database
brew services start postgresql@17
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
psql -U $(whoami) -d postgres -c "CREATE DATABASE thinkwise_agent;"
psql -U $(whoami) -d thinkwise_agent -f sql/001_init.sql

# Ollama
brew services start ollama
ollama pull nomic-embed-text

# Environment
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and TELEGRAM_BOT_TOKEN
```

## Ingestion

```bash
# Crawl + chunk + embed + store Thinkwise docs
uv run python -m wisey.ingest docs

# Crawl + chunk + embed + store community forum
uv run python -m wisey.ingest community

# Ingest personal notes from notes/ folder
uv run python -m wisey.ingest notes

# All sources at once
uv run python -m wisey.ingest all

# Fresh re-ingest (clears existing chunks first)
uv run python -m wisey.ingest docs --fresh
```

### Scheduled ingestion

Cron jobs handle automatic re-ingestion:
- **Docs**: 1st of every month at 3am (`scripts/ingest-docs.sh`)
- **Community**: Weekly on Sundays at 3am (`scripts/ingest-community.sh`)
- **Notes**: Auto-ingested via file watcher (launchd service)

## Notes

Three ways to add notes to the knowledge base:

1. **Drop a `.md` file in `notes/`** -- the file watcher auto-ingests it
2. **Telegram `/note`** -- e.g. `/note Dynamic model breaks after 2025.3. Fix: re-run code gen.`
3. **CLI** -- `uv run python -m wisey.ingest notes --fresh`

## Query

```bash
# Ask a question (retrieves context + calls Claude)
uv run python -m wisey.agent "How do I deploy to Azure?"

# Retrieve-only mode (no Claude call, just show matching chunks)
uv run python -m wisey.agent --retrieve-only "branching in Software Factory"
```

## Telegram Bot

The Wisey bot responds to:
- **Any text message** -- full RAG answer via Claude with citations
- **/sources `<question>`** -- raw matched chunks without Claude
- **/note `<text>`** -- save and index a quick note
- **/start** -- welcome message

## MCP Server (Claude Code integration)

Add to `.claude/settings.json` in the project root:

```json
{
  "mcpServers": {
    "wisey": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/wisey", "python", "-m", "wisey.mcp_server"]
    }
  }
}
```

Exposes two tools:
- **search_thinkwise** -- AI-generated answer with citations
- **search_thinkwise_docs** -- raw source chunks for manual inspection

## Services (launchd)

These services auto-start on boot and restart on crash:

| Service | Label | Log |
|---|---|---|
| Telegram bot | `com.wisey.telegram-bot` | `~/wisey-telegram.log` |
| Notes watcher | `com.wisey.watch-notes` | `~/wisey-watcher.log` |
| PostgreSQL | `homebrew.mxcl.postgresql@17` | Homebrew managed |
| Ollama | `homebrew.mxcl.ollama` | Homebrew managed |

```bash
# Manage services
launchctl stop com.wisey.telegram-bot
launchctl start com.wisey.telegram-bot
tail -f ~/wisey-telegram.log
```

## Project Structure

```
wisey/
  wisey/                    # Python package
    agent.py                # Query agent: retrieve + Claude answer
    chunker.py              # Text -> overlapping ~512-token chunks
    clean.py                # Strip boilerplate from crawled markdown
    crawl_community.py      # Community crawler (httpx + pagination)
    crawl_docs.py           # Docs crawler (sitemap-based, crawl4ai)
    db.py                   # Postgres/pgvector helpers
    embed.py                # Ollama embedding client
    ingest.py               # Main pipeline CLI: crawl -> chunk -> embed -> store
    ingest_notes.py         # Notes ingestion + single-file ingest
    mcp_server.py           # MCP server for Claude Code
    telegram_bot.py         # Telegram bot
    watch_notes.py          # File watcher for notes/ folder
  scripts/                  # Cron scripts
    ingest-docs.sh          # Monthly docs re-ingestion
    ingest-community.sh     # Weekly community re-ingestion
  sql/                      # Database migrations
    001_init.sql
    002_vector_768.sql
  notes/                    # Personal markdown notes
  .env.example              # Required environment variables
  pyproject.toml            # Python project config
  CLAUDE.md                 # Agent instructions
```

## Build Progress

- [x] PostgreSQL 17 + pgvector installed and verified
- [x] Database `thinkwise_agent` created with `chunks` table
- [x] Crawler + chunker built (docs + community)
- [x] Embeddings pipeline (Ollama nomic-embed-text)
- [x] First full crawl run (docs) -- 241 pages, 3,172 chunks
- [x] First full crawl run (community) -- 3,303 topics, 5,735 chunks
- [x] Basic agent query working end-to-end
- [x] MCP server
- [x] Telegram bot
- [x] Notes pipeline (file watcher + Telegram /note + CLI)
- [x] Cron jobs (docs monthly, community weekly pending)
- [x] launchd services (auto-start on boot)
- [ ] Web UI
