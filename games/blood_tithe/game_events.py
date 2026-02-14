"""Blood Tithe custom events — Blood Gauge, Blood Moon, cluster info with L/H tagging."""

GAUGE_UPDATE = "gaugeUpdate"
BLOOD_MOON = "bloodMoon"
BLOOD_MOON_END = "bloodMoonEnd"
CLUSTER_INFO = "clusterInfo"
CHALICE_ABSORB = "chaliceAbsorb"


def get_gauge_segment(gauge_level, config):
    """Return the current gauge segment (1-5) based on gauge level (0-100)."""
    for seg_id, seg in config.gauge_segments.items():
        low, high = seg["range"]
        if low <= gauge_level < high:
            return seg_id
    return 5  # overflow cap


def get_gauge_multiplier(gauge_level, config):
    """Return the H-symbol multiplier for the current gauge level."""
    segment = get_gauge_segment(gauge_level, config)
    return config.gauge_segments[segment]["multiplier"]


def emit_gauge_update(gamestate, delta):
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
    }
    gamestate.book.add_event(event)


def emit_cluster_info(gamestate, l_clusters, h_clusters):
    """Emit cluster info with L/H tagging so frontend can sequence animations.

    l_clusters: list of {symbol, positions, clusterSize}
    h_clusters: list of {symbol, positions, clusterSize, gaugeMultiplier}
    """
    event = {
        "index": len(gamestate.book.events),
        "type": CLUSTER_INFO,
        "lClusters": l_clusters,
        "hClusters": h_clusters,
    }
    gamestate.book.add_event(event)


def emit_blood_moon(gamestate):
    """Emit Blood Moon trigger — gauge hit 100% during bonus."""
    event = {
        "index": len(gamestate.book.events),
        "type": BLOOD_MOON,
        "extraSpins": gamestate.config.blood_moon_extra_spins,
        "lockedSpins": gamestate.config.blood_moon_locked_spins,
        "newTotalSpins": gamestate.tot_fs,
        "currentSpin": gamestate.fs,
    }
    gamestate.book.add_event(event)


def emit_chalice_absorb(gamestate, pt_positions, l_positions, l_count, gauge_delta):
    """Emit chalice absorb — PT vacuumed all L symbols into the gauge."""
    segment = get_gauge_segment(gamestate.gauge_level, gamestate.config)
    event = {
        "index": len(gamestate.book.events),
        "type": CHALICE_ABSORB,
        "ptPositions": pt_positions,
        "lPositions": l_positions,
        "lCount": l_count,
        "gaugeDelta": round(gauge_delta, 2),
        "gaugeLevel": round(gamestate.gauge_level, 2),
        "segment": segment,
        "multiplier": gamestate.config.gauge_segments[segment]["multiplier"],
    }
    gamestate.book.add_event(event)


def emit_blood_moon_end(gamestate):
    """Emit Blood Moon lock ending — gauge unlocks and drops."""
    segment = get_gauge_segment(gamestate.gauge_level, gamestate.config)
    event = {
        "index": len(gamestate.book.events),
        "type": BLOOD_MOON_END,
        "newGaugeLevel": round(gamestate.gauge_level, 2),
        "segment": segment,
        "multiplier": gamestate.config.gauge_segments[segment]["multiplier"],
    }
    gamestate.book.add_event(event)
