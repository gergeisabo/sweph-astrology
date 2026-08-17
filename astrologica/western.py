"""Western tropical astrology engine.

All longitudes are TROPICAL (sidereal=False) unless explicitly noted.
Built entirely on astrologica.core for ephemeris calculations.

Functions:
    natal_chart        — full natal chart (planets, houses, aspects, dignities)
    aspects            — Ptolemaic aspects between a set of positions
    essential_dignities— traditional rulership/exaltation/detriment/fall
    transits           — transit-to-natal aspect analysis
    synastry           — cross-chart aspects and house overlays
    solar_return       — chart for the Sun's return to its natal position
    progressions       — secondary progressions (1 day = 1 year)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import swisseph as swe

from astrologica.core import (
    BirthData,
    PlanetPosition,
    compute_positions,
    compute_houses,
    SIGNS,
    get_ayanamsa,
)

__all__ = [
    "natal_chart",
    "aspects",
    "essential_dignities",
    "transits",
    "synastry",
    "solar_return",
    "progressions",
]


# ---------------------------------------------------------------------------
# Traditional rulership tables (sign_index 0=Aries … 11=Pisces)
# ---------------------------------------------------------------------------

DOMICILES: dict[int, str] = {
    0: "Mars",       # Aries
    1: "Venus",      # Taurus
    2: "Mercury",    # Gemini
    3: "Moon",       # Cancer
    4: "Sun",        # Leo
    5: "Mercury",    # Virgo
    6: "Venus",      # Libra
    7: "Mars",       # Scorpio
    8: "Jupiter",    # Sagittarius
    9: "Saturn",     # Capricorn
    10: "Saturn",    # Aquarius (traditional)
    11: "Jupiter",   # Pisces
}

EXALTATIONS: dict[int, str] = {
    0: "Sun",        # Aries
    1: "Moon",       # Taurus
    3: "Jupiter",    # Cancer
    5: "Mercury",    # Virgo
    6: "Saturn",     # Libra
    9: "Mars",       # Capricorn
    11: "Venus",     # Pisces
}

# Pre-computed reverse lookups: planet -> set of sign indices
_DOMICILE_BY_PLANET: dict[str, set[int]] = {}
_DETRIMENT_BY_PLANET: dict[str, set[int]] = {}
_EXALTED_BY_PLANET: dict[str, set[int]] = {}
_FALL_BY_PLANET: dict[str, set[int]] = {}


def _build_reverse_tables() -> None:
    for sign, planet in DOMICILES.items():
        _DOMICILE_BY_PLANET.setdefault(planet, set()).add(sign)
        _DETRIMENT_BY_PLANET.setdefault(planet, set()).add((sign + 6) % 12)
    for sign, planet in EXALTATIONS.items():
        _EXALTED_BY_PLANET.setdefault(planet, set()).add(sign)
        _FALL_BY_PLANET.setdefault(planet, set()).add((sign + 6) % 12)


_build_reverse_tables()


# ---------------------------------------------------------------------------
# Aspect definitions
# ---------------------------------------------------------------------------

ASPECT_ANGLES: dict[str, float] = {
    "conjunction": 0.0,
    "opposition": 180.0,
    "trine": 120.0,
    "square": 90.0,
    "sextile": 60.0,
    "quincunx": 150.0,
    "semisextile": 30.0,
}

DEFAULT_ORBS: dict[str, float] = {
    "conjunction": 8.0,
    "opposition": 8.0,
    "trine": 7.0,
    "square": 7.0,
    "sextile": 6.0,
    "quincunx": 3.0,
    "semisextile": 2.0,
}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _angular_separation(lon1: float, lon2: float) -> float:
    """Shortest arc between two tropical longitudes, result in [0, 180]."""
    diff = abs(lon2 - lon1) % 360.0
    return min(diff, 360.0 - diff)


def _signed_diff(lon1: float, lon2: float) -> float:
    """Signed angular difference (lon2 − lon1) normalised to [−180, 180)."""
    diff = (lon2 - lon1) % 360.0
    if diff >= 180.0:
        diff -= 360.0
    return diff


def _merge_orbs(orbs: dict[str, float] | None) -> dict[str, float]:
    if orbs is None:
        return dict(DEFAULT_ORBS)
    merged = dict(DEFAULT_ORBS)
    merged.update(orbs)
    return merged


def _jd_to_birthdata(jd: float, lat: float, lon: float) -> BirthData:
    """Convert a Julian Day (UT) to a BirthData with tz='UTC'."""
    year, month, day, hour_dec = swe.revjul(jd, swe.GREG_CAL)
    total_sec = hour_dec * 3600.0
    h = int(total_sec // 3600)
    m = int((total_sec % 3600) // 60)
    s = int(round(total_sec % 60))
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        h += 1
    return BirthData(
        date=f"{year:04d}-{month:02d}-{day:02d}",
        time=f"{h:02d}:{m:02d}:{s:02d}",
        lat=lat,
        lon=lon,
        tz="UTC",
    )


def _parse_date_to_utc(value: str | datetime, tz: str = "UTC") -> datetime:
    """Accept 'YYYY-MM-DD', 'YYYY-MM-DD HH:MM:SS', or a datetime; return UTC."""
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    # Handle 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'
    parts = value.strip().replace("T", " ").split(" ")
    date_parts = [int(x) for x in parts[0].split("-")]
    if len(parts) > 1 and ":" in parts[1]:
        time_parts = [int(x) for x in parts[1].split(":")]
        return datetime(date_parts[0], date_parts[1], date_parts[2],
                        time_parts[0], time_parts[1], time_parts[2] if len(time_parts) > 2 else 0,
                        tzinfo=timezone.utc)
    return datetime(date_parts[0], date_parts[1], date_parts[2], tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Aspects
# ---------------------------------------------------------------------------

def aspects(
    positions: dict[str, PlanetPosition],
    orbs: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Compute Ptolemaic aspects between all unique pairs of positions.

    Parameters
    ----------
    positions
        Mapping of name → PlanetPosition (e.g. output of compute_positions).
    orbs
        Optional override for any aspect type.  Missing types fall back to
        DEFAULT_ORBS.

    Returns
    -------
    list of dicts, each::
        {planet1, planet2, type, orb, applying}
    Only the single closest aspect per planet-pair is returned.
    """
    cfg = _merge_orbs(orbs)
    names = list(positions.keys())
    results: list[dict[str, Any]] = []

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            p1 = positions[names[i]]
            p2 = positions[names[j]]
            sep = _angular_separation(p1.longitude, p2.longitude)
            signed = _signed_diff(p1.longitude, p2.longitude)

            best_type: str | None = None
            best_orb = 999.0
            for atype, angle in ASPECT_ANGLES.items():
                o = abs(sep - angle)
                if o <= cfg.get(atype, 0.0) and o < best_orb:
                    best_type = atype
                    best_orb = o

            if best_type is not None:
                # Determine applying / separating from rate of change of |sep|.
                # rate > 0  → separation increasing  → separating for exact orb
                rate = (p2.speed - p1.speed) if signed >= 0 else (p1.speed - p2.speed)
                exact_angle = ASPECT_ANGLES[best_type]
                if rate == 0:
                    applying = False
                elif abs(sep - exact_angle) < 1e-9:
                    applying = True
                else:
                    applying = ((sep - exact_angle) * rate) < 0

                results.append({
                    "planet1": names[i],
                    "planet2": names[j],
                    "type": best_type,
                    "orb": round(best_orb, 4),
                    "applying": applying,
                })

    return results


