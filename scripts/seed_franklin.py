#!/usr/bin/env python3

"""
Seed Franklin corpus into pgvector using VoyageAI embeddings (voyage-4).

Enhanced for Founders Online / historical letter files:
- Aggressive cleaning of footnotes, repetitions, editorial notes
- Smart splitting of oversized paras with better sentence handling
"""

import os
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import voyageai
from sqlalchemy import create_engine, text
from tqdm import tqdm, trange

from dotenv import load_dotenv
load_dotenv()

# ────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────

EMBED_MODEL          = "voyage-4"               # 1024 dims
CHUNK_TOKENS_TARGET  = 350
MAX_CHUNK_TOKENS     = 1400
OVERLAP_PARAGRAPHS   = 1
BATCH_SIZE           = 64                       # VoyageAI supports up to 128

vo = voyageai.Client()  # reads VOYAGE_API_KEY from env

MAX_RETRIES    = 5
BASE_BACKOFF   = 1.0
BACKOFF_FACTOR = 1.8

CORPUS_DIR = Path("corpus")

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL not set")

engine = create_engine(DB_URL)

# ────────────────────────────────────────────────
# Improved token estimation
# ────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    if not text.strip():
        return 0
    char_count = len(text)
    word_count = len(text.split())
    return max(1, int(char_count / 3.8) + word_count // 8)


# ────────────────────────────────────────────────
# Advanced cleaning for historical / Founders letters
# ────────────────────────────────────────────────

def clean_historical_letter(text: str) -> str:
    """Strip headers, footers, footnotes, repetitions, editorial notes."""
    # Remove Gutenberg-style if present
    text = re.sub(r"^\s*\*+.*START OF.*?\*+.*?\*+.*END OF.*?\*+\s*$", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Founders/Franklin Papers patterns
    # Remove repeated body sections (often duplicated 2–4x)
    # Heuristic: split on date lines or "November the" repeats, keep first occurrence
    date_pattern = r"(November the \d{1,2} 1765|This is November the \d|November the 7)"
    parts = re.split(date_pattern, text, flags=re.I)
    if len(parts) > 3:  # likely repetitions
        text = parts[0] + parts[1] + parts[2]  # keep up to first full body

    # Remove footnote blocks: lines starting with number + period, often repeated
    footnote_block = r"(?m)^\d+\s*\.\s*.*?(\n\s*\d+\s*\.\s*|$)"
    text = re.sub(footnote_block, "", text, flags=re.DOTALL)

    # Remove inline superscript numbers [1], 1., etc.
    text = re.sub(r"\[\d+\]|\b\d+\.\s*(?=[A-Z])|\s*\d+\s*$", "", text, flags=re.M)

    # Remove editorial lines
    editorial_patterns = [
        r"Note numbering follows the Franklin Papers source",
        r"Endorsed:.*",
        r"ALS : American Philosophical Society",
        r"Index Entries",
        r"Source: .*",
        r"From The Papers of Benjamin Franklin.*",
        r"\[Original source:.*?\]",
        r"Benjamin Franklin Papers.*",
    ]
    for pat in editorial_patterns:
        text = re.sub(pat, "", text, flags=re.I | re.DOTALL)

    # Normalize quotes, lines, collapse multiples
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip leading/trailing boilerplate
    text = re.sub(r"^(?:Deborah Franklin to Benjamin Franklin.*?|Benjamin Franklin Papers.*?|From Deborah Franklin.*?)\n+", "", text, flags=re.I | re.DOTALL)
    text = text.strip()

    return text


# ────────────────────────────────────────────────
# Better sentence splitter for splitting oversized
# ────────────────────────────────────────────────

def split_oversized_paragraph(para: str) -> List[str]:
    """Split large paragraph into sub-parts by sentences, avoiding common abbrevs."""
    # Improved sentence split (handles Mr., Dr., etc. better)
    sentence_re = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!|\;)\s+(?=[A-Z"“])')
    sentences = sentence_re.split(para.strip())

    sub_paras: List[str] = []
    current: List[str] = []
    current_tokens = 0

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        t = estimate_tokens(sent)
        if current_tokens + t > CHUNK_TOKENS_TARGET and current:
            sub_paras.append(" ".join(current).strip())
            current = []
            current_tokens = 0
        current.append(sent)
        current_tokens += t

    if current:
        sub_paras.append(" ".join(current).strip())

    # Final check: truncate if still huge (very rare now)
    for i, sub in enumerate(sub_paras):
        if estimate_tokens(sub) > MAX_CHUNK_TOKENS:
            print(f"    Warning: Truncating rare huge sub ({estimate_tokens(sub)} est tokens)")
            sub_paras[i] = sub[:8000] + " […] [truncated]"  # ~2000 tokens max

    return [s for s in sub_paras if s]


# ────────────────────────────────────────────────
# Chunking
# ────────────────────────────────────────────────

def chunk_paragraphs(text: str) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: List[str] = []
    buffer: List[str] = []
    buffer_tokens = 0

    for para in paragraphs:
        t = estimate_tokens(para)
        if t > MAX_CHUNK_TOKENS * 1.2:  # only split if clearly oversized
            print(f"    Splitting oversized para (~{t} est tokens)")
            sub_paras = split_oversized_paragraph(para)
        else:
            sub_paras = [para]

        for sub in sub_paras:
            sub_t = estimate_tokens(sub)
            if buffer_tokens + sub_t > CHUNK_TOKENS_TARGET and buffer:
                chunks.append("\n\n".join(buffer))
                buffer = buffer[-OVERLAP_PARAGRAPHS:]
                buffer_tokens = sum(estimate_tokens(p) for p in buffer)
            buffer.append(sub)
            buffer_tokens += sub_t

    if buffer:
        chunks.append("\n\n".join(buffer))

    return [c for c in chunks if estimate_tokens(c) > 10]  # skip tiny


def chunk_almanack(text: str) -> List[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    chunks = []
    for line in lines:
        t = estimate_tokens(line)
        if 5 < len(line) < 300 or t < MAX_CHUNK_TOKENS:
            chunks.append(line)
        elif t > MAX_CHUNK_TOKENS:
            print(f"    Splitting oversized almanack entry (~{t} est tokens)")
            chunks.extend(split_oversized_paragraph(line))
    return chunks


# ────────────────────────────────────────────────
# Tagging (unchanged)
# ────────────────────────────────────────────────

TAG_RULES: Dict[str, List[str]] = {
    "industry":  ["industry", "labor", "work", "diligence"],
    "virtue":    ["virtue", "temperance", "humility", "resolution", "prudence"],
    "finance":   ["money", "debt", "wealth", "frugality", "thrift"],
    "civic":     ["public", "society", "city", "assembly", "law", "government"],
    "education": ["learning", "study", "library", "school", "education", "knowledge"],
}

def auto_tags(text: str) -> List[str]:
    lower = text.lower()
    found = {tag for tag, words in TAG_RULES.items() if any(w in lower for w in words)}
    return sorted(found)


# ────────────────────────────────────────────────
# Embed batch with retry (unchanged)
# ────────────────────────────────────────────────

def embed_batch_with_retry(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = vo.embed(texts, model=EMBED_MODEL)
            embeddings = result.embeddings
            if len(embeddings) != len(texts):
                raise RuntimeError(f"Mismatch: {len(embeddings)} vs {len(texts)}")
            return embeddings
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise
            delay = BASE_BACKOFF * (BACKOFF_FACTOR ** (attempt - 1))
            print(f"  VoyageAI retry {attempt}/{MAX_RETRIES} after {delay:.1f}s → {e}")
            time.sleep(delay)


# ────────────────────────────────────────────────
# DB helpers (unchanged)
# ────────────────────────────────────────────────

def get_embedding_dimension() -> Optional[int]:
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT atttypmod - 4 FROM pg_attribute
                WHERE attrelid = 'franklin_passages.embedding'::regclass AND attname = 'embedding'
            """))
            dim = result.scalar()
            return dim if dim and dim > 0 else None
    except Exception:
        return None


def clear_table() -> None:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE franklin_passages"))


def insert_rows(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    with engine.begin() as conn:
        for row in tqdm(rows, desc="  Inserting", unit="row", leave=False):
            conn.execute(text("""
                INSERT INTO franklin_passages
                    (source, title, year, tags, token_count, content, embedding)
                VALUES (:source, :title, :year, :tags, :token_count, :content, :embedding)
            """), row)


# ────────────────────────────────────────────────
# Process file
# ────────────────────────────────────────────────

def process_file(path: Path) -> None:
    rel = path.relative_to(CORPUS_DIR)
    print(f"  {rel}")

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        cleaned = clean_historical_letter(raw)
    except Exception as e:
        print(f"    → Clean error: {e}")
        return

    source = path.stem.lower()

    if "almanack" in source:
        chunks = chunk_almanack(cleaned)
    else:
        chunks = chunk_paragraphs(cleaned)

    if not chunks:
        print("    → no chunks")
        return

    print(f"    → {len(chunks):,} chunks (cleaned len: {len(cleaned):,} chars)")

    rows = []

    for i in trange(0, len(chunks), BATCH_SIZE, desc="    Embedding", unit="batch", leave=False):
        batch = chunks[i:i + BATCH_SIZE]

        # Debug oversized
        for j, txt in enumerate(batch):
            et = estimate_tokens(txt)
            if et > MAX_CHUNK_TOKENS:
                print(f"      Oversized chunk {i+j} (~{et} est tokens, {len(txt)} chars) — should be rare now")

        try:
            embs = embed_batch_with_retry(batch)
        except Exception as e:
            print(f"    → Embed fail batch {i//BATCH_SIZE + 1}: {e}")
            continue

        for content, emb in zip(batch, embs):
            rows.append({
                "source": source,
                "title": path.name,
                "year": None,
                "tags": auto_tags(content),
                "token_count": estimate_tokens(content),
                "content": content,
                "embedding": emb,
            })

    if rows:
        insert_rows(rows)
        print(f"    → Inserted {len(rows):,} passages")


def main() -> None:
    print("Franklin corpus seeder (enhanced for letters)\n")

    db_dim = get_embedding_dimension()
    expected = 1024
    if db_dim is None:
        print("WARNING: Can't detect embedding dim — check table")
    elif db_dim != expected:
        print(f"ERROR: DB dim {db_dim} != model {expected} — fix VECTOR(1024)")
        return
    else:
        print(f"Dim check: OK ({db_dim})\n")

    print("Clearing table...")
    clear_table()

    txt_files = sorted(CORPUS_DIR.rglob("*.txt"))
    if not txt_files:
        print("No .txt files found")
        return

    print(f"Found {len(txt_files)} files\n")

    for path in tqdm(txt_files, desc="Files", unit="file"):
        process_file(path)

    print("\nDone.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"\nFatal: {e}")
        raise