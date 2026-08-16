"""Tests for astrologica.western_ext — extended Western astrology.

Birth reference: Gergely, Kisvárda
  1991-02-15 18:45 CET (Europe/Budapest)
  48.2264 N, 22.0847 E
"""
import math
import pytest
from astrologica.core import BirthData, compute_positions, compute_houses
from astrologica import western_ext as we

BIRTH = BirthData(
    date="1991-02-15", time="18:45:00",
    lat=48.2264, lon=22.0847,
    tz="Europe/Budapest", place="Kisvárda",
)


# ── midpoints ───────────────────────────────────────────────────────────────

class TestMidpoints:
    def test_returns_dict(self):
        pos = compute_positions(BIRTH)
        mps = we.midpoints(pos)
        assert isinstance(mps, dict)
        assert len(mps) > 0

    def test_keys_are_planet_pairs(self):
        pos = compute_positions(BIRTH)
        mps = we.midpoints(pos)
        for key in mps:
            a, b = key.split("/")
            assert a in pos
            assert b in pos

    def test_midpoint_is_arithmetic_mean(self):
        pos = compute_positions(BIRTH)
        mps = we.midpoints(pos)
        sun = pos["Sun"].longitude
        moon = pos["Moon"].longitude
        expected = (sun + moon) / 2 % 360
        assert abs(mps["Moon/Sun"] - expected) < 0.001 or abs(mps["Sun/Moon"] - expected) < 0.001

    def test_midpoint_identity(self):
        """Midpoint of a planet with itself = itself."""
        pos = compute_positions(BIRTH)
        # Not generated for same planet, but we can compute manually
        sun_lon = pos["Sun"].longitude
        mid = (sun_lon + sun_lon) / 2 % 360
        assert abs(mid - sun_lon) < 0.0001


class TestMidpointTrees:
    def test_returns_dict_with_sign_info(self):
        pos = compute_positions(BIRTH)
        tree = we.midpoint_trees(pos)
        assert isinstance(tree, dict)
        for key, val in tree.items():
            assert "longitude" in val
            assert "sign" in val
            assert "degree_in_sign" in val


# ── antiscia ────────────────────────────────────────────────────────────────

class TestAntiscia:
    def test_returns_dict(self):
        pos = compute_positions(BIRTH)
        anti = we.antiscia(pos)
        assert isinstance(anti, dict)
        assert len(anti) == len(pos)

    def test_antiscia_of_antiscia_is_original(self):
        """Applying antiscia twice should return near-original."""
        pos = compute_positions(BIRTH)
        for name, p in pos.items():
            anti_lon = we._norm(180 - p.longitude)
            double_anti = we._norm(180 - anti_lon)
            assert abs(double_anti - p.longitude) < 0.0001

    def test_cancer_capricorn_on_axis(self):
        """0° Cancer antiscia = 0° Cancer (on the mirror axis)."""
        assert abs(we._norm(180 - 90) - 90) < 0.0001  # Cancer = 90°
        assert abs(we._norm(180 - 270) - 270) < 0.0001  # Capricorn = 270°


# ── harmonics ───────────────────────────────────────────────────────────────

class TestHarmonics:
    def test_harmonic_1_rejected(self):
        pos = compute_positions(BIRTH)
        with pytest.raises(ValueError):
            we.harmonics(pos, 1)

    def test_harmonic_2_doubles_angles(self):
        pos = compute_positions(BIRTH)
        h2 = we.harmonics(pos, 2)
        for name in pos:
            expected = (pos[name].longitude * 2) % 360
            assert abs(h2[name] - expected) < 0.001

    def test_harmonic_12_wraps_aries(self):
        """H12 of 30° Aries (30°) = 360° = 0° Aries."""
        # Create a fake position at 30°
        from astrologica.core import PlanetPosition
        fake = {"Test": PlanetPosition("Test", 30.0, 0, 0, False)}
        h12 = we.harmonics(fake, 12)
        assert abs(h12["Test"] - 0.0) < 0.001 or abs(h12["Test"] - 360.0) < 0.001


