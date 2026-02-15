"""Volatility profile generator — reads LUT CSVs, outputs distribution stats.

Usage:
    python scripts/volatility_profile.py games/dungeon_quest
    python scripts/volatility_profile.py games/dungeon_quest --json
    python scripts/volatility_profile.py games/dungeon_quest --mode bonus
"""

import csv
import json
import math
import os
import sys
from collections import defaultdict


def read_lut(path):
    """Read lookUpTable CSV → list of (id, weight, payout_mult)."""
    rows = []
    with open(path) as f:
        for row in csv.reader(f):
            rows.append((int(row[0]), int(row[1]), int(row[2]) / 100))
    return rows


def read_segmented_lut(path):
    """Read segmented LUT → list of (id, gametype, base_payout, free_payout)."""
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path) as f:
        for row in csv.reader(f):
            rows.append((int(row[0]), row[1], float(row[2]), float(row[3])))
    return rows


def compute_profile(rows):
    """Compute volatility profile from LUT rows."""
    total_weight = sum(w for _, w, _ in rows)
    payouts = []
    for _, w, p in rows:
        for _ in range(w):
            payouts.append(p)

    n = len(payouts)
    payouts.sort()

    # Basic stats
    mean = sum(payouts) / n
    variance = sum((p - mean) ** 2 for p in payouts) / n
    std_dev = math.sqrt(variance)

    # Hit rate
    hits = sum(1 for p in payouts if p > 0)
    hit_rate = hits / n

    # Percentiles
    def percentile(pct):
        idx = int(pct / 100 * n)
        return payouts[min(idx, n - 1)]

    pcts = {
        "p10": percentile(10),
        "p25": percentile(25),
        "p50": percentile(50),
        "p75": percentile(75),
        "p90": percentile(90),
        "p95": percentile(95),
        "p99": percentile(99),
        "p99.9": percentile(99.9),
    }

    # Win bands (multiplier ranges)
    bands = [
        ("0x (dead)", 0, 0),
        ("0.01-1x (below bet)", 0.01, 1),
        ("1-2x (small)", 1, 2),
        ("2-5x", 2, 5),
        ("5-10x", 5, 10),
        ("10-30x", 10, 30),
        ("30-100x", 30, 100),
        ("100-500x", 100, 500),
        ("500-1000x", 500, 1000),
        ("1000-5000x", 1000, 5000),
        ("5000x+", 5000, float("inf")),
    ]

    band_counts = []
    for label, lo, hi in bands:
        if lo == 0 and hi == 0:
            count = sum(1 for p in payouts if p == 0)
        else:
            count = sum(1 for p in payouts if lo <= p < hi)
        band_counts.append((label, count, count / n * 100))

    # Top 20 wins
    top = payouts[-20:][::-1]

    return {
        "outcomes": n,
        "total_weight": total_weight,
        "hit_rate": hit_rate,
        "mean_payout": mean,
        "min_payout": payouts[0],
        "max_payout": payouts[-1],
        "std_dev": std_dev,
        "variance": variance,
        "cv": std_dev / mean if mean > 0 else 0,  # coefficient of variation
        "percentiles": pcts,
        "bands": band_counts,
        "top_20": top,
    }


