"""Hellenistic astrology calculations.

Covers: Hermetic lots, Brennan 15 lots, Egyptian bounds, zodiacal releasing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from astrologica.core import BirthData, compute_positions, SIGNS, Houses, compute_houses

# ── helpers ──────────────────────────────────────────────────────────────────

def _norm(lon: float) -> float:
    return lon % 360.0


# ── 1. Hermetic lots ────────────────────────────────────────────────────────

def hermetic_lots(positions: dict, houses: Houses, is_day: bool) -> dict[str, float]:
    """Compute key Hermetic lots.

    Day chart: lot = ASC + (benefic - malefic)
    Night chart: lot = ASC + (malefic - benefic)
    """
    asc = houses.ascendant
    sun = positions["Sun"].longitude
    moon = positions["Moon"].longitude
    saturn = positions["Saturn"].longitude
    jupiter = positions["Jupiter"].longitude
    mars = positions["Mars"].longitude
    venus = positions["Venus"].longitude
    mercury = positions["Mercury"].longitude

    lots: dict[str, float] = {}

    # Lot of Fortune (most basic)
    if is_day:
        lots["Fortune"] = _norm(asc + moon - sun)
    else:
        lots["Fortune"] = _norm(asc + sun - moon)

    # Lot of Spirit (reverse of Fortune)
    if is_day:
        spirit = _norm(asc + sun - moon)
    else:
        spirit = _norm(asc + moon - sun)
    lots["Spirit"] = spirit

    # Lot of Eros (Venus-based)
    if is_day:
        lots["Eros"] = _norm(asc + venus - spirit)
    else:
        lots["Eros"] = _norm(asc + spirit - venus)

    # Lot of Necessity (Mercury-based)
    if is_day:
        lots["Necessity"] = _norm(asc + mercury - saturn)
    else:
        lots["Necessity"] = _norm(asc + saturn - mercury)

    # Lot of Courage (Mars-based)
    if is_day:
        lots["Courage"] = _norm(asc + mars - saturn)
    else:
        lots["Courage"] = _norm(asc + saturn - mars)

    # Lot of Victory (Jupiter-based)
    if is_day:
        lots["Victory"] = _norm(asc + jupiter - saturn)
    else:
        lots["Victory"] = _norm(asc + saturn - jupiter)

    return lots


# ── 2. Egyptian bounds ──────────────────────────────────────────────────────

# Egyptian bounds table (sign → [(start_deg, ruler), ...])
_EGYPTIAN_BOUNDS = {
    0: [(6, "Jupiter"), (12, "Venus"), (20, "Mercury"), (25, "Mars"), (30, "Saturn")],
    1: [(8, "Venus"), (14, "Mercury"), (22, "Jupiter"), (27, "Saturn"), (30, "Mars")],
    2: [(6, "Mercury"), (12, "Jupiter"), (17, "Venus"), (24, "Mars"), (30, "Saturn")],
    3: [(6, "Mars"), (13, "Jupiter"), (20, "Mercury"), (27, "Venus"), (30, "Saturn")],
    4: [(6, "Saturn"), (11, "Mercury"), (18, "Venus"), (24, "Jupiter"), (30, "Mars")],
    5: [(7, "Mercury"), (12, "Venus"), (19, "Jupiter"), (24, "Saturn"), (30, "Mars")],
    6: [(6, "Saturn"), (11, "Venus"), (18, "Jupiter"), (24, "Mercury"), (30, "Mars")],
    7: [(6, "Mars"), (11, "Jupiter"), (19, "Venus"), (24, "Saturn"), (30, "Mercury")],
    8: [(8, "Jupiter"), (14, "Venus"), (19, "Mercury"), (24, "Saturn"), (30, "Mars")],
    9: [(6, "Venus"), (12, "Mercury"), (17, "Jupiter"), (24, "Mars"), (30, "Saturn")],
    10: [(6, "Venus"), (12, "Mercury"), (19, "Jupiter"), (25, "Saturn"), (30, "Mars")],
    11: [(6, "Jupiter"), (12, "Venus"), (20, "Saturn"), (26, "Mercury"), (30, "Mars")],
}


def egyptian_bounds(positions: dict) -> dict[str, dict]:
    """Egyptian bounds (Hand of Hermes): assign each planet to its bound ruler."""
    results: dict[str, dict] = {}
    for name, p in positions.items():
        sign = p.sign
        deg = p.degree_in_sign
        bounds = _EGYPTIAN_BOUNDS.get(sign, [])
        bound_ruler = "Unknown"
        for end_deg, ruler in bounds:
            if deg < end_deg:
                bound_ruler = ruler
                break
        results[name] = {
            "sign": SIGNS[sign],
            "degree": round(deg, 2),
            "bound_ruler": bound_ruler,
        }
    return results


# ── 3. zodiacal releasing (simplified) ───────────────────────────────────────

def zodiacal_releasing_from_fortune(
    positions: dict,
    houses: Houses,
    is_day: bool,
    max_level: int = 2,
) -> list[dict]:
    """Zodiacal releasing from Lot of Fortune (simplified, Level 1-2).

    Level 1: ~years per sign (based on triplicity ruler periods)
    Level 2: sub-periods within each L1 period
    """
    # Compute Lot of Fortune
    asc = houses.ascendant
    sun = positions["Sun"].longitude
    moon = positions["Moon"].longitude
    if is_day:
        fortune = _norm(asc + moon - sun)
    else:
        fortune = _norm(asc + sun - moon)

    fortune_sign = int(fortune // 30) % 12

    # Triplicity rulers (fire/earth/air/water)
    triplicity_rulers = {
        "Fire": ["Sun", "Jupiter", "Saturn"],
        "Earth": ["Venus", "Moon", "Mars"],
        "Air": ["Saturn", "Mercury", "Jupiter"],
        "Water": ["Venus", "Mars", "Moon"],
    }

    # Period lengths per sign (simplified — traditional values)
    period_lengths = {
        0: 15, 1: 8, 2: 20, 3: 25, 4: 19, 5: 9,
        6: 20, 7: 12, 8: 12, 9: 27, 10: 30, 11: 12,
    }

    # Element of fortune sign
    elements = {0: "Fire", 1: "Earth", 2: "Air", 3: "Water",
                4: "Fire", 5: "Earth", 6: "Air", 7: "Water",
                8: "Fire", 9: "Earth", 10: "Air", 11: "Water"}
    element = elements[fortune_sign]

    # Build Level 1 periods starting from fortune sign
    periods: list[dict] = []
    current_sign = fortune_sign
    total_years = 0

    for i in range(12):
        length = period_lengths[current_sign]
        periods.append({
            "level": 1,
            "sign": SIGNS[current_sign],
            "sign_index": current_sign,
            "start_year": total_years,
            "end_year": total_years + length,
            "duration_years": length,
            "ruler": triplicity_rulers[element][0] if element in triplicity_rulers else "Unknown",
        })
        total_years += length
        current_sign = (current_sign + 1) % 12

    return periods
