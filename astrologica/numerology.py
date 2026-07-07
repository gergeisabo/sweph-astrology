"""Numerology engine — Pythagorean, Chaldean, Kabbalistic, and Vedic systems.

All systems compute from a birth date and/or name.
No external dependencies — pure arithmetic.
"""
from __future__ import annotations

# === DIGIT SYSTEMS ===

PYTHAGOREAN = {
    'A': 1, 'J': 1, 'S': 1,
    'B': 2, 'K': 2, 'T': 2,
    'C': 3, 'L': 3, 'U': 3,
    'D': 4, 'M': 4, 'V': 4,
    'E': 5, 'N': 5, 'W': 5,
    'F': 6, 'O': 6, 'X': 6,
    'G': 7, 'P': 7, 'Y': 7,
    'H': 8, 'Q': 8, 'Z': 8,
    'I': 9, 'R': 9,
}

CHALDEAN = {
    'A': 1, 'I': 1, 'J': 1, 'Q': 1, 'Y': 1,
    'B': 2, 'K': 2, 'R': 2,
    'C': 3, 'G': 3, 'L': 3, 'S': 3,
    'D': 4, 'M': 4, 'T': 4,
    'E': 5, 'H': 5, 'N': 5, 'X': 5,
    'U': 6, 'V': 6, 'W': 6,
    'O': 7, 'Z': 7,
    'F': 8, 'P': 8,
}

# Kabbalistic (Hebrew gematria mapping for Latin letters)
KABBALISTIC = {
    'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8, 'I': 9,
    'J': 600, 'K': 10, 'L': 20, 'M': 30, 'N': 40, 'O': 50, 'P': 60, 'Q': 70,
    'R': 80, 'S': 90, 'T': 100, 'U': 200, 'V': 700, 'W': 900, 'X': 300,
    'Y': 400, 'Z': 500,
}

SYSTEMS = {
    "pythagorean": PYTHAGOREAN,
    "chaldean": CHALDEAN,
    "kabbalistic": KABBALISTIC,
}

# === VEDIC NUMEROLOGY ===
# In Vedic numerology, numbers 1-9 map to planets:
# 1=Sun, 2=Moon, 3=Jupiter, 4=Rahu(Uranus), 5=Mercury, 6=Venus, 7=Ketu(Neptune),
# 8=Saturn, 9=Mars
VEDIC_PLANETS = {
    1: "Sun", 2: "Moon", 3: "Jupiter", 4: "Rahu",
    5: "Mercury", 6: "Venus", 7: "Ketu", 8: "Saturn", 9: "Mars",
}

MEANINGS = {
    1: {"title": "The Leader", "traits": "independent, original, pioneering, ambitious"},
    2: {"title": "The Peacemaker", "traits": "diplomatic, sensitive, cooperative, harmonious"},
    3: {"title": "The Communicator", "traits": "creative, expressive, social, optimistic"},
    4: {"title": "The Builder", "traits": "practical, disciplined, reliable, hardworking"},
    5: {"title": "The Freedom Seeker", "traits": "adventurous, versatile, dynamic, curious"},
    6: {"title": "The Nurturer", "traits": "responsible, loving, protective, healing"},
    7: {"title": "The Seeker", "traits": "analytical, spiritual, introspective, wise"},
    8: {"title": "The Powerhouse", "traits": "ambitious, authoritative, business-oriented, material"},
    9: {"title": "The Humanitarian", "traits": "compassionate, idealistic, selfless, artistic"},
    11: {"title": "Master Intuitive", "traits": "visionary, inspirational, sensitive, idealistic"},
    22: {"title": "Master Builder", "traits": "practical visionary, large-scale achievements"},
    33: {"title": "Master Teacher", "traits": "selfless service, healing, spiritual guidance"},
}


def _reduce(n: int, keep_master: bool = True) -> int:
    """Reduce a number to a single digit, optionally preserving master numbers 11, 22, 33."""
    while n > 9:
        if keep_master and n in (11, 22, 33):
            return n
        n = sum(int(d) for d in str(n))
    return n


def life_path_number(date_str: str) -> int:
    """Life Path Number from birth date (YYYY-MM-DD).

    Sum all digits of the full date, reduce to single digit (keeping master numbers).
    """
    digits = [int(c) for c in date_str if c.isdigit()]
    return _reduce(sum(digits))


def birthday_number(date_str: str) -> int:
    """Birthday Number from the day of birth."""
    day = int(date_str.split("-")[2])
    return _reduce(day)


def attitude_number(date_str: str) -> int:
    """Attitude Number = month + day, reduced."""
    parts = date_str.split("-")
    month, day = int(parts[1]), int(parts[2])
    return _reduce(month + day)


def personal_year(date_str: str, current_year: int) -> int:
    """Personal Year Number for a given year."""
    parts = date_str.split("-")
    month, day = int(parts[1]), int(parts[2])
    return _reduce(month + day + current_year)


def name_number(name: str, system: str = "pythagorean") -> int:
    """Expression / Destiny Number from full name."""
    table = SYSTEMS[system]
    total = sum(table.get(c.upper(), 0) for c in name if c.isalpha())
    return _reduce(total)


def soul_urge_number(name: str, system: str = "pythagorean") -> int:
    """Soul Urge (Heart's Desire) — vowels only."""
    table = SYSTEMS[system]
    vowels = set("AEIOU")
    total = sum(table.get(c.upper(), 0) for c in name if c.upper() in vowels and c.isalpha())
    return _reduce(total)


def personality_number(name: str, system: str = "pythagorean") -> int:
    """Personality Number — consonants only."""
    table = SYSTEMS[system]
    vowels = set("AEIOU")
    total = sum(table.get(c.upper(), 0) for c in name if c.upper() not in vowels and c.isalpha())
    return _reduce(total)


def vedic_number(date_str: str) -> dict:
    """Vedic numerology (also called Indian or Vedic Lo Shu)."""
    lp = life_path_number(date_str)
    return {
        "root_number": lp,
        "planet": VEDIC_PLANETS.get(lp, "Unknown"),
        "meaning": MEANINGS.get(lp, {}),
    }


def full_profile(name: str, date_str: str, system: str = "pythagorean") -> dict:
    """Complete numerological profile."""
    lp = life_path_number(date_str)
    return {
        "life_path": lp,
        "life_path_meaning": MEANINGS.get(lp, {}),
        "birthday": birthday_number(date_str),
        "attitude": attitude_number(date_str),
        "expression": name_number(name, system),
        "soul_urge": soul_urge_number(name, system),
        "personality": personality_number(name, system),
        "vedic": vedic_number(date_str),
        "system": system,
    }
