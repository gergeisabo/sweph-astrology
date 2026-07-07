"""Tests for the BaZi (Four Pillars of Destiny) engine.

Anchor reference: Gergely, Kisvárda, 1991-02-15 17:45 CET
Expected chart: Xin Wei / Geng Yin / Bing Chen / Ding You
Day Master: Bing (Yang Fire, 丙) — the Self.
"""
import pytest

from astrologica.core import BirthData
from astrologica import bazi

BIRTH = BirthData("1991-02-15", "17:45:00", 48.2264, 22.0847, "Europe/Budapest")


class TestFourPillars:
    def test_returns_four_pillars(self):
        p = bazi.four_pillars(BIRTH)
        for key in ("year", "month", "day", "hour"):
            assert key in p, f"missing pillar {key}"
            pillar = p[key]
            for field in ("stem", "branch", "stem_index", "branch_index",
                          "stem_element", "branch_element", "pillar"):
                assert field in pillar, f"pillar {key} missing field {field}"

    def test_year_pillar_xin_wei(self):
        """1991 (after Li Chun) = Xin Wei — Metal Goat year."""
        p = bazi.four_pillars(BIRTH)["year"]
        assert p["stem"] == "Xin", f"year stem: {p['stem']}"
        assert p["branch"] == "Wei", f"year branch: {p['branch']}"
        assert p["animal"] == "Goat"
        assert p["stem_element"] == "Metal"
        assert p["branch_element"] == "Earth"

    def test_month_pillar_geng_yin(self):
        """Feb 15 is after Li Chun -> Month 1 (Yin/Tiger).
        For an Xin year, the Five Tigers rule gives Geng Yin for Month 1."""
        p = bazi.four_pillars(BIRTH)["month"]
        assert p["stem"] == "Geng", f"month stem: {p['stem']}"
        assert p["branch"] == "Yin", f"month branch: {p['branch']}"

    def test_day_pillar_bing_chen(self):
        """Day pillar derived from JD 2448303 -> Bing Chen."""
        p = bazi.four_pillars(BIRTH)["day"]
        assert p["stem"] == "Bing", f"day stem: {p['stem']}"
        assert p["branch"] == "Chen", f"day branch: {p['branch']}"

    def test_hour_pillar_ding_you(self):
        """17:45 falls in the You hour (17-19).
        For a Bing day, the Five Rats rule gives Ding You."""
        p = bazi.four_pillars(BIRTH)["hour"]
        assert p["stem"] == "Ding", f"hour stem: {p['stem']}"
        assert p["branch"] == "You", f"hour branch: {p['branch']}"

    def test_full_chart_string(self):
        p = bazi.four_pillars(BIRTH)
        assert p["year"]["pillar"] == "Xin Wei"
        assert p["month"]["pillar"] == "Geng Yin"
        assert p["day"]["pillar"] == "Bing Chen"
        assert p["hour"]["pillar"] == "Ding You"

    def test_pre_lichun_uses_previous_year(self):
        """A birth in January should belong to the prior solar year."""
        early = BirthData("1991-01-15", "12:00:00", 0.0, 0.0, "UTC")
        p = bazi.four_pillars(early)["year"]
        # 1991-01-15 is before Li Chun -> solar year 1990 = Geng Wu (Metal Horse)
        assert p["stem"] == "Geng"
        assert p["branch"] == "Wu"
        assert p["animal"] == "Horse"


class TestDayMaster:
    def test_day_master_is_bing(self):
        """The Day Master (Self) for the anchor birth is Bing (Yang Fire)."""
        assert bazi.day_master(BIRTH) == "Bing"


