"""Timing and predictive astrology engine.

Covers: profections, firdaria, progressions (secondary/tertiary/minor),
symbolic directions, primary directions, lunar & planetary returns,
ingress search, retrograde periods, eclipses, transit calendar,
forecast calendar.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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

# ── helpers ──────────────────────────────────────────────────────────────────

def _norm(lon: float) -> float:
    return lon % 360.0


def _ang_diff(a: float, b: float) -> float:
    d = (b - a) % 360
    return d if d <= 180 else d - 360


def _jd_to_datetime(jd: float) -> datetime:
    y, m, d, h = swe.revjul(jd)
    hh = int(h)
    mm = int((h - hh) * 60)
    ss = int(((h - hh) * 60 - mm) * 60)
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


# ── 1. annual profections ───────────────────────────────────────────────────

def profections(birth: BirthData, target_age: int | None = None) -> dict:
    """Annual profections: each year advances one house/sign.

    If target_age given, returns that year's profection.
    Otherwise returns a table of profections age 0..11 (full cycle).
    """
    houses = compute_houses(birth)
    asc_sign = int(houses.ascendant // 30) % 12

    if target_age is not None:
        activated_house = (target_age % 12) + 1
        prof_sign = (asc_sign + target_age) % 12
        return {
            "age": target_age,
            "activated_house": activated_house,
            "profection_sign": SIGNS[prof_sign],
            "profection_sign_index": prof_sign,
            "profection_lord": _sign_ruler(prof_sign),
        }

    # Full 12-year cycle
    table = []
    for age in range(12):
        activated_house = (age % 12) + 1
        prof_sign = (asc_sign + age) % 12
        table.append({
            "age": age,
            "activated_house": activated_house,
            "profection_sign": SIGNS[prof_sign],
            "profection_lord": _sign_ruler(prof_sign),
        })
    return {"cycle_length": 12, "asc_sign": SIGNS[asc_sign], "profections": table}


def _sign_ruler(sign_idx: int) -> str:
    """Traditional sign ruler."""
    rulers = {
        0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon",
        4: "Sun", 5: "Mercury", 6: "Venus", 7: "Mars",
        8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter",
    }
    return rulers[sign_idx]


# ── 2. firdaria ─────────────────────────────────────────────────────────────

# Traditional firdaria periods (7 planets + nodes = 9 periods)
_FIRDARIA_DAY = [
    ("Sun", 10), ("Venus", 8), ("Mercury", 13), ("Moon", 9),
    ("Saturn", 11), ("Jupiter", 12), ("Mars", 7),
    ("North Node", 3), ("South Node", 2),
]
_FIRDARIA_NIGHT = [
    ("Moon", 9), ("Saturn", 11), ("Jupiter", 12), ("Mars", 7),
    ("Sun", 10), ("Venus", 8), ("Mercury", 13),
    ("North Node", 3), ("South Node", 2),
]


def firdaria(birth: BirthData) -> list[dict]:
    """Firdaria: medieval planetary period system.

    Returns all major periods from birth to ~75 years.
    """
    pos = compute_positions(birth)
    houses = compute_houses(birth)
    sun_house = houses.house_of(pos["Sun"].longitude)
    is_day = sun_house in {7, 8, 9, 10, 11, 12}

    sequence = _FIRDARIA_DAY if is_day else _FIRDARIA_NIGHT
    total_cycle = sum(d for _, d in sequence)  # 75 years

    periods: list[dict] = []
    current_age = 0
    for planet, duration in sequence:
        if current_age > 100:
            break
        periods.append({
            "ruler": planet,
            "start_age": current_age,
            "end_age": current_age + duration,
            "duration_years": duration,
            "sub_periods_count": duration,  # each year has a sub-ruler
        })
        current_age += duration

    return periods


# ── 3. progressions ─────────────────────────────────────────────────────────

def tertiary_progressions(birth: BirthData, target_year: int) -> dict:
    """Tertiary progressions: 1 day = 1 lunar month (~27.3 days).

    Progressed date = birth date + (elapsed days / 27.321661) days.
    """
    birth_jd = birth.julian_day()
    elapsed_days = (target_year - int(birth.date[:4])) * 365.25
    prog_days = elapsed_days / 27.321661  # sidereal month
    prog_jd = birth_jd + prog_days

    y, m, d, h = swe.revjul(prog_jd)
    prog_birth = BirthData(
        date=f"{y}-{m:02d}-{d:02d}",
        time=f"{int(h):02d}:{int((h-int(h))*60):02d}:00",
        lat=birth.lat, lon=birth.lon, tz="UTC",
    )
    prog_pos = compute_positions(prog_birth)
    prog_houses = compute_houses(prog_birth)

    return {
        "type": "tertiary",
        "target_year": target_year,
        "progressed_date": f"{y}-{m:02d}-{d:02d}",
        "progressed_positions": prog_pos,
        "progressed_houses": prog_houses,
    }


def minor_progressions(birth: BirthData, target_year: int) -> dict:
    """Minor progressions: 1 day = 1 solar month (~30.44 days).

    Progressed date = birth date + (elapsed days / 30.4375) days.
    """
    birth_jd = birth.julian_day()
    elapsed_days = (target_year - int(birth.date[:4])) * 365.25
    prog_days = elapsed_days / 30.4375
    prog_jd = birth_jd + prog_days

    y, m, d, h = swe.revjul(prog_jd)
    prog_birth = BirthData(
        date=f"{y}-{m:02d}-{d:02d}",
        time=f"{int(h):02d}:{int((h-int(h))*60):02d}:00",
        lat=birth.lat, lon=birth.lon, tz="UTC",
    )
    prog_pos = compute_positions(prog_birth)
    prog_houses = compute_houses(prog_birth)

    return {
        "type": "minor",
        "target_year": target_year,
        "progressed_date": f"{y}-{m:02d}-{d:02d}",
        "progressed_positions": prog_pos,
        "progressed_houses": prog_houses,
    }


def symbolic_directions(birth: BirthData, target_age: float) -> dict:
    """Symbolic directions: 1° = 1 year.

    Move all positions forward by target_age degrees.
    """
    pos = compute_positions(birth)
    directed = {
        name: _norm(p.longitude + target_age)
        for name, p in pos.items()
    }
    return {
        "type": "symbolic",
        "target_age": target_age,
        "directed_positions": directed,
    }


# ── 4. primary directions ───────────────────────────────────────────────────

def primary_directions(birth: BirthData, target_age: float) -> dict:
    """Primary directions (Placidus semi-arc method, simplified).

    Move ASC by target_age degrees along the ecliptic; recompute houses
    for that "directed" ASC to get the directed positions.
    """
    houses = compute_houses(birth)
    directed_asc = _norm(houses.ascendant + target_age)
    directed_mc = _norm(houses.mc + target_age)

    return {
        "type": "primary",
        "method": "placidus_semi_arc",
        "target_age": target_age,
        "directed_asc": directed_asc,
        "directed_asc_sign": SIGNS[int(directed_asc // 30) % 12],
        "directed_mc": directed_mc,
        "directed_mc_sign": SIGNS[int(directed_mc // 30) % 12],
    }


# ── 5. lunar return ─────────────────────────────────────────────────────────

def lunar_return(birth: BirthData, year: int, month: int | None = None) -> dict:
    """Find the lunar return date/time for a given year.

    Searches for when transiting Moon longitude = natal Moon longitude.
    """
    natal_pos = compute_positions(birth)
    natal_moon_lon = natal_pos["Moon"].longitude

    # Start searching from beginning of target year (or month)
    if month:
        search_jd = swe.julday(year, month, 1, 0.0)
    else:
        search_jd = swe.julday(year, 1, 1, 0.0)

    return_jd = _find_planet_return(search_jd, swe.MOON, natal_moon_lon)

    dt = _jd_to_datetime(return_jd)
    ret_pos = compute_positions(BirthData(
        date=dt.strftime("%Y-%m-%d"),
        time=dt.strftime("%H:%M:%S"),
        lat=birth.lat, lon=birth.lon, tz="UTC",
    ))
    ret_houses = compute_houses(BirthData(
        date=dt.strftime("%Y-%m-%d"),
        time=dt.strftime("%H:%M:%S"),
        lat=birth.lat, lon=birth.lon, tz="UTC",
    ))

    return {
        "return_date_utc": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "return_jd": return_jd,
        "natal_moon_longitude": round(natal_moon_lon, 4),
        "return_positions": ret_pos,
        "return_houses": ret_houses,
    }


def solar_return(birth: BirthData, year: int) -> dict:
    """Solar return: when transiting Sun returns to natal Sun longitude.

    Delegates to western.solar_return if available, otherwise computes here.
    """
    natal_pos = compute_positions(birth)
    natal_sun_lon = natal_pos["Sun"].longitude

    search_jd = swe.julday(year, 1, 1, 0.0)
    return_jd = _find_planet_return(search_jd, swe.SUN, natal_sun_lon)

    dt = _jd_to_datetime(return_jd)
    ret_pos = compute_positions(BirthData(
        date=dt.strftime("%Y-%m-%d"),
        time=dt.strftime("%H:%M:%S"),
        lat=birth.lat, lon=birth.lon, tz="UTC",
    ))
    ret_houses = compute_houses(BirthData(
        date=dt.strftime("%Y-%m-%d"),
        time=dt.strftime("%H:%M:%S"),
        lat=birth.lat, lon=birth.lon, tz="UTC",
    ))

    return {
        "return_date_utc": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "return_jd": return_jd,
        "natal_sun_longitude": round(natal_sun_lon, 4),
        "return_positions": ret_pos,
        "return_houses": ret_houses,
    }


def planetary_return(birth: BirthData, planet: str, year: int) -> dict:
    """Return of any planet to its natal longitude."""
    natal_pos = compute_positions(birth)
    natal_lon = natal_pos[planet].longitude
    pid = PLANETS[planet]

    search_jd = swe.julday(year, 1, 1, 0.0)
    return_jd = _find_planet_return(search_jd, pid, natal_lon)

    dt = _jd_to_datetime(return_jd)
    return {
        "planet": planet,
        "return_date_utc": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "natal_longitude": round(natal_lon, 4),
    }


def _find_planet_return(search_jd: float, planet_id: int, target_lon: float) -> float:
    """Bisection search for when planet longitude = target_lon."""
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    def lon_diff(jd):
        res, _ = swe.calc_ut(jd, planet_id, flags)
        d = (res[0] - target_lon) % 360
        return d if d <= 180 else d - 360

    # Scan forward in 1-day steps to find sign change
    jd = search_jd
    prev_diff = lon_diff(jd)
    for _ in range(400):  # max ~400 days
        jd += 1.0
        cur_diff = lon_diff(jd)
        if (prev_diff > 0 and cur_diff < 0) or (prev_diff < 0 and cur_diff > 0):
            # Refine with bisection
            lo, hi = jd - 1.0, jd
            for _ in range(30):
                mid = (lo + hi) / 2
                mid_diff = lon_diff(mid)
                if abs(mid_diff) < 0.0001:
                    return mid
                if (lon_diff(lo) > 0) != (mid_diff > 0):
                    hi = mid
                else:
                    lo = mid
            return (lo + hi) / 2
        prev_diff = cur_diff

    return jd  # fallback


# ── 6. ingress search ───────────────────────────────────────────────────────

def ingresses(planet: str, from_date: str, to_date: str) -> list[dict]:
    """Find when a planet enters each sign in a date range."""
    pid = PLANETS[planet]
    y, m, d = [int(x) for x in from_date.split("-")]
    jd_start = swe.julday(y, m, d, 0.0)
    y2, m2, d2 = [int(x) for x in to_date.split("-")]
    jd_end = swe.julday(y2, m2, d2, 0.0)

    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    results: list[dict] = []
    jd = jd_start
    prev_sign = -1

    while jd < jd_end:
        res, _ = swe.calc_ut(jd, pid, flags)
        cur_sign = int(res[0] // 30) % 12
        if prev_sign >= 0 and cur_sign != prev_sign:
            # Refine the exact crossing
            crossing_jd = _refine_crossing(jd - 1, jd, pid, prev_sign * 30.0, (prev_sign + 1) * 30.0)
            dt = _jd_to_datetime(crossing_jd)
            results.append({
                "date_utc": dt.strftime("%Y-%m-%d %H:%M"),
                "planet": planet,
                "from_sign": SIGNS[prev_sign],
                "to_sign": SIGNS[cur_sign],
            })
        prev_sign = cur_sign
        jd += 0.5  # check every 12 hours

    return results


def _refine_crossing(jd_lo: float, jd_hi: float, planet_id: int, lo_bound: float, hi_bound: float) -> float:
    """Bisection to find exact sign crossing."""
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    for _ in range(30):
        mid = (jd_lo + jd_hi) / 2
        res, _ = swe.calc_ut(mid, planet_id, flags)
        lon = res[0] % 360
        # Determine which side of the boundary we're on
        if abs(lon - hi_bound) < abs(lon - lo_bound):
            jd_hi = mid
        else:
            jd_lo = mid
    return (jd_lo + jd_hi) / 2


# ── 7. retrograde periods ───────────────────────────────────────────────────

def retrograde_periods(planet: str, from_date: str, to_date: str) -> list[dict]:
    """Find retrograde periods (speed sign changes) in a date range."""
    pid = PLANETS[planet]
    y, m, d = [int(x) for x in from_date.split("-")]
    jd_start = swe.julday(y, m, d, 0.0)
    y2, m2, d2 = [int(x) for x in to_date.split("-")]
    jd_end = swe.julday(y2, m2, d2, 0.0)

    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    results: list[dict] = []
    jd = jd_start
    prev_speed = None
    station_start = None

    while jd < jd_end:
        res, _ = swe.calc_ut(jd, pid, flags)
        speed = res[3]
        if prev_speed is not None:
            if prev_speed > 0 and speed <= 0:
                station_start = jd
                # Find exact station point
                stat_jd = _refine_station(jd - 1, jd, pid)
                dt = _jd_to_datetime(stat_jd)
                results.append({
                    "type": "retrograde_start",
                    "date_utc": dt.strftime("%Y-%m-%d %H:%M"),
                    "planet": planet,
                    "longitude": round(res[0], 4),
                    "sign": SIGNS[int(res[0] // 30) % 12],
                })
            elif prev_speed <= 0 and speed > 0:
                stat_jd = _refine_station(jd - 1, jd, pid)
                dt = _jd_to_datetime(stat_jd)
                res2, _ = swe.calc_ut(stat_jd, pid, flags)
                results.append({
                    "type": "retrograde_end",
                    "date_utc": dt.strftime("%Y-%m-%d %H:%M"),
                    "planet": planet,
                    "longitude": round(res2[0], 4),
                    "sign": SIGNS[int(res2[0] // 30) % 12],
                })
        prev_speed = speed
        jd += 0.5

    return results


def _refine_station(jd_lo: float, jd_hi: float, planet_id: int) -> float:
    """Bisection to find exact station (speed=0)."""
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    for _ in range(30):
        mid = (jd_lo + jd_hi) / 2
        res, _ = swe.calc_ut(mid, planet_id, flags)
        speed = res[3]
        if abs(speed) < 0.0001:
            return mid
        # Determine direction
        res_lo, _ = swe.calc_ut(jd_lo, planet_id, flags)
        if (res_lo[3] > 0) != (speed > 0):
            jd_hi = mid
        else:
            jd_lo = mid
    return (jd_lo + jd_hi) / 2


# ── 8. eclipses ─────────────────────────────────────────────────────────────

def eclipses(from_date: str, to_date: str) -> list[dict]:
    """Find all solar and lunar eclipses in a date range."""
    y, m, d = [int(x) for x in from_date.split("-")]
    jd_start = swe.julday(y, m, d, 0.0)
    y2, m2, d2 = [int(x) for x in to_date.split("-")]
    jd_end = swe.julday(y2, m2, d2, 0.0)

    results: list[dict] = []

    # Solar eclipses
    jd = jd_start
    while jd < jd_end:
        try:
            res = swe.sol_eclipse_when_glob(jd, swe.FLG_SWIEPH)
            ecl_jd = res[1][0]  # JD of maximum eclipse
            if ecl_jd > jd_end:
                break
            dt = _jd_to_datetime(ecl_jd)
            ecl_flags = res[0]  # eclipse type flags
            ecl_type = _eclipse_type(ecl_flags)
            results.append({
                "type": "solar",
                "date_utc": dt.strftime("%Y-%m-%d %H:%M"),
                "subtype": ecl_type,
                "jd": ecl_jd,
            })
            jd = ecl_jd + 1  # move past this eclipse
        except swe.Error:
            break

    # Lunar eclipses
    jd = jd_start
    while jd < jd_end:
        try:
            res = swe.lun_eclipse_when(jd, swe.FLG_SWIEPH)
            ecl_jd = res[1][0]  # JD of maximum eclipse
            if ecl_jd > jd_end:
                break
            dt = _jd_to_datetime(ecl_jd)
            ecl_flags = res[0]  # eclipse type flags
            ecl_type = _lunar_eclipse_type(ecl_flags)
            results.append({
                "type": "lunar",
                "date_utc": dt.strftime("%Y-%m-%d %H:%M"),
                "subtype": ecl_type,
                "jd": ecl_jd,
            })
            jd = ecl_jd + 1
        except swe.Error:
            break

    results.sort(key=lambda x: x["jd"])
    return results


def _eclipse_type(flags: int) -> str:
    if flags & swe.ECL_TOTAL:
        return "total"
    if flags & swe.ECL_ANNULAR:
        return "annular"
    if flags & swe.ECL_ANNULAR_TOTAL:
        return "annular-total"
    if flags & swe.ECL_PARTIAL:
        return "partial"
    return "hybrid"


def _lunar_eclipse_type(flags: int) -> str:
    if flags & swe.ECL_TOTAL:
        return "total"
    if flags & swe.ECL_PARTIAL:
        return "partial"
    if flags & swe.ECL_PENUMBRAL:
        return "penumbral"
    return "unknown"


# ── 9. transit calendar ─────────────────────────────────────────────────────

def _compute_transit_aspects(natal_pos, transit_pos, orb):
    """Compute aspects between transit and natal positions."""
    from astrologica.western import aspects
    return aspects(transit_pos, natal_pos, orb=orb)


def transit_calendar(
    birth: BirthData,
    year: int,
    month: int,
    major_orb: float = 3.0,
) -> list[dict]:
    """Month-by-month transit calendar: which transiting planets aspect natal.

    Returns one entry per day with applying/separating aspects.
    """
    natal_pos = compute_positions(birth)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    import calendar as cal
    num_days = cal.monthrange(year, month)[1]
    entries: list[dict] = []

    for day in range(1, num_days + 1):
        jd = swe.julday(year, month, day, 12.0)  # noon UTC
        aspects_today: list[dict] = []

        for planet_name, planet_id in PLANETS.items():
            if planet_name in ("Rahu", "Ketu", "Lilith"):
                continue
            try:
                res, _ = swe.calc_ut(jd, planet_id, flags)
            except swe.Error:
                continue
            transit_lon = res[0]
            transit_speed = res[3]

            for natal_name, natal_p in natal_pos.items():
                if natal_name in ("Rahu", "Ketu", "Lilith"):
                    continue
                diff = abs((transit_lon - natal_p.longitude + 180) % 360 - 180)

                for aspect_angle, aspect_name in [
                    (0, "conjunction"), (60, "sextile"), (90, "square"),
                    (120, "trine"), (180, "opposition"),
                ]:
                    orb = abs(diff - aspect_angle)
                    if orb <= major_orb:
                        # Applying or separating?
                        # If transit is faster and behind natal → applying
                        # Simplified: check if angle is closing
                        next_jd = jd + 0.5
                        try:
                            next_res, _ = swe.calc_ut(next_jd, planet_id, flags)
                            next_diff = abs((next_res[0] - natal_p.longitude + 180) % 360 - 180)
                            next_orb = abs(next_diff - aspect_angle)
                            applying = next_orb < orb
                        except swe.Error:
                            applying = False

                        aspects_today.append({
                            "transit": planet_name,
                            "natal": natal_name,
                            "aspect": aspect_name,
                            "orb": round(orb, 2),
                            "applying": applying,
                        })

        if aspects_today:
            entries.append({
                "date": f"{year}-{month:02d}-{day:02d}",
                "aspects": aspects_today,
            })

    return entries


# ── 10. forecast calendar ───────────────────────────────────────────────────

def forecast_calendar(
    birth: BirthData,
    year: int,
    month: int,
) -> dict:
    """Forecast calendar combining transits, profections, and progressions.

    Higher-level view: major themes for each week.
    """
    tc = transit_calendar(birth, year, month)

    # Profection for the year
    age = year - int(birth.date[:4])
    prof = profections(birth, target_age=age)

    # Progressed Moon position for the month (secondary progression)
    from astrologica.western import progressions
    prog = progressions(birth, target_date=f"{year}-{month:02d}-15")

    # Compile weekly summary
    weeks: list[dict] = []
    for entry in tc:
        # Count aspects by type
        aspect_counts = {}
        for a in entry["aspects"]:
            key = a["aspect"]
            aspect_counts[key] = aspect_counts.get(key, 0) + 1

        weeks.append({
            "date": entry["date"],
            "aspect_count": len(entry["aspects"]),
            "aspect_breakdown": aspect_counts,
            "applying_count": sum(1 for a in entry["aspects"] if a["applying"]),
        })

    return {
        "year": year,
        "month": month,
        "profection": prof,
        "progressed_moon_sign": SIGNS[prog["progressed_positions"]["Moon"].sign] if "Moon" in prog["progressed_positions"] else None,
        "daily_summary": weeks,
    }
