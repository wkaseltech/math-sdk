"""Vampire Slots v9 — 6x6 cluster cascade, base game as primary RTP delivery.

v9: x10 gauge cap (was x20), lower dead quota, base 50-200x is the star.
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


class GameConfig(Config):
    """Singleton Vampire Slots configuration."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "vampire_slots"
        self.provider_number = 0
        self.working_name = "Vampire Slots"
        self.wincap = 8000.0
        self.win_type = "cluster"
        self.rtp = 0.9700
        self.construct_paths()

        # Grid: 6 columns x 6 rows = 36 cells
        self.num_reels = 6
        self.num_rows = [6] * self.num_reels

        # Max cascade depth (prevents infinite loops with L-heavy boards)
        self.max_cascade_depth = 20

        # Cluster size tiers (min-3 on 36-cell grid — deep cascades, high turnover)
        t1 = (3, 5)      # Small cluster
        t2 = (6, 10)     # Medium cluster
        t3 = (11, 18)    # Large cluster
        t4 = (19, 36)    # Massive cluster

        # Paytable: 8 symbols (4 high vampires, 4 low blood vials)
        # v8: L symbols = gauge fuel (minimal payout), H symbols = payload (doubled, × gauge multiplier)
        # L-first eval: L fills gauge → H uses NEW multiplier in same tumble
        pay_group = {
            # L1 (J) — cheapest vial (gauge fuel)
            (t1, "L1"): 0.02,
            (t2, "L1"): 0.08,
            (t3, "L1"): 0.30,
            (t4, "L1"): 1.00,

            # L2 (Q)
            (t1, "L2"): 0.03,
            (t2, "L2"): 0.12,
            (t3, "L2"): 0.50,
            (t4, "L2"): 1.50,

            # L3 (K)
            (t1, "L3"): 0.04,
            (t2, "L3"): 0.15,
            (t3, "L3"): 0.70,
            (t4, "L3"): 2.00,

            # L4 (A) — highest vial
            (t1, "L4"): 0.05,
            (t2, "L4"): 0.20,
            (t3, "L4"): 1.00,
            (t4, "L4"): 3.00,

            # H4 (The Feral) — weakest vampire (× gauge mult)
            (t1, "H4"): 0.50,
            (t2, "H4"): 2.50,
            (t3, "H4"): 10.00,
            (t4, "H4"): 25.00,

            # H3 (The Knight)
            (t1, "H3"): 0.80,
            (t2, "H3"): 4.00,
            (t3, "H3"): 15.00,
            (t4, "H3"): 40.00,

            # H2 (The Countess)
            (t1, "H2"): 1.20,
            (t2, "H2"): 6.00,
            (t3, "H2"): 25.00,
            (t4, "H2"): 60.00,

            # H1 (The Elder) — rarest, biggest (x20 gauge = t4 2400x)
            (t1, "H1"): 2.50,
            (t2, "H1"): 10.00,
            (t3, "H1"): 40.00,
            (t4, "H1"): 120.00,
        }
        self.paytable = self.convert_range_table(pay_group)

        self.include_padding = True

        # SC (Coffin) = scatter for bonus trigger (base game only)
        # PT (Blood Moon) = retrigger token (bonus only)
        self.special_symbols = {"scatter": ["SC"], "retrigger": ["PT"]}

        # Free spin triggers: Coffin scatters from base game (6 reels max)
        self.freespin_triggers = {
            self.basegame_type: {
                3: 10,   # 3 coffins = 10 free spins
                4: 12,   # 4 coffins = 12 free spins
                5: 15,   # 5 coffins = 15 free spins
                6: 20,   # 6 coffins = 20 free spins (max)
            },
            self.freegame_type: {},  # Blood Moon retrigger is custom, not native
        }

        # Anticipation: tension at 2 coffins visible
        self.anticipation_triggers = {
            self.basegame_type: 2,
            self.freegame_type: 0,
        }

        # Blood Gauge: fill-only, 5 segments (segment 5 = x10 — sweet spot for 50-200x H wins)
        # v9: x10 cap (was x20) — kills 2400x outliers, puts H wins in 50-200x range
        self.gauge_fill_per_l_symbol_base = 5.0  # Base game: 5% per L → cascades reach x3-x5 more often
        self.gauge_fill_per_l_symbol_bonus = 0.12  # Bonus: 0.12% per L → slow trickle across spins
        self.gauge_fill_per_pt_absorb_base = 2.5  # Base PT absorb: 2.5% per L vacuumed (15 vials = 37.5%)
        self.gauge_fill_per_pt_absorb_bonus = 0.25  # Bonus PT absorb: 0.25% per L (15 vials = 3.75%)
        self.gauge_segments = {
            1: {"range": (0, 20), "multiplier": 1, "name": "Empty"},
            2: {"range": (20, 40), "multiplier": 2, "name": "Warming"},
            3: {"range": (40, 60), "multiplier": 3, "name": "Rising"},
            4: {"range": (60, 80), "multiplier": 5, "name": "Surging"},
            5: {"range": (80, 100.01), "multiplier": 10, "name": "Overflowing"},
        }

        # Blood Moon retrigger: gauge hits 100% during bonus
        self.blood_moon_extra_spins = 3
        self.blood_moon_locked_spins = 3
        self.blood_moon_unlock_gauge = 80.0  # gauge drops to 80% after lock ends

        # Blood Moon escalation: during Blood Moon, multiplier grows per cascade
        self.blood_moon_base_multiplier = 10   # starts at x10 (segment 5)
        self.blood_moon_escalation_per_cascade = 2  # +2x per cascade during Blood Moon

        # L and H symbol sets (for gauge logic)
        self.l_symbols = {"L1", "L2", "L3", "L4"}
        self.h_symbols = {"H1", "H2", "H3", "H4"}

        # All regular symbols (for PT replacement during bonus)
        self.regular_symbols = ["H1", "H2", "H3", "H4", "L1", "L2", "L3", "L4"]

        # Reel strips
        reels = {
            "BR0": "BR0.csv",    # Base game reels (SC, no PT)
            "FR0": "FR0.csv",    # Free game reels (PT, no SC)
            "WCAP": "WCAP.csv",  # Win cap reels (SC + PT, H1-heavy)
        }
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        mode_maxwins = {"base": 8000, "bonus": 8000}

        # V1 VALIDATION: wincap distributions commented out for quick sims.
        # Re-enable for production runs.
        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=mode_maxwins["base"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    # Distribution(
                    #     criteria="wincap",
                    #     quota=0.001,
                    #     win_criteria=mode_maxwins["base"],
                    #     conditions={
                    #         "reel_weights": {
                    #             self.basegame_type: {"BR0": 1},
                    #             self.freegame_type: {"FR0": 1, "WCAP": 5},
                    #         },
                    #         "scatter_triggers": {3: 1, 4: 2},
                    #         "force_wincap": True,
                    #         "force_freegame": True,
                    #     },
                    # ),
                    Distribution(
                        criteria="0",
                        quota=0.45,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "search_conditions": 0,
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.04,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "scatter_triggers": {3: 5, 4: 1},
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.51,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name="bonus",
                cost=100,
                rtp=self.rtp,
                max_win=mode_maxwins["bonus"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=True,
                distributions=[
                    # Distribution(
                    #     criteria="wincap",
                    #     quota=0.001,
                    #     win_criteria=mode_maxwins["bonus"],
                    #     conditions={
                    #         "reel_weights": {
                    #             self.basegame_type: {"BR0": 1},
                    #             self.freegame_type: {"FR0": 1, "WCAP": 5},
                    #         },
                    #         "scatter_triggers": {3: 1, 4: 2},
                    #         "force_wincap": True,
                    #         "force_freegame": True,
                    #     },
                    # ),
                    Distribution(
                        criteria="freegame",
                        quota=1.0,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "scatter_triggers": {3: 5, 4: 1},
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                ],
            ),
        ]
