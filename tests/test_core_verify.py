"""Tests verifying the core against Astro Seek reference data.

Reference: Gergely, Kisvárda, 1991-02-15 17:45 CET
Verified on Astro Seek with Sidereal / Lahiri / Whole Sign settings.
Max tolerated delta: 30 arc-seconds (0.0083°).
"""
import pytest
from astrologica.core import BirthData, compute_positions, compute_houses, get_ayanamsa

BIRTH = BirthData("1991-02-15", "17:45:00", 48.2264, 22.0847, "Europe/Budapest")
MAX_DELTA = 0.0083  # 30 arc-seconds

# (planet_name, expected_sidereal_longitude)
ASTRO_SEEK_SIDEREAL = {
    "Sun":     302.7617,  # Aquarius 2°45'42"
    "Moon":    314.1650,  # Aquarius 14°09'54"
    "Mercury": 291.7911,  # Capricorn 21°47'28"
    "Venus":   328.0089,  # Aquarius 28°00'32"
    "Mars":     44.3306,  # Taurus 14°19'50"
    "Jupiter": 102.5761,  # Cancer 12°34'34"
    "Saturn":  277.2744,  # Capricorn 7°16'28"
    "Uranus":  258.5303,  # Sagittarius 18°31'49"
    "Neptune": 262.0089,  # Sagittarius 22°00'32"
    "Pluto":   206.6278,  # Libra 26°37'40"
}


@pytest.fixture
def sidereal_positions():
    return compute_positions(BIRTH, sidereal=True, ayanamsa="lahiri")


class TestAstroSeekMatch:
    def test_ayanamsa_value(self):
        jd = BIRTH.julian_day()
        ay = get_ayanamsa(jd, "lahiri")
        # Astro Seek: 23°44' = 23.7333°
        assert abs(ay - 23.7333) < 0.002, f"Ayanamsa {ay}°, expected ~23.7333°"

    @pytest.mark.parametrize("planet_name,expected_lon", list(ASTRO_SEEK_SIDEREAL.items()))
    def test_sidereal_longitude(self, sidereal_positions, planet_name, expected_lon):
        p = sidereal_positions[planet_name]
        delta = abs(p.longitude - expected_lon)
        assert delta < MAX_DELTA, (
            f"{planet_name}: got {p.longitude:.4f}°, expected {expected_lon:.4f}°, "
            f"delta {delta * 3600:.1f}\" > {MAX_DELTA * 3600:.1f}\""
        )

    def test_lagna_sidereal(self):
        h = compute_houses(BIRTH, system="whole_sign", sidereal=True, ayanamsa="lahiri")
        # Lagna: Leo 13.23° = 133.23°
        assert abs(h.ascendant - 133.23) < 0.1, f"Lagna {h.ascendant}°, expected ~133.23°"

    def test_jupiter_retrograde(self, sidereal_positions):
        assert sidereal_positions["Jupiter"].retrograde is True

    def test_rahu_retrograde(self, sidereal_positions):
        assert sidereal_positions["Rahu"].retrograde is True
