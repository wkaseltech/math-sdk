"""Dungeon Quest v6 — Cluster cascade with XP multiplier progression + potion retrigger"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


class GameConfig(Config):
    """Singleton Dungeon Quest configuration."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "dungeon_quest"
        self.provider_number = 0
        self.working_name = "Dungeon Quest"
        self.wincap = 8000.0
        self.win_type = "cluster"
        self.rtp = 0.9700
        self.construct_paths()

        # Grid: 5 columns × 7 rows = 35 cells
        self.num_reels = 5
        self.num_rows = [7] * self.num_reels

        # Cluster size tiers (scaled for 35-cell grid, minimum cluster = 4)
        t1 = (4, 8)      # Small cluster
        t2 = (9, 15)     # Medium cluster
        t3 = (16, 24)    # Large cluster
        t4 = (25, 35)    # Massive cluster

        # Paytable: 7 symbols (4 high, 3 low)
        # Values are multipliers on the bet BEFORE XP multiplier is applied
        # Scaled ~1.5x from min-3 values to compensate for lower hit rate
        pay_group = {
            # LICH (H1) — Undead sorcerer king, rarest, biggest payout
            (t1, "H1"): 2.5,
            (t2, "H1"): 6.0,
            (t3, "H1"): 20.0,
            (t4, "H1"): 45.0,

            # DRAGON (H2) — Fearsome beast
            (t1, "H2"): 1.5,
            (t2, "H2"): 4.0,
            (t3, "H2"): 12.5,
            (t4, "H2"): 30.0,

            # LIZARDMAN (H3) — Scaled warrior
            (t1, "H3"): 1.0,
            (t2, "H3"): 3.0,
            (t3, "H3"): 7.5,
            (t4, "H3"): 22.5,

            # GOBLIN (H4) — Armed and cunning
            (t1, "H4"): 0.75,
            (t2, "H4"): 2.5,
            (t3, "H4"): 6.0,
            (t4, "H4"): 17.5,

            # SKELETON (L1) — Undead warrior
            (t1, "L1"): 0.4,
            (t2, "L1"): 1.25,
            (t3, "L1"): 4.0,
            (t4, "L1"): 10.0,

            # SPIDER (L2) — Dungeon crawler
            (t1, "L2"): 0.25,
            (t2, "L2"): 0.75,
            (t3, "L2"): 2.5,
            (t4, "L2"): 7.5,

            # BAT (L3) — Weakest enemy
            (t1, "L3"): 0.15,
            (t2, "L3"): 0.4,
            (t3, "L3"): 1.5,
            (t4, "L3"): 4.5,
        }
        self.paytable = self.convert_range_table(pay_group)

        self.include_padding = True
        # Key scatter + Potion (bonus-only retrigger). No wilds.
        # PT registered as "potion" special type so the SDK creates Symbol objects for it.
        # PT is NOT in the paytable — it doesn't pay, only adds free spins.
        self.special_symbols = {"scatter": ["SC"], "potion": ["PT"]}

        # Free spin triggers: Key scatters trigger bonus from base game only
        # Potion retrigger is handled custom in game_executables.py — NOT via freespin_triggers
        self.freespin_triggers = {
            self.basegame_type: {
                3: 8,    # 3 keys = 8 free spins
                4: 10,   # 4 keys = 10 free spins
                5: 12,   # 5 keys = 12 free spins
                6: 15,   # 6 keys = 15 free spins
                7: 18,   # 7 keys = 18 free spins
            },
            self.freegame_type: {},  # Empty — potion retrigger is custom, not native
        }

        # Anticipation: start tension animation at 2 keys visible
        self.anticipation_triggers = {
            self.basegame_type: 2,
            self.freegame_type: 0,  # No anticipation for potions
        }

        # XP Multiplier System (custom — logic in game_executables.py)
        self.xp_multiplier_tiers = {
            1: 1,    # Level 1: ×1 (default)
            2: 2,    # Level 2: ×2
            3: 3,    # Level 3: ×3
            4: 5,    # Level 4: ×5
            5: 10,   # Level 5: ×10
            6: 20,   # Level MAX: ×20
        }

        # Cumulative cluster count thresholds to reach each level
        self.xp_thresholds = {
            2: 2,    # 2 clusters → Level 2
            3: 5,    # 5 clusters → Level 3
            4: 9,    # 9 clusters → Level 4
            5: 15,   # 15 clusters → Level 5
            6: 22,   # 22 clusters → Level MAX
        }

        # Max level escalation: multiplier keeps growing with each additional cluster
        self.max_level = 6
        self.max_level_base_multiplier = 20
        self.max_level_escalation_per_cluster = 3

        # Regular symbols list (for potion replacement during bonus)
        self.regular_symbols = ["H1", "H2", "H3", "H4", "L1", "L2", "L3"]

        # Reel strips
        reels = {
            "BR0": "BR0.csv",    # Base game reels (no PT)
            "FR0": "FR0.csv",    # Free game reels (PT ~1%, no SC)
            "WCAP": "WCAP.csv",  # Win cap reels (includes PT at ~2%)
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
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwins["base"],
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1, "WCAP": 5},
                            },
                            "scatter_triggers": {3: 1, 4: 2},
                            "force_wincap": True,
                            "force_freegame": True,
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
                        criteria="0",
                        quota=0.50,
                        win_criteria=0.0,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.459,
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
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwins["bonus"],
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1, "WCAP": 5},
                            },
                            "scatter_triggers": {3: 1, 4: 2},
                            "force_wincap": True,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.999,
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
