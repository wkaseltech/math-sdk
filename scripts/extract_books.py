"""
Extract BookEvent sequences from sim output and combine with optimized
weights to produce JSON files for the web-sdk DevAuthenticate mock RGS.

Reads from:
    library/books/books_{mode}.json       (uncompressed, preferred)
    library/publish_files/books_{mode}.jsonl.zst  (compressed, fallback)

Usage:
    python scripts/extract_books.py

Output:
    mock_books_base.json  — ~500 base-game books with weights
    mock_books_bonus.json — ~100 bonus-game books with weights
"""

import csv
import io
import json
import os
import sys

try:
    import zstandard as zstd
except ImportError:
    zstd = None

# ── Config ──────────────────────────────────────────────────────────
GAME_NAME = sys.argv[1] if len(sys.argv) > 1 else "blood_tithe"
GAME_DIR = os.path.join(os.path.dirname(__file__), "..", "games", GAME_NAME)
BOOKS_DIR = os.path.join(GAME_DIR, "library", "books")
PUBLISH_DIR = os.path.join(GAME_DIR, "library", "publish_files")

# How many books to extract per mode
EXTRACT_COUNTS = {"base": 500, "bonus": 100}

# Map game names to web-sdk app dirs
SDK_APP_MAP = {
    "blood_tithe": "vampire-slots",
    "vampire_slots": "vampire-slots",
    "dungeon_quest": "dungeon-quest",
}
sdk_app = SDK_APP_MAP.get(GAME_NAME, GAME_NAME.replace("_", "-"))

# Output directory (web-sdk static/mockBooks — served at runtime, no bundler issues)
WEB_SDK_MOCK_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "web-sdk",
    "apps",
    sdk_app,
    "static",
    "mockBooks",
)


def read_weights(csv_path):
    """Read lookup table CSV (no header row).
    Columns: simulation_id, round_probability, payout_multiplier
    Returns dict: {sim_id: round_probability}
    """
    weights = {}
    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            sim_id = int(row[0])
            probability = int(row[1])
            weights[sim_id] = probability
    return weights


def read_books_zst(zst_path, max_count):
    """Decompress .jsonl.zst and yield up to max_count parsed book dicts."""
    if zstd is None:
        sys.exit("zstandard not installed. Run: pip install zstandard")
    decompressor = zstd.ZstdDecompressor()
    count = 0
    with open(zst_path, "rb") as f:
        with decompressor.stream_reader(f) as reader:
            txt_stream = io.TextIOWrapper(reader, encoding="utf-8")
            for line in txt_stream:
                line = line.strip()
                if not line:
                    continue
                book = json.loads(line)
                yield book
                count += 1
                if count >= max_count:
                    break


def read_books_json(json_path, max_count):
    """Read uncompressed books JSON (list of book dicts)."""
    with open(json_path, "r", encoding="utf-8") as f:
        all_books = json.load(f)
    for book in all_books[:max_count]:
        yield book


def extract_mode(mode_name, events_file, weights_file, max_count, output_path):
    """Extract books for a single mode and write JSON output."""
    csv_path = os.path.join(PUBLISH_DIR, weights_file)

    if not os.path.exists(csv_path):
        print(f"  SKIP: {csv_path} not found")
        return

    # Prefer uncompressed JSON from library/books/, fall back to .jsonl.zst
    json_path = os.path.join(BOOKS_DIR, f"books_{mode_name}.json")
    zst_path = os.path.join(PUBLISH_DIR, events_file)

    if os.path.exists(json_path):
        source = json_path
        reader = read_books_json(json_path, max_count)
        print(f"  Reading from {os.path.basename(json_path)} (uncompressed)...")
    elif os.path.exists(zst_path):
        source = zst_path
        reader = read_books_zst(zst_path, max_count)
        print(f"  Decompressing {events_file}...")
    else:
        print(f"  SKIP: no book data found for {mode_name}")
        return

    print(f"  Reading weights from {weights_file}...")
    weights = read_weights(csv_path)

    print(f"  Extracting {max_count} books...")
    books = []
    total_weight = 0
    for book in reader:
        book_id = book["id"]
        weight = weights.get(book_id, 1)
        books.append(
            {
                "id": book_id,
                "weight": weight,
                "payoutMultiplier": book.get("payoutMultiplier", 0),
                "events": book["events"],
            }
        )
        total_weight += weight

    output = {"books": books, "totalWeight": total_weight}

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Wrote {len(books)} books -> {output_path} ({size_mb:.1f} MB)")

    # Print a summary of payout distribution
    payouts = [b["payoutMultiplier"] for b in books]
    zero_wins = sum(1 for p in payouts if p == 0)
    print(f"  Payout range: {min(payouts)} - {max(payouts)}")
    print(f"  Zero-win books: {zero_wins}/{len(books)}")


def main():
    index_path = os.path.join(PUBLISH_DIR, "index.json")
    if not os.path.exists(index_path):
        sys.exit(f"index.json not found at {index_path}")

    with open(index_path, "r") as f:
        index = json.load(f)

    print(f"Publish dir: {os.path.abspath(PUBLISH_DIR)}")
    print(f"Output dir:  {os.path.abspath(WEB_SDK_MOCK_DIR)}")
    print()

    for mode in index["modes"]:
        name = mode["name"]
        max_count = EXTRACT_COUNTS.get(name, 100)
        output_file = f"mock_books_{name}.json"
        output_path = os.path.join(WEB_SDK_MOCK_DIR, output_file)

        print(f"[{name}] Extracting up to {max_count} books...")
        extract_mode(
            mode_name=name,
            events_file=mode["events"],
            weights_file=mode["weights"],
            max_count=max_count,
            output_path=output_path,
        )
        print()

    print("Done! Copy the JSON files to your web-sdk mockBooks directory if needed.")


if __name__ == "__main__":
    main()
