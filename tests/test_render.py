"""Tests for render module."""
import os
import pytest
from astrologica.render import western_wheel_svg, vedic_wheel_svg, save_svg
from astrologica.western import natal_chart
from astrologica.core import BirthData

BIRTH = BirthData("1991-02-15", "17:45:00", 48.2264, 22.0847, "Europe/Budapest")


@pytest.fixture
def chart():
    return natal_chart(BIRTH)


@pytest.fixture
def planets(chart):
    return {
        name: {"longitude": p.longitude, "sign": p.sign_name,
               "degree": p.degree_in_sign, "retrograde": p.retrograde}
        for name, p in chart["planets"].items()
    }


class TestWesternWheel:
    def test_returns_svg_string(self, chart, planets):
        svg = western_wheel_svg(planets, chart["houses"].cusps, chart["houses"].ascendant)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")

    def test_contains_planet_symbols(self, chart, planets):
        svg = western_wheel_svg(planets, chart["houses"].cusps, chart["houses"].ascendant)
        assert "☉" in svg  # Sun
        assert "☽" in svg  # Moon

    def test_contains_asc_mc_markers(self, chart, planets):
        svg = western_wheel_svg(planets, chart["houses"].cusps, chart["houses"].ascendant)
        assert "ASC" in svg
        assert "MC" in svg

    def test_save_svg(self, chart, planets, tmp_path):
        svg = western_wheel_svg(planets, chart["houses"].cusps, chart["houses"].ascendant)
        path = str(tmp_path / "test.svg")
        save_svg(svg, path)
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert content.startswith("<svg")


class TestVedicWheel:
    def test_returns_svg_string(self, chart, planets):
        svg = vedic_wheel_svg(planets, chart["houses"].cusps)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")

    def test_contains_title(self, chart, planets):
        svg = vedic_wheel_svg(planets, chart["houses"].cusps, title="Test Chart")
        assert "Test Chart" in svg
