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
    # Rave Variables (sub-structure)
    determination_color: int       # Design Sun Color (1-6)
    determination_tone: int        # Design Sun Tone (1-6)
    environment_color: int         # Design Nodes Color (1-6)
    environment_tone: int          # Design Nodes Tone (1-6)
    motivation_color: int          # Personality Sun Color (1-6)
    perspective_color: int         # Personality Nodes Color (1-6)
    sense_tone: int                # Personality Sun Tone (1-6)
    cognition_tone: int            # Design Sun Tone (1-6)


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

    # Defined centers: a center is defined only if it participates in at least
    # one complete channel (both gates active).
    defined_centers = set()
    for ch_name in defined_channels:
        g1, g2 = CHANNELS[ch_name]
        for center, gates in CENTERS.items():
            if g1 in gates or g2 in gates:
                defined_centers.add(center)

    # Motor-to-Throat connectivity: build graph of centers connected via
    # defined channels and check if any motor center (Heart/Root/Solar Plexus)
    # can reach Throat through the defined channel network.
    MOTOR_CENTERS = {"Heart", "Root", "Solar Plexus"}

    # Build adjacency: which centers connect to which via defined channels
    center_adj: dict[str, set[str]] = {c: set() for c in CENTERS}
    for ch_name in defined_channels:
        g1, g2 = CHANNELS[ch_name]
        c1 = c2 = None
        for center, gates in CENTERS.items():
            if g1 in gates:
                c1 = center
            if g2 in gates:
                c2 = center
        if c1 and c2 and c1 != c2:
            center_adj[c1].add(c2)
            center_adj[c2].add(c1)

    # BFS from each motor center to see if Throat is reachable
    motor_to_throat = False
    if "Throat" in defined_centers:
        for motor in MOTOR_CENTERS:
            if motor in defined_centers:
                visited = {motor}
                queue = [motor]
                found = False
                while queue:
                    current = queue.pop(0)
                    if current == "Throat":
                        found = True
                        break
                    for neighbor in center_adj[current]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                if found:
                    motor_to_throat = True
                    break

    sacral_defined = "Sacral" in defined_centers

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

    # Incarnation Cross: Earth is 180° opposite Sun on the zodiac wheel.
    # Must use wheel INDEX (not gate number) to find the opposite position.
    p_sun_g = personality_gates["Sun"]
    p_sun_idx = IGING_WHEEL.index(p_sun_g)
    p_earth_g = IGING_WHEEL[(p_sun_idx + 32) % 64]
    d_sun_g = design_gates["Sun"]
    d_sun_idx = IGING_WHEEL.index(d_sun_g)
    d_earth_g = IGING_WHEEL[(d_sun_idx + 32) % 64]
    incarnation_cross = f"{p_sun_g}/{p_earth_g}/{d_sun_g}/{d_earth_g}"

    # === Rave Variables (sub-structure) ===
    # Color (1-6) and Tone (1-6) from position within gate/line.
    # Gate = 5.625°, Line = 0.9375°, Color = 0.15625°, Tone = 0.02604°
    # Variable sources:
    #   Determination = Design Sun (Color + Tone for variant)
    #   Environment   = Design Nodes (Color + Tone for variant)
    #   Sense         = Personality Sun Tone
    #   Cognition     = Design Sun Tone
    #   Motivation    = Personality Sun Color
    #   Perspective   = Personality Nodes Color
    # Use TRUE NODE (not Mean) for Environment and Perspective.

    _GATE_SIZE = 360.0 / 64
    _LINE_SIZE = _GATE_SIZE / 6
    _COLOR_SIZE = _LINE_SIZE / 6
    _TONE_SIZE = _COLOR_SIZE / 6
    _OFFSET = 58.0

    def _get_color_tone(lon: float) -> tuple[int, int]:
        """Return (color, tone) for a tropical longitude."""
        angle = (lon + _OFFSET) % 360.0
        pos_in_gate = angle % _GATE_SIZE
        line_idx = int(pos_in_gate / _LINE_SIZE)
        pos_after_line = pos_in_gate - line_idx * _LINE_SIZE
        color_idx = int(pos_after_line / _COLOR_SIZE)
        pos_after_color = pos_after_line - color_idx * _COLOR_SIZE
        tone_idx = int(pos_after_color / _TONE_SIZE)
        return color_idx + 1, tone_idx + 1

    import swisseph as _swe
    _jd = birth.julian_day()
    _jd_design = design_birth.julian_day()

    # Design Sun
    _d_sun_lon = _swe.calc_ut(_jd_design, _swe.SUN)[0][0]
    det_color, det_tone = _get_color_tone(_d_sun_lon)

    # Design Nodes (True Node)
    _d_node_lon = _swe.calc_ut(_jd_design, _swe.TRUE_NODE)[0][0]
    env_color, env_tone = _get_color_tone(_d_node_lon)

    # Personality Sun
    _p_sun_lon = personality["Sun"].longitude
    mot_color, sense_tone = _get_color_tone(_p_sun_lon)

    # Personality Nodes (True Node)
    _p_node_lon = _swe.calc_ut(_jd, _swe.TRUE_NODE)[0][0]
    per_color, _ = _get_color_tone(_p_node_lon)

    # Cognition = Design Sun Tone (same as det_tone)
    cog_tone = det_tone

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
        determination_color=det_color,
        determination_tone=det_tone,
        environment_color=env_color,
        environment_tone=env_tone,
        motivation_color=mot_color,
        perspective_color=per_color,
        sense_tone=sense_tone,
        cognition_tone=cog_tone,
    )
