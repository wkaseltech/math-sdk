from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    """Override/extend universal state.py for Dungeon Quest."""

    def reset_book(self):
        super().reset_book()
        self.tumble_win = 0
        # Basegame: reset XP at start of every new spin
        self.reset_xp()

    def reset_fs_spin(self):
        super().reset_fs_spin()
        # Freegame: do NOT reset XP between free spins (XP persists)

    def check_fs_condition(self, scatter_key: str = "scatter") -> bool:
        """Override: return False if no freespin triggers defined for current gametype."""
        triggers = self.config.freespin_triggers.get(self.gametype, {})
        if not triggers:
            return False
        return super().check_fs_condition(scatter_key)

    def update_freespin_amount(self, scatter_key: str = "scatter") -> None:
        """Override: clamp scatter count to max defined trigger key."""
        from src.events.events import fs_trigger_event
        scatter_count = self.count_special_symbols(scatter_key)
        triggers = self.config.freespin_triggers[self.gametype]
        # Clamp to highest defined trigger if scatter count exceeds it
        if scatter_count not in triggers:
            scatter_count = max(k for k in triggers.keys() if k <= scatter_count)
        self.tot_fs = triggers[scatter_count]
        if self.gametype == self.config.basegame_type:
            fs_trigger_event(self, basegame_trigger=True, freegame_trigger=False)
        else:
            fs_trigger_event(self, basegame_trigger=False, freegame_trigger=True)

    def assign_special_sym_function(self):
        pass

    def check_repeat(self) -> None:
        """Checks if the spin failed a criteria constraint at any point."""
        if self.repeat is False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True

            if self.get_current_distribution_conditions()["force_freegame"] and not (self.triggered_freegame):
                self.repeat = True

            if self.win_manager.running_bet_win == 0 and self.criteria != "0":
                self.repeat = True