def _cross_aspects(
    set_a: dict[str, PlanetPosition],
    set_b: dict[str, PlanetPosition],
    orbs: dict[str, float] | None = None,
    key_a: str = "planet1",
    key_b: str = "planet2",
) -> list[dict[str, Any]]:
    """Aspects between two *different* sets of positions (e.g. natal vs transit)."""
    cfg = _merge_orbs(orbs)
    results: list[dict[str, Any]] = []
    for na, pa in set_a.items():
        for nb, pb in set_b.items():
            sep = _angular_separation(pa.longitude, pb.longitude)
            signed = _signed_diff(pa.longitude, pb.longitude)
            best_type: str | None = None
            best_orb = 999.0
            for atype, angle in ASPECT_ANGLES.items():
                o = abs(sep - angle)
                if o <= cfg.get(atype, 0.0) and o < best_orb:
                    best_type = atype
                    best_orb = o
            if best_type is not None:
                rate = (pb.speed - pa.speed) if signed >= 0 else (pa.speed - pb.speed)
                exact_angle = ASPECT_ANGLES[best_type]
                if rate == 0:
                    applying = False
                elif abs(sep - exact_angle) < 1e-9:
                    applying = True
                else:
                    applying = ((sep - exact_angle) * rate) < 0
                results.append({
                    key_a: na,
                    key_b: nb,
                    "type": best_type,
                    "orb": round(best_orb, 4),
                    "applying": applying,
                })
    return results


