#!/usr/bin/env python3

"""
Auto-download + clean Benjamin Franklin public domain texts
from Project Gutenberg and prepare the corpus/ directory.

Creates:

corpus/
  autobiography.txt
  almanack.txt
  way_to_wealth.txt
  silence_dogood.txt
  junto_rules.txt (stub template)
  letters/  (empty folder for manual additions)

Safe to re-run (overwrites files).
"""

import re
import requests
from pathlib import Path


# -------------------------
# Config
# -------------------------

CORPUS = Path("corpus")

SOURCES = {
    # Gutenberg IDs may change occasionally; these are stable as of now.
    "autobiography": "https://www.gutenberg.org/cache/epub/20203/pg20203.txt",
    "almanack_bundle": "https://www.gutenberg.org/cache/epub/50926/pg50926.txt",
    "silence_dogood": "https://www.gutenberg.org/cache/epub/36776/pg36776.txt",
    "poor_richards_improved": "https://www.gutenberg.org/cache/epub/43855/pg43855.txt",
    
}

HEADERS_RE = r"\*\*\* START OF.*?\*\*\*"
FOOTERS_RE = r"\*\*\* END OF.*?\*\*\*"


# -------------------------
# Helpers
# -------------------------

def download(url):
    print(f"Downloading {url}")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text


def clean_gutenberg(text: str) -> str:
    """Remove Gutenberg wrapper + normalize formatting"""

    text = re.sub(HEADERS_RE, "", text, flags=re.S)
    text = re.sub(FOOTERS_RE, "", text, flags=re.S)

    text = text.replace("\r\n", "\n")

    # normalize quotes
    text = text.replace("“", '"').replace("”", '"')

    # collapse extra blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def save(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Saved {path}")


# -------------------------
# Specialized cleaners
# -------------------------

def split_almanack_bundle(text: str):
    """
    Gutenberg edition usually contains:
    - Poor Richard’s Almanack
    - The Way to Wealth

    We split them heuristically.
    """

    lower = text.lower()

    idx = lower.find("the way to wealth")

    if idx != -1:
        almanack = text[:idx]
        wealth = text[idx:]
    else:
        # fallback: keep everything as almanack
        almanack = text
        wealth = ""

    return almanack, wealth


def clean_almanack(text: str):
    """
    Make aphorisms line-based.
    Perfect for your chunker.
    """

    lines = []

    for line in text.split("\n"):
        l = line.strip()

        if not l:
            continue

        # skip obvious headings
        if l.isupper() and len(l) > 20:
            continue

        lines.append(l)

    return "\n".join(lines)


# -------------------------
# Main
# -------------------------

def main():
    CORPUS.mkdir(exist_ok=True)

    # ---------------------
    # Autobiography
    # ---------------------
    auto = clean_gutenberg(download(SOURCES["autobiography"]))
    save(CORPUS / "autobiography.txt", auto)

    # ---------------------
    # Almanack + Way to Wealth
    # ---------------------
    bundle = clean_gutenberg(download(SOURCES["almanack_bundle"]))
    almanack, wealth = split_almanack_bundle(bundle)

    save(CORPUS / "almanack.txt", clean_almanack(almanack))

    if wealth:
        save(CORPUS / "way_to_wealth.txt", wealth)

    # ---------------------
    # Silence Dogood
    # ---------------------
    dogood = clean_gutenberg(download(SOURCES["silence_dogood"]))
    save(CORPUS / "silence_dogood.txt", dogood)

    # ---------------------
    # Junto rules template
    # ---------------------
    junto_stub = """
Junto Rules and Queries (Benjamin Franklin)

Paste the 24 Junto questions here manually.
They are short and copy-paste works best for historical accuracy.

Example:

1. Have you met with anything in the author you last read remarkable?
2. What new story have you lately heard agreeable for telling in conversation?
...
24. In what manner can the Junto assist you?
"""
    save(CORPUS / "junto_rules.txt", junto_stub.strip())

    # ---------------------
    # Letters directory
    # ---------------------
    (CORPUS / "letters").mkdir(exist_ok=True)

    print("\nDone.")
    print("Add individual letters manually into corpus/letters/*.txt")
    print("Then run your seed_franklin.py")


if __name__ == "__main__":
    main()
