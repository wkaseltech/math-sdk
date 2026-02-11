from game_override import GameStateOverride
from game_events import emit_music_change


class GameState(GameStateOverride):
    """Dungeon Quest v6 — core simulation logic with potion retrigger."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            # reset_book() calls reset_xp() — XP starts fresh each base spin
            self.reset_book()
            self.draw_board()

            self.get_clusters_update_wins()
            self.emit_tumble_win_events()

            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.get_clusters_update_wins()
                self.emit_tumble_win_events()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition() and self.check_freespin_entry():
                # Entering bonus — emit music change
                emit_music_change(self, "bonus_game_loop", "bonus_enter")
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

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