# ---------------------------------------------------------------------------
# Essential dignities
# ---------------------------------------------------------------------------

def essential_dignities(
    positions: dict[str, PlanetPosition],
) -> dict[str, str | None]:
    """Determine essential dignity for each planet using traditional rulerships.

    Returns
    -------
    Mapping of planet name → highest-ranking dignity label::

        "Domicile"  — planet rules the sign it is in
        "Exalted"   — planet is exalted in the sign
        "Detriment" — planet is in the sign opposite its domicile
        "Fall"      — planet is in the sign opposite its exaltation
        None        — peregrine (no essential dignity)
    """
    result: dict[str, str | None] = {}
    for name, pos in positions.items():
        s = pos.sign
        if name in _DOMICILE_BY_PLANET and s in _DOMICILE_BY_PLANET[name]:
            result[name] = "Domicile"
        elif name in _EXALTED_BY_PLANET and s in _EXALTED_BY_PLANET[name]:
            result[name] = "Exalted"
        elif name in _DETRIMENT_BY_PLANET and s in _DETRIMENT_BY_PLANET[name]:
            result[name] = "Detriment"
        elif name in _FALL_BY_PLANET and s in _FALL_BY_PLANET[name]:
            result[name] = "Fall"
        else:
            result[name] = None
    return result


# ---------------------------------------------------------------------------
# Natal chart
# ---------------------------------------------------------------------------

def natal_chart(
    birth: BirthData,
    house_system: str = "placidus",
) -> dict[str, Any]:
    """Compute a complete Western natal chart.

    Returns a dict with keys:
        ``planets``     — dict[str, PlanetPosition] (tropical)
        ``houses``      — Houses object
        ``aspects``     — list of aspect dicts
        ``dignities``   — dict[str, str | None]
        ``chart_point`` — midpoint of Asc / MC / Sun / Moon (float longitude)
    """
    planets = compute_positions(birth, sidereal=False)
    houses = compute_houses(birth, system=house_system, sidereal=False)
    chart_aspects = aspects(planets)
    dignities = essential_dignities(planets)

    chart_point = (
        houses.ascendant + houses.mc
        + planets["Sun"].longitude + planets["Moon"].longitude
    ) / 4.0 % 360.0

    return {
        "planets": planets,
        "houses": houses,
        "aspects": chart_aspects,
        "dignities": dignities,
        "chart_point": chart_point,
    }


# ---------------------------------------------------------------------------
# Transits
# ---------------------------------------------------------------------------

def transits(
    birth: BirthData,
    transit_date: str | datetime,
    orb: float = 1.0,
) -> dict[str, Any]:
    """Compute transit positions and their aspects to the natal chart.

    Parameters
    ----------
    birth         — natal birth data
    transit_date  — 'YYYY-MM-DD' string or datetime (UTC)
    orb           — uniform orb (degrees) applied to every aspect type

    Returns dict with ``natal_positions``, ``transit_positions``,
    ``transit_date``, and ``aspects`` (list of cross-aspects).
    """
    natal = compute_positions(birth, sidereal=False)

    target_utc = _parse_date_to_utc(transit_date)
    transit_birth = BirthData(
        date=target_utc.strftime("%Y-%m-%d"),
        time=target_utc.strftime("%H:%M:%S"),
        lat=birth.lat,
        lon=birth.lon,
        tz="UTC",
    )
    transit_positions = compute_positions(transit_birth, sidereal=False)

    uniform_orbs = {k: orb for k in DEFAULT_ORBS}
    cross = _cross_aspects(
        transit_positions, natal,
        orbs=uniform_orbs,
        key_a="transit_planet",
        key_b="natal_planet",
    )

    return {
        "natal_positions": natal,
        "transit_positions": transit_positions,
        "transit_date": transit_birth.date,
        "aspects": cross,
    }