def compute_bonus_stats(segmented_rows):
    """Compute bonus-specific stats from segmented LUT."""
    bonus_outcomes = [r for r in segmented_rows if r[3] > 0]  # has freegame payout
    base_only = [r for r in segmented_rows if r[3] == 0]

    if not bonus_outcomes:
        return None

    bonus_payouts = [r[3] for r in bonus_outcomes]
    bonus_rate = len(bonus_outcomes) / len(segmented_rows) * 100

    return {
        "bonus_rate": bonus_rate,
        "bonus_count": len(bonus_outcomes),
        "base_only_count": len(base_only),
        "bonus_avg_payout": sum(bonus_payouts) / len(bonus_payouts),
        "bonus_min": min(bonus_payouts),
        "bonus_max": max(bonus_payouts),
        "bonus_median": sorted(bonus_payouts)[len(bonus_payouts) // 2],
    }


def format_text(profile, bonus_stats=None, mode="base"):
    """Format profile as readable text."""
    lines = []
    lines.append(f"{'=' * 60}")
    lines.append(f"  VOLATILITY PROFILE — {mode.upper()} MODE")
    lines.append(f"{'=' * 60}")
    lines.append("")
    lines.append(f"  Outcomes:      {profile['outcomes']:,}")
    lines.append(f"  Hit rate:      {profile['hit_rate'] * 100:.1f}%")
    lines.append(f"  Mean payout:   {profile['mean_payout']:.2f}x")
    lines.append(f"  Min / Max:     {profile['min_payout']:.1f}x / {profile['max_payout']:.1f}x")
    lines.append(f"  Std deviation: {profile['std_dev']:.2f}")
    lines.append(f"  Variance:      {profile['variance']:.2f}")
    lines.append(f"  CV (vol idx):  {profile['cv']:.2f}")
    lines.append("")

    # Volatility classification
    cv = profile["cv"]
    if cv < 3:
        vol_class = "LOW"
    elif cv < 8:
        vol_class = "MEDIUM"
    elif cv < 15:
        vol_class = "HIGH"
    else:
        vol_class = "VERY HIGH"
    lines.append(f"  Volatility:    {vol_class} (CV={cv:.1f})")
    lines.append("")

    lines.append("  PERCENTILES")
    lines.append("  " + "-" * 30)
    for k, v in profile["percentiles"].items():
        lines.append(f"  {k:>8s}:  {v:>10.2f}x")
    lines.append("")

    lines.append("  WIN DISTRIBUTION")
    lines.append("  " + "-" * 50)
    max_bar = 40
    max_pct = max(pct for _, _, pct in profile["bands"])
    for label, count, pct in profile["bands"]:
        if count == 0:
            continue
        bar_len = int(pct / max_pct * max_bar) if max_pct > 0 else 0
        bar = "#" * max(bar_len, 1) if count > 0 else ""
        lines.append(f"  {label:>20s}  {bar}  {pct:5.1f}% ({count:,})")
    lines.append("")

    if bonus_stats:
        lines.append("  BONUS STATS")
        lines.append("  " + "-" * 30)
        lines.append(f"  Trigger rate:  {bonus_stats['bonus_rate']:.1f}% of outcomes")
        lines.append(f"  Avg payout:    {bonus_stats['bonus_avg_payout']:.1f}x")
        lines.append(f"  Median:        {bonus_stats['bonus_median']:.1f}x")
        lines.append(f"  Min / Max:     {bonus_stats['bonus_min']:.1f}x / {bonus_stats['bonus_max']:.1f}x")
        lines.append("")

    lines.append(f"  TOP 20 PAYOUTS")
    lines.append("  " + "-" * 30)
    for i, p in enumerate(profile["top_20"], 1):
        lines.append(f"  {i:>3d}. {p:>10.1f}x")

    lines.append("")
    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate volatility profile from LUT")
    parser.add_argument("game_path", help="Path to game directory (e.g. games/dungeon_quest)")
    parser.add_argument("--mode", default="base", choices=["base", "bonus", "all"], help="Bet mode")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    lut_dir = os.path.join(args.game_path, "library", "lookup_tables")

    modes = ["base", "bonus"] if args.mode == "all" else [args.mode]

    for mode in modes:
        lut_path = os.path.join(lut_dir, f"lookUpTable_{mode}.csv")
        seg_path = os.path.join(lut_dir, f"lookUpTableSegmented_{mode}.csv")

        if not os.path.exists(lut_path):
            print(f"LUT not found: {lut_path}")
            continue

        rows = read_lut(lut_path)
        profile = compute_profile(rows)

        bonus_stats = None
        seg_rows = read_segmented_lut(seg_path)
        if seg_rows:
            bonus_stats = compute_bonus_stats(seg_rows)

        if args.json:
            out = {"mode": mode, "profile": profile}
            if bonus_stats:
                out["bonus_stats"] = bonus_stats
            print(json.dumps(out, indent=2, default=str))
        else:
            print(format_text(profile, bonus_stats, mode))


if __name__ == "__main__":
    main()
