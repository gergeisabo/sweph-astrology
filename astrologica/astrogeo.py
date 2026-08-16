"""Astrogeography and relocation astrology.

Covers: ACG (Astro*Carto*Graphy) lines, local space lines,
geodetic equivalents, parans (paranatellonta), relocation charts.
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
)

# ── helpers ──────────────────────────────────────────────────────────────────

def _norm(lon: float) -> float:
    return lon % 360.0


# ── 1. ACG lines (Astro*Carto*Graphy) ───────────────────────────────────────

def acg_lines(
    birth: BirthData,
    planets: list[str] | None = None,
    step_deg: float = 2.0,
) -> dict[str, list[dict]]:
    """Compute ACG lines: where each planet is conjunct ASC/MC/DSC/IC.

    For each planet, sweep longitudes -180..+180 at the birth LATITUDE,
    computing houses at the birth moment. When a planet's longitude
    matches ASC (0°), MC (90°), DSC (180°), or IC (270°) within step_deg,
    record the longitude as an ACG line point.

    Returns: {planet_name: [{"longitude": float, "angle": "ASC"|"MC"|"DSC"|"IC", ...}]}
    """
    jd = birth.julian_day()
    pos = compute_positions(birth)
    planet_list = planets or [p for p in pos if p not in ("Rahu", "Ketu", "Lilith")]

    results: dict[str, list[dict]] = {}

    for pname in planet_list:
        if pname not in pos:
            continue
        planet_lon = pos[pname].longitude
        lines: list[dict] = []

        # Track crossings for each angle type
        prev_diffs: dict[str, float] = {}

        for lon_deg in range(-180, 181, int(step_deg)):
            # Compute houses at this longitude (birth latitude, birth time)
            cusps, ascmc = swe.houses(jd, birth.lat, lon_deg, b"P")
            asc = ascmc[0]
            mc = ascmc[1]
            dsc = (asc + 180) % 360
            ic = (mc + 180) % 360

            angles = {"ASC": asc, "MC": mc, "DSC": dsc, "IC": ic}

            for angle_name, angle_lon in angles.items():
                diff = (planet_lon - angle_lon + 180) % 360 - 180
                key = angle_name

                if key in prev_diffs:
                    prev = prev_diffs[key]
                    # Sign change = crossing
                    if (prev > 0 and diff <= 0) or (prev < 0 and diff >= 0):
                        # Interpolate exact crossing longitude
                        frac = abs(prev) / (abs(prev) + abs(diff)) if (abs(prev) + abs(diff)) > 0 else 0.5
                        cross_lon = lon_deg - step_deg + frac * step_deg
                        lines.append({
                            "longitude": round(cross_lon, 2),
                            "angle": angle_name,
                            "planet_longitude": round(planet_lon, 4),
                            "sign": SIGNS[int(planet_lon // 30) % 12],
                        })

                prev_diffs[key] = diff

        results[pname] = lines

    return results


# ── 2. local space lines ────────────────────────────────────────────────────

def local_space_lines(birth: BirthData) -> dict[str, dict]:
    """Azimuth direction of each planet from birthplace at birth time.

    Uses swe.azalt to convert ecliptic positions to horizontal coordinates.
    Returns: {planet: {"azimuth": float, "altitude": float, "direction": str}}
    """
    jd = birth.julian_day()
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    geo = (birth.lon, birth.lat, 0)  # [lon, lat, alt]

    results: dict[str, dict] = {}
    for pname, pid in PLANETS.items():
        try:
            res, _ = swe.calc_ut(jd, pid, flags)
            ecl_pos = [res[0], res[1], res[2]]  # lon, lat, dist
            azalt = swe.azalt(jd, 0, geo, 1013.25, 15, ecl_pos)
            azimuth = azalt[0]
            altitude = azalt[1]
            direction = _azimuth_to_direction(azimuth)
            results[pname] = {
                "azimuth": round(azimuth, 2),
                "altitude": round(altitude, 2),
                "direction": direction,
            }
        except swe.Error:
            continue

    return results


def _azimuth_to_direction(az: float) -> str:
    """Convert azimuth degrees to compass direction."""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((az + 11.25) / 22.5) % 16
    return dirs[idx]


# ── 3. geodetic equivalents ─────────────────────────────────────────────────

def geodetic_chart(birth: BirthData) -> dict:
    """Geodetic chart: MC = natal MC longitude mapped to geographic longitude.

    Convention: 0° Cancer = 0° longitude (Greenwich), 0° Aries = 90°E, etc.
    Geodetic MC longitude = natal MC (in degrees east from Greenwich).
    """
    houses = compute_houses(birth)
    mc = houses.mc

    # Geodetic longitude: MC degrees mapped to longitude
    # 0° Aries = 0° longitude, 0° Cancer = 90°E, etc.
    geodetic_lon = mc  # direct mapping

    # Compute houses at geodetic longitude (equator for standard geodetic)
    jd = birth.julian_day()
    cusps, ascmc = swe.houses(jd, 0.0, geodetic_lon, b"P")  # lat=0 (equator)

    return {
        "natal_mc": round(mc, 4),
        "natal_mc_sign": SIGNS[int(mc // 30) % 12],
        "geodetic_longitude": round(geodetic_lon, 4),
        "geodetic_asc": round(ascmc[0], 4),
        "geodetic_mc": round(ascmc[1], 4),
    }


# ── 4. parans (paranatellonta) ──────────────────────────────────────────────

def parans(birth: BirthData) -> list[dict]:
    """Simplified paranatellonta: planets rising/setting/culminating at same time.

    A paran occurs when two planets share the same meridian or horizon
    transit time at the birth latitude. We check if any two planets
    rise/set/culminate within a time orb (default ~2 hours).
    """
    jd = birth.julian_day()
    geo = (birth.lon, birth.lat, 0)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    # Get rise/transit/set times for each planet
    planet_times: dict[str, dict] = {}
    for pname, pid in PLANETS.items():
        if pname in ("Rahu", "Ketu", "Lilith"):
            continue
        try:
            rise = swe.rise_trans(jd, pid, rsmi=swe.CALC_RISE, geopos=geo)[1][0]
            transit = swe.rise_trans(jd, pid, rsmi=swe.CALC_MTRANSIT, geopos=geo)[1][0]
            set_t = swe.rise_trans(jd, pid, rsmi=swe.CALC_SET, geopos=geo)[1][0]
            planet_times[pname] = {
                "rise_jd": rise,
                "transit_jd": transit,
                "set_jd": set_t,
            }
        except (swe.Error, IndexError):
            continue

    # Find pairs that rise/set/culminate within 2 hours (0.083 days)
    orb_days = 2.0 / 24.0
    results: list[dict] = []
    names = sorted(planet_times.keys())

    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for event in ["rise_jd", "transit_jd", "set_jd"]:
                diff_hours = abs(planet_times[a][event] - planet_times[b][event]) * 24
                if diff_hours <= 2.0:
                    event_name = event.replace("_jd", "")
                    results.append({
                        "planet1": a,
                        "planet2": b,
                        "event": event_name,
                        "time_diff_hours": round(diff_hours, 2),
                    })

    return results


# ── 5. relocation chart ─────────────────────────────────────────────────────

def relocation_chart(birth: BirthData, target_lat: float, target_lon: float) -> dict:
    """Relocation chart: natal chart recalculated for a different location.

    Same birth moment (UTC), different geographic coordinates.
    Planetary positions stay the same; houses and angles change.
    """
    # Use same UTC time but different location
    utc = birth.to_utc()
    reloc_birth = BirthData(
        date=utc.strftime("%Y-%m-%d"),
        time=utc.strftime("%H:%M:%S"),
        lat=target_lat,
        lon=target_lon,
        tz="UTC",
    )

    pos = compute_positions(reloc_birth)
    houses = compute_houses(reloc_birth)

    return {
        "original_location": {"lat": birth.lat, "lon": birth.lon, "place": birth.place},
        "relocation_location": {"lat": target_lat, "lon": target_lon},
        "positions": pos,
        "houses": houses,
        "ascendant": round(houses.ascendant, 4),
        "mc": round(houses.mc, 4),
        "asc_sign": SIGNS[int(houses.ascendant // 30) % 12],
        "mc_sign": SIGNS[int(houses.mc // 30) % 12],
    }
