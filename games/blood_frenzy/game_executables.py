"""Blood Frenzy game logic — gauge fill, H gating, Blood Frenzy retrigger."""

from game_calculations import GameCalculations
from src.calculations.cluster import Cluster
from game_events import (
    get_gauge_multiplier,
    get_active_h_symbols,
    emit_gauge_update,
    emit_symbol_unlock,
    emit_cluster_info,
    emit_blood_frenzy,
    emit_blood_frenzy_end,
)
from src.events.events import update_freespin_event


class GameExecutables(GameCalculations):
    """Gauge tracking, H gating, and cluster evaluation."""

    def reset_gauge(self):
        """Reset gauge state to defaults."""
        self.gauge_level = 0.0
        self.frenzy_active = False
        self.frenzy_spins_remaining = 0
        self.frenzy_cascade_count = 0
        self._pending_gauge_delta = 0.0
        self._pending_newly_unlocked = set()
        self._pre_fill_active_h = set()

    def fill_gauge(self, l_symbol_count):
        """Add to gauge from L cluster wins. Returns delta amount."""
        if self.frenzy_active:
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

    def get_active_h(self):
        """Return set of H symbols currently unlocked by gauge level."""
        if self.frenzy_active:
            return set(self.config.h_symbols)  # All H active during frenzy
        return get_active_h_symbols(self.gauge_level, self.config)

    def check_blood_frenzy(self):
        """Check if gauge hit 100% during bonus — trigger Blood Frenzy."""
        if self.gametype != self.config.freegame_type:
            return False
        if self.frenzy_active:
            return False
        if self.gauge_level >= 100.0:
            self.frenzy_active = True
            self.frenzy_spins_remaining = self.config.blood_frenzy_locked_spins
            self.tot_fs += self.config.blood_frenzy_extra_spins
            emit_blood_frenzy(self)
            return True
        return False

    def update_blood_frenzy(self):
        """Tick down frenzy lock. Called once per free spin."""
        if not self.frenzy_active:
            return
        self.frenzy_spins_remaining -= 1
        if self.frenzy_spins_remaining <= 0:
            self.frenzy_active = False
            self.gauge_level = self.config.blood_frenzy_unlock_gauge
            emit_blood_frenzy_end(self)

    def get_current_h_multiplier(self):
        """Get effective H multiplier, including frenzy escalation."""
        base_mult = get_gauge_multiplier(self.gauge_level, self.config)
        if self.frenzy_active:
            escalation = self.frenzy_cascade_count * self.config.blood_frenzy_escalation_per_cascade
            return self.config.blood_frenzy_base_multiplier + escalation
        return base_mult

    def get_clusters_update_wins(self):
        """Find clusters with L-first evaluation and H gating."""
        # Snapshot active H BEFORE gauge fill (to detect new unlocks)
        self._pre_fill_active_h = self.get_active_h()

        return_data = {"totalWin": 0, "wins": []}

        # Two-pass evaluation: L first → gauge fill → active H with new mult
        self.board, self.win_data, l_clusters, h_clusters, l_sym_count, gauge_delta = (
            self.evaluate_clusters_with_gating(
                config=self.config,
                board=self.board,
                gauge_fill_fn=self.fill_gauge,
                get_h_mult_fn=self.get_current_h_multiplier,
                get_active_h_fn=self.get_active_h,
                return_data=return_data,
            )
        )

        # Detect newly unlocked H symbols
        post_fill_active_h = self.get_active_h()
        newly_unlocked = post_fill_active_h - self._pre_fill_active_h

        # Store for deferred emission
        self._pending_gauge_delta = gauge_delta
        self._pending_newly_unlocked = newly_unlocked

        # Emit cluster info
        if l_clusters or h_clusters:
            emit_cluster_info(self, l_clusters, h_clusters)

        # Emit symbol unlock event if new H symbols activated
        if newly_unlocked:
            emit_symbol_unlock(self, newly_unlocked)

        # Track diagnostics
        if hasattr(self, "_spin_h_clusters"):
            h_mult = self.get_current_h_multiplier()
            h_count = len(h_clusters)
            self._spin_h_clusters += h_count
            seg = self._gauge_to_segment(self.gauge_level) if hasattr(self, "_gauge_to_segment") else 1
            if seg > self._spin_max_gauge_seg:
                self._spin_max_gauge_seg = seg
            if h_count > 0:
                if h_mult > 1:
                    self._spin_empowered_h += h_count
                else:
                    self._spin_h_at_x1 += h_count

            # Track gating: which H symbols were active
            for sym in post_fill_active_h:
                key = f"active_{sym}"
                if hasattr(self, "gating_counts"):
                    self.gating_counts[key] = self.gating_counts.get(key, 0) + 1

            # Track unlock events
            for sym in newly_unlocked:
                key = f"unlock_{sym}"
                if hasattr(self, "gating_counts"):
                    self.gating_counts[key] = self.gating_counts.get(key, 0) + 1

        # Track frenzy cascades for escalation
        if self.frenzy_active and self.win_data["totalWin"] > 0:
            self.frenzy_cascade_count += 1

        # Record cluster wins for force conditions
        Cluster.record_cluster_wins(self)

        # Update win manager
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        self.win_manager.tumble_win = self.win_data["totalWin"]

        # Check Blood Frenzy after gauge fill
        self.check_blood_frenzy()

    def emit_pending_gauge_update(self):
        """Emit deferred gaugeUpdate event (called AFTER winInfo + updateTumbleWin)."""
        if self._pending_gauge_delta > 0:
            emit_gauge_update(self, self._pending_gauge_delta, self._pending_newly_unlocked)
            self._pending_gauge_delta = 0.0
            self._pending_newly_unlocked = set()

    def update_freespin(self) -> None:
        """Called before a new reveal during freegame. Gauge persists."""
        self.fs += 1
        update_freespin_event(self)
        self.win_manager.reset_spin_win()
        self.win_data = {}
        self.update_blood_frenzy()
