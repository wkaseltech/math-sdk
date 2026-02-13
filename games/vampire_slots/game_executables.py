"""Vampire Slots game logic — Blood Gauge fill, H multiplier, Blood Moon retrigger."""

import random

from game_calculations import GameCalculations
from src.calculations.cluster import Cluster
from game_events import (
    get_gauge_multiplier,
    emit_gauge_update,
    emit_cluster_info,
    emit_blood_moon,
    emit_blood_moon_end,
    emit_chalice_absorb,
)
from src.events.events import update_freespin_event, json_ready_sym


class GameExecutables(GameCalculations):
    """Blood Gauge tracking and cluster evaluation with L-first evaluation."""

    def reset_gauge(self):
        """Reset gauge state to defaults."""
        self.gauge_level = 0.0
        self.blood_moon_active = False
        self.blood_moon_spins_remaining = 0
        self.blood_moon_cascade_count = 0
        self._pending_gauge_delta = 0.0

    def fill_gauge(self, l_symbol_count):
        """Add blood to gauge from L cluster wins. Returns delta amount.
        Uses base rate (4%) in base game, bonus rate (1.1%) in free game.
        """
        if self.blood_moon_active:
            return 0.0
        if self.gametype == self.config.freegame_type:
            rate = self.config.gauge_fill_per_l_symbol_bonus
        else:
            rate = self.config.gauge_fill_per_l_symbol_base
        delta = l_symbol_count * rate
        old_level = self.gauge_level
        self.gauge_level = min(100.0, self.gauge_level + delta)
        actual_delta = self.gauge_level - old_level
        return actual_delta

    def check_blood_moon(self):
        """Check if gauge hit 100% during bonus — trigger Blood Moon retrigger."""
        if self.gametype != self.config.freegame_type:
            return False
        if self.blood_moon_active:
            return False
        if self.gauge_level >= 100.0:
            self.blood_moon_active = True
            self.blood_moon_spins_remaining = self.config.blood_moon_locked_spins
            self.tot_fs += self.config.blood_moon_extra_spins
            emit_blood_moon(self)
            return True
        return False

    def update_blood_moon(self):
        """Tick down Blood Moon lock. Called once per free spin."""
        if not self.blood_moon_active:
            return
        self.blood_moon_spins_remaining -= 1
        if self.blood_moon_spins_remaining <= 0:
            self.blood_moon_active = False
            self.gauge_level = self.config.blood_moon_unlock_gauge
            emit_blood_moon_end(self)

    def process_retrigger_tokens(self):
        """PT (Chalice) absorbs ALL L symbols on the board, then disappears.

        When PT is present:
        - Count every L1-L4 symbol on the board (clustered or not)
        - Fill gauge with that total count * fill rate
        - Mark all L symbols + PT for explosion (they disappear)
        - Emit chaliceAbsorb event for frontend animation
        - Tumble the board (symbols fall down, new ones from reel strip)

        Works in both base game and free game.
        Returns the number of PT collected (0 = no PT on board).
        """
        pt_count = self.count_special_symbols("retrigger")
        if pt_count == 0:
            return 0

        pt_positions = list(self.special_syms_on_board["retrigger"])

        # Scan entire board for L symbols
        l_positions = []
        for reel_idx in range(len(self.board)):
            for row_idx in range(len(self.board[reel_idx])):
                sym = self.board[reel_idx][row_idx]
                if sym.defn.name in self.config.l_symbols:
                    l_positions.append({"reel": reel_idx, "row": row_idx})

        l_count = len(l_positions)

        # Fill gauge from absorbed L symbols (separate PT rate for base vs bonus)
        if l_count > 0 and not self.blood_moon_active:
            pt_rate = (self.config.gauge_fill_per_pt_absorb_bonus
                       if self.gametype == self.config.freegame_type
                       else self.config.gauge_fill_per_pt_absorb_base)
            delta = l_count * pt_rate
            old_level = self.gauge_level
            self.gauge_level = min(100.0, self.gauge_level + delta)
            gauge_delta = self.gauge_level - old_level
        else:
            gauge_delta = 0.0

        # Emit chalice absorb event BEFORE tumble (frontend: orbs fly to gauge)
        if l_count > 0:
            emit_chalice_absorb(self, pt_positions, l_positions, l_count, gauge_delta)

        # Mark all L symbols + PT for explosion (they disappear off the board)
        for pos in l_positions:
            self.board[pos["reel"]][pos["row"]].explode = True

        for pos in pt_positions:
            self.board[pos["reel"]][pos["row"]].explode = True

        # Tumble: remove exploded symbols, drop remaining, fill from reel strip
        self.tumble_board()
        self._emit_chalice_tumble_event(l_positions, pt_positions)

        # Rebuild special symbol index after board modification
        self.get_special_symbols_on_board()

        # Check Blood Moon after gauge fill
        self.check_blood_moon()

        return pt_count

    def _emit_chalice_tumble_event(self, l_positions, pt_positions):
        """Emit a tumbleBoard event for the chalice absorption removal.

        Uses the same format as the SDK tumble_board_event but with
        PT + L positions as the exploding symbols (no win_data dependency).
        Both l_positions and pt_positions are lists of {"reel": r, "row": row} dicts.
        """
        exploding = []
        for pos in l_positions + pt_positions:
            row = pos["row"] + 1 if self.config.include_padding else pos["row"]
            exploding.append({"reel": pos["reel"], "row": row})

        exploding = sorted(exploding, key=lambda x: x["reel"])

        new_symbols_list = [[] for _ in range(self.config.num_reels)]
        special_attributes = list(self.config.special_symbols.keys())
        for r, syms in enumerate(self.new_symbols_from_tumble):
            if len(syms) > 0:
                new_symbols_list[r] = [json_ready_sym(s, special_attributes) for s in syms]

        event = {
            "index": len(self.book.events),
            "type": "tumbleBoard",
            "newSymbols": new_symbols_list,
            "explodingSymbols": exploding,
        }
        self.book.add_event(event)

    def get_current_h_multiplier(self):
        """Get the effective H multiplier, including Blood Moon escalation."""
        base_mult = get_gauge_multiplier(self.gauge_level, self.config)
        if self.blood_moon_active:
            escalation = self.blood_moon_cascade_count * self.config.blood_moon_escalation_per_cascade
            return self.config.blood_moon_base_multiplier + escalation
        return base_mult

    def get_clusters_update_wins(self):
        """Find clusters, L-first evaluation: L fills gauge, H uses NEW multiplier."""
        clusters = Cluster.get_clusters(self.board)
        return_data = {"totalWin": 0, "wins": []}

        # Two-pass evaluation: L first → gauge fill → H with new mult
        self.board, self.win_data, l_clusters, h_clusters, l_sym_count, gauge_delta = (
            self.evaluate_clusters_with_gauge(
                config=self.config,
                board=self.board,
                clusters=clusters,
                gauge_fill_fn=self.fill_gauge,
                get_h_mult_fn=self.get_current_h_multiplier,
                return_data=return_data,
            )
        )

        # Store gauge delta for deferred emission (after winInfo + updateTumbleWin)
        self._pending_gauge_delta = gauge_delta

        # Emit cluster info for frontend animation sequencing
        if l_clusters or h_clusters:
            emit_cluster_info(self, l_clusters, h_clusters)

        # Track Blood Moon cascades for escalation
        if self.blood_moon_active and self.win_data["totalWin"] > 0:
            self.blood_moon_cascade_count += 1

        # Record cluster wins for force conditions
        Cluster.record_cluster_wins(self)

        # Update win manager
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        self.win_manager.tumble_win = self.win_data["totalWin"]

        # Check Blood Moon after gauge fill (needs current gauge state)
        self.check_blood_moon()

    def emit_pending_gauge_update(self):
        """Emit the deferred gaugeUpdate event (called AFTER winInfo + updateTumbleWin)."""
        if self._pending_gauge_delta > 0:
            emit_gauge_update(self, self._pending_gauge_delta)
            self._pending_gauge_delta = 0.0

    def update_freespin(self) -> None:
        """Called before a new reveal during freegame. Gauge persists."""
        self.fs += 1
        update_freespin_event(self)
        self.win_manager.reset_spin_win()
        self.win_data = {}
        # Tick Blood Moon lock
        self.update_blood_moon()
