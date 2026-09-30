"""
Download 100 English classics from Project Gutenberg mirrors.

Uses the Gutenberg mirror at https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt
Strips the Gutenberg header/footer boilerplate to get clean text.

Usage:
    uv run fetch_gutenberg.py
"""
import os
import re
import time
import urllib.request
import urllib.error

# ─── 100 Classic English Texts (Gutenberg IDs) ──────────────────────────────
# Curated list spanning novels, poetry, philosophy, drama, non-fiction
BOOKS = [
    # --- Novels & Fiction ---
    (1342, "Pride and Prejudice", "Jane Austen"),
    (11, "Alice in Wonderland", "Lewis Carroll"),
    (1661, "Sherlock Holmes Adventures", "Arthur Conan Doyle"),
    (84, "Frankenstein", "Mary Shelley"),
    (1952, "The Yellow Wallpaper", "Charlotte Perkins Gilman"),
    (174, "The Picture of Dorian Gray", "Oscar Wilde"),
    (345, "Dracula", "Bram Stoker"),
    (2701, "Moby Dick", "Herman Melville"),
    (98, "A Tale of Two Cities", "Charles Dickens"),
    (1400, "Great Expectations", "Charles Dickens"),
    (46, "A Christmas Carol", "Charles Dickens"),
    (766, "David Copperfield", "Charles Dickens"),
    (730, "Oliver Twist", "Charles Dickens"),
    (1260, "Jane Eyre", "Charlotte Bronte"),
    (768, "Wuthering Heights", "Emily Bronte"),
    (16328, "Beowulf", "Anonymous"),
    (160, "The Jungle Book", "Rudyard Kipling"),
    (236, "The Jungle Book 2", "Rudyard Kipling"),
    (35, "The Time Machine", "H.G. Wells"),
    (36, "The War of the Worlds", "H.G. Wells"),
    (5230, "The Invisible Man", "H.G. Wells"),
    (43, "The Strange Case of Dr Jekyll and Mr Hyde", "R.L. Stevenson"),
    (120, "Treasure Island", "R.L. Stevenson"),
    (1232, "The Prince", "Niccolo Machiavelli"),
    (2600, "War and Peace", "Leo Tolstoy"),
    (2554, "Crime and Punishment", "Fyodor Dostoevsky"),
    (28054, "The Brothers Karamazov", "Fyodor Dostoevsky"),
    (4300, "Ulysses", "James Joyce"),
    (2814, "Dubliners", "James Joyce"),
    (64317, "The Great Gatsby", "F. Scott Fitzgerald"),
    (805, "This Side of Paradise", "F. Scott Fitzgerald"),
    (1250, "Anthem", "Ayn Rand"),
    (5200, "Metamorphosis", "Franz Kafka"),
    (7849, "The Trial", "Franz Kafka"),
    (244, "A Study in Scarlet", "Arthur Conan Doyle"),
    (2852, "The Hound of the Baskervilles", "Arthur Conan Doyle"),
    (1080, "A Modest Proposal", "Jonathan Swift"),
    (829, "Gulliver's Travels", "Jonathan Swift"),
    (2591, "Grimm's Fairy Tales", "Brothers Grimm"),
    (2500, "Siddhartha", "Hermann Hesse"),
    (514, "Little Women", "Louisa May Alcott"),
    (1184, "The Count of Monte Cristo", "Alexandre Dumas"),
    (1399, "Anna Karenina", "Leo Tolstoy"),
    (74, "Tom Sawyer", "Mark Twain"),
    (76, "Huckleberry Finn", "Mark Twain"),
    (3176, "The Awakening", "Kate Chopin"),
    (215, "The Call of the Wild", "Jack London"),
    (910, "White Fang", "Jack London"),
    (5827, "The Problems of Philosophy", "Bertrand Russell"),
    (25344, "The Scarlet Letter", "Nathaniel Hawthorne"),
    (209, "The Turn of the Screw", "Henry James"),
    (432, "The Portrait of a Lady", "Henry James"),
    (1727, "The Odyssey", "Homer"),
    (6130, "The Iliad", "Homer"),
    (8800, "The Divine Comedy", "Dante Alighieri"),
    (100, "Complete Works of Shakespeare", "William Shakespeare"),
    (1513, "Romeo and Juliet", "William Shakespeare"),
    (1524, "Hamlet", "William Shakespeare"),
    (1533, "Macbeth", "William Shakespeare"),
    (2264, "A Midsummer Night's Dream", "William Shakespeare"),
    (1514, "The Tempest", "William Shakespeare"),
    (2267, "King Lear", "William Shakespeare"),
    (1532, "Othello", "William Shakespeare"),
    (23, "Narrative of Frederick Douglass", "Frederick Douglass"),
    (73, "Tom Sawyer Abroad", "Mark Twain"),
    (4363, "Beyond Good and Evil", "Friedrich Nietzsche"),
    (7205, "Thus Spake Zarathustra", "Friedrich Nietzsche"),
    (3207, "Leviathan", "Thomas Hobbes"),
    (1497, "Republic", "Plato"),
    (10616, "The Art of War", "Sun Tzu"),
    (3600, "Meditations", "Marcus Aurelius"),
    (996, "Don Quixote", "Miguel de Cervantes"),
    (1998, "Thus Spake Zarathustra Alt", "Friedrich Nietzsche"),
    (135, "Les Miserables", "Victor Hugo"),
    (1184, "Monte Cristo", "Alexandre Dumas"),
    (2542, "Paradise Lost", "John Milton"),
    (4085, "The Castle of Otranto", "Horace Walpole"),
    (1322, "Leaves of Grass", "Walt Whitman"),
    (1934, "Songs of Innocence and Experience", "William Blake"),
    (2680, "Meditations on First Philosophy", "Rene Descartes"),
    (4705, "A Treatise of Human Nature", "David Hume"),
    (5740, "Tractatus Logico-Philosophicus", "Ludwig Wittgenstein"),
    (3296, "On the Origin of Species", "Charles Darwin"),
    (4217, "A Portrait of the Artist as a Young Man", "James Joyce"),
    (786, "Around the World in 80 Days", "Jules Verne"),
    (164, "20000 Leagues Under the Sea", "Jules Verne"),
    (103, "Around the World in 80 Days Alt", "Jules Verne"),
    (6688, "Autobiography of Benjamin Franklin", "Benjamin Franklin"),
    (408, "Souls of Black Folk", "W.E.B. Du Bois"),
    (16, "Peter Pan", "J.M. Barrie"),
    (55, "The Wonderful Wizard of Oz", "L. Frank Baum"),
    (45, "Anne of Green Gables", "L.M. Montgomery"),
    (31284, "The Importance of Being Earnest", "Oscar Wilde"),
    (844, "The Importance of Being Earnest Alt", "Oscar Wilde"),
    (8492, "The Communist Manifesto", "Karl Marx"),
    (28233, "The King in Yellow", "Robert W. Chambers"),
    (58585, "The Rime of the Ancient Mariner", "Samuel Taylor Coleridge"),
    (7370, "Second Treatise of Government", "John Locke"),
    (30254, "The Romance of Lust", "Anonymous"),
    (1023, "Bleak House", "Charles Dickens"),
    (19337, "A Doll's House", "Henrik Ibsen"),
    (2148, "The Works of Edgar Allan Poe Vol 2", "Edgar Allan Poe"),
    (2147, "The Works of Edgar Allan Poe Vol 1", "Edgar Allan Poe"),
]

