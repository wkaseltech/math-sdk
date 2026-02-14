"""Blood Tithe — L-first cluster evaluation with gauge-based H multiplier and wild support.

Wilds (WI) expand both L and H clusters via BFS bridging.
Persist rule: wilds never clear with vials. They only leave the board when part of a
winning H cluster. This means wilds survive L cluster explosions and persist across
cascade tumbles until they bridge a vampire cluster.
"""

from src.executables.executables import Executables
from src.calculations.cluster import Cluster
from src.config.config import Config
from src.calculations.board import Board


def _get_neighbors(reel, row, num_reels, board):
    """Get orthogonal neighbors within board bounds."""
    neighbors = []
    if reel > 0 and row < len(board[reel - 1]):
        neighbors.append((reel - 1, row))
    if reel < num_reels - 1 and row < len(board[reel + 1]):
        neighbors.append((reel + 1, row))
    if row > 0:
        neighbors.append((reel, row - 1))
    if row < len(board[reel]) - 1:
        neighbors.append((reel, row + 1))
    return neighbors


def _find_clusters_with_wilds(board, symbol_set, wild_pool, num_reels):
    """Find connected components of same-type symbols, bridging through wilds.

    For each symbol type in symbol_set, BFS from all positions of that type.
    Wilds in wild_pool act as bridges (claimed wilds are removed from pool).

    Returns dict of sym -> list of sets, each set = {(reel, row), ...}.
    """
    result = {}

    for sym in sorted(symbol_set):
        sym_positions = set()
        for r in range(num_reels):
            for c in range(len(board[r])):
                if board[r][c].defn.name == sym:
                    sym_positions.add((r, c))

        if not sym_positions:
            continue

        visited = set()
        sym_clusters = []

        for start in sorted(sym_positions):
            if start in visited:
                continue

            component = set()
            frontier = [start]
            component.add(start)
            visited.add(start)

            while frontier:
                pos = frontier.pop(0)
                for nr, nc in _get_neighbors(pos[0], pos[1], num_reels, board):
                    if (nr, nc) in component:
                        continue
                    if (nr, nc) in sym_positions and (nr, nc) not in visited:
                        component.add((nr, nc))
                        visited.add((nr, nc))
                        frontier.append((nr, nc))
                    elif (nr, nc) in wild_pool:
                        component.add((nr, nc))
                        wild_pool.discard((nr, nc))
                        frontier.append((nr, nc))

            sym_clusters.append(component)

        if sym_clusters:
            result[sym] = sym_clusters

    return result


class GameCalculations(Executables):
    """Two-pass cluster evaluation: L clusters fill gauge first, then H clusters use NEW multiplier.
    Wild symbols (WI) expand both L and H clusters, with a persist check between passes.
    """

    def evaluate_clusters_with_gauge(
        self,
        config: Config,
        board: Board,
        clusters: dict,
        gauge_fill_fn=None,
        get_h_mult_fn=None,
        return_data: dict = None,
    ):
        """Evaluate clusters in two passes with wild expansion.

        Pass 1: L clusters (expanded with adjacent wilds) -> base wins (x1), gauge fill
        Pass 2: H clusters (expanded with ALL wilds) -> wins with new multiplier
        Wilds only explode when part of a winning H cluster. Otherwise they persist.

        Returns:
            board, return_data, l_cluster_info, h_cluster_info, total_l_symbols, gauge_delta, wild_info
        """
        if return_data is None:
            return_data = {"totalWin": 0, "wins": []}

        wild_sym = getattr(config, 'wild_symbol', None)
        num_reels = len(board)

        # --- Locate all wild positions ---
        wild_positions = set()
        if wild_sym:
            for r in range(num_reels):
                for c in range(len(board[r])):
                    if board[r][c].defn.name == wild_sym:
                        wild_positions.add((r, c))

        total_win = 0
        l_cluster_info = []
        h_cluster_info = []
        total_l_symbols = 0
        all_explode = set()

        # --- Pass 1: L clusters expanded with wilds ---
        wild_pool_l = set(wild_positions)
        l_expanded = _find_clusters_with_wilds(board, config.l_symbols, wild_pool_l, num_reels)
        wilds_in_l = wild_positions - wild_pool_l

        for sym, sym_clusters in l_expanded.items():
            for component in sym_clusters:
                size = len(component)
                if (size, sym) not in config.paytable:
                    continue

                sym_win = config.paytable[(size, sym)]
                total_win += sym_win
                total_l_symbols += size

                json_positions = [{"reel": p[0], "row": p[1]} for p in sorted(component)]
                central_pos = Cluster.get_central_cluster_position(json_positions)

                return_data["wins"].append({
                    "symbol": sym,
                    "clusterSize": size,
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
                })
                l_cluster_info.append({
                    "symbol": sym,
                    "positions": json_positions,
                    "clusterSize": size,
                })
                # Only explode non-wild positions — wilds survive L cluster explosions
                all_explode.update(pos for pos in component if pos not in wild_positions)

        # --- Fill gauge from L symbols (wilds in L clusters count toward fill) ---
        gauge_delta = 0.0
        if gauge_fill_fn and total_l_symbols > 0:
            gauge_delta = gauge_fill_fn(total_l_symbols)

        # --- Get NEW H multiplier (after gauge fill) ---
        h_mult = get_h_mult_fn() if get_h_mult_fn else 1

        # --- Pass 2: H clusters expanded with ALL wilds ---
        # All wilds persist — they're available for H pass regardless of L participation
        wild_pool_h = set(wild_positions)
        h_expanded = _find_clusters_with_wilds(board, config.h_symbols, wild_pool_h, num_reels)
        wilds_in_h = wild_positions - wild_pool_h

        for sym, sym_clusters in h_expanded.items():
            for component in sym_clusters:
                size = len(component)
                if (size, sym) not in config.paytable:
                    continue

                sym_win = config.paytable[(size, sym)]
                win_with_mult = sym_win * h_mult
                total_win += win_with_mult

                json_positions = [{"reel": p[0], "row": p[1]} for p in sorted(component)]
                central_pos = Cluster.get_central_cluster_position(json_positions)

                return_data["wins"].append({
                    "symbol": sym,
                    "clusterSize": size,
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
                })
                h_cluster_info.append({
                    "symbol": sym,
                    "positions": json_positions,
                    "clusterSize": size,
                    "gaugeMultiplier": h_mult,
                })
                # Wilds in H clusters DO explode — they've served their purpose
                all_explode.update(component)

        # --- Mark ALL positions as explode atomically ---
        # Wilds NOT in any H cluster stay on the board for the next cascade
        for pos in all_explode:
            board[pos[0]][pos[1]].explode = True

        return_data["totalWin"] += total_win

        wild_info = {
            "total_on_board": len(wild_positions),
            "joined_l": len(wilds_in_l),
            "persisted": len(wild_positions),  # all wilds persist now
            "cleared": 0,  # wilds never clear with vials
            "joined_h": len(wilds_in_h),
        }

        return board, return_data, l_cluster_info, h_cluster_info, total_l_symbols, gauge_delta, wild_info
