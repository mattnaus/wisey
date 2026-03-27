-- 001_init.sql
-- Initial schema for the Thinkwise Knowledge Agent
-- Run against: thinkwise_agent database on Mac Mini

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

-- IVFFlat index for cosine similarity search.
-- NOTE: Rebuild this index after loading a significant amount of data:
--   DROP INDEX chunks_embedding_idx;
--   CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX chunks_embedding_idx ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
