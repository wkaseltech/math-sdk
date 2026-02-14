"""Generate reel strips for Blood Tithe v12 (6x6 grid, balanced reels + wilds).

BR0: Base game — 8 paying symbols + SC (coffin scatter) + PT (chalice) + WI (wild)
FR0: Free game — 8 paying symbols + PT (blood moon retrigger) + WI (wild), no SC
WCAP: Win cap — H1/H2 heavy, includes SC + PT + WI

Symbols: L1(J) L2(Q) L3(K) L4(A) H1(Elder) H2(Countess) H3(Knight) H4(Feral) WI(Wild)
"""
import csv
import random

random.seed(42)

ROWS = 120
REELS = 6
MIN_SC_GAP = 7    # min rows between SC on same reel (wrapping)
MIN_PT_GAP = 15   # min rows between PT on same reel
MIN_WI_GAP = 5    # min rows between WI on same reel (light anti-clump)

# Symbol sets (8 paying: 4L + 4H)
L_SYMBOLS = ["L1", "L2", "L3", "L4"]
H_SYMBOLS = ["H1", "H2", "H3", "H4"]
PAYING_SYMBOLS = L_SYMBOLS + H_SYMBOLS

# Balanced reel weights — all symbols roughly equal
# H1 slightly rarer for paytable hierarchy, but no L-heavy skew
BASE_WEIGHTS = {
    "L1": 1.00, "L2": 1.00, "L3": 1.00, "L4": 1.00,
    "H4": 1.00, "H3": 0.95, "H2": 0.85, "H1": 0.70,
}

FREE_WEIGHTS = {
    "L1": 1.00, "L2": 1.00, "L3": 1.00, "L4": 1.00,
    "H4": 1.00, "H3": 0.95, "H2": 0.85, "H1": 0.70,
}

WCAP_WEIGHTS = {
    "L1": 0.50, "L2": 0.55, "L3": 0.60, "L4": 0.65,
    "H4": 1.00, "H3": 1.15, "H2": 1.40, "H1": 1.60,
}


def write_reel(path, data):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in data:
            writer.writerow(row)


def place_specials(num_rows, num_per_col, min_gap):
    """Place special symbols with minimum gap constraint (wrapping reel)."""
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


def build_reel(weights, special_positions, num_rows):
    """Build reel strip with random shuffle (no clumping)."""
    reel = [None] * num_rows

    for pos, sym in special_positions:
        reel[pos] = sym

    remaining_slots = sum(1 for s in reel if s is None)
    total_weight = sum(weights.values())

    # Calculate target counts from weights
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

    # Build random symbol sequence (no clumping)
    pool = []
    for sym, count in counts.items():
        pool.extend([sym] * count)
    random.shuffle(pool)

    # Fill in empty slots
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

    # Count adjacency (same symbol in consecutive rows)
    adj = 0
    for r in range(len(data)):
        if data[r][reel_idx] == data[(r + 1) % len(data)][reel_idx]:
            adj += 1
    adj_pct = adj / len(data) * 100

    print(f"  {name} Reel {reel_idx}: {dict(sorted(counts.items()))} ratio={ratio:.2f}x adj={adj_pct:.1f}%")

    # Check special symbol spacing
    for sp in special_syms:
        sp_rows = [r for r in range(len(data)) if data[r][reel_idx] == sp]
        violations = 0
        for i in range(len(sp_rows)):
            for j in range(i + 1, len(sp_rows)):
                dist = min(abs(sp_rows[i] - sp_rows[j]), len(data) - abs(sp_rows[i] - sp_rows[j]))
                gap = MIN_SC_GAP if sp == "SC" else MIN_PT_GAP
                if dist < gap:
                    violations += 1
        if violations:
            print(f"    WARNING: {sp} spacing violations = {violations}")

    return 0


# ============ BR0 (Base Game) ============
print("=== Generating BR0.csv (6 reels, 3 SC/col, 1 PT/col, 4 WI/col, balanced) ===")
SC_PER_COL = 3   # Target ~4% trigger rate on 6 reels
PT_PER_COL_BR0 = 1  # Rare chalice in base game
WI_PER_COL_BR0 = 4  # ~3.3% wild density (4/120)

br0 = [[None] * REELS for _ in range(ROWS)]
for reel in range(REELS):
    sc_pos = place_specials(ROWS, SC_PER_COL, MIN_SC_GAP)
    pt_pos = place_specials(ROWS, PT_PER_COL_BR0, MIN_PT_GAP)
    # Ensure PT doesn't overlap with SC
    while any(p in sc_pos for p in pt_pos):
        pt_pos = place_specials(ROWS, PT_PER_COL_BR0, MIN_PT_GAP)
    wi_pos = place_specials(ROWS, WI_PER_COL_BR0, MIN_WI_GAP)
    # Ensure WI doesn't overlap with SC or PT
    taken = set(sc_pos + pt_pos)
    while any(p in taken for p in wi_pos):
        wi_pos = place_specials(ROWS, WI_PER_COL_BR0, MIN_WI_GAP)
    special_positions = [(p, "SC") for p in sc_pos] + [(p, "PT") for p in pt_pos] + [(p, "WI") for p in wi_pos]
    reel_data = build_reel(BASE_WEIGHTS, special_positions, ROWS)
    for r in range(ROWS):
        br0[r][reel] = reel_data[r]
    print(f"  Reel {reel} SC at: {sc_pos}, PT at: {pt_pos}, WI at: {wi_pos}")

