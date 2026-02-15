"""Blood Frenzy custom events — gauge updates, symbol unlocks, frenzy mode."""

GAUGE_UPDATE = "gaugeUpdate"
SYMBOL_UNLOCK = "symbolUnlock"
BLOOD_FRENZY = "bloodFrenzy"
BLOOD_FRENZY_END = "bloodFrenzyEnd"
CLUSTER_INFO = "clusterInfo"


def get_gauge_segment(gauge_level, config):
    """Return the current gauge segment (1-5) based on gauge level (0-100)."""
    for seg_id, seg in config.gauge_segments.items():
        low, high = seg["range"]
        if low <= gauge_level < high:
            return seg_id
    return 5


def get_gauge_multiplier(gauge_level, config):
    """Return the H-symbol multiplier for the current gauge level."""
    segment = get_gauge_segment(gauge_level, config)
    return config.gauge_segments[segment]["multiplier"]


def get_active_h_symbols(gauge_level, config):
    """Return set of H symbols unlocked at the current gauge level."""
    current_seg = get_gauge_segment(gauge_level, config)
    active = set()
    for sym, required_seg in config.h_unlock_thresholds.items():
        if current_seg >= required_seg:
            active.add(sym)
    return active


def emit_gauge_update(gamestate, delta, newly_unlocked=None):
    """Emit gauge state after L clusters fill the gauge."""
    segment = get_gauge_segment(gamestate.gauge_level, gamestate.config)
    event = {
        "index": len(gamestate.book.events),
        "type": GAUGE_UPDATE,
        "level": round(gamestate.gauge_level, 2),
        "delta": round(delta, 2),
        "segment": segment,
        "multiplier": gamestate.config.gauge_segments[segment]["multiplier"],
        "segmentName": gamestate.config.gauge_segments[segment]["name"],
        "newlyUnlocked": list(newly_unlocked) if newly_unlocked else [],
    }
    gamestate.book.add_event(event)


def emit_symbol_unlock(gamestate, symbols):
    """Emit symbol unlock event — H symbols becoming active."""
    if not symbols:
        return
    segment = get_gauge_segment(gamestate.gauge_level, gamestate.config)
    event = {
        "index": len(gamestate.book.events),
        "type": SYMBOL_UNLOCK,
        "unlockedSymbols": list(symbols),
        "segment": segment,
        "multiplier": gamestate.config.gauge_segments[segment]["multiplier"],
    }
    gamestate.book.add_event(event)


def emit_cluster_info(gamestate, l_clusters, h_clusters):
    """Emit cluster info with L/H tagging for frontend animation sequencing."""
    event = {
        "index": len(gamestate.book.events),
        "type": CLUSTER_INFO,
        "lClusters": l_clusters,
        "hClusters": h_clusters,
    }
    gamestate.book.add_event(event)


def emit_blood_frenzy(gamestate):
    """Emit Blood Frenzy trigger — gauge hit 100% during bonus."""
    event = {
        "index": len(gamestate.book.events),
        "type": BLOOD_FRENZY,
        "extraSpins": gamestate.config.blood_frenzy_extra_spins,
        "lockedSpins": gamestate.config.blood_frenzy_locked_spins,
        "newTotalSpins": gamestate.tot_fs,
        "currentSpin": gamestate.fs,
    }
    gamestate.book.add_event(event)


def emit_blood_frenzy_end(gamestate):
    """Emit Blood Frenzy lock ending."""
    segment = get_gauge_segment(gamestate.gauge_level, gamestate.config)
    event = {
        "index": len(gamestate.book.events),
        "type": BLOOD_FRENZY_END,
        "newGaugeLevel": round(gamestate.gauge_level, 2),
        "segment": segment,
        "multiplier": gamestate.config.gauge_segments[segment]["multiplier"],
    }
    gamestate.book.add_event(event)
