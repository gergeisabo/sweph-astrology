"""Destiny Matrix (Matrix of Destiny) — Ladini method.

A numerological system where each "position" on a grid is derived from the birth date.
The 22 positions correspond to the 22 Major Arcana of Tarot (only 1-22 are used).

Grid layout (3x3 + extra positions):

    [13]  [14]  [15]
    [16]  [17]  [18]     Center (E) = day
    [19]  [20]  [21]

Additional: [22] bottom center, [A] top center = month,
[B] right center = year, [C] left center = year digits sum

Core formula:
  A = month                    (top)
  E = day                      (center)
  B = sum of year digits       (right)
  C = sum of (A + E)           (left)
  D = sum of (E + B)           (bottom-left diagonal)
  F = sum of (A + C)           (top-left diagonal)

All values reduced to 1-22 (no reduction below 22 — the 23rd arcana is not used).
"""
from __future__ import annotations


def _to_arcana(n: int) -> int:
    """Reduce a number to 1-22 range (Major Arcana only)."""
    while n > 22:
        n = sum(int(d) for d in str(n))
    if n == 0:
        n = 22
    return n


ARCANA = {
    1: ("The Magician", "individuality, willpower, initiative, leadership"),
    2: ("The High Priestess", "intuition, diplomacy, receptivity, partnership"),
    3: ("The Empress", "creativity, fertility, communication, self-expression"),
    4: ("The Emperor", "structure, authority, stability, discipline"),
    5: ("The Hierophant", "tradition, teaching, spirituality, conformity"),
    6: ("The Lovers", "love, choices, harmony, relationships"),
    7: ("The Chariot", "movement, will, victory, control"),
    8: ("Strength", "inner power, courage, patience, mastery"),
    9: ("The Hermit", "wisdom, solitude, introspection, guidance"),
    10: ("Wheel of Fortune", "cycles, luck, destiny, change"),
    11: ("Justice", "fairness, truth, balance, law"),
    12: ("The Hanged Man", "sacrifice, perspective, surrender, pause"),
    13: ("Death", "transformation, endings, rebirth, transition"),
    14: ("Temperance", "balance, moderation, healing, blending"),
    15: ("The Devil", "bondage, materialism, temptation, shadow"),
    16: ("The Tower", "disruption, revelation, sudden change, awakening"),
    17: ("The Star", "hope, inspiration, healing, serenity"),
    18: ("The Moon", "illusion, dreams, intuition, subconscious"),
    19: ("The Sun", "joy, success, vitality, clarity"),
    20: ("Judgement", "renewal, awakening, calling, absolution"),
    21: ("The World", "completion, fulfillment, wholeness, integration"),
    22: ("The Fool", "new beginnings, spontaneity, freedom, innocence"),
}


def compute(date_str: str) -> dict:
    """Compute the full Destiny Matrix for a birth date.

    Args:
        date_str: Birth date in YYYY-MM-DD format.

    Returns:
        Dict with all 22+ positions, their arcana number, name, and meaning.
    """
    parts = date_str.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])

    year_sum = sum(int(d) for d in str(year))
    month_sum = sum(int(d) for d in str(month).zfill(2))
    day_sum = sum(int(d) for d in str(day).zfill(2))

    # Core positions
    A = _to_arcana(month_sum)          # top — incoming energy
    E = _to_arcana(day_sum)            # center — self
    B = _to_arcana(year_sum)           # right — outgoing energy

    # Derived positions
    C = _to_arcana(A + E)              # left — comfort zone
    D = _to_arcana(E + B)              # bottom-right — karmic tail
    F = _to_arcana(A + C)              # top-left diagonal
    G = _to_arcana(B + D)              # bottom-right diagonal
    H = _to_arcana(C + D)              # bottom — material
    K = _to_arcana(F + G)              # top — spiritual

    # Additional karmic positions
    love_line = _to_arcana(C + E)      # love/relationships
    money_line = _to_arcana(E + G)     # finances
    creativity = _to_arcana(A + B)     # creative potential

    positions = {
        "A": A, "B": B, "C": C, "D": D, "E": E, "F": F, "G": G, "H": H, "K": K,
        "love": love_line, "money": money_line, "creativity": creativity,
    }

    result = {}
    for key, num in positions.items():
        name, meaning = ARCANA.get(num, ("Unknown", ""))
        result[key] = {"arcana": num, "name": name, "meaning": meaning}

    # Convenience: the center (E) is the most important
    result["center"] = result["E"]
    result["love_line"] = result["love"]
    result["money_line"] = result["money"]

    return result


def describe(energy: int) -> dict:
    """Get the arcana description for a specific number (1-22)."""
    num = _to_arcana(energy)
    name, meaning = ARCANA.get(num, ("Unknown", ""))
    return {"arcana": num, "name": name, "meaning": meaning}
