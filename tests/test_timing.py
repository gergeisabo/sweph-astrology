"""Tests for astrologica.timing — timing and predictive engine.

Birth reference: Gergely, Kisvárda
  1991-02-15 18:45 CET (Europe/Budapest)
  48.2264 N, 22.0847 E
"""
from astrologica.core import BirthData, compute_positions, SIGNS
from astrologica import timing

BIRTH = BirthData(
    date="1991-02-15", time="18:45:00",
    lat=48.2264, lon=22.0847,
    tz="Europe/Budapest", place="Kisvárda",
)


# ── profections ─────────────────────────────────────────────────────────────

class TestProfections:
    def test_single_age(self):
        p = timing.profections(BIRTH, target_age=0)
        assert p["activated_house"] == 1
        assert p["profection_sign"] == SIGNS[5]  # Virgo (ASC sign at 18:45)

    def test_cycle_of_12(self):
        p = timing.profections(BIRTH)
        assert p["cycle_length"] == 12
        assert len(p["profections"]) == 12

    def test_age_35_profection(self):
        """Age 35 → 35 mod 12 = 11 → House 12."""
        p = timing.profections(BIRTH, target_age=35)
        assert p["activated_house"] == 12

    def test_profection_lord_is_planet(self):
        p = timing.profections(BIRTH, target_age=5)
        assert p["profection_lord"] in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]


# ── firdaria ────────────────────────────────────────────────────────────────

class TestFirdaria:
    def test_returns_periods(self):
        f = timing.firdaria(BIRTH)
        assert isinstance(f, list)
        assert len(f) > 0

    def test_periods_cover_lifetime(self):
        f = timing.firdaria(BIRTH)
        last = f[-1]
        assert last["end_age"] >= 75

    def test_first_period_ruler(self):
        f = timing.firdaria(BIRTH)
        # Night chart (Sun in house 6): first period ruler = Moon
        assert f[0]["ruler"] == "Moon"

    def test_period_durations_sum(self):
        f = timing.firdaria(BIRTH)
        total = sum(p["duration_years"] for p in f)
        assert total == 75  # full cycle


# ── tertiary progressions ───────────────────────────────────────────────────

class TestTertiaryProgressions:
    def test_returns_positions(self):
        tp = timing.tertiary_progressions(BIRTH, 2026)
        assert "progressed_positions" in tp
        assert "progressed_houses" in tp
        assert tp["type"] == "tertiary"

    def test_progressed_date_differs(self):
        tp = timing.tertiary_progressions(BIRTH, 2026)
        assert tp["progressed_date"] != BIRTH.date


# ── minor progressions ──────────────────────────────────────────────────────

class TestMinorProgressions:
    def test_returns_positions(self):
        mp = timing.minor_progressions(BIRTH, 2026)
        assert "progressed_positions" in mp
        assert mp["type"] == "minor"


# ── symbolic directions ─────────────────────────────────────────────────────

class TestSymbolicDirections:
    def test_adds_degrees(self):
        sd = timing.symbolic_directions(BIRTH, target_age=10)
        pos = compute_positions(BIRTH)
        for name in pos:
            expected = (pos[name].longitude + 10) % 360
            assert abs(sd["directed_positions"][name] - expected) < 0.001


# ── primary directions ──────────────────────────────────────────────────────

class TestPrimaryDirections:
    def test_returns_directed_angles(self):
        pd = timing.primary_directions(BIRTH, target_age=30)
        assert "directed_asc" in pd
        assert "directed_mc" in pd
        assert pd["type"] == "primary"


# ── lunar return ────────────────────────────────────────────────────────────

class TestLunarReturn:
    def test_return_near_natal_moon(self):
        lr = timing.lunar_return(BIRTH, 2026, 8)
        natal_pos = compute_positions(BIRTH)
        natal_moon = natal_pos["Moon"].longitude
        # The return Moon should be very close to natal Moon
        ret_moon = lr["return_positions"]["Moon"].longitude
        diff = abs((ret_moon - natal_moon + 180) % 360 - 180)
        assert diff < 1.0  # within 1 degree

    def test_return_date_in_target_month(self):
        lr = timing.lunar_return(BIRTH, 2026, 8)
        assert "2026-08" in lr["return_date_utc"]


