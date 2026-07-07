"""Vedic (Jyotish) sidereal astrology engine.

Built on :mod:`astrologica.core`. All longitudes are SIDEREAL (Lahiri ayanamsa).
Use::

    from astrologica.core import BirthData, compute_positions, compute_houses
    from astrologica.vedic import nakshatra, vimshottari_dasha, varga_chart, yogas

    birth = BirthData("1991-02-15", "17:45:00", 48.2264, 22.0847, "Europe/Budapest")
    pos   = compute_positions(birth, sidereal=True, ayanamsa="lahiri")
    moon_nak = nakshatra(pos["Moon"].longitude)

Reference chart (Gergely, Kisvárda 1991-02-15 17:45 CET, Lahiri):
    Sun     Aquarius 2°46'   (302.76°)  Dhanishtha pada 3
    Moon    Aquarius 14°10'  (314.17°)  Shatabhisha pada 3
    Jupiter Cancer 12°35' R  (102.58°)  exalted
    Saturn  Capricorn 7°16'  (277.27°)  domicile
    Lagna   Leo 13°23'
    Ayanamsa 23°44' (23.7331°)
"""

from __future__ import annotations

from datetime import timedelta
from typing import Dict, List

from astrologica.core import (
    BirthData,
    Houses,
    PlanetPosition,
    compute_houses,
    compute_positions,
    get_ayanamsa,
    SIGNS,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NAK_SPAN = 13.333333333333334  # 13°20' = 13 + 20/60
PADA_SPAN = 3.3333333333333335  # 3°20'  = 3  + 20/60

NAK_NAMES: List[str] = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishtha", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

# Nakshatra rulers cycle Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn,
# Mercury — repeated exactly 3 times across the 27 nakshatras.
NAK_RULERS: List[str] = (
    ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    * 3
)

NAK_DEITIES: List[str] = [
    "Ashwini Kumaras", "Yama", "Agni", "Brahma", "Soma",
    "Rudra", "Aditi", "Brihaspati", "Nagas", "Pitris",
    "Bhaga", "Aryaman", "Savitar", "Vishvakarma", "Vayu",
    "Indragni", "Mitra", "Indra", "Nirriti", "Apas",
    "Vishvedevas", "Brahma", "Vasus", "Varuna", "Aja Ekapada",
    "Ahirbudhnya", "Pushan",
]

# Vimshottari dasha durations in years (total = 120).
VIM_DURATIONS: Dict[str, float] = {
    "Ketu": 7.0, "Venus": 20.0, "Sun": 6.0, "Moon": 10.0, "Mars": 7.0,
    "Rahu": 18.0, "Jupiter": 16.0, "Saturn": 19.0, "Mercury": 17.0,
}
# Vimshottari cyclic order starting from Ketu.
VIM_ORDER: List[str] = [
    "Ketu", "Venus", "Sun", "Moon", "Mars",
    "Rahu", "Jupiter", "Saturn", "Mercury",
]

# Ashtottari dasha durations in years (total = 108).
ASH_DURATIONS: Dict[str, float] = {
    "Sun": 6.0, "Moon": 15.0, "Mars": 8.0, "Rahu": 17.0,
    "Jupiter": 18.0, "Saturn": 10.0, "Mercury": 17.0, "Venus": 17.0,
}
ASH_ORDER: List[str] = [
    "Sun", "Moon", "Mars", "Rahu", "Jupiter",
    "Saturn", "Mercury", "Venus",
]

# Vimshottari nakshatra-ruler → starting nakshatra index (0-based) for the
# lord's segment (used to compute sub-periods if needed).
SIGN_QUALITY = {  # 0=movable, 1=fixed, 2=dual (mod 3 of sign index)
    0: 0, 1: 1, 2: 2, 3: 0, 4: 1, 5: 2,
    6: 0, 7: 1, 8: 2, 9: 0, 10: 1, 11: 2,
}

# ---------------------------------------------------------------------------
# Nakshatra
# ---------------------------------------------------------------------------

def nakshatra(longitude: float) -> dict:
    """Return nakshatra data for a sidereal longitude.

    Parameters
    ----------
    longitude:
        Sidereal ecliptic longitude in degrees (0–360).

    Returns
    -------
    dict with keys: ``number`` (1-27), ``name``, ``pada`` (1-4), ``ruler``,
    ``deity``, ``degree_in_nakshatra``.
    """
    lon = longitude % 360.0
    idx = int(lon / NAK_SPAN) % 27           # 0-based nakshatra index
    start = idx * NAK_SPAN                    # start longitude of nakshatra
    deg_in_nak = lon - start                  # 0 .. 13.333
    pada = int(deg_in_nak / PADA_SPAN) + 1    # 1..4
    return {
        "number": idx + 1,
        "name": NAK_NAMES[idx],
        "pada": pada,
        "ruler": NAK_RULERS[idx],
        "deity": NAK_DEITIES[idx],
        "degree_in_nakshatra": round(deg_in_nak, 4),
    }


# ---------------------------------------------------------------------------
# Dasha systems
# ---------------------------------------------------------------------------

def _add_years(start_dt, years: float):
    """Add a fractional number of years to a datetime using 365.25-day years.

    (dateutil.relativedelta is not available in this environment, so we use a
    fixed Julian-year approximation — standard for dasha date computation.)
    """
    return start_dt + timedelta(days=years * 365.25)


def _dasha_sequence(
    birth: BirthData,
    body_longitude: float,
    order: List[str],
    durations: Dict[str, float],
    use_pada_offset: bool,
) -> List[dict]:
    """Compute a dasha sequence.

    Parameters
    ----------
    use_pada_offset:
        False → Vimshottari style: balance of dasha from the Moon's nakshatra
        ruler (uses remaining degrees in the nakshatra).
        True  → Ashtottari style: starts from the Sun's nakshatra *pada*
        number; balance computed within the pada.
    """
    nak = nakshatra(body_longitude)
    if use_pada_offset:
        # Ashtottari: the starting lord index in ASH_ORDER is (pada - 1).
        start_idx = (nak["pada"] - 1) % len(order)
        # Pada span = 3°20'; balance within the pada.
        pada_start = (nak["number"] - 1) * NAK_SPAN + (nak["pada"] - 1) * PADA_SPAN
        deg_into_pada = (body_longitude % 360.0) - pada_start
        deg_into_pada %= PADA_SPAN
        balance_frac = 1.0 - (deg_into_pada / PADA_SPAN)
        first_lord = order[start_idx]
        first_dur = durations[first_lord]
        balance_years = balance_frac * first_dur
    else:
        # Vimshottari: the starting lord is the nakshatra ruler.
        ruler = nak["ruler"]
        start_idx = order.index(ruler)
        balance_frac = 1.0 - (nak["degree_in_nakshatra"] / NAK_SPAN)
        first_lord = order[start_idx]
        first_dur = durations[first_lord]
        balance_years = balance_frac * first_dur

    entries: List[dict] = []
    start_dt = birth.to_utc()
    n = len(order)

    # First (partial) period.
    end_dt = _add_years(start_dt, balance_years)
    entries.append({
        "lord": first_lord,
        "start_date": start_dt,
        "end_date": end_dt,
        "duration_years": round(balance_years, 4),
    })
    cursor = end_dt

    # Remaining full periods.
    for i in range(1, n):
        lord = order[(start_idx + i) % n]
        dur = durations[lord]
        nxt = _add_years(cursor, dur)
        entries.append({
            "lord": lord,
            "start_date": cursor,
            "end_date": nxt,
            "duration_years": dur,
        })
        cursor = nxt

    return entries


def vimshottari_dasha(birth: BirthData, moon_longitude: float) -> List[dict]:
    """Compute the 120-year Vimshottari Dasha sequence.

    Starts from the Moon's nakshatra ruler; the first period is the
    proportional *balance of dasha* at birth.
    """
    return _dasha_sequence(
        birth, moon_longitude, VIM_ORDER, VIM_DURATIONS, use_pada_offset=False
    )


def ashtottari_dasha(birth: BirthData, sun_longitude: float) -> List[dict]:
    """Compute the 108-year Ashtottari Dasha sequence.

    Eight planets (no Ketu). Starts from the Sun's nakshatra pada number.
    """
    return _dasha_sequence(
        birth, sun_longitude, ASH_ORDER, ASH_DURATIONS, use_pada_offset=True
    )


# ---------------------------------------------------------------------------
# Divisional (varga) charts
# ---------------------------------------------------------------------------

def _navamsa_sign(lon: float) -> int:
    """Compute the Navamsa (D9) sign index for a longitude."""
    sign = int(lon // 30) % 12
    deg = lon % 30
    part = int(deg / PADA_SPAN)  # 0..8
    quality = SIGN_QUALITY[sign]
    if quality == 0:       # movable — count from same sign
        base = sign
    elif quality == 1:     # fixed — count from 9th sign
        base = (sign + 8) % 12
    else:                  # dual — count from 5th sign
        base = (sign + 4) % 12
    return (base + part) % 12


def _drekkana_sign(lon: float) -> int:
    """D3 Drekkana: each sign split into 3 parts of 10°.
    Part 1 → same sign, part 2 → 5th sign, part 3 → 9th sign (Aries-based
    counting — the standard Parashara rule).
    """
    sign = int(lon // 30) % 12
    deg = lon % 30
    part = int(deg // 10)  # 0,1,2
    offset = part * 4
    return (sign + offset) % 12


def _varga_sign_for_num(lon: float, varga_num: int) -> int:
    """Return the sign index for a planet in a given divisional chart.

    Implements the standard Parashara varga formulas for D1–D60.
    """
    sign = int(lon // 30) % 12
    deg = lon % 30

    if varga_num == 1:   # Rashi
        return sign
    if varga_num == 2:   # Hora — odd/even sign halves
        # Odd signs: 0–15° Sun, 15–30° Moon (sign index preserved)
        return sign
    if varga_num == 3:   # Drekkana
        return _drekkana_sign(lon)
    if varga_num == 4:   # Chaturthamsa — 4 parts of 7°30'
        part = int(deg / 7.5)
        return (sign + part) % 12
    if varga_num == 7:   # Saptamamsa — 7 parts of 4°17'8.57"
        part = int(deg / (30.0 / 7))
        # Odd signs count from sign itself; even signs from 7th sign.
        base = sign if sign % 2 == 0 else (sign + 6) % 12
        return (base + part) % 12
    if varga_num == 9:   # Navamsa
        return _navamsa_sign(lon)
    if varga_num == 10:  # Dashamamsa — 10 parts of 3°
        part = int(deg / 3.0)
        # Count from sign for odd signs, from 9th for even signs.
        base = sign if sign % 2 == 0 else (sign + 8) % 12
        return (base + part) % 12
    if varga_num == 12:  # Dvadasamsa — 12 parts of 2°30'
        part = int(deg / 2.5)
        return (sign + part) % 12
    if varga_num == 16:  # Shodasamsa — 16 parts of 1°52'30"
        part = int(deg / (30.0 / 16))
        # Count from Aries, Leo, Sagittarius (movable signs of each element).
        base = (sign - (sign % 4))  # 0, 4, 8 → Aries, Leo, Sag
        return (base + part) % 12
    if varga_num == 20:  # Vimsamsa — 20 parts of 1°30'
        part = int(deg / 1.5)
        # Odd signs count from Aries; even signs from Sagittarius.
        base = 0 if sign % 2 == 0 else 8
        return (base + part) % 12
    if varga_num == 24:  # Chaturvimsamsa — 24 parts of 1°15'
        part = int(deg / 1.25)
        # Odd signs: count from Leo; even signs: count from Cancer.
        base = 4 if sign % 2 == 0 else 3
        return (base + part) % 12
    if varga_num == 27:  # Bhamsa / Saptavimsamsa — 27 parts of 1°6'40"
        part = int(deg / (30.0 / 27))
        # Count from a fixed sign quadrant.
        base = (sign - (sign % 3))  # 0,3,6,9 → Aries, Cancer, Libra, Cap
        return (base + part) % 12
    if varga_num == 30:  # Trimsamsa — 30 parts of 1°
        part = int(deg / 1.0)
        # Odd signs: count from Aries; even signs: from Libra (traditional).
        base = 0 if sign % 2 == 0 else 6
        return (base + part) % 12
    if varga_num == 40:  # Chatvarimsamsa — 40 parts of 0°45'
        part = int(deg / 0.75)
        # Count from 7th sign of the sign (standard).
        base = (sign + 6) % 12
        return (base + part) % 12
    if varga_num == 45:  # Panchachatvarimsamsa — 45 parts of 0°40'
        part = int(deg / (30.0 / 45))
        # Count from the sign itself.
        return (sign + part) % 12
    if varga_num == 60:  # Shashtiamsa — 60 parts of 0°30'
        part = int(deg / 0.5)
        # Count from the same sign for each pair.
        return (sign + part) % 12

    raise ValueError(f"Unsupported varga number: {varga_num}")


def varga_chart(positions: Dict[str, PlanetPosition], varga_num: int) -> Dict[str, PlanetPosition]:
    """Compute a divisional chart for a set of sidereal positions.

    Parameters
    ----------
    positions:
        Dict of planet name → :class:`PlanetPosition` (sidereal longitudes).
    varga_num:
        Divisional chart number (1, 2, 3, 7, 9, 10, 12, 16, 20, 24, 27, 30,
        40, 45, 60).

    Returns
    -------
    dict mapping planet name → new :class:`PlanetPosition` whose ``longitude``
    is placed at the *start* of the computed varga sign (0° of that sign),
    carrying the sign information. ``latitude``/``speed`` are preserved.
    """
    out: Dict[str, PlanetPosition] = {}
    for name, p in positions.items():
        vsign = _varga_sign_for_num(p.longitude, varga_num)
        out[name] = PlanetPosition(
            name=name,
            longitude=float(vsign * 30),  # place at 0° of the varga sign
            latitude=p.latitude,
            speed=p.speed,
            retrograde=p.retrograde,
        )
    return out


# ---------------------------------------------------------------------------
# Dignities
# ---------------------------------------------------------------------------

EXALTED: Dict[str, int] = {
    "Sun": 0,       # Aries
    "Moon": 1,      # Taurus
    "Mercury": 5,   # Virgo
    "Jupiter": 3,   # Cancer
    "Mars": 9,      # Capricorn
    "Venus": 11,    # Pisces
    "Saturn": 6,    # Libra
}

DOMICILE: Dict[str, List[int]] = {
    "Sun": [4],              # Leo
    "Moon": [1],             # Taurus (Cancer is domicile, see note)
    "Mercury": [2, 5],       # Gemini, Virgo
    "Venus": [1, 6],         # Taurus, Libra
    "Mars": [0, 7],          # Aries, Scorpio
    "Jupiter": [8, 11],      # Sagittarius, Pisces
    "Saturn": [9, 10],       # Capricorn, Aquarius
}
# Correct Moon domicile: Cancer (3).
DOMICILE["Moon"] = [3]


def dignity(planet_name: str, sign_index: int) -> str:
    """Return the Vedic dignity of a planet in a sign.

    Parameters
    ----------
    planet_name:
        One of Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn.
    sign_index:
        Sign index 0–11 (Aries=0 … Pisces=11).

    Returns
    -------
    One of ``"exalted"``, ``"domicile"``, ``"debilitated"``,
    ``"detriment"``, ``"neutral"``.
    """
    if planet_name in EXALTED and sign_index == EXALTED[planet_name]:
        return "exalted"
    if planet_name in DOMICILE and sign_index in DOMICILE[planet_name]:
        return "domicile"
    if planet_name in EXALTED and sign_index == (EXALTED[planet_name] + 6) % 12:
        return "debilitated"
    if planet_name in DOMICILE and sign_index in [
        (d + 6) % 12 for d in DOMICILE[planet_name]
    ]:
        return "detriment"
    return "neutral"


# ---------------------------------------------------------------------------
# Yogas
# ---------------------------------------------------------------------------

def _conjunction(p1: PlanetPosition, p2: PlanetPosition, orb: float = 10.0) -> bool:
    """True if two planets are within ``orb`` degrees of each other."""
    d = abs(p1.longitude - p2.longitude) % 360
    return min(d, 360 - d) <= orb


def _relative_house(from_lon: float, target_lon: float) -> int:
    """Whole-sign house of ``target`` counted from ``from`` (1-based)."""
    return ((int(target_lon // 30) - int(from_lon // 30)) % 12) + 1


def yogas(
    positions: Dict[str, PlanetPosition],
    houses: Houses,
    lagna_sign: int,
) -> List[dict]:
    """Detect classical Vedic yogas.

    Returns a list of dicts with ``name`` and ``description`` keys.
    """
    out: List[dict] = []

    # Need the core planets; bail gracefully if missing.
    def get(name: str) -> PlanetPosition | None:
        return positions.get(name)

    sun, moon = get("Sun"), get("Moon")
    mercury = get("Mercury")
    mars = get("Mars")
    jupiter = get("Jupiter")
    venus = get("Venus")
    saturn = get("Saturn")

    # --- Budhaditya Yoga: Sun + Mercury conjunct -------------------------
    if sun and mercury and _conjunction(sun, mercury, orb=14.0):
        out.append({
            "name": "Budhaditya Yoga",
            "description": "Sun and Mercury conjunct — intellect, fame, wealth.",
        })

    # --- Gajakesari Yoga: Jupiter in kendra (1/4/7/10) from Moon ---------
    if moon and jupiter:
        h = _relative_house(moon.longitude, jupiter.longitude)
        if h in (1, 4, 7, 10):
            out.append({
                "name": "Gajakesari Yoga",
                "description": f"Jupiter in {h}th from Moon — wisdom, virtue, prosperity.",
            })

    # --- Pancha Mahapurusha Yogas ----------------------------------------
    # Planet in its own sign or exaltation AND in a kendra (1/4/7/10 from Lagna).
    def _mahapurusha(planet: PlanetPosition | None, yoga: str) -> None:
        if planet is None:
            return
        h = houses.house_of(planet.longitude)
        if h not in (1, 4, 7, 10):
            return
        dig = dignity(planet.name, planet.sign)
        if dig in ("exalted", "domicile"):
            out.append({
                "name": yoga,
                "description": f"{planet.name} {dig} in kendra house {h}.",
            })

    _mahapurusha(mars, "Ruchaka Yoga")
    _mahapurusha(mercury, "Bhadra Yoga")
    _mahapurusha(jupiter, "Hamsa Yoga")
    _mahapurusha(venus, "Malavya Yoga")
    _mahapurusha(saturn, "Sasa Yoga")

    # --- Chandra-Mangala Yoga: Moon + Mars conjunct ----------------------
    if moon and mars and _conjunction(moon, mars, orb=8.0):
        out.append({
            "name": "Chandra-Mangala Yoga",
            "description": "Moon and Mars conjunct — wealth through enterprise.",
        })

    # --- Kemadruma Yoga: no planets (excl. Sun, Rahu, Ketu) in 2nd/12th
    #     from Moon --------------------------------------------------------
    if moon:
        flanks = {2, 12}
        grahas = ("Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
        present = False
        for gname in grahas:
            g = positions.get(gname)
            if g is None or g is moon:
                continue
            if _relative_house(moon.longitude, g.longitude) in flanks:
                present = True
                break
        if not present:
            out.append({
                "name": "Kemadruma Yoga",
                "description": "No planets in 2nd/12th from Moon — austerity, struggle.",
            })

    return out


# ---------------------------------------------------------------------------
# Doshas
# ---------------------------------------------------------------------------

def doshas(
    positions: Dict[str, PlanetPosition],
    houses: Houses,
) -> List[dict]:
    """Detect classical Vedic doshas (afflictions)."""
    out: List[dict] = []

    mars = positions.get("Mars")
    moon = positions.get("Moon")
    rahu = positions.get("Rahu")
    ketu = positions.get("Ketu")

    # --- Mangal Dosha: Mars in 1, 2, 4, 7, 8, 12 -------------------------
    if mars:
        h = houses.house_of(mars.longitude)
        if h in (1, 2, 4, 7, 8, 12):
            out.append({
                "name": "Mangal Dosha",
                "description": f"Mars in house {h} — marital affliction (Manglik).",
            })

    # --- Kaal Sarpa: all planets on one side of Rahu-Ketu axis -----------
    if rahu and ketu:
        axis = rahu.longitude % 360.0
        grahas = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
        above = 0
        below = 0
        n = 0
        for gn in grahas:
            g = positions.get(gn)
            if g is None:
                continue
            n += 1
            # Angle from Rahu, normalized 0–360.
            rel = (g.longitude - axis) % 360.0
            if 0 < rel < 180:
                above += 1
            elif 180 < rel < 360:
                below += 1
        if n > 0 and (above == n or below == n):
            out.append({
                "name": "Kaal Sarpa Dosha",
                "description": "All planets on one side of the Rahu-Ketu axis.",
            })

    # --- Gand Mool: Moon in junction nakshatras -------------------------
    if moon:
        nak = nakshatra(moon.longitude)
        gand = {"Ashwini", "Ashlesha", "Jyeshtha", "Mula", "Revati"}
        if nak["name"] in gand:
            out.append({
                "name": "Gand Mool Dosha",
                "description": f"Moon in {nak['name']} nakshatra (pada {nak['pada']}).",
            })

    return out


# ---------------------------------------------------------------------------
# Panchang
# ---------------------------------------------------------------------------

# Yoga lord sequence (Sun..Saturn cycled) for the 27 yogas.
_YOGA_LORDS: List[str] = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyana", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti",
]

# Karana names (11 repeating). There are 60 karanas in a lunar month: 7 movable
# (repeating 7×) + 4 fixed at month end. We compute the simpler 7-movable cycle
# for index → name lookup, which is sufficient for a panchang summary.
_MOVABLE_KARANAS: List[str] = [
    "Bava", "Balava", "Kaulava", "Taitila", "Garaja",
    "Vanija", "Vishti",
]
_FIXED_KARANAS: List[str] = ["Shakuni", "Chatushpada", "Naga", "Kimstughna"]


def panchang(birth: BirthData) -> dict:
    """Compute the Vedic panchang (five limbs) for a birth/event.

    Returns
    -------
    dict with keys: ``vara`` (weekday), ``tithi`` (number + name), ``nakshatra``,
    ``yoga`` (number + name), ``karana`` (number + name).
    """
    pos = compute_positions(birth, sidereal=True, ayanamsa="lahiri")
    sun = pos["Sun"].longitude
    moon = pos["Moon"].longitude

    # --- Vara (weekday) -------------------------------------------------
    utc = birth.to_utc()
    # Weekday: Monday=0 .. Sunday=6 in Python; shift to Sunday=0 for Vedic.
    py_wday = utc.weekday()  # Mon=0..Sun=6
    vara_index = (py_wday + 1) % 7   # Sunday=0
    VARA_NAMES = [
        "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
    ]

    # --- Tithi ----------------------------------------------------------
    diff = (moon - sun) % 360.0
    tithi_f = diff / 12.0                       # 1..30 (fractional)
    tithi_num = int(tithi_f) + 1                # 1..30
    paksha = "Shukla" if tithi_num <= 15 else "Krishna"
    tithi_in_paksha = ((tithi_num - 1) % 15) + 1
    _TITHI_NAMES = [
        "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
        "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
        "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi",
        "Purnima",  # index 14 → used for Shukla 15
    ]
    if paksha == "Shukla":
        tithi_name = _TITHI_NAMES[tithi_in_paksha - 1]
        if tithi_in_paksha == 15:
            tithi_name = "Purnima"
    else:
        if tithi_in_paksha == 15:
            tithi_name = "Amavasya"
        else:
            tithi_name = _TITHI_NAMES[tithi_in_paksha - 1]

    # --- Nakshatra (of Moon) --------------------------------------------
    nak = nakshatra(moon)

    # --- Yoga -----------------------------------------------------------
    # Yoga index = ((sun + moon) / 13°20') + 1, mod 27.
    yoga_lon = (sun + moon) % 360.0
    yoga_num = int(yoga_lon / NAK_SPAN) + 1
    if yoga_num > 27:
        yoga_num = 1
    yoga_name = _YOGA_LORDS[yoga_num - 1]

    # --- Karana ---------------------------------------------------------
    # Karana = half a tithi → 60 karanas per month.
    karana_f = diff / 6.0                      # 0..60
    karana_idx = int(karana_f)                 # 0..59
    if karana_idx < 57:
        karana_name = _MOVABLE_KARANAS[karana_idx % 7]
        karana_num = (karana_idx % 7) + 1
    else:
        karana_name = _FIXED_KARANAS[karana_idx - 57]
        karana_num = karana_idx + 1

    return {
        "vara": VARA_NAMES[vara_index],
        "vara_index": vara_index,
        "tithi": {
            "number": tithi_num,
            "name": tithi_name,
            "paksha": paksha,
        },
        "nakshatra": nak,
        "yoga": {
            "number": yoga_num,
            "name": yoga_name,
        },
        "karana": {
            "number": karana_num,
            "name": karana_name,
        },
    }


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def vedic_chart(birth: BirthData) -> dict:
    """One-shot Vedic chart: positions + houses + key derived data.

    Returns a dict with ``positions``, ``houses``, ``lagna_sign``,
    ``nakshatra_moon``, ``dignities``, ``yogas``, ``doshas``, ``panchang``.
    """
    pos = compute_positions(birth, sidereal=True, ayanamsa="lahiri")
    hs = compute_houses(birth, system="whole_sign", sidereal=True, ayanamsa="lahiri")
    lagna_sign = int(hs.ascendant // 30) % 12
    return {
        "positions": pos,
        "houses": hs,
        "lagna_sign": lagna_sign,
        "nakshatra_moon": nakshatra(pos["Moon"].longitude),
        "dignities": {
            name: dignity(name, p.sign) for name, p in pos.items()
            if name in EXALTED
        },
        "yogas": yogas(pos, hs, lagna_sign),
        "doshas": doshas(pos, hs),
        "panchang": panchang(birth),
    }
