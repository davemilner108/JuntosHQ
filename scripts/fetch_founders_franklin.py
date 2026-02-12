#!/usr/bin/env python3
import json
import time
import requests
from pathlib import Path
import re
from tqdm import tqdm
from bs4 import BeautifulSoup

# ----------------------------
# Configuration
# ----------------------------
CORPUS_DIR = Path("corpus/founders_franklin")
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

METADATA_FILE = Path("corpus/founders_online_metadata.json")

HTML_BASE = "https://founders.archives.gov/documents/Franklin"
TEXT_BASE  = f"{HTML_BASE}"  # for /letter-text or /transcript attempts

DELAY = 1.0          # Increased for politeness (adjust as needed)
MIN_YEAR = 1720
USER_AGENT = "FranklinCorpusBuilder/1.0 (contact: your.email@example.com)"  # Be polite!

DEBUG_HTML = False   # Set True to save failing pages for inspection

# ----------------------------
# Helpers
# ----------------------------
def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")

def extract_doc_id(permalink: str) -> str:
    return permalink.rstrip("/").split("/")[-1]

def fetch_clean_text(doc_id: str, session: requests.Session) -> str:
    """
    Try plain-text endpoints first → fallback to HTML parsing.
    Returns cleaned text or empty string on failure.
    """
    text = ""

    # Preferred: Try /letter-text (often plain text, clean transcription)
    for suffix in ["/letter-text", "/transcript"]:  # some docs use one or the other
        url = f"{HTML_BASE}/{doc_id}{suffix}"
        try:
            r = session.get(url, timeout=20)
            if r.status_code == 200:
                text = r.text.strip()
                if text and len(text) > 100:  # rough sanity check
                    # Minimal cleanup
                    text = re.sub(r"\n{3,}", "\n\n", text)
                    text = re.sub(r"[ \t]+", " ", text)
                    print(f"Success via {suffix} for {doc_id}")
                    return text
        except Exception as e:
            print(f"Plain-text attempt {suffix} failed for {doc_id}: {e}")

    # Fallback: Scrape HTML
    url = f"{HTML_BASE}/{doc_id}"
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Modern selectors (2025–2026 structure) — try in order of likelihood
        candidates = [
            soup.find("div", class_=re.compile(r"(transcript|letter-text|document-body)", re.I)),
            soup.find("main"),
            soup.find("div", {"role": "main"}),
            soup.find("article"),
            soup.find("div", class_="content"),
            soup.find("div", id=re.compile(r"(content|body|main)", re.I)),
        ]
        content_div = next((c for c in candidates if c), None)

        if not content_div:
            print(f"No suitable content container found for {doc_id}")
            if DEBUG_HTML:
                Path(f"debug_{doc_id}.html").write_text(r.text, encoding="utf-8")
            return ""

        # Remove unwanted elements
        for tag in content_div(["script", "style", "sup", "aside", "footer", "nav", "header"]):
            tag.decompose()

        # Convert <em>/<i> to *markdown italics*
        for em in content_div.find_all(["em", "i"]):
            if em.string:
                em.string.replace_with(f"*{em.get_text(strip=True)}*")

        # Extract paragraphs, lists, pre
        lines = []
        for block in content_div.find_all(["p", "li", "pre", "div"]):
            txt = block.get_text(" ", strip=True)
            if txt and len(txt) > 1:
                lines.append(txt)

        text = "\n\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        if text:
            print(f"Success via HTML fallback for {doc_id}")
            return text

    except Exception as e:
        print(f"HTML fetch/parse failed for {doc_id}: {e}")

    return ""

# ----------------------------
# Main
# ----------------------------
def main():
    if not METADATA_FILE.exists():
        print(f"Metadata file missing: {METADATA_FILE}")
        print("Download from: https://founders.archives.gov/Metadata/founders-online-metadata.json")
        return

    data = json.loads(METADATA_FILE.read_text(encoding="utf-8"))

    # Filter Franklin documents
    franklin_docs = []
    for d in data:
        if d.get("project") != "Franklin Papers":
            continue
        authors = d.get("authors") or []
        if not any("Franklin" in a for a in authors):
            continue
        date_from = d.get("date-from") or "0"
        try:
            year = int(date_from[:4])
        except (ValueError, TypeError):
            continue
        if year < MIN_YEAR:
            continue
        franklin_docs.append(d)

    print(f"Found {len(franklin_docs)} potential Franklin documents.")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    total_saved = 0

    for doc in tqdm(franklin_docs, desc="Processing Franklin docs"):
        doc_title = doc.get("title", "untitled")
        permalink = doc.get("permalink", "")
        if not permalink:
            continue

        doc_id = extract_doc_id(permalink)
        content = fetch_clean_text(doc_id, session)

        if not content:
            print(f"Skipping {doc_title} ({doc_id}): no usable text")
            print(f"  URL: {HTML_BASE}/{doc_id}")
            continue

        # Filename
        date = doc.get("date-from") or doc.get("date-to") or "undated"
        title_slug = slugify(doc_title)[:80]
        filename = f"{date}_{title_slug}.txt"
        path = CORPUS_DIR / filename

        if path.exists():
            # print(f"Already exists: {filename}")
            continue

        path.write_text(content, encoding="utf-8")
        total_saved += 1
        time.sleep(DELAY)

    print(f"\nDone. Saved {total_saved} new Franklin letters to {CORPUS_DIR}")
    print(f"Total documents processed: {len(franklin_docs)}")

if __name__ == "__main__":
    main()