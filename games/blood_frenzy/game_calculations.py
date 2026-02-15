"""Blood Frenzy — L-first cluster evaluation with gated H symbols.

Pass 1: L clusters pay at x1, fill gauge. All L symbols always cluster.
Pass 2: Only UNLOCKED H symbols cluster. Active H pays at current gauge multiplier.
         Locked H symbols are invisible to the cluster algorithm.
"""

from src.executables.executables import Executables
from src.calculations.cluster import Cluster
from src.config.config import Config
from src.calculations.board import Board


class GameCalculations(Executables):
    """Two-pass cluster evaluation with H symbol gating."""

    def evaluate_clusters_with_gating(
        self,
        config: Config,
        board: Board,
        gauge_fill_fn=None,
        get_h_mult_fn=None,
        get_active_h_fn=None,
        return_data: dict = None,
    ):
        """Evaluate clusters: L first (gauge fill), then only active H (gated by gauge).

        Unlike Blood Tithe which uses pre-computed clusters dict, we need to
        run clustering TWICE: once for L (all L always participate), once for
        only the unlocked H symbols. Locked H symbols are excluded from clustering.

        Returns:
            board, return_data, l_cluster_info, h_cluster_info, total_l_symbols,
            gauge_delta, newly_unlocked
        """
        if return_data is None:
            return_data = {"totalWin": 0, "wins": []}

        total_win = 0
        l_cluster_info = []
        h_cluster_info = []
        total_l_symbols = 0
        all_explode_positions = []

        # --- Pass 1: L clusters (always active, x1 multiplier) ---
        # Get clusters for ALL symbols, but only process L
        all_clusters = Cluster.get_clusters(board)

        for sym in all_clusters:
            if sym not in config.l_symbols:
                continue
            for cluster in all_clusters[sym]:
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

        # --- Get active H symbols (post-fill gauge level) ---
        active_h = get_active_h_fn() if get_active_h_fn else set(config.h_symbols)
        h_mult = get_h_mult_fn() if get_h_mult_fn else 1

        # --- Pass 2: Only ACTIVE H clusters ---
        # We use the same cluster result but only process unlocked H symbols
        for sym in all_clusters:
            if sym not in active_h:
                continue
            for cluster in all_clusters[sym]:
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

        # --- Mark ALL positions as explode atomically ---
        for positions in all_explode_positions:
            board[positions[0]][positions[1]].explode = True

        return_data["totalWin"] += total_win

        return board, return_data, l_cluster_info, h_cluster_info, total_l_symbols, gauge_delta
