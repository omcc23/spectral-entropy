"""
Download classics from Project Gutenberg in multiple languages.

Languages: French, German, Spanish, Italian, Portuguese, Dutch, Polish, Finnish, Russian, Swedish

Usage:
    uv run fetch_gutenberg_multilingual.py
"""
import os, re, time, urllib.request, urllib.error

OUT_BASE = os.path.join(os.path.dirname(__file__), "texts", "gutenberg_multi")

GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
GUTENBERG_URL2 = "https://www.gutenberg.org/files/{id}/{id}-0.txt"

# ─── Curated book lists per language ─────────────────────────────────────────
# Format: (gutenberg_id, title, author)
from new_catalog import BOOKS


def strip_gutenberg_header(text):
    start_markers = [
        "*** START OF THIS PROJECT GUTENBERG",
        "*** START OF THE PROJECT GUTENBERG",
        "***START OF THIS PROJECT GUTENBERG",
    ]
    end_markers = [
        "*** END OF THIS PROJECT GUTENBERG",
        "*** END OF THE PROJECT GUTENBERG",
        "***END OF THIS PROJECT GUTENBERG",
        "End of the Project Gutenberg",
        "End of Project Gutenberg",
    ]
    start_idx = 0
    for m in start_markers:
        idx = text.find(m)
        if idx != -1:
            nl = text.find("\n", idx)
            if nl != -1:
                start_idx = nl + 1
            break
    end_idx = len(text)
    for m in end_markers:
        idx = text.find(m)
        if idx != -1:
            end_idx = idx
            break
    return text[start_idx:end_idx].strip()


def download_book(lang, book_id, title):
    lang_dir = os.path.join(OUT_BASE, lang.lower())
    os.makedirs(lang_dir, exist_ok=True)
    safe_title = re.sub(r'[^a-zA-Z0-9]+', '_', title).strip('_').lower()
    outpath = os.path.join(lang_dir, f"{book_id}_{safe_title}.txt")

    if os.path.exists(outpath) and os.path.getsize(outpath) > 1000:
        print(f"  ✓ Exists: [{lang}] {title} ({os.path.getsize(outpath):,}b)")
        return True

    urls = [
        GUTENBERG_URL.format(id=book_id),
        GUTENBERG_URL2.format(id=book_id),
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Research; entropy-analysis)'
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                try:
                    text = raw.decode('utf-8')
                except UnicodeDecodeError:
                    text = raw.decode('latin-1')
                text = strip_gutenberg_header(text)
                if len(text) < 500:
                    continue
                with open(outpath, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"  ✓ Downloaded: [{lang}] {title} ({len(text):,} chars)")
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            continue

    print(f"  ✗ FAILED: [{lang}] {title} (id={book_id})")
    return False


def main():
    os.makedirs(OUT_BASE, exist_ok=True)
    total_books = sum(len(v) for v in BOOKS.values())
    print(f"Downloading {total_books} texts across {len(BOOKS)} languages")
    print("=" * 60)

    stats = {}
    for lang, books in BOOKS.items():
        # Deduplicate by ID
        seen = set()
        unique = []
        for b in books:
            if b[0] not in seen:
                seen.add(b[0])
                unique.append(b)

        print(f"\n--- {lang} ({len(unique)} texts) ---")
        ok, fail = 0, 0
        for bid, title, author in unique:
            if download_book(lang, bid, title):
                ok += 1
            else:
                fail += 1
            time.sleep(0.5)
        stats[lang] = (ok, fail)

    print("\n" + "=" * 60)
    print("Summary:")
    for lang, (ok, fail) in stats.items():
        print(f"  {lang}: {ok} downloaded, {fail} failed")
    print(f"Total: {sum(v[0] for v in stats.values())} downloaded, "
          f"{sum(v[1] for v in stats.values())} failed")


if __name__ == "__main__":
    main()
