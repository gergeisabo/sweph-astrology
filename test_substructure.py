#!/usr/bin/env python3
"""Verify Design date and gate assignments, then fine-tune sub-structure."""
import sys
sys.path.insert(0, '/home/zd0l0r/Projects/astrologica')

import swisseph as swe
from astrologica.core import BirthData, _EPHE_PATH

swe.set_ephe_path(_EPHE_PATH)

GATE_SIZE = 360.0 / 64
LINE_SIZE = GATE_SIZE / 6
COLOR_SIZE = LINE_SIZE / 6
TONE_SIZE = COLOR_SIZE / 6

IGING_WHEEL = [
    41, 19, 13, 49, 30, 55, 37, 63, 22, 36,
    25, 17, 21, 51, 42,  3, 27, 24,  2, 23,
     8, 20, 16, 35, 45, 12, 15, 52, 39, 53,
    62, 56, 31, 33,  7,  4, 29, 59, 40, 64,
    47,  6, 46, 18, 48, 57, 32, 50, 28, 44,
     1, 43, 14, 34,  9,  5, 26, 11, 10, 58,
    38, 54, 61, 60,
]

birth = BirthData(
    date="1991-02-15", time="18:45:00",
    lat=48.2264, lon=22.0847, tz="Etc/GMT-1", place="test"
)

jd_birth = birth.julian_day()
sun_at_birth = swe.calc_ut(jd_birth, swe.SUN)[0][0]
target_lon = swe.degnorm(sun_at_birth - 88.0)
jd_start = jd_birth - 100
jd_design = swe.solcross_ut(target_lon, jd_start)

print(f"Birth: 1991-02-15 18:45 CET")
print(f"Birth JD: {jd_birth:.6f}")
print(f"Sun at birth: {sun_at_birth:.6f}°")
print(f"Design Sun target: {target_lon:.6f}°")
print(f"Design JD: {jd_design:.6f}")

# Print design date
rev = swe.revjul(jd_design)
print(f"Design date: {int(rev[0])}-{int(rev[1]):02d}-{int(rev[2]):02d} {rev[3]:.4f} UT")

# All planets at Design time
planets = {
    'Sun': swe.SUN, 'Moon': swe.MOON, 'Mercury': swe.MERCURY,
    'Venus': swe.VENUS, 'Mars': swe.MARS, 'Jupiter': swe.JUPITER,
    'Saturn': swe.SATURN, 'Uranus': swe.URANUS, 'Neptune': swe.NEPTUNE,
    'Pluto': swe.PLUTO, 'NNode': swe.TRUE_NODE
}

print(f"\nDesign positions:")
for name, pid in planets.items():
    lon = swe.calc_ut(jd_design, pid)[0][0]
    angle = (lon + 58.0) % 360.0
    gate_idx = int(angle / 360.0 * 64)
    if gate_idx >= 64: gate_idx = 63
    gate = IGING_WHEEL[gate_idx]
    pos_in_gate = angle % GATE_SIZE
    line = int(pos_in_gate / LINE_SIZE) + 1
    if line > 6: line = 6
    pos_in_line = pos_in_gate % LINE_SIZE
    color = int(pos_in_line / COLOR_SIZE) + 1
    print(f"  {name:8s}: lon={lon:.6f}°  gate={gate:2d}  line={line}  color={color}  pos_in_line={pos_in_line:.6f}°")

# Now verify Design Sun lon matches target
design_sun = swe.calc_ut(jd_design, swe.SUN)[0][0]
print(f"\nDesign Sun verification: {design_sun:.6f}° vs target {target_lon:.6f}° (diff={abs(design_sun-target_lon):.6f}°)")

# Now let's check: what if the issue is that we should compute Design differently?
# Some HD practitioners use 88 days exactly, not 88° solar arc
import datetime

birth_dt = datetime.datetime(1991, 2, 15, 17, 45, 0)  # 18:45 CET = 17:45 UTC
design_88days = birth_dt - datetime.timedelta(days=88)
jd_88days = swe.julday(
    design_88days.year, design_88days.month, design_88days.day,
    design_88days.hour + design_88days.minute/60.0
)

print(f"\nAlternative: 88 days before birth:")
print(f"  Design date: {design_88days}")
for name in ['Sun', 'Moon']:
    pid = planets[name]
    lon = swe.calc_ut(jd_88days, pid)[0][0]
    angle = (lon + 58.0) % 360.0
    gate_idx = int(angle / 360.0 * 64)
    if gate_idx >= 64: gate_idx = 63
    gate = IGING_WHEEL[gate_idx]
    pos_in_gate = angle % GATE_SIZE
    line = int(pos_in_gate / LINE_SIZE) + 1
    if line > 6: line = 6
    pos_in_line = pos_in_gate % LINE_SIZE
    color = int(pos_in_line / COLOR_SIZE) + 1
    print(f"  {name}: lon={lon:.6f}°  gate={gate}  line={line}  color={color}")

# Check Personality Sun too (should be Gate 26 for a typical Aq generator)
print(f"\nPersonality positions at birth:")
for name, pid in planets.items():
    lon = swe.calc_ut(jd_birth, pid)[0][0]
    angle = (lon + 58.0) % 360.0
    gate_idx = int(angle / 360.0 * 64)
    if gate_idx >= 64: gate_idx = 63
    gate = IGING_WHEEL[gate_idx]
    print(f"  {name:8s}: lon={lon:.6f}°  gate={gate}")

print("\nDone.")
