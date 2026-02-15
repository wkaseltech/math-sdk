"""Blood Frenzy v1 — 6x6 cluster cascade, gated H symbols behind gauge thresholds.

Scheme A (gentle ramp): H1 always active, H2 @ x2, H3 @ x3, H4 @ x5.
L symbols are villagers (fuel). H symbols are hunters (gated payload).
L resolves first → fills gauge → unlocked H symbols pay at gauge multiplier.
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


class GameConfig(Config):
    """Singleton Blood Frenzy configuration."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "blood_frenzy"
        self.provider_number = 0
        self.working_name = "Blood Frenzy"
        self.wincap = 8000.0
        self.win_type = "cluster"
        self.rtp = 0.9700
        self.construct_paths()

        # Grid: 6 columns x 6 rows = 36 cells
        self.num_reels = 6
        self.num_rows = [6] * self.num_reels

        self.max_cascade_depth = 20

        # Cluster size tiers (min-3 on 36-cell grid)
        t1 = (3, 5)
        t2 = (6, 10)
        t3 = (11, 18)
        t4 = (19, 36)

        # Paytable: 8 symbols (4L villagers, 4H hunters)
        # L = fuel (small payouts, fill gauge). H = payload (gated, × gauge mult when active).
        # H values higher than Blood Tithe because gating reduces their effective frequency.
        pay_group = {
            # L1 (Peasant) — cheapest villager
            (t1, "L1"): 0.10,
            (t2, "L1"): 0.10,
            (t3, "L1"): 0.30,
            (t4, "L1"): 1.00,

            # L2 (Merchant)
            (t1, "L2"): 0.10,
            (t2, "L2"): 0.10,
            (t3, "L2"): 0.50,
            (t4, "L2"): 1.50,

            # L3 (Noble)
            (t1, "L3"): 0.10,
            (t2, "L3"): 0.20,
            (t3, "L3"): 0.70,
            (t4, "L3"): 2.00,

            # L4 (Priest) — highest villager
            (t1, "L4"): 0.10,
            (t2, "L4"): 0.20,
            (t3, "L4"): 1.00,
            (t4, "L4"): 3.00,

            # H1 (Warrior) — always active, lowest hunter
            (t1, "H1"): 0.80,
            (t2, "H1"): 3.00,
            (t3, "H1"): 12.00,
            (t4, "H1"): 30.00,

            # H2 (Cleric) — unlocks at x2
            (t1, "H2"): 1.50,
            (t2, "H2"): 6.00,
            (t3, "H2"): 25.00,
            (t4, "H2"): 60.00,

            # H3 (Paladin) — unlocks at x3
            (t1, "H3"): 2.50,
            (t2, "H3"): 10.00,
            (t3, "H3"): 40.00,
            (t4, "H3"): 100.00,

            # H4 (Cardinal) — unlocks at x5, rarest and biggest
            (t1, "H4"): 5.00,
            (t2, "H4"): 20.00,
            (t3, "H4"): 60.00,
            (t4, "H4"): 200.00,
        }
        self.paytable = self.convert_range_table(pay_group)

        self.include_padding = True

        # SC = scatter for bonus trigger
        # No PT/chalice in Blood Frenzy v1 — keep it clean
        self.special_symbols = {"scatter": ["SC"]}

        self.freespin_triggers = {
            self.basegame_type: {
                3: 10,
                4: 12,
                5: 15,
                6: 20,
            },
            self.freegame_type: {},
        }

        self.anticipation_triggers = {
            self.basegame_type: 2,
            self.freegame_type: 0,
        }

        # Blood Gauge: 5 segments — same structure as Blood Tithe
        # But here they GATE H symbols (Scheme A) AND multiply active H payouts
        self.gauge_fill_per_l_symbol_base = 5.0    # Base: 5% per L (resets per spin)
        self.gauge_fill_per_l_symbol_bonus = 0.15   # Bonus: 0.15% per L (persists)
        self.gauge_segments = {
            1: {"range": (0, 20), "multiplier": 1, "name": "Empty"},
            2: {"range": (20, 40), "multiplier": 2, "name": "Warming"},
            3: {"range": (40, 60), "multiplier": 3, "name": "Rising"},
            4: {"range": (60, 80), "multiplier": 5, "name": "Surging"},
            5: {"range": (80, 100.01), "multiplier": 10, "name": "Overflowing"},
        }

        # Gating thresholds: which gauge segment unlocks each H symbol
        # Scheme A (gentle ramp)
        self.h_unlock_thresholds = {
            "H1": 1,   # Always active (segment 1 = x1)
            "H2": 2,   # Unlocks at segment 2 (x2, gauge >= 20%)
            "H3": 3,   # Unlocks at segment 3 (x3, gauge >= 40%)
            "H4": 4,   # Unlocks at segment 4 (x5, gauge >= 60%)
        }

        # Blood Frenzy retrigger (same mechanic as Blood Moon)
        self.blood_frenzy_extra_spins = 3
        self.blood_frenzy_locked_spins = 3
        self.blood_frenzy_unlock_gauge = 80.0
        self.blood_frenzy_base_multiplier = 10
        self.blood_frenzy_escalation_per_cascade = 2

        # Symbol sets
        self.l_symbols = {"L1", "L2", "L3", "L4"}
        self.h_symbols = {"H1", "H2", "H3", "H4"}
        self.regular_symbols = ["H1", "H2", "H3", "H4", "L1", "L2", "L3", "L4"]

        # Reel strips
        reels = {
            "BR0": "BR0.csv",
            "FR0": "FR0.csv",
            "WCAP": "WCAP.csv",
        }
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        mode_maxwins = {"base": 8000, "bonus": 8000}

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
                    Distribution(
                        criteria="0",
                        quota=0.55,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "search_conditions": 0,
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.01,
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
                        quota=0.44,
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
                cost=300,
                rtp=self.rtp,
                max_win=mode_maxwins["bonus"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=True,
                distributions=[
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
