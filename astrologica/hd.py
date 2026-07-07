"""Human Design engine.

Computes the BodyGraph from birth data. Uses the I'Ching 64 gates mapped
to tropical zodiac degrees. Based on the Human Design System as channeled
by Ra Uru Hu (1987).

Key calculations:
1. Personality (Conscious): positions at birth
2. Design (Unconscious): positions 88° of solar arc before birth (~88 days)
3. Each gate = 5°37'30" (360/64), mapped to the 64 hexagrams of I'Ching
4. Channels: pairs of gates that connect centers
5. Type, Strategy, Authority, Profile derived from activated gates/channels
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone

import swisseph as swe

from .core import BirthData, PlanetPosition, compute_positions, _EPHE_PATH

# Ensure ephemeris path is set (shared with core).
swe.set_ephe_path(_EPHE_PATH)

# === 64 GATES ===
# Canonical gate sequence around the Rave Mandala.
# Verified against multiple independent HD calculators (MicFell/human_design_engine,
# geodetheseeker/human-design-py) and cross-checked against the Medium Human Design
# Academy article placing Gate 1 at Scorpio 13°15' (223.25°) and the
# gethumandesign.com Rave Mandala documentation.
#
# Gate 41 starts at the Capricorn/Aquarius boundary (~302° tropical).
# The sequence reads: 41 → 19 → 13 → 49 → 30 → 55 → 37 → 63 → 22 → 36
#   → 25 → 17 → 21 → 51 → 42 → 3 → 27 → 24 → 2 → 23 → 8 → 20 → 16
#   → 35 → 45 → 12 → 15 → 52 → 39 → 53 → 62 → 56 → 31 → 33 → 7 → 4
#   → 29 → 59 → 40 → 64 → 47 → 6 → 46 → 18 → 48 → 57 → 32 → 50 → 28
#   → 44 → 1 → 43 → 14 → 34 → 9 → 5 → 26 → 11 → 10 → 58 → 38 → 54
#   → 61 → 60 → (wraps to 41).

GATE_SIZE = 360.0 / 64  # 5.625° per gate

# The I'Ching-to-zodiac offset: adding 58° to a tropical longitude and
# reading into IGING_WHEEL gives the correct gate.  Derived from:
#   Gate 41 at index 0 covers 302°–307.625° (Aquarius 2°–7°37'30").
#   Gate 1  at index 50 covers 223.25°–228.875° (Scorpio 13°15'–18°52'30").
_IGING_OFFSET = 58.0  # degrees

# 64 gates in order around the wheel, starting with Gate 41.
IGING_WHEEL: list[int] = [
    41, 19, 13, 49, 30, 55, 37, 63, 22, 36,
    25, 17, 21, 51, 42,  3, 27, 24,  2, 23,
     8, 20, 16, 35, 45, 12, 15, 52, 39, 53,
    62, 56, 31, 33,  7,  4, 29, 59, 40, 64,
    47,  6, 46, 18, 48, 57, 32, 50, 28, 44,
     1, 43, 14, 34,  9,  5, 26, 11, 10, 58,
    38, 54, 61, 60,
]

# === CHANNELS (connecting pairs) ===
# Each channel connects two gates between centers.
CHANNELS = {
    "1-8": (1, 8),
    "1-7": (1, 7),
    "2-14": (2, 14),
    "3-60": (3, 60),
    "4-63": (4, 63),
    "5-15": (5, 15),
    "6-59": (6, 59),
    "7-31": (7, 31),
    "9-52": (9, 52),
    "10-20": (10, 20),
    "10-34": (10, 34),
    "10-57": (10, 57),
    "11-35": (11, 35),
    "12-22": (12, 22),
    "13-33": (13, 33),
    "16-48": (16, 48),
    "17-62": (17, 62),
    "18-58": (18, 58),
    "19-49": (19, 49),
    "20-34": (20, 34),
    "20-57": (20, 57),
    "21-45": (21, 45),
    "22-12": (22, 12),
    "23-43": (23, 43),
    "24-61": (24, 61),
    "25-51": (25, 51),
    "26-44": (26, 44),
    "27-50": (27, 50),
    "28-38": (28, 38),
    "29-46": (29, 46),
    "30-41": (30, 41),
    "32-54": (32, 54),
    "34-10": (34, 10),
    "34-20": (34, 20),
    "34-57": (34, 57),
    "35-36": (35, 36),
    "37-40": (37, 40),
    "37-63": (37, 63),
    "38-28": (38, 28),
    "39-55": (39, 55),
    "42-53": (42, 53),
    "47-64": (47, 64),
    "48-16": (48, 16),
    "49-19": (49, 19),
    "50-27": (50, 27),
    "51-25": (51, 25),
    "52-9": (52, 9),
    "53-42": (53, 42),
    "54-32": (54, 32),
    "57-10": (57, 10),
    "57-20": (57, 20),
    "57-34": (57, 34),
    "59-6": (59, 6),
    "61-24": (61, 24),
    "62-17": (62, 17),
    "63-4": (63, 4),
    "64-47": (64, 47),
}


def gate_at_longitude(longitude: float) -> tuple[int, int]:
    """Return (gate_number, line_number) for a tropical longitude.

    Gate: 1-64. Line: 1-6 (each gate has 6 lines of ~0.94° each).
    Uses the verified Rave Mandala mapping (IGING_WHEEL with 58° offset).
    """
    angle = (longitude + _IGING_OFFSET) % 360.0
    gate_idx = int(angle / 360.0 * 64)  # 0-63
    # Guard against 360.0 rounding into index 64.
    if gate_idx >= 64:
        gate_idx = 63
    gate_number = IGING_WHEEL[gate_idx]
    line = int((angle / GATE_SIZE * 6) % 6) + 1  # 1-6
    return (gate_number, line)


# === TYPES ===
# Determined by which centers are defined (activated)

CENTERS = {
    "Head": [64, 61, 63],
    "Ajna": [47, 24, 4, 17, 43, 11],
    "Throat": [62, 23, 56, 16, 20, 31, 8, 33, 35, 12, 45, 7],
    "G": [1, 13, 25, 46, 2, 15, 10, 7, 1],
    "Heart": [21, 40, 26, 51],
    "Solar Plexus": [37, 6, 49, 22, 36, 55, 30],
    "Sacral": [34, 5, 14, 29, 3, 42, 59, 9, 27],
    "Spleen": [48, 57, 44, 50, 32, 28, 18],
    "Root": [60, 52, 54, 53, 38, 39, 58, 19, 41, 60],
}

TYPE_FROM_DEFINED = {
    frozenset(): "Reflector",
    # Generators: Sacral defined, Throat not connected to a motor
    # Manifesting Generators: Sacral defined, Throat connected to motor
    # Projectors: Sacral undefined, at least one other center defined
    # Manifestors: Throat connected to Heart/Root/Solar Plexus, Sacral undefined
}


@dataclass
class HumanDesignChart:
    personality: dict[str, PlanetPosition]  # conscious (birth)
    design: dict[str, PlanetPosition]       # unconscious (88° before)
    personality_gates: dict[str, int]
    design_gates: dict[str, int]
    all_active_gates: set[int]
    defined_channels: list[str]
    defined_centers: set[str]
    type: str
    strategy: str
    authority: str
    profile: tuple[int, int]
    incarnation_cross: str


def _get_design_date(birth: BirthData) -> BirthData:
    """Compute the Design date by finding when the Sun was exactly 88°
    before its natal longitude (the 88° solar arc method).

    Uses Swiss Ephemeris swe.solcross_ut for precision.
    """
    jd_birth = birth.julian_day()
    sun_at_birth = swe.calc_ut(jd_birth, swe.SUN)[0][0]
    target_lon = swe.degnorm(sun_at_birth - 88.0)
    # Start searching ~88-100 days before birth.
    jd_start = jd_birth - 100
    jd_design = swe.solcross_ut(target_lon, jd_start)
    # Convert back to a BirthData in UTC.
    rev = swe.revjul(jd_design)
    # Extract fractional day as H:M:S
    frac = rev[3]  # decimal hours
    h = int(frac)
    m = int((frac - h) * 60)
    s = int(((frac - h) * 60 - m) * 60 + 0.5)
    if s >= 60:
        s -= 60
        m += 1
    if m >= 60:
        m -= 60
        h += 1
    return BirthData(
        date=f"{int(rev[0]):04d}-{int(rev[1]):02d}-{int(rev[2]):02d}",
        time=f"{h:02d}:{m:02d}:{s:02d}",
        lat=birth.lat,
        lon=birth.lon,
        tz="UTC",
        place="Design (computed)",
    )


def compute(birth: BirthData) -> HumanDesignChart:
    """Compute the full Human Design bodygraph."""
    # Personality (conscious) = birth positions (tropical)
    personality = compute_positions(birth, sidereal=False)

    # Design (unconscious) = 88° solar arc before birth
    design_birth = _get_design_date(birth)
    design = compute_positions(design_birth, sidereal=False)

    # Get gates for all positions
    personality_gates = {name: gate_at_longitude(p.longitude)[0] for name, p in personality.items()}
    design_gates = {name: gate_at_longitude(p.longitude)[0] for name, p in design.items()}

    # All active gates
    all_gates = set(personality_gates.values()) | set(design_gates.values())

    # Defined channels: both endpoints gates active
    defined_channels = []
    for ch_name, (g1, g2) in CHANNELS.items():
        if g1 in all_gates and g2 in all_gates:
            defined_channels.append(ch_name)

    # Defined centers
    defined_centers = set()
    for center, gates in CENTERS.items():
        if any(g in all_gates for g in gates):
            defined_centers.add(center)

    # Type determination
    sacral_defined = "Sacral" in defined_centers
    throat_defined = "Throat" in defined_centers
    motor_to_throat = False  # simplified
    if "Heart" in defined_centers or "Root" in defined_centers or "Solar Plexus" in defined_centers:
        motor_to_throat = throat_defined  # simplified check

    if not defined_centers:
        hd_type = "Reflector"
        strategy = "Wait a lunar cycle"
    elif sacral_defined and motor_to_throat:
        hd_type = "Manifesting Generator"
        strategy = "Respond, then inform"
    elif sacral_defined:
        hd_type = "Generator"
        strategy = "Wait to respond"
    elif motor_to_throat and not sacral_defined:
        hd_type = "Manifestor"
        strategy = "Inform before acting"
    else:
        hd_type = "Projector"
        strategy = "Wait for invitation"

    # Authority
    if "Solar Plexus" in defined_centers:
        authority = "Emotional"
    elif "Sacral" in defined_centers:
        authority = "Sacral"
    elif "Spleen" in defined_centers:
        authority = "Splenic"
    elif "Heart" in defined_centers:
        authority = "Ego"
    elif "G" in defined_centers:
        authority = "Self-Projected"
    else:
        authority = "Lunar (none)"

    # Profile: Personality Sun line / Design Sun line
    p_sun_gate, p_sun_line = gate_at_longitude(personality["Sun"].longitude)
    d_sun_gate, d_sun_line = gate_at_longitude(design["Sun"].longitude)
    profile = (p_sun_line, d_sun_line)

    # Incarnation Cross (simplified)
    p_sun_g = personality_gates["Sun"]
    p_earth_g = (p_sun_g + 32) % 64 or 64  # opposite gate
    d_sun_g = design_gates["Sun"]
    d_earth_g = (d_sun_g + 32) % 64 or 64
    incarnation_cross = f"{p_sun_g}/{p_earth_g}/{d_sun_g}/{d_earth_g}"

    return HumanDesignChart(
        personality=personality,
        design=design,
        personality_gates=personality_gates,
        design_gates=design_gates,
        all_active_gates=all_gates,
        defined_channels=defined_channels,
        defined_centers=defined_centers,
        type=hd_type,
        strategy=strategy,
        authority=authority,
        profile=profile,
        incarnation_cross=incarnation_cross,
    )
