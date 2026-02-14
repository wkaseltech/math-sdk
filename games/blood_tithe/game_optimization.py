"""Blood Tithe v12 — cascade-forward optimizer scaling with wild support."""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructFenceBias,
    ConstructConditions,
    verify_optimization_input,
)


class OptimizationSetup:
    """"""

    def __init__(self, game_config):
        self.game_config = game_config
        wincaps = {}
        for bm in game_config.bet_modes:
            wincaps[bm.get_name()] = bm.get_wincap()
        self.game_config.opt_params = {
            "base": {
                "conditions": {
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "freegame": ConstructConditions(
                        rtp=0.27, hr=400, search_conditions={"symbol": "scatter"}
                    ).return_dict(),
                    "basegame": ConstructConditions(hr=4.0, rtp=0.70).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        # Suppress noise wins, boost empowered vampire zone
                        {"criteria": "basegame", "scale_factor": 0.5, "win_range": (0, 1), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.7, "win_range": (1, 5), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 1.5, "win_range": (5, 50), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 1.2, "win_range": (50, 200), "probability": 1.0},
                        # Suppress dud bonuses, boost good outcomes
                        {"criteria": "freegame", "scale_factor": 0.5, "win_range": (0, 30), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 1.4, "win_range": (30, 100), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 1.3, "win_range": (100, 500), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=500,
                    num_per_fence=200,
                    min_m2m=1,
                    max_m2m=500,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                ).return_dict(),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["basegame"],
                    bias_ranges=[(0.5, 1.5)],
                    bias_weights=[0.4],
                ).return_dict(),
            },
            "bonus": {
                "conditions": {
                    "freegame": ConstructConditions(rtp=0.97, hr="x").return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "freegame", "scale_factor": 0.5, "win_range": (0, 30), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 1.4, "win_range": (30, 100), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 1.3, "win_range": (100, 500), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=500,
                    num_per_fence=200,
                    min_m2m=1,
                    max_m2m=500,
                    pmb_rtp=1.0,
                    sim_trials=2000,
                    test_spins=[10, 20, 50],
                    test_weights=[0.6, 0.2, 0.2],
                    score_type="rtp",
                ).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
