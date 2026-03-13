"""Tests for the trade query builder."""

from __future__ import annotations

import pytest

from pop.build_parser.models import Item, ItemMod
from pop.trade.query_builder import _extract_numeric_value, build_trade_query
from pop.trade.stat_cache import StatCache

SAMPLE_STATS = [
    {"id": "explicit.stat_3299347043", "text": "+# to maximum Life", "type": "explicit"},
    {"id": "explicit.stat_3261801346", "text": "#% increased Attack Speed", "type": "explicit"},
    {"id": "explicit.stat_4220027924", "text": "+#% to Cold Resistance", "type": "explicit"},
    {"id": "explicit.stat_3372524247", "text": "+#% to Fire Resistance", "type": "explicit"},
    {"id": "explicit.stat_2974417149", "text": "+# to Strength", "type": "explicit"},
]


@pytest.fixture
def stat_cache() -> StatCache:
    c = StatCache()
    c._ingest(SAMPLE_STATS)
    return c


# ===========================================================================
# Value extraction
# ===========================================================================


class TestExtractNumericValue:
    def test_integer(self):
        assert _extract_numeric_value("+120 to maximum Life") == 120.0

    def test_decimal(self):
        assert _extract_numeric_value("1.5% of Life Regenerated") == 1.5

    def test_percentage(self):
        assert _extract_numeric_value("10% increased Attack Speed") == 10.0

    def test_no_number(self):
        assert _extract_numeric_value("Cannot be Knocked Back") is None

    def test_first_number_extracted(self):
        # "Adds 10 to 20 Fire Damage" → 10.0
        assert _extract_numeric_value("Adds 10 to 20 Fire Damage") == 10.0


# ===========================================================================
# Query building — Unique items
# ===========================================================================


class TestUniqueQuery:
    @pytest.mark.asyncio
    async def test_unique_item_name_search(self, stat_cache: StatCache):
        item = Item(
            name="Headhunter",
            base_type="Leather Belt",
            rarity="UNIQUE",
            slot="Belt",
        )
        request, trade_url = await build_trade_query(item, stat_cache, "Standard")

        assert request.query.name == "Headhunter"
        assert request.query.type is None
        assert len(request.query.stats) == 0
        assert "Standard" in trade_url

    @pytest.mark.asyncio
    async def test_unique_has_no_stat_filters(self, stat_cache: StatCache):
        item = Item(
            name="Goldrim",
            base_type="Leather Cap",
            rarity="UNIQUE",
        )
        request, _ = await build_trade_query(item, stat_cache)
        assert len(request.query.stats) == 0


# ===========================================================================
# Query building — Rare items
# ===========================================================================


class TestRareQuery:
    @pytest.mark.asyncio
    async def test_rare_uses_base_type(self, stat_cache: StatCache):
        item = Item(
            name="Doom Knot",
            base_type="Diamond Ring",
            rarity="RARE",
            explicits=[
                ItemMod(text="+120 to maximum Life"),
                ItemMod(text="+40% to Cold Resistance"),
            ],
        )
        request, _ = await build_trade_query(item, stat_cache, "Standard")

        assert request.query.type == "Diamond Ring"
        assert request.query.name is None

    @pytest.mark.asyncio
    async def test_rare_has_stat_filters(self, stat_cache: StatCache):
        item = Item(
            name="Doom Knot",
            base_type="Diamond Ring",
            rarity="RARE",
            explicits=[
                ItemMod(text="+120 to maximum Life"),
                ItemMod(text="10% increased Attack Speed"),
            ],
        )
        request, _ = await build_trade_query(item, stat_cache)

        assert len(request.query.stats) == 1
        group = request.query.stats[0]
        assert group.type == "count"
        assert len(group.filters) == 2

    @pytest.mark.asyncio
    async def test_rare_count_min_is_60_pct(self, stat_cache: StatCache):
        item = Item(
            base_type="Astral Plate",
            rarity="RARE",
            explicits=[
                ItemMod(text="+120 to maximum Life"),
                ItemMod(text="+40% to Cold Resistance"),
                ItemMod(text="+35% to Fire Resistance"),
                ItemMod(text="+50 to Strength"),
                ItemMod(text="10% increased Attack Speed"),
            ],
        )
        request, _ = await build_trade_query(item, stat_cache)

        group = request.query.stats[0]
        # 5 mods → floor(5 * 0.6) = 3
        assert group.value == {"min": 3}

    @pytest.mark.asyncio
    async def test_value_min_is_70_pct(self, stat_cache: StatCache):
        item = Item(
            base_type="Leather Belt",
            rarity="RARE",
            explicits=[ItemMod(text="+100 to maximum Life")],
        )
        request, _ = await build_trade_query(item, stat_cache)

        filt = request.query.stats[0].filters[0]
        assert filt.value is not None
        assert filt.value["min"] == 70.0  # 100 * 0.7

    @pytest.mark.asyncio
    async def test_unmatched_mods_skipped(self, stat_cache: StatCache):
        item = Item(
            base_type="Vaal Regalia",
            rarity="RARE",
            explicits=[
                ItemMod(text="+120 to maximum Life"),
                ItemMod(text="Some completely unrecognized mod xyz123"),
            ],
        )
        request, _ = await build_trade_query(item, stat_cache)

        group = request.query.stats[0]
        # Only the life mod should match
        assert len(group.filters) == 1