print("\nBR0 verification:")
for reel in range(REELS):
    verify_reel(br0, reel, "BR0", {"SC", "PT", "WI"})

write_reel("games/blood_tithe/reels/BR0.csv", br0)
print("BR0.csv written!\n")


# ============ FR0 (Free Game) ============
print("=== Generating FR0.csv (6 reels, 2 PT/col, 4 WI/col, no SC, balanced) ===")
PT_PER_COL = 2  # Blood Moon retrigger tokens + chalice absorb
WI_PER_COL_FR0 = 4  # Same wild density as base

fr0 = [[None] * REELS for _ in range(ROWS)]
for reel in range(REELS):
    pt_pos = place_specials(ROWS, PT_PER_COL, MIN_PT_GAP)
    wi_pos = place_specials(ROWS, WI_PER_COL_FR0, MIN_WI_GAP)
    # Ensure WI doesn't overlap with PT
    while any(p in pt_pos for p in wi_pos):
        wi_pos = place_specials(ROWS, WI_PER_COL_FR0, MIN_WI_GAP)
    special_positions = [(p, "PT") for p in pt_pos] + [(p, "WI") for p in wi_pos]
    reel_data = build_reel(FREE_WEIGHTS, special_positions, ROWS)
    for r in range(ROWS):
        fr0[r][reel] = reel_data[r]
    print(f"  Reel {reel} PT at: {pt_pos}, WI at: {wi_pos}")

print("\nFR0 verification:")
for reel in range(REELS):
    verify_reel(fr0, reel, "FR0", {"PT", "WI"})

write_reel("games/blood_tithe/reels/FR0.csv", fr0)
print("FR0.csv written!\n")


# ============ WCAP (Win Cap) ============
print("=== Generating WCAP.csv (6 reels, 6 SC/col, 4 PT/col, 6 WI/col, H1/H2 heavy) ===")
WCAP_SC_PER_COL = 6
WCAP_PT_PER_COL = 4
WCAP_WI_PER_COL = 6  # Higher wild density for win cap

wcap = [[None] * REELS for _ in range(ROWS)]
for reel in range(REELS):
    sc_pos = place_specials(ROWS, WCAP_SC_PER_COL, MIN_SC_GAP)
    # Place PT in gaps between SC
    remaining_positions = [i for i in range(ROWS) if i not in sc_pos]
    random.shuffle(remaining_positions)
    pt_pos = sorted(remaining_positions[:WCAP_PT_PER_COL])
    # Place WI in remaining gaps
    taken = set(sc_pos + pt_pos)
    wi_remaining = [i for i in range(ROWS) if i not in taken]
    random.shuffle(wi_remaining)
    wi_pos = sorted(wi_remaining[:WCAP_WI_PER_COL])

    special_positions = [(p, "SC") for p in sc_pos] + [(p, "PT") for p in pt_pos] + [(p, "WI") for p in wi_pos]
    reel_data = build_reel(WCAP_WEIGHTS, special_positions, ROWS)
    for r in range(ROWS):
        wcap[r][reel] = reel_data[r]
    print(f"  Reel {reel} SC at: {sc_pos}, PT at: {pt_pos}, WI at: {wi_pos}")

print("\nWCAP verification:")
for reel in range(REELS):
    verify_reel(wcap, reel, "WCAP", {"SC", "PT", "WI"})

write_reel("games/blood_tithe/reels/WCAP.csv", wcap)
print("WCAP.csv written!\n")


# ============ Summary ============
print("=== SUMMARY ===")
# Calculate effective composition (BR0: specials = SC+PT+WI, rest = paying)
br0_specials_per_reel = SC_PER_COL + PT_PER_COL_BR0 + WI_PER_COL_BR0
br0_paying_per_reel = ROWS - br0_specials_per_reel
l_pct = sum(BASE_WEIGHTS[s] for s in L_SYMBOLS) / sum(BASE_WEIGHTS.values()) * 100
h_pct = sum(BASE_WEIGHTS[s] for s in H_SYMBOLS) / sum(BASE_WEIGHTS.values()) * 100
wi_pct = WI_PER_COL_BR0 / ROWS * 100
print(f"BR0: {REELS} reels x {ROWS} rows, {SC_PER_COL} SC + {PT_PER_COL_BR0} PT + {WI_PER_COL_BR0} WI/col, balanced")
print(f"FR0: {REELS} reels x {ROWS} rows, {PT_PER_COL} PT + {WI_PER_COL_FR0} WI/col, balanced")
print(f"WCAP: {REELS} reels x {ROWS} rows, {WCAP_SC_PER_COL} SC + {WCAP_PT_PER_COL} PT + {WCAP_WI_PER_COL} WI/col, H1/H2 heavy")
print(f"Paying symbols: {len(PAYING_SYMBOLS)} (4L + 4H)")
print(f"Board composition (paying only): L ~{l_pct:.0f}%, H ~{h_pct:.0f}%")
print(f"Wild density: ~{wi_pct:.1f}% ({WI_PER_COL_BR0} per reel, ~{WI_PER_COL_BR0 * REELS / 36:.1f} per board)")
print(f"No clumping — pure random distribution")
