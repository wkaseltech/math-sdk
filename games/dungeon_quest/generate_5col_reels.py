"""Generate 5-column reel strips for 5x7 grid migration.

Reads existing 4-column strips, analyzes symbol frequencies,
generates 5-column strips with adjusted scatter density to maintain
~same trigger rate on the larger grid.

Scatter math:
  Old: 4 reels × 6 rows = 24 cells, ~11 SC/col → P(SC on reel) ≈ 0.33 → P(≥3 of 4) ≈ 10%
  New: 5 reels × 7 rows = 35 cells, ~7 SC/col → P(SC on reel) ≈ 0.245 → P(≥3 of 5) ≈ 10%
"""

import csv
import random
import os
from collections import Counter

random.seed(42)

REEL_LENGTH = 200
NUM_COLS_OLD = 4
NUM_COLS_NEW = 5
REELS_DIR = os.path.join(os.path.dirname(__file__), "reels")

# Target SC per column for 5x7 grid (7 visible rows)
# P(≥1 SC in 7-row window) ≈ 7*SC_count/200
# Want P ≈ 0.245 → SC_count ≈ 200*0.245/7 ≈ 7
TARGET_SC_PER_COL = 7

# Target PT per column for FR0 (bonus reels)
# Currently ~3-4 PT per column on 4-col strips
# Keep same density per column
TARGET_PT_PER_COL = 3