# ── solar return ────────────────────────────────────────────────────────────

class TestSolarReturn:
    def test_return_near_natal_sun(self):
        sr = timing.solar_return(BIRTH, 2026)
        natal_pos = compute_positions(BIRTH)
        natal_sun = natal_pos["Sun"].longitude
        ret_sun = sr["return_positions"]["Sun"].longitude
        diff = abs((ret_sun - natal_sun + 180) % 360 - 180)
        assert diff < 1.0

    def test_return_in_target_year(self):
        sr = timing.solar_return(BIRTH, 2026)
        assert "2026" in sr["return_date_utc"]


# ── planetary return ────────────────────────────────────────────────────────

class TestPlanetaryReturn:
    def test_jupiter_return(self):
        pr = timing.planetary_return(BIRTH, "Jupiter", 2026)
        assert pr["planet"] == "Jupiter"
        assert "2026" in pr["return_date_utc"]


# ── ingresses ───────────────────────────────────────────────────────────────

class TestIngresses:
    def test_find_ingresses(self):
        ing = timing.ingresses("Sun", "2026-01-01", "2026-12-31")
        assert isinstance(ing, list)
        # Sun enters each sign once per year
        assert len(ing) >= 10

    def test_ingress_has_signs(self):
        ing = timing.ingresses("Sun", "2026-03-01", "2026-04-30")
        for entry in ing:
            assert entry["planet"] == "Sun"
            assert entry["to_sign"] in SIGNS


# ── retrograde periods ──────────────────────────────────────────────────────

class TestRetrogradePeriods:
    def test_mercury_retrogrades_2026(self):
        rg = timing.retrograde_periods("Mercury", "2026-01-01", "2026-12-31")
        # Mercury retrogrades ~3-4 times per year
        assert len(rg) >= 4  # start+end pairs

    def test_retrograde_has_types(self):
        rg = timing.retrograde_periods("Mercury", "2026-01-01", "2026-12-31")
        types = {r["type"] for r in rg}
        assert "retrograde_start" in types
        assert "retrograde_end" in types


# ── eclipses ────────────────────────────────────────────────────────────────

class TestEclipses:
    def test_eclipses_2026(self):
        ec = timing.eclipses("2026-01-01", "2026-12-31")
        assert isinstance(ec, list)
        assert len(ec) >= 2  # at least solar + lunar

    def test_known_aug_2026_solar(self):
        """2026-08-12 total solar eclipse (known event)."""
        ec = timing.eclipses("2026-08-01", "2026-08-31")
        solar = [e for e in ec if e["type"] == "solar"]
        assert len(solar) >= 1
        assert "2026-08-12" in solar[0]["date_utc"]

    def test_known_aug_2026_lunar(self):
        """2026-08-28 partial lunar eclipse (known event)."""
        ec = timing.eclipses("2026-08-15", "2026-09-05")
        lunar = [e for e in ec if e["type"] == "lunar"]
        assert len(lunar) >= 1
        assert "2026-08-28" in lunar[0]["date_utc"]


# ── transit calendar ────────────────────────────────────────────────────────

class TestTransitCalendar:
    def test_returns_daily_entries(self):
        tc = timing.transit_calendar(BIRTH, 2026, 9, major_orb=3.0)
        assert isinstance(tc, list)
        assert len(tc) > 0  # most days have some transit aspect

    def test_entry_has_aspects(self):
        tc = timing.transit_calendar(BIRTH, 2026, 9, major_orb=5.0)
        for entry in tc[:5]:
            assert "date" in entry
            assert "aspects" in entry
            for a in entry["aspects"]:
                assert "transit" in a
                assert "natal" in a
                assert "aspect" in a
                assert "orb" in a


# ── forecast calendar ───────────────────────────────────────────────────────

class TestForecastCalendar:
    def test_returns_profection_and_progressions(self):
        fc = timing.forecast_calendar(BIRTH, 2026, 9)
        assert "profection" in fc
        assert "daily_summary" in fc
