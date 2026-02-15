"""Dungeon Quest custom events — XP system, hero state, music changes, potion collection."""

UPDATE_XP = "updateXP"
HERO_STATE_CHANGE = "heroStateChange"
MUSIC_CHANGE = "musicChange"
POTION_COLLECTED = "potionCollected"

# Hero pose mapping by level
HERO_POSES = {
    1: "idle",
    2: "level2",
    3: "bonus_stance",
    4: "boss_stance",
    5: "boss_stance",
    6: "boss_stance",  # Level MAX
}


def calculate_level(cluster_count, config):
    """Return the XP level based on cumulative cluster count."""
    level = 1
    for lvl, threshold in sorted(config.xp_thresholds.items()):
        if cluster_count >= threshold:
            level = lvl
    return level


def xp_to_next_level(cluster_count, current_level, config):
    """Return clusters remaining until next level, or 0 if max."""
    if current_level >= config.max_level:
        return 0
    next_threshold = config.xp_thresholds.get(current_level + 1, 0)
    return max(0, next_threshold - cluster_count)


def emit_update_xp(gamestate):
    """Emit XP update event after each cluster win."""
    event = {
        "index": len(gamestate.book.events),
        "type": UPDATE_XP,
        "clusterCount": gamestate.xp_cluster_count,
        "level": gamestate.xp_level,
        "multiplier": gamestate.xp_multiplier,
        "escalating": gamestate.xp_level >= gamestate.config.max_level,
        "xpToNextLevel": xp_to_next_level(
            gamestate.xp_cluster_count, gamestate.xp_level, gamestate.config
        ),
    }
    gamestate.book.add_event(event)


def emit_hero_state_change(gamestate, new_level):
    """Emit hero pose change when level changes."""
    event = {
        "index": len(gamestate.book.events),
        "type": HERO_STATE_CHANGE,
        "pose": HERO_POSES.get(new_level, "idle"),
        "level": new_level,
    }
    gamestate.book.add_event(event)


def emit_music_change(gamestate, track, trigger):
    """Emit music crossfade event."""
    event = {
        "index": len(gamestate.book.events),
        "type": MUSIC_CHANGE,
        "track": track,
        "trigger": trigger,
    }
    gamestate.book.add_event(event)


def emit_potion_collected(gamestate, count, positions, new_total_fs, replacements):
    """Emit potion collection event during free spins.
    Each potion on the board adds 1 extra free spin.
    Includes replacement symbols so frontend can update the board visually.
    """
    # Serialize post-replacement board for frontend boardSettle
    post_board = []
    for reel in gamestate.board:
        post_board.append([{"name": sym.name} for sym in reel])

    event = {
        "index": len(gamestate.book.events),
        "type": POTION_COLLECTED,
        "potionCount": count,
        "positions": positions,
        "extraSpins": count,
        "newTotalSpins": new_total_fs,
        "currentSpin": gamestate.fs,
        "replacements": replacements,
        "postBoard": post_board,
    }
    gamestate.book.add_event(event)
