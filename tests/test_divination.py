"""Tests for divination module — Tarot, I Ching, Runes, Geomancy."""
import pytest
from astrologica.divination import (
    tarot_draw, iching_throw_coins, iching_lookup, iching_by_question,
    runes_draw, geomancy_cast, geomancy_lookup,
    DECKS, HEXAGRAMS, RUNE_SETS, GEOMANTIC_FIGURES,
)


class TestTarot:
    def test_rider_waite_deck_has_78_cards(self):
        deck = DECKS["rider_waite"]()
        assert len(deck) == 78

    def test_marseille_deck_has_78_cards(self):
        deck = DECKS["marseille"]()
        assert len(deck) == 78

    def test_lenormand_deck_has_36_cards(self):
        deck = DECKS["lenormand"]()
        assert len(deck) == 36

    def test_draw_returns_correct_count(self):
        cards = list(tarot_draw(n=3, seed=42))
        assert len(cards) == 3

    def test_card_has_required_fields(self):
        cards = list(tarot_draw(n=1, seed=42))
        card = cards[0]
        assert "card" in card
        assert "number" in card
        assert "keywords" in card
        assert "reversed" in card
        assert "position" in card

    def test_single_card_draw(self):
        cards = list(tarot_draw(n=1, seed=99))
        assert len(cards) == 1

    def test_three_card_spread(self):
        cards = list(tarot_draw(n=3, seed=7))
        assert len(cards) == 3
        assert cards[0]["position"] == 1
        assert cards[1]["position"] == 2
        assert cards[2]["position"] == 3


class TestIChing:
    def test_throw_returns_valid_hexagram(self):
        result = iching_throw_coins(seed=42)
        assert 1 <= result["primary"]["number"] <= 64
        assert 1 <= result["resulting"]["number"] <= 64

    def test_throw_has_lines(self):
        result = iching_throw_coins(seed=42)
        assert len(result["lines"]) == 6
        for line in result["lines"]:
            assert line in (6, 7, 8, 9)

    def test_lookup_all_64(self):
        for num in range(1, 65):
            hexagram = iching_lookup(num)
            assert hexagram["number"] == num
            assert len(hexagram["name"]) > 0

    def test_lookup_known_hexagram(self):
        h = iching_lookup(1)
        assert h["name"] == "The Creative"
        assert h["chinese"] == "創"

    def test_by_question_returns_result(self):
        result = iching_by_question("Should I take the job?", seed=42)
        assert 1 <= result["primary"]["number"] <= 64

    def test_changing_lines_valid(self):
        result = iching_throw_coins(seed=42)
        for line_num in result["changing_lines"]:
            assert 1 <= line_num <= 6

    def test_no_changing_means_same_result(self):
        """When no changing lines, primary == resulting."""
        # Find a seed with no changing lines
        for seed in range(100):
            result = iching_throw_coins(seed=seed)
            if not result["changing_lines"]:
                assert result["primary"]["number"] == result["resulting"]["number"]
                return


class TestRunes:
    def test_elder_futhark_has_24(self):
        assert len(RUNE_SETS["elder_futhark"]) == 24

    def test_younger_futhark_has_16(self):
        assert len(RUNE_SETS["younger_futhark"]) == 16

    def test_anglo_saxon_has_33(self):
        assert len(RUNE_SETS["anglo_saxon_futhorc"]) == 33

    def test_draw_returns_correct_count(self):
        runes = list(runes_draw(n=3, seed=42))
        assert len(runes) == 3

    def test_rune_has_required_fields(self):
        runes = list(runes_draw(n=1, seed=42))
        rune = runes[0]
        assert "rune" in rune
        assert "symbol" in rune
        assert "meaning" in rune
        assert "element" in rune
        assert "deity" in rune

    def test_single_rune_draw(self):
        runes = list(runes_draw(n=1, seed=99))
        assert len(runes) == 1


class TestGeomancy:
    def test_cast_returns_all_components(self):
        result = geomancy_cast(seed=42)
        assert len(result["mothers"]) == 4
        assert len(result["daughters"]) == 4
        assert len(result["nephews"]) == 4
        assert len(result["witnesses"]) == 2
        assert "judge" in result

    def test_cast_judge_is_valid_figure(self):
        result = geomancy_cast(seed=42)
        assert result["judge"] in GEOMANTIC_FIGURES

    def test_cast_judge_has_detail(self):
        result = geomancy_cast(seed=42)
        assert "element" in result["judge_detail"]
        assert "meaning" in result["judge_detail"]

    def test_lookup_all_16_figures(self):
        for name in GEOMANTIC_FIGURES:
            fig = geomancy_lookup(name)
            assert fig["name"] == name
            assert "element" in fig
            assert "meaning" in fig

    def test_lookup_invalid_name_raises(self):
        with pytest.raises(ValueError):
            geomancy_lookup("NonExistent")

    def test_casts_are_reproducible(self):
        r1 = geomancy_cast(seed=42)
        r2 = geomancy_cast(seed=42)
        assert r1 == r2

    def test_mothers_are_valid_names(self):
        result = geomancy_cast(seed=42)
        for mother in result["mothers"]:
            assert mother in GEOMANTIC_FIGURES
