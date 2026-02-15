# Vampire Slots — Game Reference

6x6 cluster cascade slot with a Blood Gauge multiplier system. Base game carries 72% of RTP through cascading + gauge interaction. Bonus is super rare (0.25% trigger, ~291x avg) but devastating. Buy bonus at 300x. Sine-wave reel gradients + cascade-forward optimizer scaling (v11).

## Visual Direction

**Blood Gauge:** A tall glass vessel with etched measurement lines — but instead of volume markings, each line shows its multiplier (x1, x2, x3, x5, x10). Blood rises visibly between segments. The container glows and pulses at x5+, cracks and overflows at x10.

**L Symbols (Vials):** Glass vials filled with blood. When a cluster pays, the vials shatter — blood drains downward into streams that flow toward the gauge. The drain animation is the core visual beat of every cascade.

**PT (Chalice):** An ornate chalice that generates a blood whirlpool, vacuuming nearby vials into its vortex. After absorbing, a delayed geyser erupts upward from the chalice, shooting blood into the gauge.

**H Symbols (Vampires) — Unpowered:** When H clusters resolve at x1 (no gauge bonus), the vampires wither and crumble — they're starved, desiccated. The animation sells the "you needed gauge but didn't get it" moment.

**H Symbols (Vampires) — Empowered:** When H clusters resolve with an active gauge multiplier, the vampire delivers a voice line, eyes glow, and teleports away in a burst of dark energy. Higher multipliers = more dramatic exit (x10 should feel devastating).

**Blood Moon:** Screen tint shifts to deep crimson. Gauge vessel cracks fully, blood rains from above. Everything at max intensity — locked x10, escalating multipliers, vampires at full power.

## How To Play

**Clusters:** Connect 3 or more matching symbols horizontally or vertically to form a cluster. Winning clusters are removed and new symbols fall in from above. Cascades continue until no new clusters form.

**Cluster Payouts:** Payouts are based on cluster size tiers, not individual symbol count. A cluster of 3 pays the same as a cluster of 5 — what matters is which tier you reach.
- **3–5 symbols** (Tier 1) — Small win
- **6–10 symbols** (Tier 2) — Medium win
- **11–18 symbols** (Tier 3) — Large win
- **19–36 symbols** (Tier 4) — Massive win

**Blood Gauge:** Vial symbols (L) fill the Blood Gauge when they cluster. Each L symbol adds 5% to the gauge. The gauge has 5 multiplier segments — the higher it fills, the more Vampire symbols (H) pay. Vials resolve first in every cascade, so the gauge can fill and empower vampires in the same tumble. The gauge resets at the start of each new spin.

**Chalice:** When a Chalice appears, it absorbs nearby vial symbols and feeds their blood directly into the gauge.

**Coffin Scatter:** Land 3 or more Coffin scatters to trigger the Free Spins bonus.

**Free Spins:** During Free Spins, the Blood Gauge persists between spins — it never resets. The fill rate is slower (0.12% per L symbol), but it builds across every spin.

**Blood Moon:** If the gauge reaches 100% during Free Spins, Blood Moon activates — 3 extra spins locked at x10 multiplier, escalating +2x with every cascade.

## The Feeling

Base game: ~25% of spins cascade. When they do, vials drain into the gauge, it climbs, and H vampire clusters hit with growing multipliers. A good cascade reaching x5 or x10 gauge pays 50-200x. Most spins are dead (75% effective), but the 25% that hit feel active and rewarding.

Bonus: Lands naturally ~1 in 400 spins (3+ coffin scatters). When it does, it's an event. 10+ free spins with persistent gauge (doesn't reset between spins). Slow fill (0.12%/L) but accumulates across all spins. Average bonus pays ~108x.

## Blood Moon (Bonus Feature)

If gauge hits 100% during bonus: Blood Moon activates. +3 extra spins locked at x10 multiplier. During Blood Moon, multiplier escalates +2x per cascade (x10, x12, x14...). After lock ends, gauge drops to 80%. Rate: ~14% of bonuses.

## Key Numbers

