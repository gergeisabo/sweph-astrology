"""Core ephemeris wrapper and shared data structures.

Every engine (western, vedic, bazi, hd, ...) builds on this module.
API contract — do not break without updating all engines:

    BirthData(date="1991-02-15", time="17:45:00", lat=48.2264, lon=22.0847,
              tz="Europe/Budapest", place="Kisvárda")

    chart = compute_positions(birth)          # tropical longitudes
    chart = compute_positions(birth, sidereal=True, ayanamsa="lahiri")

Returns PlanetPosition dataclasses with .longitude, .latitude, .speed,
.retrograde, .sign (0-11), .degree_in_sign.

Verified reference (Gergely, Kisvárda 1991-02-15 17:45 CET, cross-checked
against Astro Seek to within 1 arc-minute):
    Sun  tropical 302°45'42" (Aquarius 2°45')   sidereal Lahiri: Capricorn ~9°
    Moon tropical 314°09'54" (Aquarius 14°09')  sidereal Lahiri: Aquarius ~20°26'
    Ayanamsa Lahiri 1991-02-15: 23°44' (23.7331°)
"""

from __future__ import annotations

import os
import zoneinfo
from dataclasses import dataclass, field
from datetime import datetime, timezone

import swisseph as swe

# Ephemeris data files live next to the package root.
_EPHE_PATH = os.environ.get(
    "ASTROLOGICA_EPHE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ephe"),
)
swe.set_ephe_path(_EPHE_PATH)

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SIGNS_HU = [
    "Kos", "Bika", "Ikrek", "Rák", "Oroszlán", "Szűz",
    "Mérleg", "Skorpió", "Nyilas", "Bak", "Vízöntő", "Halak",
]

# Planet IDs. Ketu is computed as Rahu + 180°.
PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "Rahu": swe.TRUE_NODE,
    "Chiron": swe.CHIRON,
    "Lilith": swe.MEAN_APOG,
}

AYANAMSAS = {
    "lahiri": swe.SIDM_LAHIRI,
    "raman": swe.SIDM_RAMAN,
    "krishnamurti": swe.SIDM_KRISHNAMURTI,
    "fagan_bradley": swe.SIDM_FAGAN_BRADLEY,
    "yukteshwar": swe.SIDM_YUKTESHWAR,
}

HOUSE_SYSTEMS = {
    "placidus": b"P",
    "koch": b"K",
    "whole_sign": b"W",
    "equal": b"E",
    "campanus": b"C",
    "regiomontanus": b"R",
    "porphyry": b"O",
}


@dataclass
class BirthData:
    """Birth (or event) data. time is local civil time; tz an IANA zone name."""

    date: str  # YYYY-MM-DD
    time: str  # HH:MM or HH:MM:SS
    lat: float
    lon: float
    tz: str = "UTC"
    place: str = ""

    def to_utc(self) -> datetime:
        parts = [int(x) for x in self.time.split(":")]
        while len(parts) < 3:
            parts.append(0)
        local = datetime(
            *[int(x) for x in self.date.split("-")], *parts,
            tzinfo=zoneinfo.ZoneInfo(self.tz),
        )
        return local.astimezone(timezone.utc)

    def julian_day(self) -> float:
        utc = self.to_utc()
        return swe.julday(
            utc.year, utc.month, utc.day,
            utc.hour + utc.minute / 60.0 + utc.second / 3600.0,
        )


@dataclass
class PlanetPosition:
    name: str
    longitude: float  # 0-360, tropical or sidereal depending on request
    latitude: float
    speed: float  # degrees/day in longitude; negative = retrograde
    retrograde: bool
    sign: int = field(init=False)
    degree_in_sign: float = field(init=False)

    def __post_init__(self) -> None:
        self.sign = int(self.longitude // 30) % 12
        self.degree_in_sign = self.longitude % 30

    @property
    def sign_name(self) -> str:
        return SIGNS[self.sign]

    def dms(self) -> str:
        d = int(self.degree_in_sign)
        m_f = (self.degree_in_sign - d) * 60
        m = int(m_f)
        s = int(round((m_f - m) * 60))
        if s == 60:
            s = 0
            m += 1
        return f"{d}\u00b0{m:02d}'{s:02d}\""


@dataclass
class Houses:
    system: str
    cusps: list[float]  # 12 entries, index 0 = 1st house cusp
    ascendant: float
    mc: float

    def house_of(self, longitude: float) -> int:
        """1-based house number for a longitude, honoring the house system."""
        if self.system == "whole_sign":
            asc_sign = int(self.ascendant // 30)
            return ((int(longitude // 30) - asc_sign) % 12) + 1
        for i in range(12):
            start = self.cusps[i]
            end = self.cusps[(i + 1) % 12]
            span = (end - start) % 360
            if (longitude - start) % 360 < span:
                return i + 1
        return 12


def get_ayanamsa(jd: float, name: str = "lahiri") -> float:
    swe.set_sid_mode(AYANAMSAS[name])
    return swe.get_ayanamsa(jd)


def compute_positions(
    birth: BirthData,
    sidereal: bool = False,
    ayanamsa: str = "lahiri",
    include: list[str] | None = None,
) -> dict[str, PlanetPosition]:
    """Compute planet positions.

    sidereal=False: raw tropical longitudes from Swiss Ephemeris (FLG_SWIEPH only).
    sidereal=True:  tropical longitudes with ayanamsa subtracted (MANUAL offset —
                    NOT swe.FLG_SIDEREAL, because that flag applies the correction
                    INSIDE the library and can conflict with set_sid_mode; we want
                    deterministic, explicit subtraction).
    """
    jd = birth.julian_day()
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    # NOTE: do NOT set swe.FLG_SIDEREAL — we subtract ayanamsa manually.

    names = include or list(PLANETS.keys())
    out: dict[str, PlanetPosition] = {}
    ay = get_ayanamsa(jd, ayanamsa) if sidereal else 0.0

    for name in names:
        pid = PLANETS[name]
        try:
            res, _ = swe.calc_ut(jd, pid, flags)
        except swe.Error:
            continue  # e.g. Chiron outside ephemeris file range
        lon = (res[0] - ay) % 360.0 if sidereal else res[0]
        out[name] = PlanetPosition(
            name=name,
            longitude=lon,
            latitude=res[1],
            speed=res[3],
            retrograde=res[3] < 0,
        )
    if "Rahu" in out:
        r = out["Rahu"]
        out["Ketu"] = PlanetPosition(
            name="Ketu",
            longitude=(r.longitude + 180.0) % 360.0,
            latitude=-r.latitude,
            speed=r.speed,
            retrograde=True,
        )
    return out


def compute_houses(
    birth: BirthData,
    system: str = "placidus",
    sidereal: bool = False,
    ayanamsa: str = "lahiri",
) -> Houses:
    jd = birth.julian_day()
    hsys = HOUSE_SYSTEMS[system]
    cusps, ascmc = swe.houses(jd, birth.lat, birth.lon, hsys)
    cusps = list(cusps)
    asc, mc = ascmc[0], ascmc[1]
    if sidereal:
        ay = get_ayanamsa(jd, ayanamsa)
        cusps = [(c - ay) % 360 for c in cusps]
        asc = (asc - ay) % 360
        mc = (mc - ay) % 360
    if system == "whole_sign":
        asc_sign = int(asc // 30)
        cusps = [((asc_sign + i) % 12) * 30.0 for i in range(12)]
    return Houses(system=system, cusps=cusps, ascendant=asc, mc=mc)
