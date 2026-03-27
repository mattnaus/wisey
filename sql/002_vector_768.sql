-- 002_vector_768.sql
-- Switch from 1536-dim (OpenAI) to 768-dim (nomic-embed-text via Ollama)

DROP INDEX IF EXISTS chunks_embedding_idx;

ALTER TABLE chunks
    ALTER COLUMN embedding TYPE vector(768);

CREATE INDEX chunks_embedding_idx ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
