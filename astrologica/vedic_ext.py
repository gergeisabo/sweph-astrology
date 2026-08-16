"""Extended Vedic astrology calculations.

Covers: muhurat (electional) engine, ashtakoota/dashakoota compatibility,
ashtakavarga (BAV/SAV), KP system basics, Jaimini basics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import swisseph as swe

from astrologica.core import (
    BirthData,
    PLANETS,
    SIGNS,
    compute_houses,
    compute_positions,
    get_ayanamsa,
)
from astrologica.vedic import nakshatra, panchang

# ── helpers ──────────────────────────────────────────────────────────────────

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

NAK_RULERS = {
    0: "Ketu", 1: "Venus", 2: "Sun", 3: "Moon", 4: "Mars", 5: "Rahu",
    6: "Jupiter", 7: "Saturn", 8: "Mercury", 9: "Ketu", 10: "Venus", 11: "Sun",
    12: "Moon", 13: "Mars", 14: "Rahu", 15: "Jupiter", 16: "Saturn", 17: "Mercury",
    18: "Ketu", 19: "Venus", 20: "Sun", 21: "Moon", 22: "Mars", 23: "Rahu",
    24: "Jupiter", 25: "Saturn", 26: "Mercury",
}

TITHIS = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya",
]

VARAS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
VARA_RULERS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


# ── 1. ashtakoota compatibility (36-point gun milan) ────────────────────────

def ashtakoota(moon_nak1: int, moon_nak2: int) -> dict:
    """Ashtakoota compatibility: 36-point gun milan.

    Args:
        moon_nak1: Moon nakshatra index (0-26) for person 1
        moon_nak2: Moon nakshatra index (0-26) for person 2

    Returns: detailed scoring breakdown.
    """
    # Varna (1 point): spiritual compatibility
    varna_score = _varna_score(moon_nak1, moon_nak2)

    # Vashya (2 points): mutual attraction
    vashya_score = _vashya_score(moon_nak1, moon_nak2)

    # Tara (3 points): health/luck compatibility
    tara_score = _tara_score(moon_nak1, moon_nak2)

    # Yoni (4 points): sexual/physical compatibility
    yoni_score = _yoni_score(moon_nak1, moon_nak2)

    # Graha Maitri (5 points): planetary friendship
    graha_score = _graha_maitri_score(moon_nak1, moon_nak2)

    # Gana (6 points): temperament compatibility
    gana_score = _gana_score(moon_nak1, moon_nak2)

    # Bhakoot (7 points): emotional/love compatibility
    bhakoot_score = _bhakoot_score(moon_nak1, moon_nak2)

    # Nadi (8 points): health/genetic compatibility
    nadi_score = _nadi_score(moon_nak1, moon_nak2)

    total = (varna_score + vashya_score + tara_score + yoni_score +
             graha_score + gana_score + bhakoot_score + nadi_score)

    return {
        "total": total,
        "max": 36,
        "varna": {"score": varna_score, "max": 1},
        "vashya": {"score": vashya_score, "max": 2},
        "tara": {"score": tara_score, "max": 3},
        "yoni": {"score": yoni_score, "max": 4},
        "graha_maitri": {"score": graha_score, "max": 5},
        "gana": {"score": gana_score, "max": 6},
        "bhakoot": {"score": bhakoot_score, "max": 7},
        "nadi": {"score": nadi_score, "max": 8},
        "person1_nakshatra": NAKSHATRAS[moon_nak1],
        "person2_nakshatra": NAKSHATRAS[moon_nak2],
        "verdict": _compatibility_verdict(total),
    }


def _varna_score(n1: int, n2: int) -> int:
    """Varna: Brahmin(3,6,9,12,15,18,21,24), Kshatriya(0,4,7,10,13,16,19,22,25),
    Vaishya(1,5,8,11,14,17,20,23), Shudra(2)"""
    varna_map = {
        0: 1, 1: 2, 2: 3, 3: 0, 4: 1, 5: 2, 6: 0, 7: 1, 8: 2,
        9: 0, 10: 1, 11: 2, 12: 0, 13: 1, 14: 2, 15: 0, 16: 1, 17: 2,
        18: 0, 19: 1, 20: 2, 21: 0, 22: 1, 23: 2, 24: 0, 25: 1, 26: 2,
    }
    v1 = varna_map.get(n1, 0)
    v2 = varna_map.get(n2, 0)
    return 1 if v1 >= v2 else 0


def _vashya_score(n1: int, n2: int) -> int:
    """Vashya: mutual attraction (simplified — 2 if same, 1 if friendly)."""
    # Simplified: same nakshatra = 2, same ruler = 1
    if n1 == n2:
        return 2
    r1 = NAK_RULERS.get(n1)
    r2 = NAK_RULERS.get(n2)
    if r1 == r2:
        return 1
    return 0


def _tara_score(n1: int, n2: int) -> int:
    """Tara: count from person1's nakshatra to person2's (mod 9)."""
    count = (n2 - n1) % 27
    remainder = count % 9
    if remainder in (0, 3, 5, 7):
        return 3
    elif remainder in (2, 4, 6, 8):
        return 1.5
    return 0


def _yoni_score(n1: int, n2: int) -> int:
    """Yoni: sexual compatibility (simplified)."""
    # Each nakshatra has a yoni animal; simplified scoring
    yoni_table = [
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
        13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,
    ]
    y1 = yoni_table[n1]
    y2 = yoni_table[n2]
    if y1 == y2:
        return 4
    # Friendly pairs
    friendly = {(0, 7), (1, 6), (2, 5), (3, 4), (8, 15), (9, 14), (10, 13),
                (11, 12), (16, 23), (17, 22), (18, 21), (19, 20), (24, 26)}
    if (y1, y2) in friendly or (y2, y1) in friendly:
        return 3
    return 1


def _graha_maitri_score(n1: int, n2: int) -> int:
    """Graha Maitri: planetary friendship between nakshatra rulers."""
    r1 = NAK_RULERS.get(n1)
    r2 = NAK_RULERS.get(n2)
    if r1 == r2:
        return 5
    # Friends
    friends = {
        "Sun": ["Moon", "Mars", "Jupiter"],
        "Moon": ["Sun", "Mercury"],
        "Mars": ["Sun", "Moon", "Jupiter"],
        "Mercury": ["Sun", "Venus"],
        "Jupiter": ["Sun", "Moon", "Mars"],
        "Venus": ["Mercury", "Saturn"],
        "Saturn": ["Mercury", "Venus"],
    }
    if r2 in friends.get(r1, []) or r1 in friends.get(r2, []):
        return 4
    # Neutral
    neutrals = {
        "Sun": ["Mercury", "Venus"],
        "Moon": ["Jupiter", "Venus", "Saturn"],
        "Mars": ["Venus", "Saturn"],
        "Mercury": ["Mars", "Jupiter", "Saturn"],
        "Jupiter": ["Saturn"],
        "Venus": ["Mars", "Jupiter"],
        "Saturn": ["Jupiter"],
    }
    if r2 in neutrals.get(r1, []) or r1 in neutrals.get(r2, []):
        return 3
    return 1


def _gana_score(n1: int, n2: int) -> int:
    """Gana: temperament (Deva=0, Manushya=1, Rakshasa=2)."""
    gana_map = {
        0: 2, 1: 1, 2: 0, 3: 1, 4: 2, 5: 0, 6: 1, 7: 0, 8: 2,
        9: 0, 10: 1, 11: 0, 12: 1, 13: 2, 14: 0, 15: 1, 16: 2, 17: 0,
        18: 2, 19: 1, 20: 0, 21: 1, 22: 2, 23: 0, 24: 1, 25: 0, 26: 1,
    }
    g1 = gana_map.get(n1, 1)
    g2 = gana_map.get(n2, 1)
    if g1 == g2:
        return 6
    if (g1 == 0 and g2 == 1) or (g1 == 1 and g2 == 0):
        return 5
    if (g1 == 1 and g2 == 2) or (g1 == 2 and g2 == 1):
        return 3
    return 0


def _bhakoot_score(n1: int, n2: int) -> int:
    """Bhakoot: moon sign compatibility (simplified)."""
    # Count sign distance between moon signs
    sign1 = n1 * 40 / 40  # simplified: nakshatra → sign
    sign2 = n2 * 40 / 40
    # For simplicity: same sign = 7, trine = 5, else 0
    r1 = NAK_RULERS.get(n1)
    r2 = NAK_RULERS.get(n2)
    if r1 == r2:
        return 7
    return 3


def _nadi_score(n1: int, n2: int) -> int:
    """Nadi: health/genetic compatibility (8 points)."""
    # 3 nadis: Aadi(0), Madhya(1), Antya(2)
    nadi_map = {
        0: 0, 1: 1, 2: 2, 3: 0, 4: 1, 5: 2, 6: 0, 7: 1, 8: 2,
        9: 0, 10: 1, 11: 2, 12: 0, 13: 1, 14: 2, 15: 0, 16: 1, 17: 2,
        18: 0, 19: 1, 20: 2, 21: 0, 22: 1, 23: 2, 24: 0, 25: 1, 26: 2,
    }
    n1_val = nadi_map.get(n1, 1)
    n2_val = nadi_map.get(n2, 1)
    if n1_val != n2_val:
        return 8
    return 0  # same nadi = dosha


def _compatibility_verdict(total: float) -> str:
    if total >= 32:
        return "Excellent match"
    elif total >= 25:
        return "Very good match"
    elif total >= 18:
        return "Good match"
    elif total >= 12:
        return "Average match"
    else:
        return "Poor match — significant doshas present"


# ── 2. muhurat engine ───────────────────────────────────────────────────────

# Activity-specific nakshatra scoring
_MUHURAT_NAK_SCORES = {
    "vehicle": {
        "excellent": [1, 3, 6, 10, 11, 15, 20, 21, 23],  # Rohini, Mrigashira, etc.
        "good": [0, 2, 4, 5, 7, 8, 9, 12, 13, 14, 16, 17, 18, 19, 22, 24, 25, 26],
    },
    "finance": {
        "excellent": [6, 7, 9, 11, 13, 15, 20, 21, 23],  # Pushya, Ashlesha, etc.
        "good": [0, 1, 2, 3, 4, 5, 8, 10, 12, 14, 16, 17, 18, 19, 22, 24, 25, 26],
    },
    "marriage": {
        "excellent": [1, 3, 5, 6, 7, 10, 11, 13, 15, 20, 21, 23],
        "good": [0, 2, 4, 8, 9, 12, 14, 16, 17, 18, 19, 22, 24, 25, 26],
    },
    "travel": {
        "excellent": [0, 3, 6, 7, 10, 11, 12, 15, 20, 21, 23],
        "good": [1, 2, 4, 5, 8, 9, 13, 14, 16, 17, 18, 19, 22, 24, 25, 26],
    },
    "launch": {
        "excellent": [0, 1, 3, 6, 7, 10, 11, 13, 15, 20, 21, 23],
        "good": [2, 4, 5, 8, 9, 12, 14, 16, 17, 18, 19, 22, 24, 25, 26],
    },
}

# Vara (day) scoring per activity
_MUHURAT_VARA = {
    "vehicle": {"excellent": [4, 5], "good": [0, 2, 3, 6], "avoid": [1]},  # Thu/Fri best
    "finance": {"excellent": [0, 3, 4], "good": [1, 2, 5, 6], "avoid": []},
    "marriage": {"excellent": [1, 3, 4, 5], "good": [0, 2, 6], "avoid": [6]},
    "travel": {"excellent": [0, 3, 5], "good": [1, 2, 4, 6], "avoid": [2]},
    "launch": {"excellent": [0, 3, 4], "good": [1, 2, 5, 6], "avoid": [2]},
}


def muhurat_scan(
    birth: BirthData,
    activity: str,
    from_date: str,
    to_date: str,
    place_lat: float | None = None,
    place_lon: float | None = None,
) -> list[dict]:
    """Scan a date range for auspicious muhurat windows.

    Args:
        birth: birth data (for natal chart context)
        activity: one of "vehicle", "finance", "marriage", "travel", "launch"
        from_date: start date (YYYY-MM-DD)
        to_date: end date (YYYY-MM-DD)
        place_lat/lon: location for panchang (defaults to birthplace)

    Returns: list of scored days, sorted by score (best first).
    """
    from datetime import datetime, timedelta
    lat = place_lat or birth.lat
    lon = place_lon or birth.lon

    start = datetime.strptime(from_date, "%Y-%m-%d")
    end = datetime.strptime(to_date, "%Y-%m-%d")

    results: list[dict] = []
    current = start

    while current <= end:
        score = 0
        notes: list[str] = []

        # Vara (day of week) score
        dow = current.weekday()  # 0=Mon in Python, but our VARA starts with Sun
        # Convert: Python 0=Mon → Vedic 0=Sun
        vedic_dow = (dow + 1) % 7
        vara_rules = _MUHURAT_VARA.get(activity, {})
        if vedic_dow in vara_rules.get("excellent", []):
            score += 10
            notes.append(f"{VARAS[vedic_dow]}: excellent day")
        elif vedic_dow in vara_rules.get("good", []):
            score += 5
            notes.append(f"{VARAS[vedic_dow]}: good day")
        elif vedic_dow in vara_rules.get("avoid", []):
            score -= 10
            notes.append(f"{VARAS[vedic_dow]}: AVOID")

        # Nakshatra score (simplified — compute for noon)
        try:
            jd = swe.julday(current.year, current.month, current.day, 12.0)
            # Get Moon longitude at noon (sidereal)
            ay = get_ayanamsa(jd, "lahiri")
            res, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SPEED)
            moon_sid = (res[0] - ay) % 360
            nak_idx = int(moon_sid / (360 / 27)) % 27

            nak_rules = _MUHURAT_NAK_SCORES.get(activity, {})
            if nak_idx in nak_rules.get("excellent", []):
                score += 15
                notes.append(f"Nakshatra {NAKSHATRAS[nak_idx]}: excellent")
            elif nak_idx in nak_rules.get("good", []):
                score += 8
                notes.append(f"Nakshatra {NAKSHATRAS[nak_idx]}: good")
            else:
                notes.append(f"Nakshatra {NAKSHATRAS[nak_idx]}: neutral")
        except swe.Error:
            pass

        # Rahu Kalam avoidance (simplified)
        # Each day has a ~1.5 hour Rahu period; skip detailed calc for now

        # Avoid eclipses (simplified — skip new/full moon days for major activities)
        try:
            sun_res, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)
            moon_res, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH)
            angle = abs((moon_res[0] - sun_res[0]) % 360)
            if angle < 5:  # new moon
                score -= 5
                notes.append("New Moon — caution for new beginnings")
            elif abs(angle - 180) < 5:  # full moon
                score += 3
                notes.append("Full Moon — favorable for completions")
        except swe.Error:
            pass

        results.append({
            "date": current.strftime("%Y-%m-%d"),
            "day": VARAS[vedic_dow],
            "score": score,
            "notes": notes,
        })

        current += timedelta(days=1)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# ── 3. ashtakavarga (BAV — simplified) ──────────────────────────────────────

# Simplified BAV contribution tables (standard published bindu rules)
# Each planet contributes bindus to certain signs from its position
_BAV_CONTRIBUTIONS = {
    "Sun": {
        "from_sign": {
            0: [1, 2, 4, 7, 8, 9, 10, 11],
            1: [0, 3, 5, 6, 7, 9, 10, 11],
            2: [0, 1, 2, 4, 7, 8, 9, 10],
            3: [0, 3, 4, 6, 7, 8, 10, 11],
            4: [0, 1, 2, 3, 5, 7, 9, 10],
            5: [1, 3, 5, 6, 7, 9, 10, 11],
            6: [0, 2, 4, 6, 8, 9, 10, 11],
            7: [1, 2, 3, 4, 5, 7, 8, 9],
            8: [0, 1, 3, 4, 5, 7, 9, 11],
            9: [0, 2, 4, 6, 8, 10, 11],
            10: [0, 1, 2, 3, 5, 7, 8, 9],
            11: [0, 2, 4, 6, 8, 9, 10, 11],
        }
    },
}


def ashtakavarga_bav(positions: dict, planet: str) -> dict[int, int]:
    """Simplified BAV (Bhinna Ashtakavarga) for one planet.

    Returns: {sign_index: bindu_count} for all 12 signs.
    """
    if planet not in _BAV_CONTRIBUTIONS:
        # For planets without full tables, return uniform 4 (average)
        return {i: 4 for i in range(12)}

    p_sign = positions[planet].sign
    contrib = _BAV_CONTRIBUTIONS[planet]["from_sign"]
    signs_with_bindus = contrib.get(p_sign, [])

    bav: dict[int, int] = {}
    for sign in range(12):
        # Count how many natal planets contribute a bindus to this sign
        count = 0
        for pname, p in positions.items():
            if pname in ("Rahu", "Ketu", "Lilith"):
                continue
            p_contrib = _BAV_CONTRIBUTIONS.get(pname, {}).get("from_sign", {})
            if sign in p_contrib.get(p.sign, []):
                count += 1
        bav[sign] = count

    return bav


def sav(positions: dict) -> dict[int, int]:
    """SAV (Sarvashtakavarga): sum of all planets' BAVs.

    Total should be 337 (standard invariant).
    """
    total: dict[int, int] = {i: 0 for i in range(12)}
    for planet in positions:
        if planet in ("Rahu", "Ketu", "Lilith"):
            continue
        bav = ashtakavarga_bav(positions, planet)
        for sign in range(12):
            total[sign] += bav[sign]
    return total


# ── 4. dashakoota (10-point system) ─────────────────────────────────────────

def dashakoota(moon_nak1: int, moon_nak2: int) -> dict:
    """Dashakoota: 10-point compatibility system (Vedic).

    Simplified version combining ashtakoota total with additional factors.
    """
    ak = ashtakoota(moon_nak1, moon_nak2)

    # Convert 36-point to 10-point scale
    scaled = round(ak["total"] / 36 * 10, 1)

    return {
        "total_10": scaled,
        "max_10": 10,
        "ashtakoota_total": ak["total"],
        "ashtakoota_max": 36,
        "breakdown": ak,
        "verdict": _compatibility_verdict(ak["total"]),
    }
