"""Regenerate BR0.csv with:
1. 5 reels (matching 5x7 grid)
2. SC reduced from 7 to 4 per column (lower bonus trigger rate ~4%)
3. SC spacing: min 7 rows apart (no 2 keys in same visible window)
4. Flattened paying symbols: max 1.5x ratio between most/least common
"""
import csv
import random

random.seed(42)

ROWS = 200
REELS = 5
MIN_SC_GAP = 7
SC_PER_COL = 4  # down from 7 — target ~4% bonus trigger rate

PAYING_SYMBOLS = ["H1", "H2", "H3", "H4", "L1", "L2", "L3"]


def write_reel(path, data):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in data:
            writer.writerow(row)


def place_scatters(num_rows, num_sc, min_gap):
    """Place SC symbols with minimum gap constraint (wrapping reel)."""
    if num_sc == 0:
        return []

    spacing = num_rows // num_sc
    if spacing < min_gap:
        raise ValueError(f"Cannot place {num_sc} SCs with gap {min_gap} in {num_rows} rows")

    start = random.randint(0, spacing - 1)
    positions = []
    for i in range(num_sc):
        pos = (start + i * spacing + random.randint(-2, 2)) % num_rows
        positions.append(pos)

    # Fix any violations iteratively
    positions.sort()
    for _ in range(200):
        ok = True
        for i in range(len(positions)):
            j = (i + 1) % len(positions)
            if j == 0:
                dist = (positions[j] + num_rows) - positions[i]
            else:
                dist = positions[j] - positions[i]
            if dist < min_gap:
                ok = False
                positions[j] = (positions[i] + min_gap) % num_rows
                positions.sort()
                break
        if ok:
            break

    return sorted(positions)


def build_reel(paying_syms, sc_positions, num_rows):
    """Build reel strip: SC at fixed positions, paying symbols flattened in remaining."""
    reel = [None] * num_rows

    for pos in sc_positions:
        reel[pos] = "SC"

    remaining_slots = num_rows - len(sc_positions)
    num_paying = len(paying_syms)

    # Flat distribution with slight gradient (H1 rarest, L3 most common)
    base = remaining_slots / num_paying
    min_target = base * 0.85
    max_target = base * 1.18

    counts = {}
    assigned = 0
    for i, sym in enumerate(paying_syms):
        if i == num_paying - 1:
            counts[sym] = remaining_slots - assigned
        else:
            t = i / (num_paying - 1)
            target = round(min_target + t * (max_target - min_target))
            counts[sym] = target
            assigned += target

    symbols = []
    for sym, count in counts.items():
        symbols.extend([sym] * count)

    random.shuffle(symbols)

    empty = [i for i in range(num_rows) if reel[i] is None]
    diff = len(empty) - len(symbols)
    if diff > 0:
        symbols.extend([paying_syms[-1]] * diff)
    elif diff < 0:
        symbols = symbols[:len(empty)]

    for i, pos in enumerate(empty):
        reel[pos] = symbols[i]

    return reel


def verify_reel(data, reel_idx, name, special_syms):
    counts = {}
    for r in range(len(data)):
        s = data[r][reel_idx]
        counts[s] = counts.get(s, 0) + 1

    paying = {s: c for s, c in counts.items() if s not in special_syms}
    vals = list(paying.values()) if paying else [0]
    ratio = max(vals) / min(vals) if min(vals) > 0 else 0

    sc_rows = [r for r in range(len(data)) if data[r][reel_idx] == "SC"]
    violations = 0
    for i in range(len(sc_rows)):
        for j in range(i + 1, len(sc_rows)):
            dist = min(abs(sc_rows[i] - sc_rows[j]), len(data) - abs(sc_rows[i] - sc_rows[j]))
            if dist < MIN_SC_GAP:
                violations += 1

    print(f"  {name} Reel {reel_idx}: {dict(sorted(counts.items()))} ratio={ratio:.2f}x sc_violations={violations}")
    return violations


# ============ BR0 ============
print("=== Regenerating BR0.csv (5 reels, 4 SC/col) ===")

br0_new = [[None] * REELS for _ in range(ROWS)]
total_violations = 0
for reel in range(REELS):
    sc_pos = place_scatters(ROWS, SC_PER_COL, MIN_SC_GAP)
    reel_data = build_reel(PAYING_SYMBOLS, sc_pos, ROWS)
    for r in range(ROWS):
        br0_new[r][reel] = reel_data[r]
    print(f"  Reel {reel} SC at: {sc_pos}")

print("\nBR0 verification:")
for reel in range(REELS):
    v = verify_reel(br0_new, reel, "BR0", {"SC"})
    total_violations += v

if total_violations == 0:
    write_reel("games/dungeon_quest/reels/BR0.csv", br0_new)
    print("\nBR0.csv written successfully!")
else:
    print(f"\nERROR: {total_violations} SC violations remain, not writing!")

# Summary
print("\n=== SUMMARY ===")
print(f"BR0: 5 reels x 200 rows, {SC_PER_COL} SC per column (was 7), min gap {MIN_SC_GAP}")
print("Paying symbols flattened within 1.5x ratio (H1 rarest -> L3 most common)")
print("FR0, WCAP: Not touched (FR0 has no SC, WCAP is special)")
