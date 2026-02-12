import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time

BASE = "https://franklinpapers.org"
INDEX = f"{BASE}/framedVolumes.jsp"
LETTERS_DIR = Path("corpus/letters")
LETTERS_DIR.mkdir(parents=True, exist_ok=True)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def fetch(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text


def parse_index(html):
    soup = BeautifulSoup(html, "html.parser")
    vols = []

    # all <a> links in table
    for a in soup.select("table a"):
        href = a.get("href")
        title = a.get_text(strip=True)
        if href and "frameVolume" in href:
            vols.append((title, BASE + "/" + href))
    return vols


def parse_volume(html):
    soup = BeautifulSoup(html, "html.parser")
    letters = []

    # Heuristic: each <h3> or <b> is a letter heading
    for h in soup.find_all(["h3", "b"]):
        heading = h.get_text(strip=True)
        body_parts = []
        # grab all following siblings until next <h3>/<b>
        for sib in h.next_siblings:
            if sib.name in ["h3", "b"]:
                break
            if getattr(sib, "get_text", None):
                body_parts.append(sib.get_text(" ", strip=True))
        body = "\n\n".join(body_parts).strip()
        if len(body) > 200:  # skip tiny fragments
            letters.append((heading, body))
    return letters


def main():
    index_html = fetch(INDEX)
    vols = parse_index(index_html)
    print(f"Found {len(vols)} volumes")

    total_letters = 0

    for title, url in vols:
        print("Processing", title)
        vol_html = fetch(url)
        letters = parse_volume(vol_html)

        for heading, body in letters:
            year_match = re.search(r"(17\d{2})", heading)
            year = year_match.group(1) if year_match else "unknown"

            filename = f"{year}_{slugify(heading)[:60]}.txt"
            path = LETTERS_DIR / filename
            if path.exists():
                continue
            path.write_text(body, encoding="utf-8")
            total_letters += 1

        time.sleep(0.5)  # polite

    print(f"\nSaved {total_letters} letters total.")


if __name__ == "__main__":
    main()
