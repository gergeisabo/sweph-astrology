"""Tests for astrologica.western — Western tropical astrology engine.

Birth reference: Gergely, Kisvárda
    1991-02-15 17:45 CET (Europe/Budapest)
    48.2264 N, 22.0847 E
"""
from astrologica.core import BirthData, compute_positions
from astrologica import western

BIRTH = BirthData(
    date="1991-02-15",
    time="17:45:00",
    lat=48.2264,
    lon=22.0847,
    tz="Europe/Budapest",
)


class TestNatalChart:
    def test_returns_expected_keys(self):
        chart = western.natal_chart(BIRTH)
        for key in ("planets", "houses", "aspects", "dignities", "chart_point"):
            assert key in chart, f"missing key: {key}"

    def test_sun_in_aquarius_tropical(self):
        chart = western.natal_chart(BIRTH)
        sun = chart["planets"]["Sun"]
        assert sun.sign_name == "Aquarius", (
            f"Sun sign {sun.sign_name}, expected Aquarius (tropical)"
        )

    def test_jupiter_retrograde(self):
        chart = western.natal_chart(BIRTH)
        jup = chart["planets"]["Jupiter"]
        assert jup.retrograde is True, "Jupiter should be retrograde"

    def test_chart_point_is_float_longitude(self):
        chart = western.natal_chart(BIRTH)
        cp = chart["chart_point"]
        assert isinstance(cp, float)
        assert 0.0 <= cp < 360.0

    def test_sun_longitude_matches_reference(self):
        chart = western.natal_chart(BIRTH)
        sun = chart["planets"]["Sun"]
        # Tropical Aquarius 26°30' ≈ 326.5°
        assert abs(sun.longitude - 326.5) < 0.5, (
            f"Sun {sun.longitude:.2f}°, expected ~326.5° (Aquarius 26°30')"
        )


class TestAspects:
    def test_sun_moon_outside_default_orb(self):
        """
        Reference (tropical):
            Sun  Aquarius 26°30'  = 326.50°
            Moon Pisces    7°54'  = 337.90°
        Separation = 11.4° — outside every default aspect orb, so Sun-Moon
        must NOT appear in the default aspects() output.
        """
        pos = compute_positions(BIRTH, sidereal=False)
        asps = western.aspects(pos)
        pairs = {(a["planet1"], a["planet2"]) for a in asps}
        assert ("Sun", "Moon") not in pairs, (
            "Sun-Moon should not aspect with default orbs (11.4° separation)"
        )

    def test_aspects_well_formed(self):
        pos = compute_positions(BIRTH, sidereal=False)
        asps = western.aspects(pos)
        assert len(asps) > 0, "expected at least some aspects"
        for a in asps:
            assert set(a.keys()) == {"planet1", "planet2", "type", "orb", "applying"}
            assert a["type"] in (
                "conjunction", "opposition", "trine", "square",
                "sextile", "quincunx", "semisextile",
            )
            assert isinstance(a["applying"], bool)

    def test_custom_orb_finds_sun_moon(self):
        pos = compute_positions(BIRTH, sidereal=False)
        # Widen conjunction orb so the Sun-Moon ~11° gap registers.
        asps = western.aspects(pos, orbs={"conjunction": 12.0})
        labels = {
            (a["planet1"], a["planet2"]): a["type"]
            for a in asps
        }
        key = ("Sun", "Moon")
        assert key in labels, "Sun-Moon aspect missing with widened orb"
        assert labels[key] == "conjunction"


class TestEssentialDignities:
    def test_returns_all_planets(self):
        pos = compute_positions(BIRTH, sidereal=False)
        digs = western.essential_dignities(pos)
        assert set(digs.keys()) == set(pos.keys())

    def test_jupiter_tropical_leo_exile(self):
        """
        Reference (tropical, 1991-02-15 17:45 CET):
            Jupiter ≈ 126.3°  →  Leo 6°19'  (sign index 4)
        Traditional dignity of Jupiter in Leo:
            Leo is not a domicile   (Cancer & Sagittarius are)
            Leo is not an exaltation(Cancer is)
            Leo is not a detriment  (Capricorn & Gemini are)
            Leo is not a fall       (Capricorn is)
        → Jupiter is peregrine (None) in tropical Leo.
        """
        pos = compute_positions(BIRTH, sidereal=False)
        jup = pos["Jupiter"]
        assert jup.sign_name == "Leo", (
            f"Jupiter sign {jup.sign_name}, expected Leo (tropical)"
        )
        digs = western.essential_dignities(pos)
        assert digs["Jupiter"] is None, (
            f"Jupiter in Leo should be peregrine, got {digs['Jupiter']}"
        )

    def test_saturn_in_aquarius_domicile(self):
        """
        Tropical Saturn ≈ 301.0° → Aquarius 1°01' → domicile (traditional
        ruler of Aquarius).
        """
        pos = compute_positions(BIRTH, sidereal=False)
        sat = pos["Saturn"]
        assert sat.sign_name == "Aquarius"
        digs = western.essential_dignities(pos)
        assert digs["Saturn"] == "Domicile"


class TestTransits:
    def test_transits_return_structure(self):
        result = western.transits(BIRTH, "2024-07-01")
        for key in ("natal_positions", "transit_positions", "transit_date", "aspects"):
            assert key in result
        assert result["transit_date"] == "2024-07-01"
        assert isinstance(result["aspects"], list)


class TestSynastry:
    def test_synastry_structure(self):
        # Use the same birth for both as a smoke test.
        result = western.synastry(BIRTH, BIRTH)
        for key in ("chart1_planets", "chart2_planets", "aspects", "house_overlays"):
            assert key in result
        # Sun should fall in the same natal house of both charts.
        overlays = result["house_overlays"]
        assert "Sun" in overlays
        assert 1 <= overlays["Sun"] <= 12


class TestSolarReturn:
    def test_solar_return_sun_matches_natal(self):
        result = western.solar_return(BIRTH, 2024)
        delta = abs(result["return_sun_longitude"] - result["natal_sun_longitude"])
        # Normalize to shortest arc.
        if delta > 180:
            delta = 360 - delta
        assert delta < 0.01, (
            f"Return Sun {result['return_sun_longitude']:.4f}° vs natal "
            f"{result['natal_sun_longitude']:.4f}°, delta {delta:.4f}°"
        )

    def test_solar_return_year(self):
        result = western.solar_return(BIRTH, 2024)
        assert result["year"] == 2024


class TestProgressions:
    def test_progressions_advance_correctly(self):
        # 1 year after birth: progressed positions ≈ positions 1 day later.
        result = western.progressions(BIRTH, "1992-02-15")
        assert abs(result["years_elapsed"] - 1.0) < 0.01
        prog_sun = result["progressed_positions"]["Sun"].longitude
        # Sun advances ~1°/day → progressed Sun should be ~1° ahead of natal.
        natal = compute_positions(BIRTH, sidereal=False)
        diff = (prog_sun - natal["Sun"].longitude) % 360.0
        assert 0.5 < diff < 1.5, (
            f"Progressed Sun advancement {diff:.3f}°, expected ~1°"
        )
