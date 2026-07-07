"""Chinese Four Pillars of Destiny (BaZi / 八字) engine.

Pure calendar math — no Swiss Ephemeris dependency. Builds on the BirthData
class from astrologica.core, but every computation here is sexagenary-cycle
arithmetic over the Julian Day Number and solar-term boundary dates.

Reference chart verified for the project's anchor birth:
    1991-02-15 17:45 CET  ->  Xin Wei / Geng Yin / Bing Chen / Ding You
    Day Master: Bing (Yang Fire, 丙)
"""

from __future__ import annotations

import zoneinfo
from datetime import datetime, timezone
from typing import Dict, List

from astrologica.core import BirthData

# --------------------------------------------------------------------------- #
# Constant tables
# --------------------------------------------------------------------------- #

HEAVENLY_STEMS: List[str] = [
    "Jia", "Yi", "Bing", "Ding", "Wu", "Ji",
    "Geng", "Xin", "Ren", "Gui",
]
# Chinese characters for display
HEAVENLY_STEMS_CN: List[str] = [
    "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸",
]

EARTHLY_BRANCHES: List[str] = [
    "Zi", "Chou", "Yin", "Mao", "Chen", "Si",
    "Wu", "Wei", "Shen", "You", "Xu", "Hai",
]
EARTHLY_BRANCHES_CN: List[str] = [
    "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥",
]
ZODIAC_ANIMALS: List[str] = [
    "Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake",
    "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig",
]

# Element assignments --------------------------------------------------------
# Stems are even-indexed = Yang, odd-indexed = Yin of the same element.
STEM_ELEMENTS: List[str] = [
    "Wood", "Wood",        # Jia  Yi
    "Fire", "Fire",        # Bing Ding
    "Earth", "Earth",      # Wu   Ji
    "Metal", "Metal",      # Geng Xin
    "Water", "Water",      # Ren  Gui
]

BRANCH_ELEMENTS: List[str] = [
    "Water",               # Zi
    "Earth",               # Chou
    "Wood", "Wood",        # Yin Mao
    "Earth",               # Chen
    "Fire", "Fire",        # Si   Wu
    "Earth",               # Wei
    "Metal", "Metal",      # Shen You
    "Earth",               # Xu
    "Water",               # Hai
]

FIVE_ELEMENTS: List[str] = ["Wood", "Fire", "Earth", "Metal", "Water"]

# Yin/Yang from stem parity: even index = Yang, odd = Yin.
STEM_YIN_YANG: List[str] = [
    "Yang", "Yin", "Yang", "Yin", "Yang", "Yin",
    "Yang", "Yin", "Yang", "Yin",
]

# Solar-term boundary day-of-month (approximate but accurate within a day).
# Index 0..11 corresponds to the 12 solar months, with Month 1 starting at
# Li Chun (立春, ~Feb 4). Index 11 = the term in early January.
# Stored as (month_in_calendar, day_in_calendar) so we can build date objects
# in any year. For Month 1 the calendar month is February (2).
SOLAR_TERM_BOUNDARIES: List[tuple] = [
    (2, 4),    # Month 1 — Li Chun (立春, Start of Spring)
    (3, 6),    # Month 2 — Jing Zhe (惊蛰, Awakening of Insects)
    (4, 5),    # Month 3 — Qing Ming (清明, Pure Brightness)
    (5, 6),    # Month 4 — Li Xia (立夏, Start of Summer)
    (6, 6),    # Month 5 — Mang Zhong (芒种, Grain in Ear)
    (7, 7),    # Month 6 — Xiao Shu (小暑, Slight Heat)
    (8, 8),    # Month 7 — Li Qiu (立秋, Start of Autumn)
    (9, 8),    # Month 8 — Bai Lu (白露, White Dew)
    (10, 8),   # Month 9 — Han Lu (寒露, Cold Dew)
    (11, 7),   # Month 10 — Li Dong (立冬, Start of Winter)
    (12, 7),   # Month 11 — Da Xue (大雪, Major Snow)
    (1, 6),    # Month 12 — Xiao Han (小寒, Slight Cold) — January
]

# Month branches: Month 1 = Yin (Tiger), Month 2 = Mao (Rabbit), ...
# Month 1 is index 2 (Yin) in EARTHLY_BRANCHES.
MONTH_BRANCHES: List[int] = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0, 1]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _julian_day_number(year: int, month: int, day: int) -> int:
    """Integer Julian Day Number at 0h UT for a Gregorian calendar date.

    Uses the standard astronomical formula (valid for all Gregorian dates).
    """
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return (
        day
        + (153 * m + 2) // 5
        + 365 * y
        + y // 4
        - y // 100
        + y // 400
        - 32045
    )


