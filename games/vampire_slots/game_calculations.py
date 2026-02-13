"""Vampire Slots — L-first cluster evaluation with gauge-based H multiplier."""

from src.executables.executables import Executables
from src.calculations.cluster import Cluster
from src.config.config import Config
from src.calculations.board import Board


class GameCalculations(Executables):
    """Two-pass cluster evaluation: L clusters fill gauge first, then H clusters use NEW multiplier."""

    def evaluate_clusters_with_gauge(
        self,
        config: Config,
        board: Board,
        clusters: dict,
        gauge_fill_fn=None,
        get_h_mult_fn=None,
        return_data: dict = None,
    ):
        """Evaluate clusters in two passes: L first (gauge fill), then H (new multiplier).

        Pass 1: L clusters → base wins (x1), count L symbols
        gauge_fill_fn(l_count) → fills gauge, returns delta
        get_h_mult_fn() → returns NEW H multiplier after fill
        Pass 2: H clusters → wins with new multiplier
        Then: mark ALL positions as explode atomically

        Returns:
            board, return_data, l_cluster_info, h_cluster_info, total_l_symbols, gauge_delta
        """
        if return_data is None:
            return_data = {"totalWin": 0, "wins": []}

        total_win = 0
        l_cluster_info = []
        h_cluster_info = []
        total_l_symbols = 0
        all_explode_positions = []

        # --- Pass 1: L clusters only (always x1 multiplier) ---
        for sym in clusters:
            if sym not in config.l_symbols:
                continue
            for cluster in clusters[sym]:
                syms_in_cluster = len(cluster)
                if (syms_in_cluster, sym) not in config.paytable:
                    continue

                sym_win = config.paytable[(syms_in_cluster, sym)]
                total_win += sym_win
                total_l_symbols += syms_in_cluster

                json_positions = [{"reel": p[0], "row": p[1]} for p in cluster]
                central_pos = Cluster.get_central_cluster_position(json_positions)

                win_entry = {
                    "symbol": sym,
                    "clusterSize": syms_in_cluster,
                    "win": sym_win,
                    "positions": json_positions,
                    "meta": {
                        "globalMult": 1,
                        "clusterMult": 0,
                        "gaugeMultiplier": 1,
                        "winWithoutMult": sym_win,
                        "symbolType": "L",
                        "overlay": {"reel": central_pos[0], "row": central_pos[1]},
                    },
                }
                return_data["wins"].append(win_entry)
                l_cluster_info.append({
                    "symbol": sym,
                    "positions": json_positions,
                    "clusterSize": syms_in_cluster,
                })
                all_explode_positions.extend(cluster)

        # --- Fill gauge from L symbols ---
        gauge_delta = 0.0
        if gauge_fill_fn and total_l_symbols > 0:
            gauge_delta = gauge_fill_fn(total_l_symbols)

        # --- Get NEW H multiplier (after gauge fill) ---
        h_mult = get_h_mult_fn() if get_h_mult_fn else 1

        # --- Pass 2: H clusters with new multiplier ---
        for sym in clusters:
            if sym not in config.h_symbols:
                continue
            for cluster in clusters[sym]:
                syms_in_cluster = len(cluster)
                if (syms_in_cluster, sym) not in config.paytable:
                    continue

                sym_win = config.paytable[(syms_in_cluster, sym)]
                win_with_mult = sym_win * h_mult
                total_win += win_with_mult

                json_positions = [{"reel": p[0], "row": p[1]} for p in cluster]
                central_pos = Cluster.get_central_cluster_position(json_positions)

                win_entry = {
                    "symbol": sym,
                    "clusterSize": syms_in_cluster,
                    "win": win_with_mult,
                    "positions": json_positions,
                    "meta": {
                        "globalMult": h_mult,
                        "clusterMult": 0,
                        "gaugeMultiplier": h_mult,
                        "winWithoutMult": sym_win,
                        "symbolType": "H",
                        "overlay": {"reel": central_pos[0], "row": central_pos[1]},
                    },
                }
                return_data["wins"].append(win_entry)
                h_cluster_info.append({
                    "symbol": sym,
                    "positions": json_positions,
                    "clusterSize": syms_in_cluster,
                    "gaugeMultiplier": h_mult,
                })
                all_explode_positions.extend(cluster)

        # --- Mark ALL positions as explode atomically (after both passes) ---
        for positions in all_explode_positions:
            board[positions[0]][positions[1]].explode = True

        return_data["totalWin"] += total_win
        return board, return_data, l_cluster_info, h_cluster_info, total_l_symbols, gauge_delta
