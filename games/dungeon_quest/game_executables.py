import random

from game_calculations import GameCalculations
from src.calculations.cluster import Cluster
from game_events import (
    calculate_level,
    emit_update_xp,
    emit_hero_state_change,
    emit_music_change,
    emit_potion_collected,
)
from src.events.events import update_freespin_event


class GameExecutables(GameCalculations):
    """Dungeon Quest game logic — XP multiplier system + potion retrigger."""

    def reset_xp(self):
        """Reset XP state to defaults."""
        self.xp_cluster_count = 0
        self.xp_level = 1
        self.xp_multiplier = 1

    def update_xp(self):
        """After a cluster win, increment cluster count and check for level up."""
        if self.win_data["totalWin"] > 0:
            num_clusters = len(self.win_data["wins"])
            self.xp_cluster_count += num_clusters

            new_level = calculate_level(self.xp_cluster_count, self.config)

            if new_level > self.xp_level:
                old_level = self.xp_level
                self.xp_level = new_level

                emit_hero_state_change(self, new_level)

                # Music crossfade at level 5
                if new_level == 5 and old_level < 5:
                    emit_music_change(self, "boss_room_loop", "level5")

            # Calculate multiplier — escalates at Level 5
            if self.xp_level < 5:
                self.xp_multiplier = self.config.xp_multiplier_tiers[self.xp_level]
            else:
                clusters_beyond = self.xp_cluster_count - self.config.xp_thresholds[5]
                self.xp_multiplier = self.config.level5_base_multiplier + (clusters_beyond * self.config.level5_escalation_per_cluster)

            emit_update_xp(self)

    def process_potions(self):
        """During free spins: count potions on board, add 1 free spin per potion, remove them.

        Called AFTER draw_board() and BEFORE get_clusters_update_wins().
        Potions (PT) only appear on FR0/WCAP reels (bonus only).
        Each individual potion adds exactly 1 extra free spin.
        Potions are replaced with random regular symbols so they don't affect clusters.

        Returns the number of potions collected (0 if not in freegame).
        """
        if self.gametype != self.config.freegame_type:
            return 0

        potion_count = self.count_special_symbols("potion")
        if potion_count == 0:
            return 0

        # Capture positions before modifying the board
        potion_positions = list(self.special_syms_on_board["potion"])

        # Add 1 free spin per potion to the total
        self.tot_fs += potion_count

        # Replace each potion with a random regular symbol, track replacements
        replacements = []
        for pos in potion_positions:
            replacement = random.choice(self.config.regular_symbols)
            self.board[pos["reel"]][pos["row"]] = self.create_symbol(replacement)
            replacements.append({"reel": pos["reel"], "row": pos["row"], "name": replacement})

        # Rebuild special symbol index after board modification
        self.get_special_symbols_on_board()

        # Emit event for frontend animation (includes post-replacement board)
        emit_potion_collected(self, potion_count, potion_positions, self.tot_fs, replacements)

        return potion_count

    def get_clusters_update_wins(self):
        """Find clusters on board, apply XP multiplier, update win manager."""
        clusters = Cluster.get_clusters(self.board)
        return_data = {
            "totalWin": 0,
            "wins": [],
        }
        self.board, self.win_data = self.evaluate_clusters_with_xp(
            config=self.config,
            board=self.board,
            clusters=clusters,
            xp_multiplier=self.xp_multiplier,
            return_data=return_data,
        )

        Cluster.record_cluster_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        self.win_manager.tumble_win = self.win_data["totalWin"]

        # Update XP after each cluster evaluation
        self.update_xp()

    def update_freespin(self) -> None:
        """Called before a new reveal during freegame. XP persists — do NOT reset."""
        self.fs += 1
        update_freespin_event(self)
        self.win_manager.reset_spin_win()
        self.tumblewin_mult = 0
        self.win_data = {}