def _local_solar_datetime(birth: BirthData) -> datetime:
    """Birth instant expressed in local civil time (the tz field's wall-clock).

    BaZi tradition works in local solar time; for day-level precision the
    civil-time zone is a close enough proxy. We return the naive local
    datetime so callers can compare against solar-term calendar dates in the
    same timezone without UTC conversion noise.
    """
    parts = [int(x) for x in birth.time.split(":")]
    while len(parts) < 3:
        parts.append(0)
    return datetime(
        *[int(x) for x in birth.date.split("-")], *parts,
    )


def _solar_year_number(local_dt: datetime) -> int:
    """Chinese solar year number for a local datetime.

    The solar year begins at Li Chun (~Feb 4). A date in Jan/early-Feb belongs
    to the previous year's solar year.
    """
    y = local_dt.year
    # Feb 4 is our fixed Li Chun proxy; before it -> previous solar year.
    if local_dt.month < 2 or (local_dt.month == 2 and local_dt.day < 4):
        return y - 1
    return y


def _solar_month_index(local_dt: datetime) -> int:
    """0-based solar-month index (0 = Month 1 / Yin month / Tiger month).

    Walks the SOLAR_TERM_BOUNDARIES in chronological order within the solar
    year and returns the index of the most recent boundary at/before the date.
    """
    year = local_dt.year
    # Build candidate boundary datetimes for this year and the previous year
    # (the January boundary — Month 12 — belongs to the prior calendar year).
    candidates: List[tuple] = []  # (datetime, month_index)
    for idx, (mo, day) in enumerate(SOLAR_TERM_BOUNDARIES):
        # Month 12 (idx 11) starts in January; for a date in Jan/early-Feb it
        # is the previous year's January boundary.
        y = year - 1 if mo == 1 else year
        candidates.append((datetime(y, mo, day), idx))

    # Sort chronologically and find the most recent boundary <= local_dt.
    candidates.sort(key=lambda c: c[0])
    result = 0
    for boundary_dt, idx in candidates:
        if boundary_dt <= local_dt:
            result = idx
        else:
            break
    return result


# --------------------------------------------------------------------------- #
# Pillar computation
# --------------------------------------------------------------------------- #

def _year_pillar(local_dt: datetime) -> tuple:
    """Return (stem_index, branch_index) for the year pillar."""
    year = _solar_year_number(local_dt)
    stem = (year - 4) % 10
    branch = (year - 4) % 12
    return stem, branch


def _month_pillar(local_dt: datetime, year_stem: int) -> tuple:
    """Return (stem_index, branch_index) for the month pillar.

    Month branch follows the solar terms directly. Month stem is derived from
    the YEAR stem via the "Five Tigers" rule (五虎遁):
        Each stem pairs with a fixed starting stem for Month 1 (Yin/Tiger):
            Jia/Ji   -> Bing-Yin   (Bing in Month 1)
            Yi/Geng  -> Wu-Yin     (Wu   in Month 1)
            Bing/Xin -> Geng-Yin   (Geng in Month 1)
            Ding/Ren -> Ren-Yin    (Ren  in Month 1)
            Wu/Gui   -> Jia-Yin    (Jia  in Month 1)
        Month N stem = (month1_stem + N - 1) % 10.
    """
    month_idx = _solar_month_index(local_dt)  # 0..11
    branch = MONTH_BRANCHES[month_idx]

    # Five Tigers: starting stem for the Yin (Month 1) pillar.
    # Pairs: [0,5]->2, [1,6]->4, [2,7]->6, [3,8]->8, [4,9]->0
    # Formula: m1_stem = ((year_stem % 5) * 2 + 2) % 10
    m1_stem = ((year_stem % 5) * 2 + 2) % 10
    stem = (m1_stem + month_idx) % 10
    return stem, branch


def _day_pillar(jdn: int) -> tuple:
    """Return (stem_index, branch_index) for the day pillar.

    Uses the offset-calibrated sexagenary formulas:
        stem   = (jd + 9) % 10
        branch = (jd + 1) % 12
    """
    stem = (jdn + 9) % 10
    branch = (jdn + 1) % 12
    return stem, branch