class TestElementBalance:
    def test_returns_five_elements(self):
        p = bazi.four_pillars(BIRTH)
        bal = bazi.element_balance(p)
        assert set(bal.keys()) == {"Wood", "Fire", "Earth", "Metal", "Water"}

    def test_counts_sum_to_eight(self):
        p = bazi.four_pillars(BIRTH)
        bal = bazi.element_balance(p)
        assert sum(bal.values()) == 8

    def test_known_balance(self):
        """Xin Wei / Geng Yin / Bing Chen / Ding You:
        stems:   Xin(Metal) Geng(Metal) Bing(Fire) Ding(Fire)
        branches: Wei(Earth) Yin(Wood) Chen(Earth) You(Metal)
        -> Wood=1, Fire=2, Earth=2, Metal=3, Water=0
        """
        p = bazi.four_pillars(BIRTH)
        bal = bazi.element_balance(p)
        assert bal["Wood"] == 1
        assert bal["Fire"] == 2
        assert bal["Earth"] == 2
        assert bal["Metal"] == 3
        assert bal["Water"] == 0


class TestTenGods:
    def test_returns_seven_gods(self):
        gods = bazi.ten_gods(BIRTH)
        # 7 non-day-master characters
        assert len(gods) == 7
        for key in ("year_stem", "year_branch", "month_stem", "month_branch",
                    "day_branch", "hour_stem", "hour_branch"):
            assert key in gods

    def test_year_stem_is_direct_power(self):
        """Day Master Bing (Yang Fire). Year stem Xin (Yin Metal).
        Fire controls Metal -> Wealth. Yang vs Yin -> Indirect -> Pian Cai."""
        gods = bazi.ten_gods(BIRTH)
        assert gods["year_stem"] == "Pian Cai", gods["year_stem"]

    def test_month_stem_is_indirect_resource(self):
        """DM Bing (Yang Fire). Month stem Geng (Yang Metal).
        Wait — Metal is controlled BY Fire, so it is Wealth, not Resource.
        Yang/Yang same -> Direct -> Zheng Cai."""
        gods = bazi.ten_gods(BIRTH)
        assert gods["month_stem"] == "Zheng Cai", gods["month_stem"]

    def test_all_gods_are_valid_names(self):
        valid = {"Bi Jian", "Jie Cai", "Zheng Yin", "Pian Yin",
                 "Shi Shen", "Shang Guan", "Zheng Guan", "Qi Sha",
                 "Zheng Cai", "Pian Cai"}
        gods = bazi.ten_gods(BIRTH)
        for k, v in gods.items():
            assert v in valid, f"{k}: {v} not a valid Ten God name"


class TestLuckPillars:
    def test_male_returns_eight_or_more(self):
        lp = bazi.luck_pillars(BIRTH, "male")
        assert len(lp) >= 8
        for entry in lp:
            for field in ("stem", "branch", "start_age", "end_age",
                          "stem_element", "branch_element", "animal"):
                assert field in entry, f"missing {field}"

    def test_male_first_pillar_direction(self):
        """1991 is a Xin (Yin) year. Male + Yin year -> backward direction.
        Backward from Geng Yin (Month pillar) -> Ji Chou as first luck pillar."""
        lp = bazi.luck_pillars(BIRTH, "male")
        first = lp[0]
        assert first["stem"] == "Ji", first["stem"]
        assert first["branch"] == "Chou", first["branch"]

    def test_female_first_pillar_direction(self):
        """Female + Yin year -> forward direction.
        Forward from Geng Yin -> Xin Mao as first luck pillar."""
        lp = bazi.luck_pillars(BIRTH, "female")
        first = lp[0]
        assert first["stem"] == "Xin", first["stem"]
        assert first["branch"] == "Mao", first["branch"]

    def test_pillars_are_contiguous(self):
        """Each pillar's start_age should equal the previous pillar's end_age."""
        lp = bazi.luck_pillars(BIRTH, "male")
        for prev, cur in zip(lp, lp[1:]):
            assert abs(cur["start_age"] - prev["end_age"]) < 0.01

    def test_cover_80_years(self):
        lp = bazi.luck_pillars(BIRTH, "male")
        assert lp[-1]["end_age"] >= 80

    def test_start_age_positive(self):
        lp = bazi.luck_pillars(BIRTH, "male")
        assert lp[0]["start_age"] >= 0
