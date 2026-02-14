"""Blood Tithe — core simulation logic with Blood Gauge and Blood Moon retrigger."""

from game_override import GameStateOverride


class GameState(GameStateOverride):
    """Main game loop: base spins with gauge reset, bonus with persistent gauge."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            # reset_book() calls reset_gauge() — gauge starts fresh each base spin
            self.reset_book()
            self._spin_had_h_win = False
            self._spin_wild_info = {"total_on_board": 0, "joined_l": 0, "persisted": 0, "cleared": 0, "joined_h": 0}
            self.draw_board()

            # PT (Chalice): absorb L symbols, fill gauge, tumble — works in both modes
            self.process_retrigger_tokens()

            cascade_depth = 0
            self.get_clusters_update_wins()
            self._accumulate_tumble_wild_info()
            self.emit_tumble_win_events()
            self.emit_pending_gauge_update()
            if self.win_data["totalWin"] > 0:
                cascade_depth = 1

            while self.win_data["totalWin"] > 0 and not self.wincap_triggered and cascade_depth < self.config.max_cascade_depth:
                self.tumble_game_board()
                # Process any PT that tumbled in (chalice activates on landing)
                self.process_retrigger_tokens()
                self.get_clusters_update_wins()
                self._accumulate_tumble_wild_info()
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

        # Wild + broken promise diagnostics
        if hasattr(self, "wild_total_seen"):
            self._track_wild_and_conversion()

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
            self._accumulate_tumble_wild_info()
            self.emit_tumble_win_events()
            self.emit_pending_gauge_update()
            if self.win_data["totalWin"] > 0:
                fs_cascade_depth = 1

            while self.win_data["totalWin"] > 0 and not self.wincap_triggered and fs_cascade_depth < self.config.max_cascade_depth:
                self.tumble_game_board()
                # Process any PT that tumbled in (chalice activates on landing)
                self.process_retrigger_tokens()
                self.get_clusters_update_wins()
                self._accumulate_tumble_wild_info()
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
        # Wild diagnostics
        self.wild_total_seen = 0
        self.wild_joined_l = 0
        self.wild_persisted = 0
        self.wild_cleared = 0
        self.wild_joined_h = 0
        # Broken promise tracking: gauge >= x2 but no H cluster pays
        self.broken_promise_count = 0
        self.empowered_h_count = 0
        self.hitting_spin_count = 0

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

        # Blood Moon Rate (bonus only)
        if self.bonus_count > 0:
            bm_pct = self.blood_moon_count / self.bonus_count * 100
            print(f"\n  Blood Moon Rate ({betmode}): {self.blood_moon_count}/{self.bonus_count} ({bm_pct:.1f}%)")

        # Wild Diagnostics
        if self.wild_total_seen > 0:
            print(f"\n  Wild Diagnostics ({betmode}):")
            print(f"    Total wilds seen  : {self.wild_total_seen}")
            print(f"    Joined L clusters : {self.wild_joined_l} ({self.wild_joined_l / max(self.wild_total_seen, 1) * 100:.1f}%)")
            print(f"    Persisted for H   : {self.wild_persisted} ({self.wild_persisted / max(self.wild_joined_l, 1) * 100:.1f}% of L-joined)")
            print(f"    Cleared with vials: {self.wild_cleared}")
            print(f"    Joined H clusters : {self.wild_joined_h}")

        # Broken Promise Rate
        if self.hitting_spin_count > 0:
            total_empowered_eligible = self.empowered_h_count + self.broken_promise_count
            if total_empowered_eligible > 0:
                bp_pct = self.broken_promise_count / total_empowered_eligible * 100
                emp_pct = self.empowered_h_count / total_empowered_eligible * 100
                print(f"\n  Conversion ({betmode}):")
                print(f"    Hitting spins     : {self.hitting_spin_count}")
                print(f"    Gauge>=x2 + H win : {self.empowered_h_count} ({emp_pct:.1f}%) — empowered H")
                print(f"    Gauge>=x2, no H   : {self.broken_promise_count} ({bp_pct:.1f}%) — broken promise")

    def _accumulate_tumble_wild_info(self):
        """Called after each get_clusters_update_wins to accumulate wild info across cascade chain."""
        wi = getattr(self, '_last_wild_info', None)
        if wi:
            for key in self._spin_wild_info:
                self._spin_wild_info[key] += wi.get(key, 0)
        # Track if any H win happened in this tumble
        if self.win_data and self.win_data.get("wins"):
            if any(w["meta"].get("symbolType") == "H" for w in self.win_data["wins"]):
                self._spin_had_h_win = True

    def _track_wild_and_conversion(self):
        """Track wild usage and broken promise rate per spin (end of spin)."""
        wi = self._spin_wild_info
        self.wild_total_seen += wi["total_on_board"]
        self.wild_joined_l += wi["joined_l"]
        self.wild_persisted += wi["persisted"]
        self.wild_cleared += wi["cleared"]
        self.wild_joined_h += wi["joined_h"]

        # Broken promise: spin has a win AND gauge >= x2 but no H cluster in entire cascade chain
        if self.final_win > 0:
            self.hitting_spin_count += 1
            gauge_seg = self._gauge_to_segment(self.gauge_level)
            gauge_mult = self.config.gauge_segments[gauge_seg]["multiplier"]
            if gauge_mult >= 2:
                if self._spin_had_h_win:
                    self.empowered_h_count += 1
                else:
                    self.broken_promise_count += 1

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