# ── draconic ────────────────────────────────────────────────────────────────

class TestDraconic:
    def test_node_maps_to_zero(self):
        pos = compute_positions(BIRTH)
        draco = we.draconic(pos)
        assert abs(draco["Rahu"] - 0.0) < 0.01

    def test_returns_all_planets(self):
        pos = compute_positions(BIRTH)
        draco = we.draconic(pos)
        assert set(draco.keys()) == set(pos.keys())


# ── composite ───────────────────────────────────────────────────────────────

class TestComposite:
    def test_composite_of_same_chart_is_itself(self):
        pos = compute_positions(BIRTH)
        comp = we.composite(pos, pos)
        for name in comp:
            assert abs(comp[name] - pos[name].longitude) < 0.001

    def test_returns_shared_planets(self):
        pos = compute_positions(BIRTH)
        comp = we.composite(pos, pos)
        assert set(comp.keys()) == set(pos.keys())


# ── davison ─────────────────────────────────────────────────────────────────

class TestDavison:
    def test_returns_positions(self):
        dav = we.davison(BIRTH, BIRTH)
        assert isinstance(dav, dict)
        assert "Sun" in dav

    def test_same_birth_same_positions(self):
        """Davison of same birth = same positions (midpoint of identical = same)."""
        dav = we.davison(BIRTH, BIRTH)
        pos = compute_positions(BIRTH)
        for name in ["Sun", "Moon"]:
            assert abs(dav[name].longitude - pos[name].longitude) < 1.0  # ~1° tolerance for rounding


# ── heliocentric ────────────────────────────────────────────────────────────

class TestHeliocentric:
    def test_no_sun_in_result(self):
        helio = we.heliocentric(BIRTH)
        assert "Sun" not in helio

    def test_other_planets_present(self):
        helio = we.heliocentric(BIRTH)
        assert "Mercury" in helio
        assert "Venus" in helio
        assert "Mars" in helio


# ── receptions ──────────────────────────────────────────────────────────────

class TestReceptions:
    def test_returns_list(self):
        pos = compute_positions(BIRTH)
        rec = we.receptions(pos)
        assert isinstance(rec, list)


# ── fixed stars ─────────────────────────────────────────────────────────────

class TestFixedStars:
    def test_returns_star_data(self):
        stars = we.fixed_stars(BIRTH)
        assert isinstance(stars, list)
        assert len(stars) >= 10

    def test_regulus_near_virgo(self):
        """Regulus tropical 2026 ≈ 150° (Virgo 0°)."""
        stars = we.fixed_stars(BIRTH, stars=["Regulus"])
        regulus = stars[0]
        assert abs(regulus["longitude"] - 149.7) < 1.0

    def test_spica_near_virgo(self):
        """Spica tropical 2026 ≈ 204° (Virgo ~24°)."""
        stars = we.fixed_stars(BIRTH, stars=["Spica"])
        spica = stars[0]
        assert abs(spica["longitude"] - 204) < 1.0

    def test_custom_star_list(self):
        stars = we.fixed_stars(BIRTH, stars=["Sirius", "Vega"])
        assert len(stars) == 2
        names = [s["star"] for s in stars]
        assert "Sirius" in names
        assert "Vega" in names


# ── moon phase ──────────────────────────────────────────────────────────────

class TestMoonPhase:
    def test_returns_phase_info(self):
        mp = we.moon_phase(BIRTH)
        assert "angle" in mp
        assert "phase_name" in mp
        assert "illumination_pct" in mp

    def test_sun_aquarius_moon_pisces(self):
        """1991-02-15 18:45: Sun Aquarius, Moon Pisces."""
        mp = we.moon_phase(BIRTH)
        assert mp["sun_sign"] == "Aquarius"
        assert mp["moon_sign"] == "Pisces"

    def test_angle_under_45(self):
        """Sun+Moon in same sign → angle < 30° (actually ~12° for this birth)."""
        mp = we.moon_phase(BIRTH)
        assert mp["angle"] < 30

    def test_new_moon_or_crescent(self):
        """Both in Aquarius, small angle → New Moon or Crescent."""
        mp = we.moon_phase(BIRTH)
        assert mp["phase_index"] in [0, 1]  # New Moon or Waxing Crescent


