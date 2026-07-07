"""Render layer — SVG chart wheel generation for Western astrology.

Generates a basic natal chart wheel as SVG. No external dependencies.
"""
from __future__ import annotations

import math
from typing import List, Dict, Tuple

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


def _sign_symbol(sign_name: str) -> str:
    """Return Unicode zodiac symbol."""
    symbols = {
        "Aries": "♈", "Taurus": "♉", "Gemini": "♊", "Cancer": "♋",
        "Leo": "♌", "Virgo": "♍", "Libra": "♎", "Scorpio": "♏",
        "Sagittarius": "♐", "Capricorn": "♑", "Aquarius": "♒", "Pisces": "♓",
    }
    return symbols.get(sign_name, "?")


def _planet_symbol(name: str) -> str:
    """Return Unicode planet symbol."""
    symbols = {
        "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀",
        "Mars": "♂", "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅",
        "Neptune": "♆", "Pluto": "♇", "Rahu": "☊", "Ketu": "☋",
        "Chiron": "⚷", "Lilith": "⚸",
    }
    return symbols.get(name, name[:2])


def _polar_to_xy(angle_deg: float, radius: float, cx: float, cy: float) -> Tuple[float, float]:
    """Convert polar (angle from Ascendant, counterclockwise) to SVG coordinates."""
    # In SVG, 0° is right, 90° is down. Astrological 0° is left (Ascendant).
    rad = math.radians(-angle_deg + 180)
    x = cx + radius * math.cos(rad)
    y = cy + radius * math.sin(rad)
    return x, y


def western_wheel_svg(
    planets: Dict[str, Dict],
    houses: List[float],
    asc: float,
    title: str = "Natal Chart",
    width: int = 600,
    height: int = 600,
) -> str:
    """Generate an SVG natal chart wheel.

    Args:
        planets: dict of planet_name -> {"longitude": float, "sign": str, "degree": float, "retrograde": bool}
        houses: list of 12 house cusp longitudes
        asc: Ascendant longitude
        title: chart title
        width, height: SVG dimensions

    Returns:
        SVG string
    """
    cx, cy = width / 2, height / 2
    r_outer = min(width, height) / 2 - 40
    r_signs = r_outer - 30
    r_planets = r_outer - 70
    r_inner = r_outer - 100
    r_house_labels = r_outer - 130

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<text x="{cx}" y="20" text-anchor="middle" font-size="14" font-weight="bold">{title}</text>',
    ]

    # Outer circle
    lines.append(f'<circle cx="{cx}" cy="{cy}" r="{r_outer}" fill="none" stroke="black" stroke-width="2"/>')
    lines.append(f'<circle cx="{cx}" cy="{cy}" r="{r_signs}" fill="none" stroke="gray" stroke-width="1"/>')
    lines.append(f'<circle cx="{cx}" cy="{cy}" r="{r_inner}" fill="none" stroke="black" stroke-width="1"/>')

    # Sign divisions (30° each)
    for i in range(12):
        angle = i * 30
        x1, y1 = _polar_to_xy(angle, r_outer, cx, cy)
        x2, y2 = _polar_to_xy(angle, r_signs, cx, cy)
        lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="gray" stroke-width="0.5"/>')

    # Sign labels
    for i in range(12):
        mid_angle = i * 30 + 15
        x, y = _polar_to_xy(mid_angle, (r_outer + r_signs) / 2, cx, cy)
        lines.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-size="10">{_sign_symbol(SIGNS[i])}</text>')

    # House cusps
    for i, cusp in enumerate(houses):
        angle = (cusp - asc) % 360
        x1, y1 = _polar_to_xy(angle, r_inner, cx, cy)
        x2, y2 = _polar_to_xy(angle, r_signs, cx, cy)
        style = "stroke='black' stroke-width='1.5'" if i in (0, 3, 6, 9) else "stroke='gray' stroke-width='0.5'"
        lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {style}/>')

    # House numbers
    for i in range(12):
        cusp1 = houses[i]
        cusp2 = houses[(i + 1) % 12]
        mid = (cusp1 + cusp2) / 2
        if (cusp2 - cusp1) % 360 > 180:
            mid = (mid + 180) % 360
        angle = (mid - asc) % 360
        x, y = _polar_to_xy(angle, r_house_labels, cx, cy)
        lines.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-size="9" fill="gray">{i+1}</text>')

    # Planets
    for name, info in planets.items():
        lon = info.get("longitude", 0)
        angle = (lon - asc) % 360
        x, y = _polar_to_xy(angle, r_planets, cx, cy)
        symbol = _planet_symbol(name)
        retro = "R" if info.get("retrograde") else ""
        color = "red" if retro else "black"
        lines.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-size="12" fill="{color}">{symbol}</text>')
        if retro:
            lines.append(f'<text x="{x:.1f}" y="{y+12:.1f}" text-anchor="middle" font-size="7" fill="red">R</text>')

    # ASC / MC markers
    for label, lon, angle in [("ASC", asc, 180), ("MC", (asc + 90) % 360, 270)]:
        x, y = _polar_to_xy(angle, r_outer + 15, cx, cy)
        lines.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-size="10" font-weight="bold">{label}</text>')

    lines.append('</svg>')
    return '\n'.join(lines)