# De-duplicate by ID
seen = set()
BOOKS_UNIQUE = []
for b in BOOKS:
    if b[0] not in seen:
        seen.add(b[0])
        BOOKS_UNIQUE.append(b)

OUT_DIR = os.path.join(os.path.dirname(__file__), "texts", "gutenberg")

GUTENBERG_MIRROR = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
MIRROR2 = "https://www.gutenberg.org/files/{id}/{id}-0.txt"


def strip_gutenberg_header(text):
    """Remove Project Gutenberg header and footer boilerplate."""
    # Find start
    start_markers = [
        "*** START OF THIS PROJECT GUTENBERG",
        "*** START OF THE PROJECT GUTENBERG",
        "***START OF THIS PROJECT GUTENBERG",
        "*END*THE SMALL PRINT",
    ]
    end_markers = [
        "*** END OF THIS PROJECT GUTENBERG",
        "*** END OF THE PROJECT GUTENBERG",
        "***END OF THIS PROJECT GUTENBERG",
        "End of the Project Gutenberg",
        "End of Project Gutenberg",
    ]

    start_idx = 0
    for marker in start_markers:
        idx = text.find(marker)
        if idx != -1:
            # Skip to end of line after marker
            nl = text.find("\n", idx)
            if nl != -1:
                start_idx = nl + 1
            break

    end_idx = len(text)
    for marker in end_markers:
        idx = text.find(marker)
        if idx != -1:
            end_idx = idx
            break

    return text[start_idx:end_idx].strip()


def download_book(book_id, title, author):
    """Download a single book, return True if successful."""
    safe_title = re.sub(r'[^a-zA-Z0-9]+', '_', title).strip('_').lower()
    outpath = os.path.join(OUT_DIR, f"{book_id}_{safe_title}.txt")

    if os.path.exists(outpath):
        sz = os.path.getsize(outpath)
        if sz > 1000:
            print(f"  ✓ Already exists: {title} ({sz:,} bytes)")
            return True

    urls = [
        GUTENBERG_MIRROR.format(id=book_id),
        MIRROR2.format(id=book_id),
    ]

    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Research; entropy-analysis)'
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                # Try UTF-8 first, then latin-1
                try:
                    text = raw.decode('utf-8')
                except UnicodeDecodeError:
                    text = raw.decode('latin-1')

                text = strip_gutenberg_header(text)
                if len(text) < 500:
                    continue

                with open(outpath, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"  ✓ Downloaded: {title} ({len(text):,} chars)")
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            continue

    print(f"  ✗ FAILED: {title} (id={book_id})")
    return False


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Downloading {len(BOOKS_UNIQUE)} English classics to {OUT_DIR}/")
    print("=" * 60)

    success, fail = 0, 0
    for book_id, title, author in BOOKS_UNIQUE:
        ok = download_book(book_id, title, author)
        if ok:
            success += 1
        else:
            fail += 1
        time.sleep(0.5)  # Be polite to Gutenberg servers

    print(f"\nDone! {success} downloaded, {fail} failed.")


if __name__ == "__main__":
    main()
