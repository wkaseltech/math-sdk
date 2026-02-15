"""Vampire Slots — core simulation logic with Blood Gauge and Blood Moon retrigger."""

from game_override import GameStateOverride


class GameState(GameStateOverride):
    """Main game loop: base spins with gauge reset, bonus with persistent gauge."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            # reset_book() calls reset_gauge() — gauge starts fresh each base spin
            self.reset_book()
            self.draw_board()

            # PT (Chalice): absorb L symbols, fill gauge, tumble — works in both modes
            self.process_retrigger_tokens()

            cascade_depth = 0
            self.get_clusters_update_wins()
            self.emit_tumble_win_events()
            self.emit_pending_gauge_update()
            if self.win_data["totalWin"] > 0:
                cascade_depth = 1

            while self.win_data["totalWin"] > 0 and not self.wincap_triggered and cascade_depth < self.config.max_cascade_depth:
                self.tumble_game_board()
                # Process any PT that tumbled in (chalice activates on landing)
                self.process_retrigger_tokens()
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

        if hasattr(self, "blood_moon_count") and hasattr(self, "_bonus_triggered"):
            if self._bonus_triggered:
                self.bonus_count += 1
                if self._blood_moon_triggered:
                    self.blood_moon_count += 1

        # Track conversion: gauge fill → empowered vampire
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
        # Gauge persists across all free spins — reset_fs_spin() does NOT call reset_gauge()
        # But we DO want the gauge to start at 0 for the bonus (it was reset in reset_book)
        self._bonus_triggered = True
        self._blood_moon_triggered = False

        while self.fs < self.tot_fs:
            self.update_freespin()
            self.draw_board()

            # Collect PT tokens BEFORE cluster detection
            self.process_retrigger_tokens()

            fs_cascade_depth = 0
            self.get_clusters_update_wins()
            self.emit_tumble_win_events()
            self.emit_pending_gauge_update()
            if self.win_data["totalWin"] > 0:
                fs_cascade_depth = 1

            while self.win_data["totalWin"] > 0 and not self.wincap_triggered and fs_cascade_depth < self.config.max_cascade_depth:
                self.tumble_game_board()
                # Process any PT that tumbled in (chalice activates on landing)
                self.process_retrigger_tokens()
                self.get_clusters_update_wins()
                self.emit_tumble_win_events()
                self.emit_pending_gauge_update()
                if self.win_data["totalWin"] > 0:
                    fs_cascade_depth += 1

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            # Track Blood Moon triggers
            if self.blood_moon_active and not self._blood_moon_triggered:
                self._blood_moon_triggered = True

        self.end_freespin()

    def run_sims(self, betmode_copy_list, betmode, *args, **kwargs):
        """Override to track and print diagnostics after sims."""
        self.gauge_level_counts = {}
        self.cascade_depth_counts = {}
        self.zone_counts = {}
        self.blood_moon_count = 0
        self.bonus_count = 0
        self._bonus_triggered = False
        self._blood_moon_triggered = False
        self.empowered_h_hits = 0     # H clusters at gauge x2+
        self.unpowered_h_hits = 0     # H clusters at gauge x1
        self.gauge_fill_no_h = 0      # Spins where gauge > x1 but no H cluster
        self.total_h_clusters = 0     # All H clusters

        super().run_sims(betmode_copy_list, betmode, *args, **kwargs)

        # Gauge Segment Distribution (bonus mode shows how high gauge gets)
        total_gauge = sum(self.gauge_level_counts.values())
        if total_gauge > 0:
            seg_names = {1: "Empty (x1)", 2: "Warming (x2)", 3: "Rising (x3)",
                         4: "Surging (x5)", 5: "Overflowing (x10)"}
            print(f"\n  Gauge Segment Distribution ({betmode}):")
            for seg in sorted(self.gauge_level_counts):
                count = self.gauge_level_counts[seg]
                pct = count / total_gauge * 100
                print(f"    Segment {seg} {seg_names.get(seg, ''):>20}: {count:>6} ({pct:.1f}%)")

        # Cascade Depth Distribution
        total_cascade = sum(self.cascade_depth_counts.values())
        if total_cascade > 0:
            print(f"\n  Cascade Depth ({betmode}):")
            max_depth = max(self.cascade_depth_counts.keys())
            for depth in range(0, max_depth + 1):
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
            print(f"\n  Vampire Conversion ({betmode}):")
            print(f"    Total H clusters     : {self.total_h_clusters}")
            print(f"    Empowered (gauge x2+): {self.empowered_h_hits} ({emp_pct:.1f}%)")
            print(f"    Unpowered (gauge x1) : {self.unpowered_h_hits} ({unp_pct:.1f}%)")
            print(f"    Gauge filled, no vamp : {self.gauge_fill_no_h} spins (broken promise)")

        # Blood Moon Rate (bonus only)
        if self.bonus_count > 0:
            bm_pct = self.blood_moon_count / self.bonus_count * 100
            print(f"\n  Blood Moon Rate ({betmode}): {self.blood_moon_count}/{self.bonus_count} ({bm_pct:.1f}%)")

    def _gauge_to_segment(self, gauge_level):
        """Map gauge level to segment number."""
        for seg_id, seg in self.config.gauge_segments.items():
            low, high = seg["range"]
            if low <= gauge_level < high:
                return seg_id
        return 5

    def _track_zone(self, win):
        """Track win zone for diagnostics."""
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
