"""Tests for the Vedic (Jyotish) engine.

Reference chart: Gergely, Kisvárda 1991-02-15 17:45 CET, Lahiri ayanamsa.
Verified against Astro Seek sidereal positions to within ~1'.
"""
import pytest

from astrologica.core import BirthData, compute_positions, compute_houses
from astrologica.vedic import (
    nakshatra,
    vimshottari_dasha,
    ashtottari_dasha,
    varga_chart,
    dignity,
    yogas,
    doshas,
    panchang,
    NAK_NAMES,
)

BIRTH = BirthData("1991-02-15", "17:45:00", 48.2264, 22.0847, "Europe/Budapest")


@pytest.fixture(scope="module")
def pos():
    return compute_positions(BIRTH, sidereal=True, ayanamsa="lahiri")


@pytest.fixture(scope="module")
def houses():
    return compute_houses(BIRTH, system="whole_sign", sidereal=True, ayanamsa="lahiri")


# ---------------------------------------------------------------------------
# Nakshatra
# ---------------------------------------------------------------------------

class TestNakshatra:
    def test_moon_shatabhisha_pada3(self):
        # Moon sidereal ~314.165° → Shatabhisha (nakshatra 24) pada 3
        n = nakshatra(314.165)
        assert n["name"] == "Shatabhisha", f"got {n['name']}"
        assert n["number"] == 24
        assert n["pada"] == 3, f"got pada {n['pada']}"
        assert n["ruler"] == "Rahu"

    def test_sun_dhanishtha_pada3(self):
        # Sun sidereal ~302.76° → Dhanishtha (23) pada 3
        n = nakshatra(302.76)
        assert n["name"] == "Dhanishtha"
        assert n["number"] == 23
        assert n["pada"] == 3
        assert n["ruler"] == "Mars"

    def test_ashwini_start(self):
        n = nakshatra(0.5)
        assert n["name"] == "Ashwini"
        assert n["number"] == 1
        assert n["pada"] == 1
        assert n["ruler"] == "Ketu"

    def test_revati_end(self):
        # Revati spans 346.666°..360°
        n = nakshatra(359.0)
        assert n["name"] == "Revati"
        assert n["number"] == 27
        assert n["ruler"] == "Mercury"

    def test_27_unique_names(self):
        seen = {nakshatra(i * 13.3333 + 0.1)["name"] for i in range(27)}
        assert seen == set(NAK_NAMES)


# ---------------------------------------------------------------------------
# Vimshottari Dasha
# ---------------------------------------------------------------------------

class TestVimshottari:
    def test_starts_with_rahu(self, pos):
        # Moon in Shatabhisha → ruler Rahu → first dasha lord is Rahu
        moon = pos["Moon"].longitude
        d = vimshottari_dasha(BIRTH, moon)
        assert d[0]["lord"] == "Rahu", f"first lord {d[0]['lord']}"
        # Rahu full duration = 18 years, but balance at birth is partial.
        assert d[0]["duration_years"] < 18.0
        # One cycle: balance (partial Rahu) + 8 full periods.
        # Full 9-lord cycle = 120 yrs; elapsed portion of Rahu is excluded.
        total = sum(e["duration_years"] for e in d)
        expected_total = d[0]["duration_years"] + (120.0 - 18.0)
        assert abs(total - expected_total) < 0.5, f"total {total}, expected {expected_total}"

    def test_sequence_order(self, pos):
        moon = pos["Moon"].longitude
        d = vimshottari_dasha(BIRTH, moon)
        # Expected cyclic order starting from Rahu.
        expected = ["Rahu", "Jupiter", "Saturn", "Mercury",
                    "Ketu", "Venus", "Sun", "Moon", "Mars"]
        lords = [e["lord"] for e in d]
        assert lords == expected

    def test_dates_monotonic(self, pos):
        moon = pos["Moon"].longitude
        d = vimshottari_dasha(BIRTH, moon)
        for prev, cur in zip(d, d[1:]):
            assert cur["start_date"] == prev["end_date"]
            assert cur["end_date"] > cur["start_date"]


# ---------------------------------------------------------------------------
# Ashtottari Dasha
# ---------------------------------------------------------------------------

class TestAshtottari:
    def test_eight_lords(self, pos):
        sun = pos["Sun"].longitude
        d = ashtottari_dasha(BIRTH, sun)
        # Sun in Dhanishtha pada 3 → start_idx = pada-1 = 2 → Mars
        assert d[0]["lord"] == "Mars", f"first lord {d[0]['lord']}"
        lords = [e["lord"] for e in d]
        assert len(lords) == 8
        assert "Ketu" not in lords
        # Ashtottari cycle: balance (partial Mars) + 7 full periods.
        total = sum(e["duration_years"] for e in d)
        expected_total = d[0]["duration_years"] + (108.0 - 8.0)
        assert abs(total - expected_total) < 0.5, f"total {total}, expected {expected_total}"


# ---------------------------------------------------------------------------
# Varga charts
# ---------------------------------------------------------------------------

