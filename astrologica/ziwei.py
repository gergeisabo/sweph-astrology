"""Zi Wei Dou Shu (Purple Star Astrology) engine.

Simplified implementation: 12 palaces, main star placement,
birth data → palace assignments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ── constants ────────────────────────────────────────────────────────────────

PALACES = [
    "Life", "Siblings", "Spouse", "Children", "Wealth", "Health",
    "Travel", "Friends", "Career", "Property", "Fortune", "Parents",
]

MAIN_STARS = [
    "Zi Wei", "Tian Ji", "Tai Yang", "Wu Qu", "Tian Tong", "Lian Zhen",
    "Tian Fu", "Tai Yin", "Tan Lang", "Ju Men", "Tian Xiang", "Tian Liang",
    "Qi Sha", "Po Jun",
]

STEMS = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
BRANCHES = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]

# Five elements for life palace calculation
_FIVE_ELEMENTS = ["Water 2", "Metal 4", "Fire 6", "Earth 8", "Wood 10"]


@dataclass
class ZWPResult:
    """Zi Wei Dou Shu chart result."""
    birth_branch: str      # Earthly Branch of birth hour
    life_palace: int       # Life palace index (0-11)
    palaces: dict[int, str]  # palace_index → palace_name
    star_placements: dict[str, int]  # star_name → palace_index
    element: str           # Five element assignment


def ziwei_chart(
    year_stem: int,
    year_branch: int,
    month: int,
    day: int,
    hour_branch: int,
) -> ZWPResult:
    """Compute Zi Wei Dou Shu chart.

    Args:
        year_stem: 0-9 (Jia=0, Yi=1, ... Gui=9)
        year_branch: 0-11 (Zi=0, Chou=1, ... Hai=11)
        month: 1-12 (lunar month)
        day: 1-30 (lunar day)
        hour_branch: 0-11 (Zi hour=0, Chou=1, ... Hai=11)
    """
    # Life palace position: from birth hour, count forward by birth month
    life_palace = (hour_branch + month - 1) % 12

    # Assign palaces (clockwise from life palace)
    palaces: dict[int, str] = {}
    for i, name in enumerate(PALACES):
        idx = (life_palace + i) % 12
        palaces[idx] = name

    # Five element assignment based on stem + life palace
    element_idx = (year_stem + life_palace) % 5
    element = _FIVE_ELEMENTS[element_idx]

    # Simplified star placement: based on birth data
    # In full ZWDS, star positions depend on birth month, day, hour, and stem
    # This is a simplified lookup based on the life palace and birth data
    star_placements: dict[str, int] = {}

    # Zi Wei star: position depends on birth day and five element
    element_number = int(element.split()[-1])
    ziwei_pos = (life_palace + day - 1) % 12
    star_placements["Zi Wei"] = ziwei_pos

    # Tian Fu star: opposite of Zi Wei's relationship to life palace
    tianfu_pos = (life_palace + 12 - (ziwei_pos - life_palace) % 12) % 12
    star_placements["Tian Fu"] = tianfu_pos

    # Place remaining stars relative to Zi Wei and Tian Fu
    ziwei_relative = [
        ("Tian Ji", -1), ("Tai Yang", -2), ("Wu Qu", -3),
        ("Tian Tong", -4), ("Lian Zhen", -5),
    ]
    for star, offset in ziwei_relative:
        star_placements[star] = (ziwei_pos + offset) % 12

    tianfu_relative = [
        ("Tai Yin", 1), ("Tan Lang", 2), ("Ju Men", 3),
        ("Tian Xiang", 4), ("Tian Liang", 5),
    ]
    for star, offset in tianfu_relative:
        star_placements[star] = (tianfu_pos + offset) % 12

    # Qi Sha and Po Jun
    star_placements["Qi Sha"] = (life_palace + 7) % 12
    star_placements["Po Jun"] = (life_palace + 11) % 12

    return ZWPResult(
        birth_branch=BRANCHES[hour_branch],
        life_palace=life_palace,
        palaces=palaces,
        star_placements=star_placements,
        element=element,
    )
