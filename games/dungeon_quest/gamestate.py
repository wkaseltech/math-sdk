from game_override import GameStateOverride
from game_events import emit_music_change


class GameState(GameStateOverride):
    """Dungeon Quest — core simulation logic with potion retrigger."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            # reset_book() calls reset_xp() — XP starts fresh each base spin
            self.reset_book()
            self.draw_board()

            cascade_depth = 0
            self.get_clusters_update_wins()
            self.emit_tumble_win_events()
            if self.win_data["totalWin"] > 0:
                cascade_depth = 1

            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.get_clusters_update_wins()
                self.emit_tumble_win_events()
                if self.win_data["totalWin"] > 0:
                    cascade_depth += 1

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition() and self.check_freespin_entry():
                # Entering bonus — emit music change
                emit_music_change(self, "bonus_game_loop", "bonus_enter")
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()

        # Track diagnostics
        if hasattr(self, 'xp_level_counts'):
            lvl = min(self.xp_level, self.config.max_level)
            self.xp_level_counts[lvl] = self.xp_level_counts.get(lvl, 0) + 1

        if hasattr(self, 'cascade_depth_counts'):
            self.cascade_depth_counts[cascade_depth] = self.cascade_depth_counts.get(cascade_depth, 0) + 1

        if hasattr(self, 'zone_counts'):
            win = self.final_win
            if win == 0:
                zone = "dead"
            elif win < 1:
                zone = "tiny (<1x)"
            elif win < 5:
                zone = "small (1-5x)"
            elif win < 20:
                zone = "medium (5-20x)"
            elif win < 100:
                zone = "big (20-100x)"
            elif win < 500:
                zone = "mega (100-500x)"
            else:
                zone = "epic (500x+)"
            self.zone_counts[zone] = self.zone_counts.get(zone, 0) + 1

        self.imprint_wins()

    def run_sims(self, betmode_copy_list, betmode, *args, **kwargs):
        """Override to track and print diagnostics after sims."""
        self.xp_level_counts = {i: 0 for i in range(1, self.config.max_level + 1)}
        self.cascade_depth_counts = {}
        self.zone_counts = {}
        super().run_sims(betmode_copy_list, betmode, *args, **kwargs)

        # XP Level Distribution
        total_xp = sum(self.xp_level_counts.values())
        if total_xp > 0:
            print(f"\n  XP Level Distribution ({betmode}):")
            for lvl in sorted(self.xp_level_counts):
                label = "MAX" if lvl == self.config.max_level else str(lvl)
                pct = self.xp_level_counts[lvl] / total_xp * 100
                print(f"    Level {label:>3}: {self.xp_level_counts[lvl]:>6} ({pct:.1f}%)")

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

        # Zone Distribution
        total_zone = sum(self.zone_counts.values())
        if total_zone > 0:
            zone_order = ["dead", "tiny (<1x)", "small (1-5x)", "medium (5-20x)",
                          "big (20-100x)", "mega (100-500x)", "epic (500x+)"]
            print(f"\n  Win Zone Distribution ({betmode}):")
            for zone in zone_order:
                count = self.zone_counts.get(zone, 0)
                if count > 0:
                    pct = count / total_zone * 100
                    print(f"    {zone:<18}: {count:>6} ({pct:.1f}%)")

    def run_freespin(self):
        self.reset_fs_spin()
        # XP persists across all free spins — reset_fs_spin() does NOT call reset_xp()
        while self.fs < self.tot_fs:
            self.update_freespin()
            self.draw_board()

            # POTION MECHANIC: collect potions BEFORE cluster detection.
            # Each PT on the board adds 1 extra free spin to tot_fs.
            # Potions are replaced with random regular symbols, then clusters evaluated.
            self.process_potions()

            self.get_clusters_update_wins()
            self.emit_tumble_win_events()

            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.get_clusters_update_wins()
                self.emit_tumble_win_events()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            # Native retrigger check removed — potions handle all retrigger logic
            # via process_potions() above. check_fs_condition() returns False for
            # freegame anyway (freespin_triggers[freegame_type] is empty).

        # Exiting bonus — emit music change back to base
        emit_music_change(self, "base_game_loop", "bonus_exit")
        self.end_freespin()
