#!/usr/bin/env python3
import re
from pathlib import Path
from collections import OrderedDict

CORPUS_DIR = Path("corpus/founders_franklin")

# Patterns to remove (case-insensitive where appropriate)
GARBAGE_PATTERNS = [
    r"Benjamin Franklin Papers",
    r"To Cadwallader Colden ALS : New-York Historical Society",
    r"Index Entries",
    r"\[Note numbering follows the Franklin Papers source\.\]",
    r"\d+\s*\.\s*(Not found|see above|etc\.)",
    r"See above, p\.\s*\d+",
    r"See also above",
    r"Cite as",
    r"Original source:",
    r"National Archives",
    r"https://founders\.archives\.gov",
    r"\[Original source:.*?\]",
    r"Author Franklin, Benjamin",
    r"Recipient Colden, Cadwallader",
    r"Date \d+ September \d{4}",
]

def clean_text(content: str) -> str:
    lines = content.splitlines()
    cleaned_lines = []
    seen = set()  # dedup normalized lines

    in_letter = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip garbage lines
        if any(re.search(pat, stripped, re.I) for pat in GARBAGE_PATTERNS):
            continue

        # Detect start of actual letter (date + salutation)
        if re.match(r"Philada\.|Philadelphia\.?\s*(Sept|September)\.?\s*\d{1,2},?\s*\d{4}", stripped, re.I):
            in_letter = True

        if not in_letter:
            continue

        # Normalize for dedup: lower, remove punctuation except apostrophes
        norm = re.sub(r"[^a-z0-9']+", " ", stripped.lower()).strip()
        if norm in seen:
            continue
        seen.add(norm)

        cleaned_lines.append(line.rstrip())  # preserve original

    text = "\n".join(cleaned_lines).strip()

    # Extra cleanup: collapse multiple newlines, fix smart quotes if desired
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.replace("â", "'").replace("â", " ").replace("’", "'")  # fix encoding artifacts

    # Trim trailing address/closing repeats if any
    if "B Franklin" in text:
        parts = text.split("B Franklin")
        text = parts[0] + "B Franklin" + (parts[1].split("\n\n")[0] if len(parts) > 1 else "")
        text = text.strip()

    return text


def main():
    total_cleaned = 0
    for file in CORPUS_DIR.glob("*.txt"):
        original = file.read_text(encoding="utf-8")
        cleaned = clean_text(original)

        if len(cleaned) < 200 or "Sir" not in cleaned:  # rough sanity
            print(f"Skipping suspicious/short: {file.name}")
            continue

        if cleaned != original.strip():
            file.write_text(cleaned + "\n", encoding="utf-8")
            total_cleaned += 1
            print(f"Cleaned: {file.name} (was {len(original)} chars → {len(cleaned)})")
        # else:
        #     print(f"Already good: {file.name}")

    print(f"\nProcessed {len(list(CORPUS_DIR.glob('*.txt')))} files; cleaned {total_cleaned} duplicates/garbage.")

if __name__ == "__main__":
    main()