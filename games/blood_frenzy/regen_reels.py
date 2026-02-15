"""Generate reel strips for Blood Frenzy v1 (6x6 grid, balanced reels, sine gradient).

BR0: Base game — 8 paying symbols + SC (scatter), no PT
FR0: Free game — 8 paying symbols, no SC, no PT
WCAP: Win cap — H1/H2 heavy, includes SC

Symbols: L1(Peasant) L2(Merchant) L3(Noble) L4(Priest) H1(Warrior) H2(Cleric) H3(Paladin) H4(Cardinal)
"""
import csv
import random

random.seed(42)

ROWS = 120
REELS = 6
MIN_SC_GAP = 7

L_SYMBOLS = ["L1", "L2", "L3", "L4"]
H_SYMBOLS = ["H1", "H2", "H3", "H4"]
PAYING_SYMBOLS = L_SYMBOLS + H_SYMBOLS

# Balanced weights — H1 slightly more common (always active, lowest payout)
# H4 rarest (gated behind x5, highest payout)
BASE_WEIGHTS = {
    "L1": 1.05, "L2": 1.05, "L3": 1.05, "L4": 1.05,
    "H1": 1.10, "H2": 0.90, "H3": 0.80, "H4": 0.65,
}

FREE_WEIGHTS = {
    "L1": 1.05, "L2": 1.05, "L3": 1.05, "L4": 1.05,
    "H1": 1.10, "H2": 0.90, "H3": 0.80, "H4": 0.65,
}

WCAP_WEIGHTS = {
    "L1": 0.50, "L2": 0.55, "L3": 0.60, "L4": 0.65,
    "H1": 1.00, "H2": 1.20, "H3": 1.40, "H4": 1.60,
}


def write_reel(path, data):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in data:
            writer.writerow(row)


def place_specials(num_rows, num_per_col, min_gap):
    if num_per_col == 0:
        return []
    spacing = num_rows // num_per_col
    if spacing < min_gap:
        raise ValueError(f"Cannot place {num_per_col} specials with gap {min_gap} in {num_rows} rows")
    start = random.randint(0, spacing - 1)
    positions = []
    for i in range(num_per_col):
        pos = (start + i * spacing + random.randint(-2, 2)) % num_rows
        positions.append(pos)
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


def build_reel_sine(weights, special_positions, num_rows, amplitude=0.25, h_amplitude=None, cycles=3, l_symbols=None, h_symbols=None):
    import math
    if l_symbols is None or h_symbols is None:
        return build_reel(weights, special_positions, num_rows)
    if h_amplitude is None:
        h_amplitude = amplitude

    reel = [None] * num_rows
    for pos, sym in special_positions:
        reel[pos] = sym

    empty = [i for i in range(num_rows) if reel[i] is None]
    total_weight = sum(weights.values())
    target_counts = {}
    assigned = 0
    syms = list(weights.keys())
    for i, sym in enumerate(syms):
        if i == len(syms) - 1:
            target_counts[sym] = len(empty) - assigned
        else:
            target_counts[sym] = round(len(empty) * weights[sym] / total_weight)
            assigned += target_counts[sym]

    remaining = dict(target_counts)
    for pos in empty:
        t = pos / num_rows
        sine_val = math.sin(2 * math.pi * cycles * t)
        pos_weights = {}
        for sym in syms:
            if remaining.get(sym, 0) <= 0:
                continue
            base_w = weights[sym]
            if sym in l_symbols:
                pos_weights[sym] = base_w * (1 + amplitude * sine_val)
            elif sym in h_symbols:
                pos_weights[sym] = base_w * (1 - h_amplitude * sine_val)
            else:
                pos_weights[sym] = base_w

        if not pos_weights:
            for sym in syms:
                if remaining.get(sym, 0) > 0:
                    pos_weights[sym] = 1.0

        total = sum(pos_weights.values())
        r = random.random() * total
        cumulative = 0
        chosen = list(pos_weights.keys())[-1]
        for sym, w in pos_weights.items():
            cumulative += w
            if r <= cumulative:
                chosen = sym
                break

        reel[pos] = chosen
        remaining[chosen] -= 1

    return reel


def build_reel(weights, special_positions, num_rows):
    reel = [None] * num_rows
    for pos, sym in special_positions:
        reel[pos] = sym
    remaining_slots = sum(1 for s in reel if s is None)
    total_weight = sum(weights.values())
    counts = {}
    assigned = 0
    syms = list(weights.keys())
    for i, sym in enumerate(syms):
        if i == len(syms) - 1:
            counts[sym] = remaining_slots - assigned
        else:
            target = round(remaining_slots * weights[sym] / total_weight)
            counts[sym] = target
            assigned += target
    pool = []
    for sym, count in counts.items():
        pool.extend([sym] * count)
    random.shuffle(pool)
    empty = [idx for idx in range(num_rows) if reel[idx] is None]
    for idx, pos in enumerate(empty):
        reel[pos] = pool[idx] if idx < len(pool) else syms[-1]
    return reel


