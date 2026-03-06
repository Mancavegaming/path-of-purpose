"""
Build PoE trade search queries from parsed Item models.

- UNIQUE items: search by exact name only
- RARE items: search by base type + stat filters from explicit mods
  Uses "count" group with min = floor(len(mods) * 0.6) for flexible matching
"""

from __future__ import annotations

import logging
import math
import re

from pop.build_parser.models import Item
from pop.trade.models import StatFilter, StatGroup, TradeQuery, TradeSearchRequest
from pop.trade.stat_cache import StatCache

logger = logging.getLogger(__name__)


def _extract_numeric_value(mod_text: str) -> float | None:
    """Extract the first numeric value from a mod line.

    Examples:
        "+120 to maximum Life" → 120.0
        "Adds 10 to 20 Fire Damage" → 10.0  (uses first number)
        "10% increased Attack Speed" → 10.0
    """
    match = re.search(r"[\d.]+", mod_text)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


async def build_trade_query(
    item: Item,
    stat_cache: StatCache,
    league: str = "Standard",
) -> tuple[TradeSearchRequest, str]:
    """Convert a build Item into a trade search request.

    Args:
        item: The item from a PoB build export.
        stat_cache: Loaded stat cache for mod → stat ID resolution.
        league: Trade league to search in.

    Returns:
        Tuple of (TradeSearchRequest, trade_url) where trade_url is the
        browser-friendly URL for opening on the trade site.
    """
    await stat_cache.ensure_loaded()

    rarity = item.rarity.upper()

    if rarity == "UNIQUE":
        return _build_unique_query(item, league)
    else:
        return await _build_rare_query(item, stat_cache, league)


def _build_unique_query(
    item: Item,
    league: str,
) -> tuple[TradeSearchRequest, str]:
    """Build a simple name-only query for unique items."""
    query = TradeQuery(name=item.name)
    request = TradeSearchRequest(query=query)
    trade_url = (
        f"https://www.pathofexile.com/trade/search/{league}"
        f"?q={{\"query\":{{\"name\":\"{item.name}\",\"status\":{{\"option\":\"online\"}}}}}}"
    )
    return request, trade_url


async def _build_rare_query(
    item: Item,
    stat_cache: StatCache,
    league: str,
) -> tuple[TradeSearchRequest, str]:
    """Build a stat-filtered query for rare/magic items."""
    filters: list[StatFilter] = []

    for mod in item.explicits:
        stat_type = "explicit"
        if mod.is_crafted:
            stat_type = "crafted"

        entry = stat_cache.match_mod(mod.text, stat_type)
        if entry is None:
            logger.warning("No stat match for mod: '%s' — skipping", mod.text)
            continue

        # Extract numeric value and set min at 70% of the roll
        value_spec: dict[str, float] | None = None
        num = _extract_numeric_value(mod.text)
        if num is not None and num > 0:
            value_spec = {"min": round(num * 0.7, 1)}

        filters.append(StatFilter(id=entry.id, value=value_spec))

    # Use "count" mode: require at least 60% of the mods to match
    min_count = max(1, math.floor(len(filters) * 0.6))
    stat_group = StatGroup(
        type="count",
        filters=filters,
        value={"min": min_count},
    )

    query = TradeQuery(
        type=item.base_type or None,
        stats=[stat_group] if filters else [],
    )
    request = TradeSearchRequest(query=query)
    trade_url = f"https://www.pathofexile.com/trade/search/{league}"
    return request, trade_url
