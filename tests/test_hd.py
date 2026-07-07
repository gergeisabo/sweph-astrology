"""Tests for the Human Design engine.

Verifies gate mapping (64 gates on the Rave Mandala) and design-date
computation (88° solar arc) against known positions.

Reference gate positions (tropical longitude):
  Gate 1  — Scorpio 13°15'  = 223.25°  (IGING_WHEEL index 50)
  Gate 41 — Aquarius  2°    = 302.00°  (IGING_WHEEL index  0)
  Gate 25 — Pisces   28°15' = 358.25°  (IGING_WHEEL index 10)

Each gate spans exactly 5.625° (360/64).  Each line spans 0.9375°.
"""
import pytest
import swisseph as swe

from astrologica.core import BirthData
from astrologica import hd
from astrologica.hd import (
    gate_at_longitude,
    _get_design_date,
    IGING_WHEEL,
    GATE_SIZE,
    compute,
)

# ── Gate sequence integrity ──────────────────────────────────────────

class TestGateWheel:
    def test_64_unique_gates(self):
        assert len(IGING_WHEEL) == 64
        assert len(set(IGING_WHEEL)) == 64

    def test_gates_cover_1_to_64(self):
        assert set(IGING_WHEEL) == set(range(1, 65))

    def test_gate_size_is_5625(self):
        assert abs(GATE_SIZE - 5.625) < 1e-10


# ── Gate-at-longitude mapping ────────────────────────────────────────

class TestGateAtLongitude:
    """Verify specific positions against the verified Rave Mandala."""

    @pytest.mark.parametrize("longitude,expected_gate", [
        (223.25,  1),   # Gate 1  — Scorpio 13°15'
        (228.874, 1),   # Gate 1  — just before end boundary
        (302.0,   41),  # Gate 41 — Aquarius 2°
        (358.25,  25),  # Gate 25 — Pisces 28°15'
        (0.0,     25),  # Gate 25 — Aries 0° (same gate, wraps)
        (3.874,   25),  # Gate 25 — Aries ~3°52' (just before boundary)
        (5.625,   17),  # Gate 17 — Aries 5°37'30" (start of next gate)
        (280.0,   38),  # Gate 38 — Capricorn 10°
    ])
    def test_gate_at_position(self, longitude, expected_gate):
        gate, _line = gate_at_longitude(longitude)
        assert gate == expected_gate, (
            f"At {longitude}°: expected Gate {expected_gate}, got Gate {gate}"
        )

    def test_gate_1_full_range(self):
        """Gate 1 covers 223.25° to 228.875° (Scorpio 13°15' to 18°52'30")."""
        for lon in [223.25, 226.0, 228.874]:
            gate, _ = gate_at_longitude(lon)
            assert gate == 1, f"Expected Gate 1 at {lon}°, got {gate}"

    def test_gate_41_full_range(self):
        """Gate 41 covers 302° to 307.625° (Aquarius 2° to 7°37'30")."""
        for lon in [302.0, 305.0, 307.624]:
            gate, _ = gate_at_longitude(lon)
            assert gate == 41, f"Expected Gate 41 at {lon}°, got {gate}"

    def test_line_computation(self):
        """Line 1 spans 0° to 0.9375° within the gate."""
        # Gate 1, Line 1: 223.25° to 224.1875°
        _g, line = gate_at_longitude(223.25)
        assert line == 1
        _g, line = gate_at_longitude(223.25 + 0.5)
        assert line == 1

    def test_line_2(self):
        """Line 2: 0.9375° to 1.875° within the gate."""
        _g, line = gate_at_longitude(223.25 + 0.9375)
        assert line == 2

    def test_line_6(self):
        """Line 6: 4.6875° to 5.625° within the gate."""
        _g, line = gate_at_longitude(223.25 + 5.0)
        assert line == 6

    def test_all_64_gates_activated(self):
        """Every gate should appear as we sweep through 360°."""
        found = set()
        for deg in range(360):
            gate, _ = gate_at_longitude(float(deg))
            found.add(gate)
        assert found == set(range(1, 65)), (
            f"Missing gates: {set(range(1, 65)) - found}"
        )


# ── Design date (88° solar arc) ──────────────────────────────────────

BIRTH = BirthData("1991-02-15", "17:45:00", 48.2264, 22.0847, "Europe/Budapest")


class TestDesignDate:
    def test_design_date_is_before_birth(self):
        design = _get_design_date(BIRTH)
        assert design.date < BIRTH.date

    def test_solar_arc_is_88_degrees(self):
        """Sun at design moment should be exactly 88° before natal Sun."""
        design = _get_design_date(BIRTH)
        jd_birth = BIRTH.julian_day()
        jd_design = design.julian_day()
        sun_birth = swe.calc_ut(jd_birth, swe.SUN)[0][0]
        sun_design = swe.calc_ut(jd_design, swe.SUN)[0][0]
        diff = (sun_birth - sun_design) % 360
        assert abs(diff - 88.0) < 0.01, (
            f"Solar arc {diff:.4f}°, expected ~88°"
        )

    def test_design_date_approx_88_days_before(self):
        """Design date should be roughly 80-95 days before birth."""
        design = _get_design_date(BIRTH)
        from datetime import date
        d_birth = date(*[int(x) for x in BIRTH.date.split("-")])
        d_design = date(*[int(x) for x in design.date.split("-")])
        delta = (d_birth - d_design).days
        assert 75 <= delta <= 100, (
            f"Design date {delta} days before birth, expected 75-100"
        )


# ── Full compute() integration ───────────────────────────────────────

class TestCompute:
    def test_compute_returns_chart(self):
        chart = compute(BIRTH)
        assert chart.personality_gates
        assert chart.design_gates
        assert 1 <= chart.profile[0] <= 6
        assert 1 <= chart.profile[1] <= 6
        assert chart.type in (
            "Generator", "Manifesting Generator", "Projector",
            "Manifestor", "Reflector",
        )