| Metric | Value |
|--------|-------|
| Grid | 6x6 (36 cells) |
| Cluster min | 3 |
| Symbols | 8 paying + SC + PT |
| Wincap | 8,000x |
| RTP | 97.00% |
| Base RTP share | 70% (72% of total) |
| Bonus RTP share | 27% (28% of total) |
| Bonus trigger | 0.25% (1 in 400) |
| Bonus avg payout | ~291x (v11) |
| Buy bonus cost | 300x |
| Effective dead | 75% |
| Effective basegame | 25% |
| Cascade depth | 1.17 avg (sine reels) |
| Empowered H rate | 84% |
| Broken promise | ~12% of hitting spins |
| Gauge max multiplier | x10 |

## Paytable

All values shown as multiplier of bet. Vampire (H) payouts are further multiplied by the Blood Gauge level.

### Vials — Fill the Blood Gauge

| Symbol | 3–5 | 6–10 | 11–18 | 19–36 |
|--------|------|------|-------|-------|
| J Vial | 0.02x | 0.08x | 0.30x | 1.00x |
| Q Vial | 0.03x | 0.12x | 0.50x | 1.50x |
| K Vial | 0.04x | 0.15x | 0.70x | 2.00x |
| A Vial | 0.05x | 0.20x | 1.00x | 3.00x |

### Vampires — Multiplied by Blood Gauge

| Symbol | 3–5 | 6–10 | 11–18 | 19–36 |
|--------|------|------|-------|-------|
| Feral | 0.50x | 2.50x | 10.00x | 25.00x |
| Knight | 0.80x | 4.00x | 15.00x | 40.00x |
| Countess | 1.20x | 6.00x | 25.00x | 60.00x |
| Elder | 2.50x | 10.00x | 40.00x | 120.00x |

At x10 gauge, an Elder cluster of 19+ pays **1,200x** your bet.

### Special Symbols

| Symbol | Function |
|--------|----------|
| Coffin (Scatter) | 3+ triggers Free Spins |
| Chalice | Absorbs nearby vials into the Blood Gauge |

## Gauge Segments

| Segment | Range | Multiplier |
|---------|-------|-----------|
| Empty | 0-20% | x1 |
| Warming | 20-40% | x2 |
| Rising | 40-60% | x3 |
| Surging | 60-80% | x5 |
| Overflowing | 80-100% | x10 |

Fill rates: base=5.0%/L (fast, resets per spin), bonus=0.12%/L (slow, persists across spins).

## File Guide

| File | What it does |
|------|-------------|
| `game_config.py` | Grid, paytable, gauge config, distributions, bet modes, reel loading |
| `game_calculations.py` | L-first cluster eval — splits L/H, applies gauge multiplier to H |
| `game_executables.py` | Gauge fill logic, Blood Moon trigger/lock, PT absorb |
| `game_events.py` | BookEvent builders: gaugeUpdate, bloodMoon, chaliceAbsorb |
| `game_override.py` | Dead spin fence, scatter clamping, gauge reset per base spin |
| `gamestate.py` | Sim loop with cascade, freespin, diagnostics |
| `game_optimization.py` | Optimizer targets: freegame rtp=0.27 hr=400, basegame rtp=0.70 hr=4 |
| `regen_reels.py` | Reel generator. SC_PER_COL=1 (rare bonus). Run from repo root. |
| `run.py` | Sim runner. 20k base, 5k bonus, 5 threads. |

## Optimizer Notes

- `avg_win = hr x rtp` must be above minimum book payout in that fence or optimizer hangs forever
- Current: freegame avg_win = 400 x 0.27 = 108x (book median ~99x, mean ~168x)
- Current: basegame avg_win = 4 x 0.70 = 2.8x (book median 2.0x, mean 8.5x)
- num_per_fence=200 (matches freegame book count)
- min_m2m=1, max_m2m=500 (wide range avoids filtering issues)
- Wincap distributions disabled — re-enable for production

## Full Spec

KaselForge: `games/002-vampire-slots/CLAUDE.md` (frontend paths, asset status, iteration history)
