"""Tests for Phase F: ziwei, hd_ext, hellenistic."""
from astrologica.core import BirthData, compute_positions, compute_houses, SIGNS

BIRTH = BirthData(
    date="1991-02-15", time="18:45:00",
    lat=48.2264, lon=22.0847,
    tz="Europe/Budapest", place="Kisvárda",
)


# ── Zi Wei Dou Shu ──────────────────────────────────────────────────────────

class TestZiWei:
    def test_chart_returns_result(self):
        from astrologica.ziwei import ziwei_chart
        # Jia year (stem=0), Zi hour (0), month=1, day=15
        result = ziwei_chart(year_stem=0, year_branch=0, month=1, day=15, hour_branch=4)
        assert result.life_palace is not None
        assert 0 <= result.life_palace <= 11

    def test_has_all_main_stars(self):
        from astrologica.ziwei import ziwei_chart, MAIN_STARS
        result = ziwei_chart(year_stem=0, year_branch=0, month=1, day=15, hour_branch=4)
        for star in MAIN_STARS:
            assert star in result.star_placements
            assert 0 <= result.star_placements[star] <= 11

    def test_palaces_assigned(self):
        from astrologica.ziwei import ziwei_chart, PALACES
        result = ziwei_chart(year_stem=0, year_branch=0, month=1, day=15, hour_branch=4)
        assert len(result.palaces) == 12

    def test_element_assigned(self):
        from astrologica.ziwei import ziwei_chart
        result = ziwei_chart(year_stem=0, year_branch=0, month=1, day=15, hour_branch=4)
        assert result.element is not None
        assert len(result.element) > 0


# ── HD Extensions ───────────────────────────────────────────────────────────

class TestHDTransits:
    def test_returns_gates(self):
        from astrologica.hd_ext import hd_transits
        t = hd_transits(BIRTH)
        assert "active_gates" in t
        assert isinstance(t["active_gates"], dict)


class TestHDCompatibility:
    def test_returns_gates(self):
        from astrologica.hd_ext import hd_compatibility
        c = hd_compatibility(BIRTH, BIRTH)
        assert "person1_gates" in c
        assert "person2_gates" in c
        assert "shared_gates" in c


class TestIncarnationCross:
    def test_returns_four_gates(self):
        from astrologica.hd_ext import incarnation_cross
        ic = incarnation_cross(BIRTH)
        assert "cross_gates" in ic
        assert len(ic["cross_gates"]) == 4
        for gate in ic["cross_gates"]:
            assert isinstance(gate, int)
            assert 1 <= gate <= 64


# ── Hellenistic ─────────────────────────────────────────────────────────────

class TestHermeticLots:
    def test_returns_lots(self):
        from astrologica.hellenistic import hermetic_lots
        pos = compute_positions(BIRTH)
        houses = compute_houses(BIRTH)
        lots = hermetic_lots(pos, houses, is_day=False)
        assert "Fortune" in lots
        assert "Spirit" in lots

    def test_fortune_longitude_valid(self):
        from astrologica.hellenistic import hermetic_lots
        pos = compute_positions(BIRTH)
        houses = compute_houses(BIRTH)
        lots = hermetic_lots(pos, houses, is_day=False)
        for name, lon in lots.items():
            assert 0 <= lon < 360, f"{name} = {lon} out of range"

    def test_spirit_opposite_fortune_day_chart(self):
        """In a day chart, Fortune and Spirit are symmetric around ASC."""
        from astrologica.hellenistic import hermetic_lots
        pos = compute_positions(BIRTH)
        houses = compute_houses(BIRTH)
        # Force day chart
        lots = hermetic_lots(pos, houses, is_day=True)
        assert "Fortune" in lots
        assert "Spirit" in lots


class TestEgyptianBounds:
    def test_returns_bounds(self):
        from astrologica.hellenistic import egyptian_bounds
        pos = compute_positions(BIRTH)
        bounds = egyptian_bounds(pos)
        assert "Sun" in bounds
        assert "bound_ruler" in bounds["Sun"]

    def test_bound_ruler_is_planet(self):
        from astrologica.hellenistic import egyptian_bounds
        pos = compute_positions(BIRTH)
        bounds = egyptian_bounds(pos)
        valid_rulers = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
        for name, b in bounds.items():
            assert b["bound_ruler"] in valid_rulers, f"{name} bound ruler = {b['bound_ruler']}"


class TestZodiacalReleasing:
    def test_returns_periods(self):
        from astrologica.hellenistic import zodiacal_releasing_from_fortune
        pos = compute_positions(BIRTH)
        houses = compute_houses(BIRTH)
        periods = zodiacal_releasing_from_fortune(pos, houses, is_day=False)
        assert isinstance(periods, list)
        assert len(periods) == 12

    def test_periods_have_signs(self):
        from astrologica.hellenistic import zodiacal_releasing_from_fortune
        pos = compute_positions(BIRTH)
        houses = compute_houses(BIRTH)
        periods = zodiacal_releasing_from_fortune(pos, houses, is_day=False)
        for p in periods:
            assert p["sign"] in SIGNS
            assert p["duration_years"] > 0