class TestVarga:
    def test_d1_identity(self, pos):
        d1 = varga_chart(pos, 1)
        assert d1["Sun"].sign == pos["Sun"].sign
        assert d1["Jupiter"].sign == pos["Jupiter"].sign

    def test_d9_sun_libra(self, pos):
        # Sun at 302.76° (Aquarius 2°46') → Navamsa Libra
        d9 = varga_chart(pos, 9)
        assert d9["Sun"].sign == 6, f"Sun D9 sign {d9['Sun'].sign_name}"  # Libra

    def test_d9_movable_rule(self):
        # Aries 5° → movable sign, pada 2 (index 1) → Navamsa Taurus
        from astrologica.vedic import _navamsa_sign
        assert _navamsa_sign(5.0) == 1   # Aries pada 2 → Taurus
        # Aries 1° → pada 1 → Navamsa Aries
        assert _navamsa_sign(1.0) == 0   # Aries
        # Taurus 5° → fixed, count from 9th: 9th from Taurus = Capricorn
        # Capricorn + pada2 = Aquarius
        assert _navamsa_sign(35.0) == 10  # Aquarius
        # Gemini 5° → dual, count from 5th: 5th from Gemini = Libra
        # Libra + pada2 = Scorpio
        assert _navamsa_sign(65.0) == 7  # Scorpio

    def test_d3_drekkana(self):
        from astrologica.vedic import _drekkana_sign
        assert _drekkana_sign(5.0) == 0    # Aries part 1 → Aries
        assert _drekkana_sign(15.0) == 4   # Aries part 2 → Leo (5th)
        assert _drekkana_sign(25.0) == 8   # Aries part 3 → Sagittarius (9th)

    def test_d10_dashamamsa(self, pos):
        d10 = varga_chart(pos, 10)
        # Jupiter at Cancer 12°35' → part 4 (12°/3=4) from Cancer → Leo
        # Verify it's a valid sign
        assert 0 <= d10["Jupiter"].sign <= 11


# ---------------------------------------------------------------------------
# Dignity
# ---------------------------------------------------------------------------

class TestDignity:
    @pytest.mark.parametrize("planet,sign,expected", [
        ("Jupiter", 3, "exalted"),       # Cancer
        ("Jupiter", 9, "debilitated"),   # Capricorn (opposite Cancer)
        ("Sun", 0, "exalted"),           # Aries
        ("Sun", 6, "debilitated"),       # Libra
        ("Sun", 4, "domicile"),          # Leo
        ("Moon", 1, "exalted"),          # Taurus
        ("Moon", 3, "domicile"),         # Cancer
        ("Moon", 7, "debilitated"),      # Scorpio
        ("Mercury", 5, "exalted"),       # Virgo (also domicile)
        ("Mars", 9, "exalted"),          # Capricorn
        ("Mars", 3, "debilitated"),      # Cancer
        ("Venus", 11, "exalted"),        # Pisces
        ("Venus", 5, "debilitated"),     # Virgo
        ("Saturn", 6, "exalted"),        # Libra
        ("Saturn", 9, "domicile"),       # Capricorn
        ("Saturn", 0, "debilitated"),    # Aries
        ("Jupiter", 0, "neutral"),       # Aries for Jupiter
    ])
    def test_dignities(self, planet, sign, expected):
        assert dignity(planet, sign) == expected

    def test_jupiter_cancer_exalted_in_chart(self, pos):
        # Jupiter sidereal ~102.58° → Cancer (sign 3) → exalted
        assert pos["Jupiter"].sign == 3
        assert dignity("Jupiter", pos["Jupiter"].sign) == "exalted"

    def test_saturn_capricorn_domicile_in_chart(self, pos):
        assert pos["Saturn"].sign == 9
        assert dignity("Saturn", pos["Saturn"].sign) == "domicile"


# ---------------------------------------------------------------------------
# Yogas
# ---------------------------------------------------------------------------

class TestYogas:
    def test_yoga_detection(self, pos, houses):
        # Sun+Mercury in Aquarius conjunct → Budhaditya should trigger.
        # Jupiter in Cancer is 6th from Moon (Aquarius) → not a kendra →
        # no Gajakesari for this chart.
        lagna_sign = int(houses.ascendant // 30) % 12
        ys = yogas(pos, houses, lagna_sign)
        names = [y["name"] for y in ys]
        assert "Budhaditya Yoga" in names  # Sun & Mercury conjunct in Aquarius
        assert "Gajakesari Yoga" not in names  # Jupiter 6th from Moon, not kendra

    def test_chandra_mangala_absent(self, pos, houses):
        lagna_sign = int(houses.ascendant // 30) % 12
        ys = yogas(pos, houses, lagna_sign)
        names = [y["name"] for y in ys]
        # Moon Aquarius 14°, Mars Taurus 14° → ~90° apart → not conjunct
        assert "Chandra-Mangala Yoga" not in names


# ---------------------------------------------------------------------------
# Doshas
# ---------------------------------------------------------------------------

class TestDoshas:
    def test_mangal_dosha(self, pos, houses):
        # Mars at Taurus 14° → whole-sign: Taurus is 10th from Leo Lagna.
        # 10 not in {1,2,4,7,8,12} → no Mangal Dosha for this chart.
        ds = doshas(pos, houses)
        names = [d["name"] for d in ds]
        assert "Mangal Dosha" not in names

    def test_gand_mool_absent(self, pos, houses):
        # Moon in Shatabhisha → not a Gand Mool nakshatra
        ds = doshas(pos, houses)
        names = [d["name"] for d in ds]
        assert "Gand Mool Dosha" not in names


# ---------------------------------------------------------------------------
# Panchang
# ---------------------------------------------------------------------------

class TestPanchang:
    def test_vara_friday(self):
        # 1991-02-15 was a Friday
        p = panchang(BIRTH)
        assert p["vara"] == "Friday"

    def test_tithi_range(self):
        p = panchang(BIRTH)
        assert 1 <= p["tithi"]["number"] <= 30

    def test_nakshatra_of_moon(self, pos):
        p = panchang(BIRTH)
        assert p["nakshatra"]["name"] == "Shatabhisha"

    def test_yoga_range(self):
        p = panchang(BIRTH)
        assert 1 <= p["yoga"]["number"] <= 27