def read_csv(filename):
    """Read reel strip CSV, return list of rows (each row is list of symbols)."""
    path = os.path.join(REELS_DIR, filename)
    rows = []
    with open(path, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append([s.strip() for s in row])
    return rows


def count_symbols(rows):
    """Count symbol frequencies per column and total."""
    num_cols = len(rows[0])
    per_col = [Counter() for _ in range(num_cols)]
    total = Counter()
    for row in rows:
        for c, sym in enumerate(row):
            per_col[c][sym] += 1
            total[sym] += 1
    return per_col, total


def get_regular_freq(total_counts, exclude=None):
    """Get frequency distribution of regular symbols (excluding specials)."""
    if exclude is None:
        exclude = {"SC", "PT"}
    reg = {s: c for s, c in total_counts.items() if s not in exclude}
    total = sum(reg.values())
    return {s: c / total for s, c in reg.items()}


def generate_column(reg_freq, special_syms=None, length=200):
    """Generate a single column of given length with specified symbol frequencies.

    special_syms: dict of {symbol: count} for special symbols to place
    Remaining slots filled with regular symbols per reg_freq distribution.
    Special symbols are placed with minimum spacing to avoid clumping.
    """
    if special_syms is None:
        special_syms = {}

    total_specials = sum(special_syms.values())
    regular_slots = length - total_specials

    # Generate regular symbol pool
    reg_pool = []
    for sym, freq in sorted(reg_freq.items()):
        count = round(freq * regular_slots)
        reg_pool.extend([sym] * count)

    # Adjust for rounding
    while len(reg_pool) < regular_slots:
        reg_pool.append(random.choice(list(reg_freq.keys())))
    while len(reg_pool) > regular_slots:
        reg_pool.pop()

    random.shuffle(reg_pool)

    # Build full-length column: place specials at evenly-spaced positions,
    # fill remaining slots with regular symbols
    all_special_positions = set()
    special_placements = {}  # pos -> symbol

    for sym, count in special_syms.items():
        if count == 0:
            continue
        spacing = length // count
        start = random.randint(0, spacing - 1)
        for i in range(count):
            base_pos = (start + i * spacing) % length
            jitter = random.randint(-spacing // 4, spacing // 4)
            pos = (base_pos + jitter) % length
            # Resolve collision
            while pos in all_special_positions:
                pos = (pos + 1) % length
            all_special_positions.add(pos)
            special_placements[pos] = sym

    # Build column
    column = []
    reg_idx = 0
    for i in range(length):
        if i in special_placements:
            column.append(special_placements[i])
        else:
            column.append(reg_pool[reg_idx])
            reg_idx += 1

    return column


def rebuild_strip(old_rows, target_specials, num_cols_new=5):
    """Rebuild a reel strip with new column count and adjusted special symbol counts.

    old_rows: existing strip data
    target_specials: dict of {symbol: count_per_col} for special symbols
    """
    _, total_counts = count_symbols(old_rows)
    reg_freq = get_regular_freq(total_counts, exclude=set(target_specials.keys()) | {"SC", "PT"})

    columns = []
    for _ in range(num_cols_new):
        col = generate_column(reg_freq, target_specials, REEL_LENGTH)
        columns.append(col)

    # Convert columns to rows
    new_rows = []
    for r in range(REEL_LENGTH):
        row = [columns[c][r] for c in range(num_cols_new)]
        new_rows.append(row)

    return new_rows


def write_csv(filename, rows):
    """Write reel strip CSV."""
    path = os.path.join(REELS_DIR, filename)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)


def analyze_strip(name, rows):
    """Print analysis of a strip."""
    num_cols = len(rows[0])
    per_col, total = count_symbols(rows)
    print(f"\n{'='*60}")
    print(f"  {name}: {len(rows)} rows × {num_cols} cols")
    print(f"{'='*60}")
    print(f"  {'Symbol':<8} {'Total':>6} {'Per Col Avg':>12} {'Frequency':>10}")
    print(f"  {'-'*40}")
    for sym in sorted(total.keys()):
        avg = total[sym] / num_cols
        freq = total[sym] / (len(rows) * num_cols)
        print(f"  {sym:<8} {total[sym]:>6} {avg:>12.1f} {freq:>10.3f}")

    # SC/PT per column detail
    for special in ["SC", "PT"]:
        if special in total:
            counts = [per_col[c].get(special, 0) for c in range(num_cols)]
            print(f"\n  {special} per column: {counts} (total: {sum(counts)})")


def verify_spacing(rows, symbol):
    """Check minimum spacing between special symbols in each column."""
    num_cols = len(rows[0])
    for c in range(num_cols):
        positions = [r for r in range(len(rows)) if rows[r][c] == symbol]
        if len(positions) < 2:
            continue
        min_gap = min(positions[i+1] - positions[i] for i in range(len(positions)-1))
        # Also check wrap-around gap
        wrap_gap = (len(rows) - positions[-1]) + positions[0]
        min_gap = min(min_gap, wrap_gap)
        if min_gap < 5:
            print(f"  WARNING: {symbol} col {c+1} min spacing = {min_gap} (positions: {positions})")


if __name__ == "__main__":
    print("=" * 60)
    print("  CURRENT STRIPS (4-column)")
    print("=" * 60)

    # Analyze current strips
    br0_old = read_csv("BR0.csv")
    fr0_old = read_csv("FR0.csv")
    wcap_old = read_csv("WCAP.csv")

    analyze_strip("BR0 (base)", br0_old)
    analyze_strip("FR0 (bonus)", fr0_old)
    analyze_strip("WCAP (wincap)", wcap_old)

    print("\n\n" + "=" * 60)
    print("  GENERATING NEW 5-COLUMN STRIPS")
    print("=" * 60)

    # BR0: base game — has SC, no PT
    br0_new = rebuild_strip(br0_old, {"SC": TARGET_SC_PER_COL}, NUM_COLS_NEW)
    write_csv("BR0.csv", br0_new)
    analyze_strip("BR0 NEW (base)", br0_new)
    verify_spacing(br0_new, "SC")

    # FR0: bonus reels — has PT, no SC
    fr0_new = rebuild_strip(fr0_old, {"PT": TARGET_PT_PER_COL}, NUM_COLS_NEW)
    write_csv("FR0.csv", fr0_new)
    analyze_strip("FR0 NEW (bonus)", fr0_new)
    verify_spacing(fr0_new, "PT")

    # WCAP: wincap reels — has SC and PT, heavy on high symbols
    # WCAP needs special treatment: much heavier on H1/H2, more SC+PT
    wcap_old_counts = count_symbols(wcap_old)
    wcap_total = wcap_old_counts[1]
    # WCAP has high-symbol bias — preserve that
    wcap_reg_freq = get_regular_freq(wcap_total, exclude={"SC", "PT"})

    wcap_cols = []
    for _ in range(NUM_COLS_NEW):
        col = generate_column(wcap_reg_freq, {"SC": 8, "PT": 6}, REEL_LENGTH)
        wcap_cols.append(col)
    wcap_new = [[wcap_cols[c][r] for c in range(NUM_COLS_NEW)] for r in range(REEL_LENGTH)]
    write_csv("WCAP.csv", wcap_new)
    analyze_strip("WCAP NEW (wincap)", wcap_new)
    verify_spacing(wcap_new, "SC")
    verify_spacing(wcap_new, "PT")

    print("\n\nDone! New 5-column strips written to reels/")
