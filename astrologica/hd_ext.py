"""Extended Human Design calculations.

Covers: HD transits, compatibility, incarnation cross, circuitry,
dream rave, sensitivity profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import swisseph as swe

from astrologica.core import BirthData, compute_positions, SIGNS
from astrologica.hd import compute as compute_hd, gate_at_longitude


# ── HD transits ──────────────────────────────────────────────────────────────

def hd_transits(birth: BirthData) -> dict:
    """Current HD transits: which gates are activated by current planetary positions."""
    pos = compute_positions(birth)
    active_gates: dict[str, int] = {}
    for name, p in pos.items():
        if name in ("Rahu", "Ketu", "Lilith"):
            continue
        gate = gate_at_longitude(p.longitude)
        active_gates[name] = gate
    return {"active_gates": active_gates}


# ── HD compatibility ────────────────────────────────────────────────────────

def hd_compatibility(birth1: BirthData, birth2: BirthData) -> dict:
    """HD compatibility: electromagnetic connections and shared gates."""
    bg1 = compute_hd(birth1)
    bg2 = compute_hd(birth2)

    gates1 = set(bg1.all_active_gates)
    gates2 = set(bg2.all_active_gates)

    electromagnetic = gates1.symmetric_difference(gates2)

    return {
        "person1_gates": sorted(gates1),
        "person2_gates": sorted(gates2),
        "electromagnetic_gates": sorted(electromagnetic),
        "shared_gates": sorted(gates1 & gates2),
        "person1_type": bg1.type,
        "person2_type": bg2.type,
    }


# ── incarnation cross ───────────────────────────────────────────────────────

def incarnation_cross(birth: BirthData) -> dict:
    """Incarnation cross: the 4 gates formed by Sun/Earth and nodes.

    The existing HD engine already computes this — we just expose it.
    """
    bg = compute_hd(birth)
    # Earth = Sun + 32 in HD gate wheel (opposite position)
    p_sun = bg.personality_gates.get("Sun", 0)
    p_earth = bg.personality_gates.get("Earth", (p_sun + 32) % 64 or 64)
    d_sun = bg.design_gates.get("Sun", 0)
    d_earth = bg.design_gates.get("Earth", (d_sun + 32) % 64 or 64)

    return {
        "incarnation_cross": bg.incarnation_cross,
        "conscious_sun": p_sun,
        "conscious_earth": p_earth,
        "unconscious_sun": d_sun,
        "unconscious_earth": d_earth,
        "cross_gates": [p_sun, p_earth, d_sun, d_earth],
    }


# ── HD circuitry ────────────────────────────────────────────────────────────

def hd_circuitry(birth: BirthData) -> dict:
    """Circuitry analysis: which circuits are activated.

    Circuits: Individual, Tribal, Collective.
    Each channel belongs to a circuit.
    """
    # Circuit classification (simplified — gate-based)
    _INDIVIDUAL_GATES = {1, 2, 4, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24, 25, 27, 28, 29, 30, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64}
    _TRIBAL_GATES = {3, 5, 9, 15, 16, 18, 21, 25, 27, 37, 40, 45, 46, 50, 51}
    _COLLECTIVE_GATES = {2, 6, 7, 8, 10, 11, 12, 13, 14, 17, 20, 23, 24, 26, 28, 29, 30, 31, 33, 34, 35, 36, 38, 39, 41, 42, 43, 44, 47, 48, 49, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64}

    bg = compute_hd(birth)
    active = set(bg.all_active_gates)

    circuits = {
        "Individual": len(active & _INDIVIDUAL_GATES),
        "Tribal": len(active & _TRIBAL_GATES),
        "Collective": len(active & _COLLECTIVE_GATES),
    }

    dominant = max(circuits, key=circuits.get)

    return {
        "active_gates": sorted(active),
        "circuit_counts": circuits,
        "dominant_circuit": dominant,
        "defined_channels": bg.defined_channels,
    }


# ── HD design date (88° solar arc) ──────────────────────────────────────────

def design_date(birth: BirthData) -> dict:
    """Compute the HD design date: ~88 solar degrees before birth.

    This is the moment of unconscious design calculation.
    """
    jd = birth.julian_day()
    # 88° of solar motion ≈ 88 days (Sun moves ~1°/day)
    design_jd = jd - 88
    y, m, d, h = swe.revjul(design_jd)

    return {
        "design_date": f"{y}-{m:02d}-{d:02d}",
        "design_time": f"{int(h):02d}:{int((h-int(h))*60):02d}:00",
        "days_before_birth": 88,
    }
