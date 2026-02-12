#!/usr/bin/env python3

"""
Seed Franklin corpus into pgvector.

Features:
- Gutenberg cleaning
- Semantic paragraph chunking
- Aphorism splitting for almanack
- Token-aware chunk sizing
- Metadata tagging
- Batch embeddings
- Idempotent reseed (truncates table)
"""

import os
import re
import glob
from pathlib import Path

import tiktoken
from openai import OpenAI
from sqlalchemy import create_engine, text

# -----------------------------
# Config
# -----------------------------

EMBED_MODEL = "text-embedding-3-small"
CHUNK_TOKENS = 450
OVERLAP_PARAS = 1
BATCH_SIZE = 64

CORPUS_DIR = Path("corpus")

client = OpenAI()
engine = create_engine(os.getenv("DATABASE_URL"))

enc = tiktoken.encoding_for_model("gpt-4o")


# -----------------------------
# Cleaning
# -----------------------------

def clean_gutenberg(text: str) -> str:
    """Remove headers/footers + normalize whitespace"""

    # remove Gutenberg header/footer
    text = re.sub(r"\*\*\* START OF.*?\*\*\*", "", text, flags=re.S)
    text = re.sub(r"\*\*\* END OF.*?\*\*\*", "", text, flags=re.S)

    # normalize quotes
    text = text.replace("“", '"').replace("”", '"')

    # remove excessive whitespace
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# -----------------------------
# Token helpers
# -----------------------------

def tokens(s: str) -> int:
    return len(enc.encode(s))


# -----------------------------
# Chunking
# -----------------------------

def chunk_paragraphs(text: str):
    """
    Paragraph-aware chunking to ~450 tokens.
    Never split paragraphs.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    buf = []
    buf_tokens = 0

    for p in paragraphs:
        t = tokens(p)

        if buf_tokens + t > CHUNK_TOKENS and buf:
            chunks.append("\n\n".join(buf))

            # overlap last paragraph
            buf = buf[-OVERLAP_PARAS:]
            buf_tokens = sum(tokens(x) for x in buf)

        buf.append(p)
        buf_tokens += t

    if buf:
        chunks.append("\n\n".join(buf))

    return chunks


def chunk_almanack(text: str):
    """
    Each aphorism = chunk
    Perfect for retrieval.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    chunks = []
    for l in lines:
        if 5 < len(l) < 200:
            chunks.append(l)

    return chunks


# -----------------------------
# Tagging
# -----------------------------

TAG_RULES = {
    "industry": ["industry", "labor", "work", "diligence"],
    "virtue": ["virtue", "temperance", "humility", "resolution"],
    "finance": ["money", "debt", "wealth", "frugality"],
    "civic": ["public", "society", "city", "assembly", "law"],
    "education": ["learning", "study", "library", "school"],
}


def auto_tags(text):
    lower = text.lower()
    tags = []

    for tag, words in TAG_RULES.items():
        if any(w in lower for w in words):
            tags.append(tag)

    return tags


# -----------------------------
# Embeddings
# -----------------------------

def embed_batch(texts):
    res = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts
    )
    return [d.embedding for d in res.data]


# -----------------------------
# DB
# -----------------------------

def clear_table():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE franklin_passages"))


def insert_rows(rows):
    with engine.begin() as conn:
        for r in rows:
            conn.execute(text("""
                INSERT INTO franklin_passages
                (source, title, year, tags, token_count, content, embedding)
                VALUES (:source, :title, :year, :tags, :token_count, :content, :embedding)
            """), r)


# -----------------------------
# Main processing
# -----------------------------

def process_file(path: Path):
    print(f"Processing {path.name}")

    raw = path.read_text(encoding="utf-8")
    text_clean = clean_gutenberg(raw)

    source = path.stem

    if "almanack" in source.lower():
        chunks = chunk_almanack(text_clean)
    else:
        chunks = chunk_paragraphs(text_clean)

    rows = []

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i+BATCH_SIZE]
        embeddings = embed_batch(batch)

        for content, emb in zip(batch, embeddings):
            rows.append({
                "source": source,
                "title": path.name,
                "year": None,
                "tags": auto_tags(content),
                "token_count": tokens(content),
                "content": content,
                "embedding": emb
            })

    insert_rows(rows)
    print(f"Inserted {len(rows)} chunks")


def main():
    print("Clearing existing corpus...")
    clear_table()

    # top-level files
    for file in CORPUS_DIR.glob("*.txt"):
        process_file(file)

    # letters subfolder
    letters_dir = CORPUS_DIR / "letters"
    if letters_dir.exists():
        for file in letters_dir.glob("*.txt"):
            process_file(file)

    print("\nDone seeding Franklin corpus.")


if __name__ == "__main__":
    main()
