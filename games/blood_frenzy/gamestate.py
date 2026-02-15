"""Blood Frenzy — core simulation logic with gauge gating and Blood Frenzy retrigger."""

from game_override import GameStateOverride


class GameState(GameStateOverride):
    """Main game loop: base spins with gauge reset, bonus with persistent gauge."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board()

            cascade_depth = 0
            self.get_clusters_update_wins()
            self.emit_tumble_win_events()
            self.emit_pending_gauge_update()
            if self.win_data["totalWin"] > 0:
                cascade_depth = 1

            while self.win_data["totalWin"] > 0 and not self.wincap_triggered and cascade_depth < self.config.max_cascade_depth:
                self.tumble_game_board()
                self.get_clusters_update_wins()
                self.emit_tumble_win_events()
                self.emit_pending_gauge_update()
                if self.win_data["totalWin"] > 0:
                    cascade_depth += 1

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition() and self.check_freespin_entry():
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()

        # Track diagnostics
        if hasattr(self, "gauge_level_counts"):
            seg = self._gauge_to_segment(self.gauge_level)
            self.gauge_level_counts[seg] = self.gauge_level_counts.get(seg, 0) + 1

        if hasattr(self, "cascade_depth_counts"):
            self.cascade_depth_counts[cascade_depth] = self.cascade_depth_counts.get(cascade_depth, 0) + 1

        if hasattr(self, "zone_counts"):
            self._track_zone(self.final_win)

        if hasattr(self, "bonus_count") and hasattr(self, "_bonus_triggered"):
            if self._bonus_triggered:
                self.bonus_count += 1
                if self._frenzy_triggered:
                    self.frenzy_count += 1

        # Track conversion
        if hasattr(self, "_spin_h_clusters") and hasattr(self, "_spin_max_gauge_seg"):
            if self._spin_max_gauge_seg >= 2 and self._spin_h_clusters > 0:
                self.empowered_h_hits += self._spin_empowered_h
            if self._spin_max_gauge_seg >= 2 and self._spin_h_clusters == 0:
                self.gauge_fill_no_h += 1
            if self._spin_h_clusters > 0 and self._spin_max_gauge_seg < 2:
                self.unpowered_h_hits += self._spin_h_at_x1
            self.total_h_clusters += self._spin_h_clusters

        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
        self._bonus_triggered = True
        self._frenzy_triggered = False

        while self.fs < self.tot_fs:
            self.update_freespin()
            self.draw_board()

            fs_cascade_depth = 0
            self.get_clusters_update_wins()
            self.emit_tumble_win_events()
            self.emit_pending_gauge_update()
            if self.win_data["totalWin"] > 0:
                fs_cascade_depth = 1

            while self.win_data["totalWin"] > 0 and not self.wincap_triggered and fs_cascade_depth < self.config.max_cascade_depth:
                self.tumble_game_board()
                self.get_clusters_update_wins()
                self.emit_tumble_win_events()
                self.emit_pending_gauge_update()
                if self.win_data["totalWin"] > 0:
                    fs_cascade_depth += 1

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.frenzy_active and not self._frenzy_triggered:
                self._frenzy_triggered = True

        self.end_freespin()

    def run_sims(self, betmode_copy_list, betmode, *args, **kwargs):
        """Override to track and print diagnostics after sims."""
        self.gauge_level_counts = {}
        self.cascade_depth_counts = {}
        self.zone_counts = {}
        self.gating_counts = {}
        self.frenzy_count = 0
        self.bonus_count = 0
        self._bonus_triggered = False
        self._frenzy_triggered = False
        self.empowered_h_hits = 0
        self.unpowered_h_hits = 0
        self.gauge_fill_no_h = 0
        self.total_h_clusters = 0

        super().run_sims(betmode_copy_list, betmode, *args, **kwargs)

        total_spins = sum(self.gauge_level_counts.values()) if self.gauge_level_counts else 0

        # Gauge Segment Distribution
        if total_spins > 0:
            seg_names = {1: "Empty (x1)", 2: "Warming (x2)", 3: "Rising (x3)",
                         4: "Surging (x5)", 5: "Overflowing (x10)"}
            print(f"\n  Gauge Segment Distribution ({betmode}):")
            for seg in sorted(self.gauge_level_counts):
                count = self.gauge_level_counts[seg]
                pct = count / total_spins * 100
                print(f"    Segment {seg} {seg_names.get(seg, ''):>20}: {count:>6} ({pct:.1f}%)")

        # Gating Stats
        if self.gating_counts and total_spins > 0:
            print(f"\n  H Symbol Gating ({betmode}):")
            for sym in ["H1", "H2", "H3", "H4"]:
                active_key = f"active_{sym}"
                unlock_key = f"unlock_{sym}"
                active_count = self.gating_counts.get(active_key, 0)
                unlock_count = self.gating_counts.get(unlock_key, 0)
                # active_count is per-tumble, not per-spin, but gives relative picture
                threshold = self.config.h_unlock_thresholds[sym]
                seg_name = seg_names.get(threshold, "?")
                print(f"    {sym} (unlock @ seg {threshold} {seg_name}): active {active_count} tumbles, unlocked {unlock_count} times")

        # Cascade Depth Distribution
        total_cascade = sum(self.cascade_depth_counts.values())
        if total_cascade > 0:
            print(f"\n  Cascade Depth ({betmode}):")
            max_depth = max(self.cascade_depth_counts.keys())
            for depth in range(0, min(max_depth + 1, 12)):
                count = self.cascade_depth_counts.get(depth, 0)
                pct = count / total_cascade * 100
                label = "No win" if depth == 0 else f"{depth} tumble{'s' if depth > 1 else ' '}"
                print(f"    {label:<12}: {count:>6} ({pct:.1f}%)")
            avg_depth = sum(d * c for d, c in self.cascade_depth_counts.items()) / total_cascade
            print(f"    Avg depth  : {avg_depth:.2f}")

        # Win Zone Distribution
        total_zone = sum(self.zone_counts.values())
        if total_zone > 0:
            zone_order = ["dead", "tiny (<0.5x)", "small (0.5-2x)", "low (2-5x)",
                          "mid (5-20x)", "good (20-50x)", "great (50-200x)",
                          "mega (200-500x)", "epic (500x+)"]
            print(f"\n  Win Zone Distribution ({betmode}):")
            for zone in zone_order:
                count = self.zone_counts.get(zone, 0)
                if count > 0:
                    pct = count / total_zone * 100
                    print(f"    {zone:<18}: {count:>6} ({pct:.1f}%)")

        # Conversion Stats
        if self.total_h_clusters > 0:
            emp_pct = self.empowered_h_hits / self.total_h_clusters * 100
            unp_pct = self.unpowered_h_hits / self.total_h_clusters * 100
            print(f"\n  Hunter Conversion ({betmode}):")
            print(f"    Total H clusters     : {self.total_h_clusters}")
            print(f"    Empowered (gauge x2+): {self.empowered_h_hits} ({emp_pct:.1f}%)")
            print(f"    Unpowered (gauge x1) : {self.unpowered_h_hits} ({unp_pct:.1f}%)")
            print(f"    Gauge filled, no hunt: {self.gauge_fill_no_h} spins (broken promise)")

        # Frenzy Rate
        if self.bonus_count > 0:
            fr_pct = self.frenzy_count / self.bonus_count * 100
            print(f"\n  Blood Frenzy Rate ({betmode}): {self.frenzy_count}/{self.bonus_count} ({fr_pct:.1f}%)")

    def _gauge_to_segment(self, gauge_level):
        for seg_id, seg in self.config.gauge_segments.items():
            low, high = seg["range"]
            if low <= gauge_level < high:
                return seg_id
        return 5

    def _track_zone(self, win):
        if win == 0:
            zone = "dead"
        elif win < 0.5:
            zone = "tiny (<0.5x)"
        elif win < 2:
            zone = "small (0.5-2x)"
        elif win < 5:
            zone = "low (2-5x)"
        elif win < 20:
            zone = "mid (5-20x)"
        elif win < 50:
            zone = "good (20-50x)"
        elif win < 200:
            zone = "great (50-200x)"
        elif win < 500:
            zone = "mega (200-500x)"
        else:
            zone = "epic (500x+)"
        self.zone_counts[zone] = self.zone_counts.get(zone, 0) + 1
