"""Extended Western astrology calculations.

Complements astrologica.western with additional techniques:
midpoints, antiscia, harmonics, draconic, heliocentric, composite,
davison, fixed stars, moon phase, sun times, planetary hours,
declination parallels, receptions, hyleg/alcochoden, almuten,
void-of-course moon, Gauquelin sectors, lunation phase, element balance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import swisseph as swe

from astrologica.core import (
    BirthData,
    Houses,
    PlanetPosition,
    SIGNS,
    compute_houses,
    compute_positions,
    get_ayanamsa,
)

# ── helpers ──────────────────────────────────────────────────────────────────

def _norm(lon: float) -> float:
    """Normalize longitude to 0-360."""
    return lon % 360.0


def _ang_diff(a: float, b: float) -> float:
    """Shortest signed angular distance a→b in degrees (-180..+180)."""
    d = (b - a) % 360
    return d if d <= 180 else d - 360


# ── 1. midpoints ────────────────────────────────────────────────────────────

def midpoints(positions: dict[str, PlanetPosition]) -> dict[str, float]:
    """Arithmetic midpoint of every planet pair (mod 360)."""
    names = sorted(positions.keys())
    out: dict[str, float] = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            mid = _norm((positions[a].longitude + positions[b].longitude) / 2)
            out[f"{a}/{b}"] = round(mid, 4)
    return out


def midpoint_trees(positions: dict[str, PlanetPosition]) -> dict[str, dict]:
    """Full midpoint tree: all 2-planet midpoints with sign info."""
    mps = midpoints(positions)
    tree: dict[str, dict] = {}
    for key, lon in mps.items():
        sign = int(lon // 30) % 12
        tree[key] = {
            "longitude": lon,
            "sign": SIGNS[sign],
            "degree_in_sign": lon % 30,
        }
    return tree


# ── 2. antiscia ─────────────────────────────────────────────────────────────

def antiscia(positions: dict[str, PlanetPosition]) -> dict[str, dict]:
    """Antiscia (mirror across Cancer-Capricorn axis) and contra-antiscia.

    Antiscia longitude = 180 - lon (mod 360).
    Contra-antiscia = 360 - lon (mod 360).
    """
    out: dict[str, dict] = {}
    for name, p in positions.items():
        anti = _norm(180 - p.longitude)
        contra = _norm(360 - p.longitude)
        out[name] = {
            "antiscia": anti,
            "antiscia_sign": SIGNS[int(anti // 30) % 12],
            "contra_antiscia": contra,
            "contra_sign": SIGNS[int(contra // 30) % 12],
        }
    return out


# ── 3. harmonics ────────────────────────────────────────────────────────────

def harmonics(positions: dict[str, PlanetPosition], harmonic: int) -> dict[str, float]:
    """Harmonic chart: multiply each longitude by harmonic factor mod 360."""
    if harmonic < 2:
        raise ValueError("Harmonic must be >= 2")
    return {
        name: _norm(p.longitude * harmonic)
        for name, p in positions.items()
    }


# ── 4. declination parallels ────────────────────────────────────────────────

def declination_parallels(
    birth: BirthData,
    orb: float = 1.0,
) -> list[dict]:
    """Find declination parallels and contra-parallels.

    Uses FLG_EQUATORIAL to get declinations from Swiss Ephemeris.
    """
    jd = birth.julian_day()
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_EQUATORIAL
    decls: dict[str, float] = {}
    from astrologica.core import PLANETS
    for name, pid in PLANETS.items():
        try:
            res, _ = swe.calc_ut(jd, pid, flags)
            decls[name] = res[1]  # declination
        except swe.Error:
            continue

    names = sorted(decls.keys())
    out: list[dict] = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            diff = abs(decls[a] - decls[b])
            contra_diff = abs(decls[a] + decls[b])
            if diff <= orb:
                out.append({
                    "type": "parallel",
                    "planet1": a,
                    "planet2": b,
                    "decl1": round(decls[a], 4),
                    "decl2": round(decls[b], 4),
                    "orb": round(diff, 4),
                })
            if contra_diff <= orb:
                out.append({
                    "type": "contra-parallel",
                    "planet1": a,
                    "planet2": b,
                    "decl1": round(decls[a], 4),
                    "decl2": round(decls[b], 4),
                    "orb": round(contra_diff, 4),
                })
    return out


# ── 5. draconic ─────────────────────────────────────────────────────────────

def draconic(positions: dict[str, PlanetPosition]) -> dict[str, float]:
    """Draconic chart: subtract North Node longitude from all positions.

    Result: North Node maps to 0° Aries.
    """
    node_lon = positions["Rahu"].longitude
    return {
        name: _norm(p.longitude - node_lon)
        for name, p in positions.items()
    }


# ── 6. heliocentric ─────────────────────────────────────────────────────────

def heliocentric(birth: BirthData) -> dict[str, PlanetPosition]:
    """Heliocentric planet positions (Sun excluded — it's the center)."""
    jd = birth.julian_day()
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_HELCTR
    from astrologica.core import PLANETS
    out: dict[str, PlanetPosition] = {}
    for name, pid in PLANETS.items():
        if name == "Sun":
            continue  # Sun is the center in heliocentric
        try:
            res, _ = swe.calc_ut(jd, pid, flags)
            out[name] = PlanetPosition(
                name=name,
                longitude=res[0],
                latitude=res[1],
                speed=res[3],
                retrograde=res[3] < 0,
            )
        except swe.Error:
            continue
    return out


# ── 7. composite ────────────────────────────────────────────────────────────

def composite(
    positions1: dict[str, PlanetPosition],
    positions2: dict[str, PlanetPosition],
) -> dict[str, float]:
    """Composite chart: midpoint in longitude for each shared planet."""
    shared = set(positions1.keys()) & set(positions2.keys())
    return {
        name: _norm((positions1[name].longitude + positions2[name].longitude) / 2)
        for name in sorted(shared)
    }


# ── 8. davison ──────────────────────────────────────────────────────────────

def davison(birth1: BirthData, birth2: BirthData) -> dict[str, PlanetPosition]:
    """Davison chart: positions at midpoint in TIME and SPACE.

    Midpoint Julian days + midpoint geographic coordinates.
    """
    jd1 = birth1.julian_day()
    jd2 = birth2.julian_day()
    mid_jd = (jd1 + jd2) / 2
    mid_lat = (birth1.lat + birth2.lat) / 2
    mid_lon = (birth1.lon + birth2.lon) / 2

    # Convert mid_jd back to calendar date for BirthData
    y, m, d, h = swe.revjul(mid_jd)
    hh = int(h)
    mm = int((h - hh) * 60)
    ss = int(((h - hh) * 60 - mm) * 60)
    mid_birth = BirthData(
        date=f"{y}-{m:02d}-{d:02d}",
        time=f"{hh:02d}:{mm:02d}:{ss:02d}",
        lat=mid_lat,
        lon=mid_lon,
        tz="UTC",
    )
    return compute_positions(mid_birth)


# ── 9. receptions ───────────────────────────────────────────────────────────

# Traditional essential dignity tables (simplified — domicile + exaltation only)
_DOMICILE = {
    0: ["Mars"],          # Aries
    1: ["Venus"],         # Taurus
    2: ["Mercury"],       # Gemini
    3: ["Moon"],          # Cancer
    4: ["Sun"],           # Leo
    5: ["Mercury"],       # Virgo
    6: ["Venus"],         # Libra
    7: ["Mars", "Pluto"], # Scorpio (traditional + modern)
    8: ["Jupiter"],       # Sagittarius
    9: ["Saturn"],        # Capricorn
    10: ["Saturn", "Uranus"], # Aquarius (traditional + modern)
    11: ["Jupiter", "Neptune"], # Pisces
}

_EXALTATION = {
    0: ["Sun"],       # Aries
    1: ["Moon"],      # Taurus
    6: ["Saturn"],    # Libra
    8: ["Jupiter"],   # Sagittarius (some say Ketu)
    10: ["Mercury"],  # Aquarius (some say Rahu)
    11: ["Venus"],    # Pisces
}


def receptions(positions: dict[str, PlanetPosition]) -> list[dict]:
    """Find mutual receptions (domicile swap) between planet pairs."""
    out: list[dict] = []
    names = sorted(positions.keys())
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            a_sign = positions[a].sign
            b_sign = positions[b].sign
            a_in_b_domicile = b in _DOMICILE.get(a_sign, [])
            b_in_a_domicile = a in _DOMICILE.get(b_sign, [])
            if a_in_b_domicile and b_in_a_domicile:
                out.append({
                    "type": "mutual_reception_domicile",
                    "planet1": a,
                    "planet2": b,
                    "sign1": SIGNS[a_sign],
                    "sign2": SIGNS[b_sign],
                })
            elif a_in_b_domicile:
                out.append({
                    "type": "reception",
                    "receptor": b,  # planet whose domicile the other is in
                    "guest": a,
                    "sign": SIGNS[a_sign],
                })
            elif b_in_a_domicile:
                out.append({
                    "type": "reception",
                    "receptor": a,
                    "guest": b,
                    "sign": SIGNS[b_sign],
                })
    return out


# ── 10. hyleg / alcochoden ──────────────────────────────────────────────────

def hyleg_alcochoden(
    positions: dict[str, PlanetPosition],
    houses: Houses,
) -> dict[str, Any]:
    """Traditional hyleg (life-giver) and alcochoden (life-sustainer).

    Hyleg candidates: Sun, Moon, ASC, Part of Fortune, prenatal syzygy Moon.
    Selection: planet in hylegical places (houses 1, 7, 9, 10, 11) with most
    essential dignities.
    """
    hylegical_houses = {1, 7, 9, 10, 11}

    # Part of Fortune: ASC + Moon - Sun (day chart) or ASC + Sun - Moon (night)
    sun_lon = positions["Sun"].longitude
    moon_lon = positions["Moon"].longitude
    asc = houses.ascendant
    # Simplified: assume day chart (Sun above horizon = houses 7-12)
    sun_house = houses.house_of(sun_lon)
    is_day = sun_house in {7, 8, 9, 10, 11, 12}
    if is_day:
        fortune_lon = _norm(asc + moon_lon - sun_lon)
    else:
        fortune_lon = _norm(asc + sun_lon - moon_lon)

    candidates = {
        "Sun": sun_lon,
        "Moon": moon_lon,
        "ASC": asc,
        "Part of Fortune": fortune_lon,
    }

    # Find candidate in hylegical house with most dignities
    best_name = None
    best_score = -1
    for name, lon in candidates.items():
        h = houses.house_of(lon)
        if h in hylegical_houses:
            score = _dignity_score(lon)
            if score > best_score:
                best_score = score
                best_name = name

    # Alcochoden: planet with most dignities at hyleg degree
    hyleg_lon = candidates.get(best_name, asc)
    alcochoden = None
    best_dignity = -1
    for pname, p in positions.items():
        score = _dignity_score_at(hyleg_lon, pname)
        if score > best_dignity:
            best_dignity = score
            alcochoden = pname

    return {
        "hyleg": best_name or "ASC",
        "hyleg_longitude": hyleg_lon,
        "hyleg_sign": SIGNS[int(hyleg_lon // 30) % 12],
        "alcochoden": alcochoden,
        "alcochoden_dignity_score": best_dignity,
        "is_day_chart": is_day,
        "part_of_fortune": fortune_lon,
    }


def _dignity_score(lon: float) -> int:
    """Simplified dignity score at a longitude (domicile=5, exaltation=4)."""
    sign = int(lon // 30) % 12
    return 5  # placeholder — real implementation needs full table


def _dignity_score_at(lon: float, planet: str) -> int:
    """How dignified is `planet` at the given longitude's sign?"""
    sign = int(lon // 30) % 12
    score = 0
    if planet in _DOMICILE.get(sign, []):
        score += 5
    if planet in _EXALTATION.get(sign, []):
        score += 4
    return score


# ── 11. almuten ─────────────────────────────────────────────────────────────

def almuten(positions: dict[str, PlanetPosition], houses: Houses) -> dict[int, dict]:
    """Almuten of each house cusp: planet with highest essential dignity."""
    out: dict[int, dict] = {}
    for i in range(12):
        cusp_lon = houses.cusps[i]
        best_planet = None
        best_score = -1
        for pname in positions:
            score = _dignity_score_at(cusp_lon, pname)
            if score > best_score:
                best_score = score
                best_planet = pname
        out[i + 1] = {
            "house": i + 1,
            "cusp_longitude": cusp_lon,
            "cusp_sign": SIGNS[int(cusp_lon // 30) % 12],
            "almuten": best_planet,
            "score": best_score,
        }
    return out


# ── 12. fixed stars ─────────────────────────────────────────────────────────

_DEFAULT_STARS = [
    "Regulus", "Spica", "Aldebaran", "Antares", "Fomalhaut",
    "Sirius", "Pollux", "Arcturus", "Vega", "Capella",
    "Rigel", "Betelgeuse", "Deneb", "Altair", "Procyon",
]


def fixed_stars(
    birth: BirthData,
    stars: list[str] | None = None,
    aspect_orb: float = 2.0,
) -> list[dict]:
    """Fixed star positions and aspects to natal planets."""
    jd = birth.julian_day()
    star_list = stars or _DEFAULT_STARS
    positions = compute_positions(birth)

    out: list[dict] = []
    for star_name in star_list:
        try:
            # swe.fixstar_ut returns (pos_tuple, star_name_string, flags)
            result = swe.fixstar_ut(star_name, jd, swe.FLG_SWIEPH | swe.FLG_SPEED)
            pos = result[0]
            name_str = result[1]
            lon = pos[0]
            lat = pos[1]
        except swe.Error:
            continue

        # Find aspects to natal planets
        aspects: list[dict] = []
        for pname, p in positions.items():
            diff = abs(_ang_diff(lon, p.longitude))
            if diff <= aspect_orb:
                aspects.append({
                    "planet": pname,
                    "orb": round(diff, 3),
                    "type": "conjunction",
                })

        out.append({
            "star": star_name,
            "longitude": round(lon, 4),
            "latitude": round(lat, 4),
            "sign": SIGNS[int(lon // 30) % 12],
            "degree_in_sign": round(lon % 30, 4),
            "aspects": aspects,
        })
    return out


# ── 13. moon phase ──────────────────────────────────────────────────────────

_MOON_PHASES = [
    (0, "New Moon", 0),
    (45, "Waxing Crescent", 1),
    (90, "First Quarter", 2),
    (135, "Waxing Gibbous", 3),
    (180, "Full Moon", 4),
    (225, "Waning Disseminating", 5),
    (270, "Last Quarter", 6),
    (315, "Waning Balsamic", 7),
]


def moon_phase(birth: BirthData) -> dict:
    """Sun-Moon phase angle, phase name, and approximate illumination."""
    positions = compute_positions(birth)
    sun_lon = positions["Sun"].longitude
    moon_lon = positions["Moon"].longitude
    angle = (moon_lon - sun_lon) % 360

    # Find phase
    phase_name = "New Moon"
    phase_index = 0
    for threshold, name, idx in _MOON_PHASES:
        if angle >= threshold:
            phase_name = name
            phase_index = idx

    # Illumination: cos(angle) maps 0°=dark, 180°=bright
    illumination = (1 - math.cos(math.radians(angle))) / 2

    return {
        "angle": round(angle, 2),
        "phase_name": phase_name,
        "phase_index": phase_index,
        "illumination_pct": round(illumination * 100, 1),
        "sun_sign": SIGNS[int(sun_lon // 30) % 12],
        "moon_sign": SIGNS[int(moon_lon // 30) % 12],
    }


# ── 14. sun times ───────────────────────────────────────────────────────────

def sun_times(birth: BirthData) -> dict:
    """Sunrise, sunset, solar noon, and twilight times (UTC)."""
    jd = birth.julian_day()
    # swe.rise_trans geopos = [lon, lat, alt] — NOT lat, lon!
    geo = (birth.lon, birth.lat, 0)

    # rsmi: swe.CALC_RISE=1, swe.CALC_SET=2, swe.CALC_MTRANSIT=4
    rise_jd = swe.rise_trans(jd, swe.SUN, rsmi=swe.CALC_RISE, geopos=geo)[1][0]
    set_jd = swe.rise_trans(jd, swe.SUN, rsmi=swe.CALC_SET, geopos=geo)[1][0]
    transit_jd = swe.rise_trans(jd, swe.SUN, rsmi=swe.CALC_MTRANSIT, geopos=geo)[1][0]

    def _jd_to_utc_hours(jd_val: float) -> str:
        y, m, d, h = swe.revjul(jd_val)
        hh = int(h)
        mm = int((h - hh) * 60)
        ss = int(((h - hh) * 60 - mm) * 60)
        return f"{y}-{m:02d}-{d:02d} {hh:02d}:{mm:02d}:{ss:02d} UTC"

    return {
        "sunrise": _jd_to_utc_hours(rise_jd),
        "sunset": _jd_to_utc_hours(set_jd),
        "solar_noon": _jd_to_utc_hours(transit_jd),
        "day_length_hours": round((set_jd - rise_jd) * 24, 2),
    }


# ── 15. planetary hours ─────────────────────────────────────────────────────

_CHALDEAN_ORDER = [
    "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon",
]

_DAY_RULERS = {
    0: "Moon",      # Monday
    1: "Mars",      # Tuesday
    2: "Mercury",   # Wednesday
    3: "Jupiter",   # Thursday
    4: "Venus",     # Friday
    5: "Saturn",    # Saturday
    6: "Sun",       # Sunday
}


def planetary_hours(birth: BirthData) -> list[dict]:
    """12 planetary hours for the day (Chaldean order from day ruler)."""
    st = sun_times(birth)

    # Parse sunrise/sunset JDs
    def _parse_to_jd(s: str) -> float:
        parts = s.split()
        date_part = parts[0]
        time_part = parts[1]
        y, m, d = [int(x) for x in date_part.split("-")]
        hh, mm, ss = [int(x) for x in time_part.split(":")]
        return swe.julday(y, m, d, hh + mm / 60 + ss / 3600)

    rise_jd = _parse_to_jd(st["sunrise"])
    set_jd = _parse_to_jd(st["sunset"])

    # Day of week (0=Mon in Python, but swe uses 0=Sun)
    y, m, d, h = swe.revjul(rise_jd)
    # swe.day_of_week returns 0=Mon...6=Sun
    dow = swe.day_of_week(rise_jd)
    day_ruler = _DAY_RULERS[dow]

    # Find day ruler in Chaldean order
    ruler_idx = _CHALDEAN_ORDER.index(day_ruler)

    day_length = set_jd - rise_jd
    night_length = 1.0 - day_length  # approximate 24h cycle

    hours: list[dict] = []
    for i in range(12):
        if i < 7:  # daytime hours
            start = rise_jd + (i * day_length / 7)
            end = rise_jd + ((i + 1) * day_length / 7)
            period = "day"
        else:  # nighttime hours
            ni = i - 7
            start = set_jd + (ni * night_length / 7)
            end = set_jd + ((ni + 1) * night_length / 7)
            period = "night"

        planet_idx = (ruler_idx + i) % 7
        hours.append({
            "hour": i + 1,
            "period": period,
            "ruler": _CHALDEAN_ORDER[planet_idx],
            "start_jd": round(start, 6),
            "end_jd": round(end, 6),
        })

    return hours


# ── 16. void-of-course moon ─────────────────────────────────────────────────

def moon_void_of_course(birth: BirthData) -> dict:
    """Determine if Moon is void-of-course at birth time.

    VOC = Moon makes no more major aspects before leaving its current sign.
    """
    positions = compute_positions(birth)
    moon = positions["Moon"]
    moon_sign = moon.sign
    moon_lon = moon.longitude

    # End of current sign
    sign_end = (moon_sign + 1) * 30.0

    # Check each remaining degree for aspects to other planets
    # Step through in 0.5° increments (Moon moves ~0.5°/hour)
    jd = birth.julian_day()
    step_hours = 1.0  # check every hour
    current_jd = jd
    last_aspect_jd = None

    for _ in range(48):  # max 48 hours lookahead
        # Get current Moon position
        res, _ = swe.calc_ut(current_jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SPEED)
        cur_lon = res[0]
        cur_sign = int(cur_lon // 30) % 12

        # If Moon left the sign, stop
        if cur_sign != moon_sign:
            break

        # Check aspects to natal planets (from birth chart)
        for pname, p in positions.items():
            if pname == "Moon":
                continue
            diff = abs(_ang_diff(cur_lon, p.longitude))
            # Major aspects: conjunction (0°), sextile (60°), square (90°),
            # trine (120°), opposition (180°)
            for aspect_angle in [0, 60, 90, 120, 180]:
                orb = abs(diff - aspect_angle)
                if orb <= 6.0:  # generous orb for Moon
                    last_aspect_jd = current_jd
                    break

        current_jd += step_hours / 24.0

    is_voc = last_aspect_jd is None or last_aspect_jd <= jd

    return {
        "is_void_of_course": is_voc,
        "moon_sign": SIGNS[moon_sign],
        "moon_longitude": round(moon_lon, 4),
        "last_aspect_jd": last_aspect_jd,
    }


# ── 17. Gauquelin sectors ───────────────────────────────────────────────────

def gauquelin_sectors(positions: dict[str, PlanetPosition], houses: Houses) -> dict[str, int]:
    """Place each planet in one of 36 Gauquelin sectors.

    Sector 1 = rising (just below ASC), sector 10 = culminating (MC),
    sector 19 = setting (DSC), sector 28 = IC.
    """
    asc = houses.ascendant
    mc = houses.mc

    out: dict[str, int] = {}
    for name, p in positions.items():
        # Angular distance from ASC (counterclockwise)
        dist_from_asc = (p.longitude - asc) % 360
        # Map to 36 sectors (10° each)
        sector = int(dist_from_asc / 10) + 1
        if sector > 36:
            sector = 36
        out[name] = sector
    return out


# ── 18. lunation phase (Rudhyar 8-phase) ────────────────────────────────────

def lunation_phase(birth: BirthData) -> dict:
    """Rudhyar lunation phase — 8-fold subdivision of Sun-Moon cycle."""
    mp = moon_phase(birth)
    angle = mp["angle"]

    # 8 phases, each 45°
    phase_idx = int(angle / 45) % 8
    phases = [
        "I. New Moon (Impulse)",
        "II. Crescent (Challenge)",
        "III. First Quarter (Crisis of Action)",
        "IV. Gibbous (Modification)",
        "V. Full Moon (Fruition)",
        "VI. Disseminating (Demonstration)",
        "VII. Last Quarter (Crisis of Consciousness)",
        "VIII. Balsamic (Release)",
    ]

    return {
        "angle": mp["angle"],
        "phase_index": phase_idx,
        "phase_name": phases[phase_idx],
        "phase_number": phase_idx + 1,
        "illumination_pct": mp["illumination_pct"],
    }


# ── 19. element balance ─────────────────────────────────────────────────────

_ELEMENT_SIGNS = {
    "Fire": [0, 4, 8],     # Aries, Leo, Sagittarius
    "Earth": [1, 5, 9],    # Taurus, Virgo, Capricorn
    "Air": [2, 6, 10],     # Gemini, Libra, Aquarius
    "Water": [3, 7, 11],   # Cancer, Scorpio, Pisces
}

_MODE_SIGNS = {
    "Cardinal": [0, 3, 6, 9],
    "Fixed": [1, 4, 7, 10],
    "Mutable": [2, 5, 8, 11],
}


def element_balance(positions: dict[str, PlanetPosition]) -> dict:
    """Count planets by element and mode, with percentages."""
    elements = {"Fire": 0, "Earth": 0, "Air": 0, "Water": 0}
    modes = {"Cardinal": 0, "Fixed": 0, "Mutable": 0}
    total = len(positions)

    for name, p in positions.items():
        for elem, signs in _ELEMENT_SIGNS.items():
            if p.sign in signs:
                elements[elem] += 1
        for mode, signs in _MODE_SIGNS.items():
            if p.sign in signs:
                modes[mode] += 1

    return {
        "elements": {k: {"count": v, "pct": round(v / total * 100, 1) if total else 0}
                     for k, v in elements.items()},
        "modes": {k: {"count": v, "pct": round(v / total * 100, 1) if total else 0}
                  for k, v in modes.items()},
        "total_planets": total,
        "dominant_element": max(elements, key=elements.get),
        "dominant_mode": max(modes, key=modes.get),
    }