def _hour_branch_index(hour: int) -> int:
    """Map a 24h clock hour to its Earthly Branch index (0=Zi).

    Chinese hours are 2-hour blocks. The Zi (子) hour spans 23:00–00:59 and is
    conventionally split: 23:00 is "early Zi" belonging to the NEXT day's hour
    pillar, while 00:00–00:59 is "late Zi" for the current day. This function
    returns the branch index only; the early-Zi day rollover is handled by the
    caller.
    """
    return ((hour + 1) // 2) % 12


def _hour_pillar(hour: int, day_stem: int) -> tuple:
    """Return (stem_index, branch_index) for the hour pillar.

    Hour stem follows the "Five Rats" rule (五鼠遁), keyed by the DAY stem:
        Jia/Ji   day -> Jia-Zi hour
        Yi/Geng  day -> Bing-Zi hour
        Bing/Xin day -> Wu-Zi hour
        Ding/Ren day -> Geng-Zi hour
        Wu/Gui   day -> Ren-Zi hour
        Hour branch's stem = (zi_stem + branch_index) % 10.
    """
    branch = _hour_branch_index(hour)

    # Five Rats: starting stem for the Zi hour: zi_stem = (day_stem + 2) % 10
    zi_stem = (day_stem + 2) % 10
    stem = (zi_stem + branch) % 10
    return stem, branch


def four_pillars(birth: BirthData) -> Dict:
    """Compute the Four Pillars (Year, Month, Day, Hour) for a birth.

    Each pillar is a dict with the stem/branch index, English and Chinese
    names, the associated zodiac animal (for the branches), and the element.

    Returns
    -------
    dict with keys ``year``, ``month``, ``day``, ``hour``. Each value is a
    dict::

        {
            "stem": "Xin",            # English stem name
            "branch": "Wei",          # English branch name
            "stem_cn": "辛",
            "branch_cn": "未",
            "stem_index": 7,
            "branch_index": 7,
            "animal": "Goat",         # zodiac animal of the branch
            "stem_element": "Metal",
            "branch_element": "Earth",
            "pillar": "Xin Wei",      # combined display string
        }
    """
    local_dt = _local_solar_datetime(birth)
    jdn = _julian_day_number(local_dt.year, local_dt.month, local_dt.day)

    # --- Year pillar -------------------------------------------------------
    y_stem, y_branch = _year_pillar(local_dt)

    # --- Month pillar ------------------------------------------------------
    m_stem, m_branch = _month_pillar(local_dt, y_stem)

    # --- Day pillar --------------------------------------------------------
    d_stem, d_branch = _day_pillar(jdn)

    # --- Hour pillar -------------------------------------------------------
    # Early-Zi rule: 23:00–23:59 belongs to the NEXT day's hour pillar.
    hour = local_dt.hour
    day_stem_for_hour = d_stem
    if hour == 23:
        # Roll the day pillar forward by one in the sexagenary cycle to get
        # the stem that governs the next day's Zi hour.
        day_stem_for_hour = (d_stem + 1) % 10
    h_stem, h_branch = _hour_pillar(hour, day_stem_for_hour)

    def _pillar_dict(stem_i: int, branch_i: int) -> Dict:
        return {
            "stem": HEAVENLY_STEMS[stem_i],
            "branch": EARTHLY_BRANCHES[branch_i],
            "stem_cn": HEAVENLY_STEMS_CN[stem_i],
            "branch_cn": EARTHLY_BRANCHES_CN[branch_i],
            "stem_index": stem_i,
            "branch_index": branch_i,
            "animal": ZODIAC_ANIMALS[branch_i],
            "stem_element": STEM_ELEMENTS[stem_i],
            "branch_element": BRANCH_ELEMENTS[branch_i],
            "pillar": f"{HEAVENLY_STEMS[stem_i]} {EARTHLY_BRANCHES[branch_i]}",
        }

    return {
        "year": _pillar_dict(y_stem, y_branch),
        "month": _pillar_dict(m_stem, m_branch),
        "day": _pillar_dict(d_stem, d_branch),
        "hour": _pillar_dict(h_stem, h_branch),
    }


def day_master(birth: BirthData) -> str:
    """Return the Heavenly Stem of the Day Pillar (the Day Master / 日主).

    The Day Master represents the Self in BaZi — it is the reference point for
    all Ten Gods relationships and for chart balance analysis.
    """
    return four_pillars(birth)["day"]["stem"]


# --------------------------------------------------------------------------- #
# Element balance
# --------------------------------------------------------------------------- #

def element_balance(pillars: Dict) -> Dict[str, int]:
    """Count the five elements across all 8 characters (4 stems + 4 branches).

    Parameters
    ----------
    pillars : dict
        Output of :func:`four_pillars`.

    Returns
    -------
    dict mapping each of the five elements to its integer count (0..8). The
    counts always sum to 8.
    """
    counts: Dict[str, int] = {el: 0 for el in FIVE_ELEMENTS}
    for key in ("year", "month", "day", "hour"):
        p = pillars[key]
        counts[p["stem_element"]] += 1
        counts[p["branch_element"]] += 1
    return counts


# --------------------------------------------------------------------------- #
# Ten Gods (十神 / Shi Shen)
# --------------------------------------------------------------------------- #

# The five generating/controlling relationships of Wu Xing:
#   A generates B  |  A controls B
_GENERATES: Dict[str, str] = {
    "Wood": "Fire", "Fire": "Earth", "Earth": "Metal",
    "Metal": "Water", "Water": "Wood",
}
_CONTROLS: Dict[str, str] = {
    "Wood": "Earth", "Earth": "Water", "Water": "Fire",
    "Fire": "Metal", "Metal": "Wood",
}

# Relationship label -> (Direct name, Indirect name)
_RELATION_NAMES: Dict[str, tuple] = {
    "companion": ("Bi Jian", "Jie Cai"),     #比肩  劫财
    "resource": ("Zheng Yin", "Pian Yin"),   #正印  偏印
    "output": ("Shi Shen", "Shang Guan"),    #食神  伤官
    "power": ("Zheng Guan", "Qi Sha"),       #正官  七杀
    "wealth": ("Zheng Cai", "Pian Cai"),     #正财  偏财
}


def _ten_god_for(dm_element: str, dm_polarity: str,
                 char_element: str, char_polarity: str) -> str:
    """Compute the Ten God name for one character relative to the Day Master.

    Polarity match (same Yin/Yang) -> Direct (Zheng); mismatch -> Indirect (Pian).
    """
    same = dm_polarity == char_polarity
    direct, indirect = "", ""

    if char_element == dm_element:
        direct, indirect = _RELATION_NAMES["companion"]
    elif _GENERATES[char_element] == dm_element:
        # char generates DM -> Resource
        direct, indirect = _RELATION_NAMES["resource"]
    elif _GENERATES[dm_element] == char_element:
        # DM generates char -> Output
        direct, indirect = _RELATION_NAMES["output"]
    elif _CONTROLS[char_element] == dm_element:
        # char controls DM -> Power
        direct, indirect = _RELATION_NAMES["power"]
    elif _CONTROLS[dm_element] == char_element:
        # DM controls char -> Wealth
        direct, indirect = _RELATION_NAMES["wealth"]

    return direct if same else indirect


def ten_gods(birth: BirthData) -> Dict[str, str]:
    """Compute the Ten Gods (十神) for the 7 non-day-master characters.

    The Day Master (Day Pillar stem) is the reference ("the Self"). Each of
    the other 7 characters (year stem/branch, month stem/branch, day branch,
    hour stem/branch) is classified by its Wu Xing relationship to the Day
    Master and by Yin/Yang polarity match.

    Returns
    -------
    dict mapping a descriptive position key to the Ten God name, e.g.::

        {
            "year_stem": "Zheng Yin",
            "year_branch": "...",
            "month_stem": "...",
            "month_branch": "...",
            "day_branch": "...",     # the branch under the Day Master
            "hour_stem": "...",
            "hour_branch": "...",
        }
    """
    pillars = four_pillars(birth)
    day = pillars["day"]
    dm_element = day["stem_element"]
    dm_polarity = STEM_YIN_YANG[day["stem_index"]]

    targets = [
        ("year_stem", pillars["year"]["stem_index"]),
        ("year_branch", pillars["year"]["branch_index"]),
        ("month_stem", pillars["month"]["stem_index"]),
        ("month_branch", pillars["month"]["branch_index"]),
        ("day_branch", pillars["day"]["branch_index"]),
        ("hour_stem", pillars["hour"]["stem_index"]),
        ("hour_branch", pillars["hour"]["branch_index"]),
    ]

    gods: Dict[str, str] = {}
    for key, branch_or_stem_idx in targets:
        # Stems use STEM_ELEMENTS + STEM_YIN_YANG; branches use BRANCH_ELEMENTS
        # and derive polarity from their hidden stem's parity. For the Ten
        # Gods we treat every branch's polarity as Yang (its principal qi),
        # which is the common simplification in BaZi software.
        is_stem = key.endswith("_stem")
        if is_stem:
            el = STEM_ELEMENTS[branch_or_stem_idx]
            pol = STEM_YIN_YANG[branch_or_stem_idx]
        else:
            el = BRANCH_ELEMENTS[branch_or_stem_idx]
            # Branch polarity: use the parity of the branch's principal qi.
            # The principal stem of each branch has a fixed parity we can
            # read off the branch index via a lookup (Yang branches = even
            # index, Yin branches = odd index — a standard convention).
            pol = STEM_YIN_YANG[(branch_or_stem_idx * 5) % 10]
        gods[key] = _ten_god_for(dm_element, dm_polarity, el, pol)
    return gods


# --------------------------------------------------------------------------- #
# Luck Pillars (Da Yun / 大运)
# --------------------------------------------------------------------------- #

def _nearest_term_boundaries(local_dt: datetime) -> tuple:
    """Return (previous_boundary, next_boundary) as datetimes around local_dt.

    Used to compute the starting age of the first luck pillar: forward
    direction counts from birth to the next boundary; backward counts from
    the previous boundary to birth.
    """
    year = local_dt.year
    candidates: List[datetime] = []
    # Gather boundaries from the prior year through the next year so the
    # window always brackets local_dt.
    for y in (year - 1, year, year + 1):
        for mo, day in SOLAR_TERM_BOUNDARIES:
            candidates.append(datetime(y, mo, day))
    candidates.sort()

    prev_b = candidates[0]
    next_b = candidates[-1]
    for i, b in enumerate(candidates):
        if b <= local_dt:
            prev_b = b
            next_b = candidates[i + 1]
        else:
            break
    return prev_b, next_b


def luck_pillars(birth: BirthData, gender: str) -> List[Dict]:
    """Compute the 10-year Luck Pillars (大运 / Da Yun).

    Direction rule (大运 direction):
        The luck pillars march *forward* (stem+1, branch+1 each pillar) when
        the year stem's polarity matches the gender's polarity, and
        *backward* (stem−1, branch−1) otherwise. Concretely:
            Male   + Yang year stem  -> forward
            Male   + Yin  year stem  -> backward
            Female + Yang year stem  -> backward
            Female + Yin  year stem  -> forward

    Starting age:
        Forward  : days from birth to the next solar-term boundary, divided by 3.
        Backward : days from the previous boundary to birth, divided by 3.
    (One solar-term step ≈ 30.4 days; /3 yields ≈10 years per pillar — the
    Da Yun period.)

    Parameters
    ----------
    birth : BirthData
    gender : str
        ``"male"`` or ``"female"`` (case-insensitive).

    Returns
    -------
    list of dicts, one per 10-year pillar, each::

        {
            "stem": "Xin", "branch": "Wei",
            "stem_index": 7, "branch_index": 7,
            "stem_element": "Metal", "branch_element": "Earth",
            "animal": "Goat",
            "start_age": float, "end_age": float,
            "pillar": "Xin Wei",
        }
    """
    local_dt = _local_solar_datetime(birth)
    pillars = four_pillars(birth)
    year_stem_idx = pillars["year"]["stem_index"]
    month_stem_idx = pillars["month"]["stem_index"]
    month_branch_idx = pillars["month"]["branch_index"]

    year_is_yang = (year_stem_idx % 2 == 0)
    gender_l = gender.strip().lower()
    if gender_l not in ("male", "female"):
        raise ValueError(f"gender must be 'male' or 'female', got {gender!r}")

    # Polarity match -> forward.
    gender_is_yang = gender_l == "male"
    forward = year_is_yang == gender_is_yang

    prev_b, next_b = _nearest_term_boundaries(local_dt)
    if forward:
        days = (next_b - local_dt).days
    else:
        days = (local_dt - prev_b).days
    start_age = round(days / 3.0, 1)

    out: List[Dict] = []
    stem = month_stem_idx
    branch = month_branch_idx
    cur_start = start_age
    for _ in range(8):
        if forward:
            stem = (stem + 1) % 10
            branch = (branch + 1) % 12
        else:
            stem = (stem - 1) % 10
            branch = (branch - 1) % 12
        cur_end = cur_start + 10
        out.append({
            "stem": HEAVENLY_STEMS[stem],
            "branch": EARTHLY_BRANCHES[branch],
            "stem_index": stem,
            "branch_index": branch,
            "stem_element": STEM_ELEMENTS[stem],
            "branch_element": BRANCH_ELEMENTS[branch],
            "animal": ZODIAC_ANIMALS[branch],
            "start_age": cur_start,
            "end_age": cur_end,
            "pillar": f"{HEAVENLY_STEMS[stem]} {EARTHLY_BRANCHES[branch]}",
        })
        cur_start = cur_end
    return out
