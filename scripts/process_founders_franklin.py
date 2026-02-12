#!/usr/bin/env python3

import re
from pathlib import Path

CORPUS_DIR = Path("corpus/founders_franklin")


# -------------------------------------------------------------------
# Garbage metadata patterns
# -------------------------------------------------------------------

GARBAGE_PATTERNS = [
    r"Benjamin Franklin Papers",
    r"Index Entries",
    r"Cite as",
    r"Original source:",
    r"National Archives",
    r"https://founders\.archives\.gov",
    r"\[Original source:.*?\]",
    r"Author Franklin, Benjamin",
    r"Recipient .*",
    r"\[Note numbering follows.*?\]",
]


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def normalize_line(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_signature_line(line: str) -> bool:
    return bool(re.match(r"^[Bb]\.?\s*Franklin$", line.strip()))


def fix_encoding(text: str) -> str:
    return (
        text.replace("â", "'")
            .replace("’", "'")
            .replace("â", " ")
    )


def merge_hyphen_wraps(text: str) -> str:
    return re.sub(r"-\n([a-z])", r"\1", text, flags=re.I)


def collapse_duplicate_signatures(text: str) -> str:
    return re.sub(r"(B\.?\s*Franklin)(?:\s*\n\s*B\.?\s*Franklin)+", r"\1", text)


# -------------------------------------------------------------------
# Cleaner
# -------------------------------------------------------------------

def clean_text(content: str) -> str:
    content = fix_encoding(content)
    content = merge_hyphen_wraps(content)

    lines = content.sp
