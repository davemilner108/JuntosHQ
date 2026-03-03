-- Run once
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS franklin_passages (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT,
    year INT,
    tags TEXT[],
    token_count INT,
    content TEXT NOT NULL,
    embedding vector(1024)
);

CREATE INDEX IF NOT EXISTS franklin_embedding_idx
ON franklin_passages
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