# ---------------------------------------------------------------------------
# Synastry
# ---------------------------------------------------------------------------

def synastry(birth1: BirthData, birth2: BirthData) -> dict[str, Any]:
    """Cross-chart analysis between two natal charts.

    Returns dict with ``chart1_planets``, ``chart2_planets``, ``aspects``
    (cross-aspects), and ``house_overlays`` — a mapping of person-2 planet
    name → 1-based house number in person-1's chart.
    """
    chart1 = compute_positions(birth1, sidereal=False)
    chart2 = compute_positions(birth2, sidereal=False)
    houses1 = compute_houses(birth1, sidereal=False)

    cross = _cross_aspects(
        chart1, chart2,
        key_a="planet1",
        key_b="planet2",
    )

    overlays: dict[str, int] = {}
    for name, pos in chart2.items():
        overlays[name] = houses1.house_of(pos.longitude)

    return {
        "chart1_planets": chart1,
        "chart2_planets": chart2,
        "aspects": cross,
        "house_overlays": overlays,
    }


# ---------------------------------------------------------------------------
# Solar Return
# ---------------------------------------------------------------------------

def solar_return(birth: BirthData, year: int) -> dict[str, Any]:
    """Compute the solar-return chart for the given calendar year.

    Finds the exact UT moment the Sun returns to its natal tropical longitude,
    then builds a full chart for that instant at the birth location.

    Returns dict with ``year``, ``datetime`` (str), ``planets``, ``houses``,
    ``natal_sun_longitude`` and ``return_sun_longitude``.
    """
    natal = compute_positions(birth, sidereal=False)
    natal_sun = natal["Sun"].longitude

    birth_utc = birth.to_utc()
    # Start search near the birthday in the target year.
    jd = swe.julday(year, birth_utc.month, birth_utc.day, 12.0)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    for _ in range(30):
        sun_res, _ = swe.calc_ut(jd, swe.SUN, flags)
        diff = (natal_sun - sun_res[0]) % 360.0
        if diff > 180.0:
            diff -= 360.0
        if abs(diff) < 1e-6:          # ~0.0036 arc-seconds
            break
        jd += diff / 0.9856474        # Sun's mean daily motion in °/day

    sr_birth = _jd_to_birthdata(jd, birth.lat, birth.lon)
    sr_planets = compute_positions(sr_birth, sidereal=False)
    sr_houses = compute_houses(sr_birth, sidereal=False)

    return {
        "year": year,
        "datetime": f"{sr_birth.date} {sr_birth.time} UTC",
        "planets": sr_planets,
        "houses": sr_houses,
        "natal_sun_longitude": round(natal_sun, 6),
        "return_sun_longitude": round(sr_planets["Sun"].longitude, 6),
    }


# ---------------------------------------------------------------------------
# Secondary Progressions
# ---------------------------------------------------------------------------

def progressions(
    birth: BirthData,
    target_date: str | datetime,
) -> dict[str, Any]:
    """Compute secondary progressions (1 year of life = 1 day after birth).

    Returns dict with ``target_date``, ``years_elapsed``, ``progressed_positions``
    and ``progressed_houses``.
    """
    birth_utc = birth.to_utc()
    target_utc = _parse_date_to_utc(target_date)

    # Years of life → equivalent days to advance from birth moment.
    years_elapsed = (target_utc - birth_utc).total_seconds() / (365.25 * 86400.0)
    progressed_jd = birth.julian_day() + years_elapsed

    prog_birth = _jd_to_birthdata(progressed_jd, birth.lat, birth.lon)
    progressed = compute_positions(prog_birth, sidereal=False)
    prog_houses = compute_houses(prog_birth, sidereal=False)

    return {
        "target_date": target_utc.strftime("%Y-%m-%d"),
        "years_elapsed": round(years_elapsed, 3),
        "progressed_positions": progressed,
        "progressed_houses": prog_houses,
    }