def verify_reel(data, reel_idx, name, special_syms):
    counts = {}
    for r in range(len(data)):
        s = data[r][reel_idx]
        counts[s] = counts.get(s, 0) + 1
    paying = {s: c for s, c in counts.items() if s not in special_syms}
    vals = list(paying.values()) if paying else [0]
    ratio = max(vals) / min(vals) if min(vals) > 0 else 0
    adj = 0
    for r in range(len(data)):
        if data[r][reel_idx] == data[(r + 1) % len(data)][reel_idx]:
            adj += 1
    adj_pct = adj / len(data) * 100
    print(f"  {name} Reel {reel_idx}: {dict(sorted(counts.items()))} ratio={ratio:.2f}x adj={adj_pct:.1f}%")
    for sp in special_syms:
        sp_rows = [r for r in range(len(data)) if data[r][reel_idx] == sp]
        violations = 0
        for i in range(len(sp_rows)):
            for j in range(i + 1, len(sp_rows)):
                dist = min(abs(sp_rows[i] - sp_rows[j]), len(data) - abs(sp_rows[i] - sp_rows[j]))
                if dist < MIN_SC_GAP:
                    violations += 1
        if violations:
            print(f"    WARNING: {sp} spacing violations = {violations}")


# ============ BR0 (Base Game) ============
print("=== Generating BR0.csv (6 reels, 3 SC/col, balanced, sine gradient) ===")
SC_PER_COL = 3

br0 = [[None] * REELS for _ in range(ROWS)]
for reel in range(REELS):
    sc_pos = place_specials(ROWS, SC_PER_COL, MIN_SC_GAP)
    special_positions = [(p, "SC") for p in sc_pos]
    reel_data = build_reel_sine(BASE_WEIGHTS, special_positions, ROWS,
                                amplitude=0.25, h_amplitude=0.2875, cycles=3, l_symbols=L_SYMBOLS, h_symbols=H_SYMBOLS)
    for r in range(ROWS):
        br0[r][reel] = reel_data[r]
    print(f"  Reel {reel} SC at: {sc_pos}")

print("\nBR0 verification:")
for reel in range(REELS):
    verify_reel(br0, reel, "BR0", {"SC"})
write_reel("games/blood_frenzy/reels/BR0.csv", br0)
print("BR0.csv written!\n")


# ============ FR0 (Free Game) ============
print("=== Generating FR0.csv (6 reels, no specials, balanced, sine gradient) ===")

fr0 = [[None] * REELS for _ in range(ROWS)]
for reel in range(REELS):
    reel_data = build_reel_sine(FREE_WEIGHTS, [], ROWS,
                                amplitude=0.25, h_amplitude=0.25, cycles=3, l_symbols=L_SYMBOLS, h_symbols=H_SYMBOLS)
    for r in range(ROWS):
        fr0[r][reel] = reel_data[r]

print("\nFR0 verification:")
for reel in range(REELS):
    verify_reel(fr0, reel, "FR0", set())
write_reel("games/blood_frenzy/reels/FR0.csv", fr0)
print("FR0.csv written!\n")


# ============ WCAP (Win Cap) ============
print("=== Generating WCAP.csv (6 reels, 6 SC/col, H heavy) ===")
WCAP_SC_PER_COL = 6

wcap = [[None] * REELS for _ in range(ROWS)]
for reel in range(REELS):
    sc_pos = place_specials(ROWS, WCAP_SC_PER_COL, MIN_SC_GAP)
    special_positions = [(p, "SC") for p in sc_pos]
    reel_data = build_reel(WCAP_WEIGHTS, special_positions, ROWS)
    for r in range(ROWS):
        wcap[r][reel] = reel_data[r]
    print(f"  Reel {reel} SC at: {sc_pos}")

print("\nWCAP verification:")
for reel in range(REELS):
    verify_reel(wcap, reel, "WCAP", {"SC"})
write_reel("games/blood_frenzy/reels/WCAP.csv", wcap)
print("WCAP.csv written!\n")


# ============ Summary ============
print("=== SUMMARY ===")
l_pct = sum(BASE_WEIGHTS[s] for s in L_SYMBOLS) / sum(BASE_WEIGHTS.values()) * 100
h_pct = sum(BASE_WEIGHTS[s] for s in H_SYMBOLS) / sum(BASE_WEIGHTS.values()) * 100
print(f"BR0: {REELS} reels x {ROWS} rows, {SC_PER_COL} SC/col, balanced sine gradient")
print(f"FR0: {REELS} reels x {ROWS} rows, no specials, balanced sine gradient")
print(f"WCAP: {REELS} reels x {ROWS} rows, {WCAP_SC_PER_COL} SC/col, H heavy")
print(f"Paying symbols: {len(PAYING_SYMBOLS)} (4L + 4H)")
print(f"Board composition: L ~{l_pct:.0f}%, H ~{h_pct:.0f}%")
print(f"H weights: H1=1.10 (always active), H2=0.90, H3=0.80, H4=0.65 (rarest)")
print(f"SINE GRADIENT — BR0: L_A=0.25 H_A=0.2875, FR0: L_A=0.25 H_A=0.25, 3 cycles per {ROWS} rows")
