"""Tests for the trade stat cache and fuzzy matching."""

from __future__ import annotations

import pytest

from pop.trade.stat_cache import StatCache, _normalize_mod


# ===========================================================================
# Normalization tests
# ===========================================================================


class TestNormalizeMod:
    def test_strips_numbers(self):
        assert _normalize_mod("+120 to maximum Life") == "+# to maximum life"

    def test_strips_decimals(self):
        assert _normalize_mod("1.5% of Life Regenerated per second") == (
            "#% of life regenerated per second"
        )

    def test_collapses_whitespace(self):
        assert _normalize_mod("Adds  10  to  20  Fire Damage") == "adds # to # fire damage"

    def test_already_has_placeholder(self):
        assert _normalize_mod("+# to maximum Life") == "+# to maximum life"

    def test_empty_string(self):
        assert _normalize_mod("") == ""

    def test_no_numbers(self):
        assert _normalize_mod("Cannot be Knocked Back") == "cannot be knocked back"


# ===========================================================================
# Stat cache fuzzy matching
# ===========================================================================

SAMPLE_STATS = [
    {"id": "explicit.stat_3299347043", "text": "+# to maximum Life", "type": "explicit"},
    {"id": "explicit.stat_1671376347", "text": "+# to maximum Mana", "type": "explicit"},
    {"id": "explicit.stat_3261801346", "text": "#% increased Attack Speed", "type": "explicit"},
    {"id": "explicit.stat_2974417149", "text": "+# to Strength", "type": "explicit"},
    {"id": "implicit.stat_3299347043", "text": "+# to maximum Life", "type": "implicit"},
    {"id": "explicit.stat_1940865751", "text": "Adds # to # Fire Damage", "type": "explicit"},
    {"id": "explicit.stat_4220027924", "text": "+#% to Cold Resistance", "type": "explicit"},
    {"id": "explicit.stat_3372524247", "text": "+#% to Fire Resistance", "type": "explicit"},
    {"id": "explicit.stat_1671376347m", "text": "#% increased maximum Life", "type": "explicit"},
    {"id": "crafted.stat_3299347043", "text": "+# to maximum Life", "type": "crafted"},
]


class TestStatCacheMatching:
    @pytest.fixture
    def cache(self) -> StatCache:
        c = StatCache()
        c._ingest(SAMPLE_STATS)
        return c

    def test_exact_match_life(self, cache: StatCache):
        result = cache.match_mod("+120 to maximum Life", "explicit")
        assert result is not None
        assert result.id == "explicit.stat_3299347043"

    def test_exact_match_mana(self, cache: StatCache):
        result = cache.match_mod("+45 to maximum Mana", "explicit")
        assert result is not None
        assert result.id == "explicit.stat_1671376347"

    def test_attack_speed(self, cache: StatCache):
        result = cache.match_mod("10% increased Attack Speed", "explicit")
        assert result is not None
        assert result.id == "explicit.stat_3261801346"

    def test_fire_damage_range(self, cache: StatCache):
        result = cache.match_mod("Adds 10 to 20 Fire Damage", "explicit")
        assert result is not None
        assert result.id == "explicit.stat_1940865751"

    def test_type_filtering_explicit(self, cache: StatCache):
        result = cache.match_mod("+50 to maximum Life", "explicit")
        assert result is not None
        assert result.type == "explicit"

    def test_type_filtering_implicit(self, cache: StatCache):
        result = cache.match_mod("+50 to maximum Life", "implicit")
        assert result is not None
        assert result.type == "implicit"

    def test_type_filtering_crafted(self, cache: StatCache):
        result = cache.match_mod("+50 to maximum Life", "crafted")
        assert result is not None
        assert result.type == "crafted"

    def test_no_match_returns_none(self, cache: StatCache):
        result = cache.match_mod("Some completely unrelated mod text xyz", "explicit")
        assert result is None

    def test_resistance_matching(self, cache: StatCache):
        result = cache.match_mod("+40% to Fire Resistance", "explicit")
        assert result is not None
        assert "Fire Resistance" in result.text

    def test_cold_resistance(self, cache: StatCache):
        result = cache.match_mod("+35% to Cold Resistance", "explicit")
        assert result is not None
        assert "Cold Resistance" in result.text

    def test_loaded_property(self, cache: StatCache):
        assert cache.loaded is True

    def test_empty_cache_not_loaded(self):
        c = StatCache()
        assert c.loaded is False
