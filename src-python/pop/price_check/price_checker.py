"""Price check orchestration — clipboard text → trade results.

Reuses existing StatCache (fuzzy mod→stat ID matching) and TradeClient.
"""

from __future__ import annotations

import logging
import math
import re

from pop.price_check.clipboard_parser import ClipboardItem, parse_clipboard_item
from pop.trade.models import (
    StatFilter,
    StatGroup,
    TradeQuery,
    TradeSearchRequest,
    TradeSearchResult,
)
from pop.trade.stat_cache import StatCache
from pop.trade.client import TradeClient

logger = logging.getLogger(__name__)


async def price_check(
    clipboard_text: str,
    league: str = "Standard",
    enabled_mod_indices: list[int] | None = None,
) -> dict:
    """Parse clipboard item text and query the trade API for prices.

    Args:
        clipboard_text: Raw text from PoE in-game Ctrl+C.
        league: Trade league to search.
        enabled_mod_indices: If set, only include these explicit mod indices
            in the search. None = include all.

    Returns:
        Dict with keys: item, results, price_summary, clipboard_text, error.
    """
    try:
        item = parse_clipboard_item(clipboard_text)
    except (ValueError, Exception) as exc:
        return {"error": f"Failed to parse clipboard: {exc}", "clipboard_text": clipboard_text}

    item_dict = _item_to_dict(item)

    # Currency/divination cards — no trade query, just info
    if item.is_currency:
        return {
            "item": item_dict,
            "results": None,
            "price_summary": None,
            "clipboard_text": clipboard_text,
            "trade_url": f"https://www.pathofexile.com/trade/search/{league}?q={{\"query\":{{\"type\":\"{item.base_type}\"}}}}",
            "error": None,
        }

    stat_cache = StatCache()
    request, trade_url = await _build_query(item, stat_cache, league, enabled_mod_indices)

    try:
        async with TradeClient(league=league) as client:
            result = await client.search(request)
            # trade_url is already set by TradeClient with the query ID — don't overwrite
    except Exception as exc:
        return {
            "item": item_dict,
            "results": None,
            "price_summary": None,
            "clipboard_text": clipboard_text,
            "error": str(exc),
        }

    price_summary = _compute_price_summary(result)

    return {
        "item": item_dict,
        "results": result.model_dump(mode="json"),
        "price_summary": price_summary,
        "clipboard_text": clipboard_text,
        "error": None,
    }


async def _build_query(
    item: ClipboardItem,
    stat_cache: StatCache,
    league: str,
    enabled_mod_indices: list[int] | None,
) -> tuple[TradeSearchRequest, str]:
    """Build a trade search request from a clipboard item."""
    await stat_cache.ensure_loaded()

    base_url = f"https://www.pathofexile.com/trade/search/{league}"

    # --- Unique items: search by name only ---
    if item.rarity == "Unique" and item.name:
        query = TradeQuery(name=item.name)
        request = TradeSearchRequest(query=query)
        return request, base_url

    # --- Gems: search by name + level + quality ---
    if item.is_gem:
        filters: dict = {}
        gem_filters: dict = {}
        if item.gem_level > 0:
            gem_filters["gem_level"] = {"min": item.gem_level}
        if item.gem_quality > 0:
            gem_filters["quality"] = {"min": item.gem_quality}
        if gem_filters:
            filters["misc_filters"] = {"filters": gem_filters}

        query = TradeQuery(type=item.base_type, filters=filters)
        request = TradeSearchRequest(query=query)
        return request, base_url

    # --- Rare/Magic items: search by base type + stat filters ---
    mods_to_search = _get_searchable_mods(item, enabled_mod_indices)
    stat_filters: list[StatFilter] = []

    for mod_text in mods_to_search:
        entry = stat_cache.match_mod(mod_text, "explicit")
        if not entry:
            # Try implicit
            entry = stat_cache.match_mod(mod_text, "implicit")
        if not entry:
            continue

        # Extract numeric value and set min at 80%
        value = _extract_mod_value(mod_text)
        filt_value = None
        if value is not None and value > 0:
            filt_value = {"min": math.floor(value * 0.8)}

        stat_filters.append(StatFilter(id=entry.id, value=filt_value))

    stat_groups: list[StatGroup] = []
    if stat_filters:
        # Use "count" group: require at least 60% of filters to match
        min_count = max(1, math.floor(len(stat_filters) * 0.6))
        stat_groups.append(
            StatGroup(
                type="count",
                filters=stat_filters,
                value={"min": min_count},
            )
        )

    base_type = item.base_type if item.rarity != "Unique" else None
    query = TradeQuery(type=base_type, stats=stat_groups)

    # Add influence filter
    if item.influences:
        misc_filters: dict = {}
        for inf in item.influences:
            key = f"{inf.lower()}_item"
            misc_filters[key] = {"option": "true"}
        query.filters = {"misc_filters": {"filters": misc_filters}}

    request = TradeSearchRequest(query=query)
    return request, base_url


def _get_searchable_mods(
    item: ClipboardItem,
    enabled_mod_indices: list[int] | None,
) -> list[str]:
    """Get the list of mods to include in search."""
    all_explicits = item.explicits + item.crafted_mods
    if enabled_mod_indices is not None:
        return [
            all_explicits[i]
            for i in enabled_mod_indices
            if 0 <= i < len(all_explicits)
        ]
    return all_explicits


def _extract_mod_value(mod_text: str) -> float | None:
    """Extract the first numeric value from a mod text line."""
    # Handle ranges like "(10-20)"
    m = re.search(r"\((\d+)-(\d+)\)", mod_text)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2

    # Handle single values like "+120" or "45%"
    m = re.search(r"[+-]?(\d+(?:\.\d+)?)", mod_text)
    if m:
        return float(m.group(1))
    return None


def _compute_price_summary(result: TradeSearchResult) -> dict | None:
    """Compute min/median/max prices from first 10 listings."""
    prices: list[float] = []
    currency = "chaos"

    for listing in result.listings[:10]:
        if listing.price:
            prices.append(listing.price.amount)
            currency = listing.price.currency

    if not prices:
        return None

    prices.sort()
    n = len(prices)
    median = prices[n // 2] if n % 2 == 1 else (prices[n // 2 - 1] + prices[n // 2]) / 2

    return {
        "min": prices[0],
        "max": prices[-1],
        "median": round(median, 1),
        "currency": currency,
        "count": result.total,
    }


def _item_to_dict(item: ClipboardItem) -> dict:
    """Convert a ClipboardItem to a JSON-serializable dict."""
    return {
        "item_class": item.item_class,
        "rarity": item.rarity,
        "name": item.name,
        "base_type": item.base_type,
        "quality": item.quality,
        "ilvl": item.ilvl,
        "sockets": item.sockets,
        "implicits": item.implicits,
        "explicits": item.explicits,
        "crafted_mods": item.crafted_mods,
        "corrupted": item.corrupted,
        "influences": item.influences,
        "unidentified": item.unidentified,
        "note": item.note,
        "is_gem": item.is_gem,
        "is_currency": item.is_currency,
        "is_map": item.is_map,
    }
