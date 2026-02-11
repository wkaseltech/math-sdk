from src.executables.executables import Executables
from src.calculations.cluster import Cluster
from src.calculations.board import Board
from src.config.config import Config


class GameCalculations(Executables):
    """Override cluster evaluation to use XP multiplier instead of grid-position multipliers."""

    def evaluate_clusters_with_xp(
        self,
        config: Config,
        board: Board,
        clusters: dict,
        xp_multiplier: int = 1,
        return_data: dict = None,
    ) -> type:
        """Evaluate clusters and apply XP-based global multiplier to wins."""
        if return_data is None:
            return_data = {"totalWin": 0, "wins": []}

        total_win = 0
        for sym in clusters:
            for cluster in clusters[sym]:
                syms_in_cluster = len(cluster)
                if (syms_in_cluster, sym) in config.paytable:
                    sym_win = config.paytable[(syms_in_cluster, sym)]
                    win_with_mult = sym_win * xp_multiplier
                    total_win += win_with_mult
                    json_positions = [{"reel": p[0], "row": p[1]} for p in cluster]

                    central_pos = Cluster.get_central_cluster_position(json_positions)
                    return_data["wins"] += [
                        {
                            "symbol": sym,
                            "clusterSize": syms_in_cluster,
                            "win": win_with_mult,
                            "positions": json_positions,
                            "meta": {
                                "globalMult": xp_multiplier,
                                "clusterMult": 0,
                                "xpMultiplier": xp_multiplier,
                                "winWithoutMult": sym_win,
                                "overlay": {"reel": central_pos[0], "row": central_pos[1]},
                            },
                        }
                    ]

                    for positions in cluster:
                        board[positions[0]][positions[1]].explode = True

        return_data["totalWin"] += total_win

        return board, return_data