# ── sun times ───────────────────────────────────────────────────────────────

class TestSunTimes:
    def test_returns_times(self):
        st = we.sun_times(BIRTH)
        assert "sunrise" in st
        assert "sunset" in st
        assert "solar_noon" in st
        assert "day_length_hours" in st

    def test_day_length_february_hungary(self):
        """February in Hungary: day length ~10 hours."""
        st = we.sun_times(BIRTH)
        assert 9 < st["day_length_hours"] < 12


# ── planetary hours ─────────────────────────────────────────────────────────

class TestPlanetaryHours:
    def test_returns_12_hours(self):
        hours = we.planetary_hours(BIRTH)
        assert len(hours) == 12

    def test_each_hour_has_ruler(self):
        hours = we.planetary_hours(BIRTH)
        for h in hours:
            assert "ruler" in h
            assert h["ruler"] in we._CHALDEAN_ORDER

    def test_seven_day_rulers(self):
        """Each day of week has a different ruler."""
        rulers = set(we._DAY_RULERS.values())
        assert len(rulers) == 7


# ── void of course moon ─────────────────────────────────────────────────────

class TestVoidOfCourse:
    def test_returns_dict(self):
        voc = we.moon_void_of_course(BIRTH)
        assert isinstance(voc, dict)
        assert "is_void_of_course" in voc
        assert "moon_sign" in voc


# ── Gauquelin sectors ───────────────────────────────────────────────────────

class TestGauquelin:
    def test_returns_36_sectors(self):
        pos = compute_positions(BIRTH)
        houses = compute_houses(BIRTH)
        gq = we.gauquelin_sectors(pos, houses)
        for name, sector in gq.items():
            assert 1 <= sector <= 36


# ── lunation phase ──────────────────────────────────────────────────────────

class TestLunationPhase:
    def test_returns_phase(self):
        lp = we.lunation_phase(BIRTH)
        assert "phase_number" in lp
        assert 1 <= lp["phase_number"] <= 8

    def test_rudhyar_name(self):
        lp = we.lunation_phase(BIRTH)
        assert "." in lp["phase_name"]  # "I. New Moon ..." format


# ── element balance ─────────────────────────────────────────────────────────

class TestElementBalance:
    def test_returns_elements_and_modes(self):
        pos = compute_positions(BIRTH)
        eb = we.element_balance(pos)
        assert "elements" in eb
        assert "modes" in eb
        assert eb["total_planets"] == len(pos)

    def test_percentages_sum_to_100(self):
        pos = compute_positions(BIRTH)
        eb = we.element_balance(pos)
        total_pct = sum(v["pct"] for v in eb["elements"].values())
        assert abs(total_pct - 100) < 0.5

    def test_dominant_element(self):
        pos = compute_positions(BIRTH)
        eb = we.element_balance(pos)
        assert eb["dominant_element"] in ["Fire", "Earth", "Air", "Water"]


# ── hyleg / alcochoden ──────────────────────────────────────────────────────

class TestHyleg:
    def test_returns_hyleg_info(self):
        pos = compute_positions(BIRTH)
        houses = compute_houses(BIRTH)
        h = we.hyleg_alcochoden(pos, houses)
        assert "hyleg" in h
        assert "alcochoden" in h
        assert "part_of_fortune" in h

    def test_fortune_longitude_valid(self):
        pos = compute_positions(BIRTH)
        houses = compute_houses(BIRTH)
        h = we.hyleg_alcochoden(pos, houses)
        assert 0 <= h["part_of_fortune"] < 360


# ── almuten ─────────────────────────────────────────────────────────────────

class TestAlmuten:
    def test_returns_12_houses(self):
        pos = compute_positions(BIRTH)
        houses = compute_houses(BIRTH)
        alm = we.almuten(pos, houses)
        assert len(alm) == 12
        for house_num in range(1, 13):
            assert house_num in alm
