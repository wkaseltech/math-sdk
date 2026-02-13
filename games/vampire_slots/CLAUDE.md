# Vampire Slots — Game Reference

6x6 cluster cascade slot with a Blood Gauge multiplier system. Base game carries 72% of RTP through cascading + gauge interaction. Bonus is super rare (0.25% trigger, ~108x avg) but devastating. Buy bonus at 300x.

## Visual Direction

**Blood Gauge:** A tall glass vessel with etched measurement lines — but instead of volume markings, each line shows its multiplier (x1, x2, x3, x5, x10). Blood rises visibly between segments. The container glows and pulses at x5+, cracks and overflows at x10.

**L Symbols (Vials):** Glass vials filled with blood. When a cluster pays, the vials shatter — blood drains downward into streams that flow toward the gauge. The drain animation is the core visual beat of every cascade.

**PT (Chalice):** An ornate chalice that generates a blood whirlpool, vacuuming nearby vials into its vortex. After absorbing, a delayed geyser erupts upward from the chalice, shooting blood into the gauge.

**H Symbols (Vampires) — Unpowered:** When H clusters resolve at x1 (no gauge bonus), the vampires wither and crumble — they're starved, desiccated. The animation sells the "you needed gauge but didn't get it" moment.

**H Symbols (Vampires) — Empowered:** When H clusters resolve with an active gauge multiplier, the vampire delivers a voice line, eyes glow, and teleports away in a burst of dark energy. Higher multipliers = more dramatic exit (x10 should feel devastating).

**Blood Moon:** Screen tint shifts to deep crimson. Gauge vessel cracks fully, blood rains from above. Everything at max intensity — locked x10, escalating multipliers, vampires at full power.

## How It Plays

1. Player spins. 6x6 board fills from 8 paying symbols (4 L vials, 4 H vampires) + SC (coffin scatter) + PT (chalice token).
2. Clusters of 3+ matching symbols pay and explode. New symbols fall in. Repeat until no clusters.
3. **L clusters fill the Blood Gauge.** Each L symbol in a cluster adds 5% to the gauge (base game). Gauge resets every new spin.
4. **H clusters pay base value x gauge multiplier.** The gauge has 5 segments: x1 (0-20%), x2 (20-40%), x3 (40-60%), x5 (60-80%), x10 (80-100%).
5. **L-first evaluation:** Within each tumble, L clusters resolve first (filling gauge), then H clusters resolve with the NEW multiplier. This means a single cascade step can fill gauge AND apply it.
6. PT (chalice) on board absorbs nearby L symbols for bonus gauge fill (2.5% per L absorbed in base).

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
| Bonus avg payout | ~108x |
| Buy bonus cost | 300x |
| Effective dead | 67% |
| Effective basegame | 33% |
| Gauge max multiplier | x10 |

## Paytable

Cluster tiers: t1=(3-5), t2=(6-10), t3=(11-18), t4=(19-36). H symbols pay base x gauge multiplier.

| Symbol | t1 | t2 | t3 | t4 | Role |
|--------|-----|------|-------|--------|------|
| L1 (J) | 0.02 | 0.08 | 0.30 | 1.00 | Gauge fuel |
| L2 (Q) | 0.03 | 0.12 | 0.50 | 1.50 | Gauge fuel |
| L3 (K) | 0.04 | 0.15 | 0.70 | 2.00 | Gauge fuel |
| L4 (A) | 0.05 | 0.20 | 1.00 | 3.00 | Gauge fuel |
| H4 (Feral) | 0.50 | 2.50 | 10.00 | 25.00 | Payload |
| H3 (Knight) | 0.80 | 4.00 | 15.00 | 40.00 | Payload |
| H2 (Countess) | 1.20 | 6.00 | 25.00 | 60.00 | Payload |
| H1 (Elder) | 2.50 | 10.00 | 40.00 | 120.00 | Payload |
| SC (Coffin) | — | — | — | — | Bonus trigger (3+) |
| PT (Chalice) | — | — | — | — | L absorb for gauge |

At x10 gauge: H1 t4 = 1,200x. With cascading, multiple H clusters can hit per spin.

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
