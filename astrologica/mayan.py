"""Mayan Calendar system — Tzolkin, Haab, Long Count, Dreamspell.

Pure date arithmetic, no external dependencies.
Reference epoch: August 11, 3114 BCE (Gregorian) — GMT correlation 584283.
"""
from __future__ import annotations
from datetime import date, timedelta

# GMT correlation constant
JDN_OFFSET = 584283

# Tzolkin: 20 day names × 13 numbers = 260 day cycle
TZOLKIN_DAYS = [
    "Imix", "Ik", "Akbal", "Kan", "Chicchan", "Cimi", "Manik", "Lamat",
    "Muluc", "Oc", "Chuen", "Eb", "Ben", "Ix", "Men", "Cib",
    "Caban", "Etznab", "Cauac", "Ahau",
]

# Haab: 18 months × 20 days + 5 Wayeb days = 365
HAAB_MONTHS = [
    "Pop", "Wo", "Sip", "Sotz", "Sek", "Xul", "Yaxkin", "Mol",
    "Chen", "Yax", "Sak", "Keh", "Mak", "Kankin", "Muan", "Pax",
    "Kayab", "Kumku", "Wayeb",
]


def _to_jdn(d: date) -> int:
    """Julian Day Number from date."""
    a = (14 - d.month) // 12
    y = d.year + 4800 - a
    m = d.month + 12 * a - 3
    return d.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def _days_to_date(days: float) -> date:
    """JDN to Gregorian date."""
    return date(1, 1, 1) + timedelta(days=days - 1721426)


def long_count(date_str: str) -> dict:
    """Mayan Long Count for a date (YYYY-MM-DD).

    Returns baktun, katun, tun, uinal, kin.
    """
    parts = [int(x) for x in date_str.split("-")]
    d = date(parts[0], parts[1], parts[2])
    jdn = _to_jdn(d)
    days = jdn - JDN_OFFSET

    baktun = (days // 144000) % 20
    katun = (days % 144000) // 7200
    tun = (days % 7200) // 360
    uinal = (days % 360) // 20
    kin = days % 20

    return {
        "baktun": baktun,
        "katun": katun,
        "tun": tun,
        "uinal": uinal,
        "kin": kin,
        "long_count_str": f"{baktun}.{katun}.{tun}.{uinal}.{kin}",
    }


def tzolkin(date_str: str) -> dict:
    """Tzolkin day (260-day sacred calendar)."""
    parts = [int(x) for x in date_str.split("-")]
    d = date(parts[0], parts[1], parts[2])
    jdn = _to_jdn(d)
    days = jdn - JDN_OFFSET

    # Tzolkin: number 1-13, name 1-20
    tzolkin_num = (days + 3) % 13
    if tzolkin_num == 0:
        tzolkin_num = 13
    tzolkin_day_idx = (days + 19) % 20

    return {
        "number": tzolkin_num,
        "day_name": TZOLKIN_DAYS[tzolkin_day_idx],
        "full": f"{tzolkin_num} {TZOLKIN_DAYS[tzolkin_day_idx]}",
    }


def haab(date_str: str) -> dict:
    """Haab day (365-day solar calendar)."""
    parts = [int(x) for x in date_str.split("-")]
    d = date(parts[0], parts[1], parts[2])
    jdn = _to_jdn(d)
    days = jdn - JDN_OFFSET

    haab_day = (days + 8 + 17 * 20) % 365
    haab_month_idx = haab_day // 20
    haab_day_in_month = haab_day % 20

    # Handle Wayeb (last 5 days)
    if haab_month_idx >= 18:
        haab_month_idx = 18  # Wayeb

    return {
        "day": haab_day_in_month,
        "month": HAAB_MONTHS[min(haab_month_idx, 18)],
        "full": f"{haab_day_in_month} {HAAB_MONTHS[min(haab_month_idx, 18)]}",
    }


def dreamspell(date_str: str) -> dict:
    """Dreamspell Kin (Jose Arguelles' system).

    Note: Dreamspell uses a different correlation than the traditional Long Count.
    This uses the Arguelles/Harmann correlation: July 26, 1987 = 1 Dragon.
    """
    parts = [int(x) for x in date_str.split("-")]
    d = date(parts[0], parts[1], parts[2])

    # Dreamspell epoch: July 26, 1987
    epoch = date(1987, 7, 26)
    days = (d - epoch).days

    # Kin = 1-260
    kin = days % 260
    if kin <= 0:
        kin += 260

    # Dreamspell solar seal (20 seals, same as Tzolkin day names)
    seal_idx = (kin - 1) % 20
    tone = ((kin - 1) % 13) + 1

    return {
        "kin": kin,
        "tone": tone,
        "seal": TZOLKIN_DAYS[seal_idx],
        "full": f"Kin {kin}: {tone} {TZOLKIN_DAYS[seal_idx]}",
    }


def full(date_str: str) -> dict:
    """Complete Mayan calendar reading."""
    return {
        "long_count": long_count(date_str),
        "tzolkin": tzolkin(date_str),
        "haab": haab(date_str),
        "dreamspell": dreamspell(date_str),
    }


def compatibility(date1: str, date2: str) -> dict:
    """Mayan compatibility (Tzolkin affinity)."""
    t1 = tzolkin(date1)
    t2 = tzolkin(date2)
    # Simple affinity: compare numbers and day names
    num_affinity = abs(t1["number"] - t2["number"])
    name_match = t1["day_name"] == t2["day_name"]
    return {
        "person1": t1["full"],
        "person2": t2["full"],
        "number_affinity": "high" if num_affinity <= 3 else ("medium" if num_affinity <= 7 else "low"),
        "same_seal": name_match,
    }