# ===========================================================================
# Guide-aware query building (items with stat_priority)
# ===========================================================================


class TestGuideAwareQuery:
    @pytest.mark.asyncio
    async def test_guide_item_uses_priority_split(self, stat_cache: StatCache):
        """Items with stat_priority should split into required + flexible groups."""
        item = Item(
            base_type="Eternal Burgonet",
            rarity="RARE",
            stat_priority=["life", "fire resistance", "cold resistance"],
            explicits=[
                ItemMod(text="+130 to maximum Life"),
                ItemMod(text="+46% to Fire Resistance"),
                ItemMod(text="+46% to Cold Resistance"),
                ItemMod(text="10% increased Attack Speed"),
                ItemMod(text="+50 to Strength"),
            ],
        )
        request, _ = await build_trade_query(item, stat_cache)

        # Should have 2 groups: "and" for priorities, "count" for flexible
        assert len(request.query.stats) == 2
        required = request.query.stats[0]
        flexible = request.query.stats[1]

        assert required.type == "and"
        assert flexible.type == "count"

    @pytest.mark.asyncio
    async def test_priority_stats_use_80pct_min(self, stat_cache: StatCache):
        """Priority stats should have higher min values (80% vs 60%)."""
        item = Item(
            base_type="Leather Belt",
            rarity="RARE",
            stat_priority=["life"],
            explicits=[
                ItemMod(text="+100 to maximum Life"),
                ItemMod(text="10% increased Attack Speed"),
            ],
        )
        request, _ = await build_trade_query(item, stat_cache)

        required = request.query.stats[0]
        assert required.type == "and"
        life_filter = required.filters[0]
        assert life_filter.value == {"min": 80.0}  # 100 * 0.8

    @pytest.mark.asyncio
    async def test_flexible_stats_use_60pct_min(self, stat_cache: StatCache):
        """Non-priority stats should have lower min values (60%)."""
        item = Item(
            base_type="Leather Belt",
            rarity="RARE",
            stat_priority=["life"],
            explicits=[
                ItemMod(text="+100 to maximum Life"),
                ItemMod(text="10% increased Attack Speed"),
            ],
        )
        request, _ = await build_trade_query(item, stat_cache)

        flexible = request.query.stats[1]
        assert flexible.type == "count"
        speed_filter = flexible.filters[0]
        assert speed_filter.value == {"min": 6.0}  # 10 * 0.6

    @pytest.mark.asyncio
    async def test_no_stat_priority_uses_standard_query(self, stat_cache: StatCache):
        """Items without stat_priority should use the standard count-based query."""
        item = Item(
            base_type="Diamond Ring",
            rarity="RARE",
            stat_priority=[],  # Empty
            explicits=[
                ItemMod(text="+120 to maximum Life"),
                ItemMod(text="+40% to Cold Resistance"),
            ],
        )
        request, _ = await build_trade_query(item, stat_cache)

        # Standard path: single count group
        assert len(request.query.stats) == 1
        assert request.query.stats[0].type == "count"

    @pytest.mark.asyncio
    async def test_priority_max_3_required(self, stat_cache: StatCache):
        """At most 3 priority filters should be in the required group."""
        item = Item(
            base_type="Astral Plate",
            rarity="RARE",
            stat_priority=[
                "life", "fire resistance", "cold resistance",
                "attack speed", "strength",
            ],
            explicits=[
                ItemMod(text="+130 to maximum Life"),
                ItemMod(text="+46% to Fire Resistance"),
                ItemMod(text="+46% to Cold Resistance"),
                ItemMod(text="10% increased Attack Speed"),
                ItemMod(text="+50 to Strength"),
            ],
        )
        request, _ = await build_trade_query(item, stat_cache)

        required = request.query.stats[0]
        assert required.type == "and"
        assert len(required.filters) <= 3