def vedic_wheel_svg(
    planets: Dict[str, Dict],
    houses: List[float],
    title: str = "Vedic Chart (North Indian style)",
    width: int = 600,
    height: int = 600,
) -> str:
    """Generate a North Indian style Vedic chart as SVG.

    North Indian style: diamond-shaped grid with 12 houses (rhombus layout).
    Each house is a triangular section. The Ascendant house is at the top.
    """
    cx, cy = width / 2, height / 2 + 20
    size = min(width, height) / 2 - 60

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<text x="{cx}" y="25" text-anchor="middle" font-size="14" font-weight="bold">{title}</text>',
    ]

    # Diamond outline
    diamond = [
        (cx, cy - size),      # top (ASC)
        (cx + size, cy),      # right
        (cx, cy + size),      # bottom
        (cx - size, cy),      # left
    ]
    points = ' '.join(f'{x:.1f},{y:.1f}' for x, y in diamond)
    lines.append(f'<polygon points="{points}" fill="none" stroke="black" stroke-width="2"/>')

    # Inner cross
    lines.append(f'<line x1="{cx}" y1="{cy-size}" x2="{cx}" y2="{cy+size}" stroke="black" stroke-width="1"/>')
    lines.append(f'<line x1="{cx-size}" y1="{cy}" x2="{cx+size}" y2="{cy}" stroke="black" stroke-width="1"/>')

    # Diagonal lines (connecting corners to center)
    lines.append(f'<line x1="{cx}" y1="{cy-size}" x2="{cx+size}" y2="{cy}" stroke="black" stroke-width="0.5"/>')
    lines.append(f'<line x1="{cx}" y1="{cy-size}" x2="{cx-size}" y2="{cy}" stroke="black" stroke-width="0.5"/>')
    lines.append(f'<line x1="{cx}" y1="{cy+size}" x2="{cx+size}" y2="{cy}" stroke="black" stroke-width="0.5"/>')
    lines.append(f'<line x1="{cx}" y1="{cy+size}" x2="{cx-size}" y2="{cy}" stroke="black" stroke-width="0.5"/>')

    # House positions in the diamond grid (approximate centers)
    # North Indian layout: top=1, going clockwise
    house_positions = [
        (cx, cy - size * 0.6),           # 1 (top center)
        (cx + size * 0.4, cy - size * 0.4),  # 2
        (cx + size * 0.6, cy),           # 3
        (cx + size * 0.4, cy + size * 0.4),  # 4
        (cx, cy + size * 0.6),           # 5 (bottom center)
        (cx - size * 0.4, cy + size * 0.4),  # 6
        (cx - size * 0.6, cy),           # 7
        (cx - size * 0.4, cy - size * 0.4),  # 8
        (cx - size * 0.3, cy - size * 0.15), # 9
        (cx, cy),                         # 10 (center)
        (cx + size * 0.3, cy - size * 0.15), # 11
        (cx + size * 0.15, cy - size * 0.3), # 12
    ]

    # Place planets in their houses
    for name, info in planets.items():
        sign = info.get("sign", 0)
        house = info.get("house", 1)
        hx, hy = house_positions[house - 1]
        symbol = _planet_symbol(name)
        lines.append(f'<text x="{hx:.1f}" y="{hy:.1f}" text-anchor="middle" font-size="11">{symbol}</text>')

    # House numbers
    for i, (hx, hy) in enumerate(house_positions):
        lines.append(f'<text x="{hx:.1f}" y="{hy + 15:.1f}" text-anchor="middle" font-size="8" fill="gray">{i+1}</text>')

    lines.append('</svg>')
    return '\n'.join(lines)


def save_svg(svg_content: str, filepath: str) -> None:
    """Save SVG to file."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(svg_content)
