"""Tests for astrologica.astrogeo — astrogeography and relocation."""
from astrologica.core import BirthData, compute_positions, SIGNS
from astrologica import astrogeo

BIRTH = BirthData(
    date="1991-02-15", time="18:45:00",
    lat=48.2264, lon=22.0847,
    tz="Europe/Budapest", place="Kisvárda",
)


class TestACGLines:
    def test_returns_dict(self):
        acg = astrogeo.acg_lines(BIRTH, planets=["Sun", "Moon"])
        assert isinstance(acg, dict)
        assert "Sun" in acg
        assert "Moon" in acg

    def test_lines_have_angle_type(self):
        acg = astrogeo.acg_lines(BIRTH, planets=["Sun"])
        for line in acg["Sun"]:
            assert line["angle"] in ["ASC", "MC", "DSC", "IC"]

    def test_longitude_in_range(self):
        acg = astrogeo.acg_lines(BIRTH, planets=["Sun"])
        for line in acg["Sun"]:
            assert -180 <= line["longitude"] <= 180

    def test_sun_has_asc_line(self):
        """Sun should have at least one ASC line somewhere on Earth."""
        acg = astrogeo.acg_lines(BIRTH, planets=["Sun"], step_deg=1.0)
        asc_lines = [l for l in acg["Sun"] if l["angle"] == "ASC"]
        assert len(asc_lines) >= 1


class TestLocalSpaceLines:
    def test_returns_all_planets(self):
        ls = astrogeo.local_space_lines(BIRTH)
        assert isinstance(ls, dict)
        assert "Sun" in ls
        assert "Moon" in ls

    def test_azimuth_in_range(self):
        ls = astrogeo.local_space_lines(BIRTH)
        for planet, data in ls.items():
            assert 0 <= data["azimuth"] <= 360

    def test_has_direction(self):
        ls = astrogeo.local_space_lines(BIRTH)
        for planet, data in ls.items():
            assert data["direction"] in [
                "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
            ]


class TestGeodeticChart:
    def test_returns_geodetic_data(self):
        g = astrogeo.geodetic_chart(BIRTH)
        assert "natal_mc" in g
        assert "geodetic_longitude" in g
        assert "geodetic_asc" in g

    def test_mc_sign_valid(self):
        g = astrogeo.geodetic_chart(BIRTH)
        assert g["natal_mc_sign"] in SIGNS


class TestParans:
    def test_returns_list(self):
        p = astrogeo.parans(BIRTH)
        assert isinstance(p, list)

    def test_paran_has_planets_and_event(self):
        p = astrogeo.parans(BIRTH)
        for paran in p:
            assert "planet1" in paran
            assert "planet2" in paran
            assert paran["event"] in ["rise", "transit", "set"]


class TestRelocationChart:
    def test_different_location_different_asc(self):
        """Relocating to a different longitude should change the ASC."""
        orig_houses = astrogeo.relocation_chart(BIRTH, BIRTH.lat, BIRTH.lon)
        # Relocate to New York
        ny = astrogeo.relocation_chart(BIRTH, 40.7128, -74.006)
        assert orig_houses["ascendant"] != ny["ascendant"]

    def test_positions_same_as_natal(self):
        """Planetary positions don't change with relocation (same UTC moment)."""
        ny = astrogeo.relocation_chart(BIRTH, 40.7128, -74.006)
        natal_pos = compute_positions(BIRTH)
        for name in ["Sun", "Moon"]:
            diff = abs(ny["positions"][name].longitude - natal_pos[name].longitude)
            assert diff < 0.01  # essentially same positions

    def test_relocation_has_asc_mc(self):
        r = astrogeo.relocation_chart(BIRTH, 35.6762, 139.6503)  # Tokyo
        assert "asc_sign" in r
        assert "mc_sign" in r
