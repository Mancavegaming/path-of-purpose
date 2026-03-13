"""
Build PoE trade search queries from parsed Item models.

- UNIQUE items: search by exact name only
- RARE items: search by base type + stat filters from explicit mods
  - Guide-aware: if item has stat_priority, split into required (top priorities)
    and flexible (remaining) stat groups for better trade results
  - Standard: "count" group with min = floor(len(mods) * 0.6) for flexible matching
"""

from __future__ import annotations

import logging
import math
import re

from pop.build_parser.models import Item
from pop.trade.models import StatFilter, StatGroup, TradeQuery, TradeSearchRequest
from pop.trade.stat_cache import StatCache


def _sanitize_base_type(
    base_type: str | None,
    item_name: str = "",
    rarity: str = "",
) -> str | None:
    """Clean up base type for trade API queries.

    - Returns None for UNIQUE items (they search by name, not base type)
    - Returns None if it looks like PoB metadata (contains ':')
    - Strips the item's unique/rare name prefix if present
      (PoB sometimes combines "Unique Name Base Type" on one line)
    - Returns None if base_type equals item_name (not a real base type)
    """
    if not base_type:
        return None
    # Unique items never need a type filter — they search by name
    if rarity.upper() == "UNIQUE":
        return None
    if ":" in base_type:
        return None
    # If base_type IS the item name, it's not a real base type
    if item_name and base_type == item_name:
        return None
    # If base_type starts with the item name, strip it
    # e.g. "Storm Crown Bone Helmet" with name "Storm Crown" → "Bone Helmet"
    if item_name and base_type.startswith(item_name):
        stripped = base_type[len(item_name):].strip()
        if stripped:
            return stripped
        return None  # nothing left after stripping = not a real base type
    return base_type


def _clean_mod_text(text: str) -> str:
    """Strip PoB internal tags and resolve range formats from a mod line.

    Handles: {tags:attack,speed}{crafted}{range:0.5}(8-10)% increased Attack Speed
    Returns: 10% increased Attack Speed
    """
    clean = re.sub(r"\{[^}]*\}", "", text).strip()
    clean = re.sub(r"\((\d+)-(\d+)\)", lambda m: m.group(2), clean)
    return clean if clean else text

logger = logging.getLogger(__name__)

# Keywords in stat_priority that map to mod text substrings.
# Used to match priority strings to actual mod lines.
_PRIORITY_MOD_KEYWORDS: dict[str, list[str]] = {
    "life": ["maximum Life"],
    "maximum life": ["maximum Life"],
    "energy shield": ["Energy Shield"],
    "flat es": ["Energy Shield"],
    "% energy shield": ["increased maximum Energy Shield"],
    "mana": ["maximum Mana"],
    "fire resistance": ["Fire Resistance"],
    "fire res": ["Fire Resistance"],
    "cold resistance": ["Cold Resistance"],
    "cold res": ["Cold Resistance"],
    "lightning resistance": ["Lightning Resistance"],
    "lightning res": ["Lightning Resistance"],
    "chaos resistance": ["Chaos Resistance"],
    "chaos res": ["Chaos Resistance"],
    "elemental resistances": ["Fire Resistance", "Cold Resistance", "Lightning Resistance"],
    "all resistances": ["all Elemental Resistances"],
    "all res": ["all Elemental Resistances"],
    "attack speed": ["Attack Speed"],
    "increased attack speed": ["Attack Speed"],
    "cast speed": ["Cast Speed"],
    "increased cast speed": ["Cast Speed"],
    "movement speed": ["Movement Speed"],
    "move speed": ["Movement Speed"],
    "crit chance": ["Critical Strike Chance"],
    "critical strike chance": ["Critical Strike Chance"],
    "global crit": ["Critical Strike Chance"],
    "crit multi": ["Critical Strike Multiplier"],
    "critical strike multiplier": ["Critical Strike Multiplier"],
    "crit multiplier": ["Critical Strike Multiplier"],
    "spell damage": ["Spell Damage"],
    "increased spell damage": ["Spell Damage"],
    "physical damage": ["Physical Damage"],
    "increased physical damage": ["Physical Damage"],
    "% physical damage": ["Physical Damage"],
    "added physical damage": ["Physical Damage"],
    "added fire damage": ["Fire Damage"],
    "added cold damage": ["Cold Damage"],
    "added lightning damage": ["Lightning Damage"],
    "added chaos damage": ["Chaos Damage"],
    "accuracy": ["Accuracy Rating"],
    "accuracy rating": ["Accuracy Rating"],
    "armour": ["Armour"],
    "flat armour": ["to Armour"],
    "% armour": ["increased Armour"],
    "evasion": ["Evasion Rating"],
    "flat evasion": ["to Evasion Rating"],
    "% evasion": ["increased Evasion Rating"],
    "minion damage": ["Minion Damage"],
    "minion life": ["Minion Life"],
    "dot multi": ["Damage over Time Multiplier"],
    "damage over time multiplier": ["Damage over Time Multiplier"],
    "dot damage": ["Damage over Time"],
    "gem level": ["Level of all"],
    "+1 gems": ["Level of all Skill Gems"],
    "life leech": ["Leeched as Life"],
    "strength": ["to Strength"],
    "dexterity": ["to Dexterity"],
    "intelligence": ["to Intelligence"],
    "all attributes": ["to all Attributes"],
    "attributes": ["to all Attributes"],
    "fire penetration": ["Penetrates", "Fire Resistance"],
    "cold penetration": ["Penetrates", "Cold Resistance"],
    "lightning penetration": ["Penetrates", "Lightning Resistance"],
    "elemental penetration": ["Penetrates", "Elemental Resistances"],
    "block": ["Chance to Block"],
    "spell block": ["Block Spell Damage"],
    "aura effect": ["effect of Non-Curse Auras"],
}


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


def _mod_matches_priority(mod_text: str, priority: str) -> bool:
    """Check if a mod line corresponds to a stat_priority keyword."""
    keywords = _PRIORITY_MOD_KEYWORDS.get(priority.lower().strip())
    if not keywords:
        return False
    return all(kw.lower() in mod_text.lower() for kw in keywords)


async def build_trade_query(
    item: Item,
    stat_cache: StatCache,
    league: str = "Standard",
) -> tuple[TradeSearchRequest, str]:
    """Convert a build Item into a trade search request.

    If the item has stat_priority (from a guide), creates guide-aware
    queries that prioritize the most important stats.

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
    elif item.stat_priority:
        return await _build_guide_aware_query(item, stat_cache, league)
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


async def _build_guide_aware_query(
    item: Item,
    stat_cache: StatCache,
    league: str,
) -> tuple[TradeSearchRequest, str]:
    """Build a query prioritized by guide stat_priority.

    Splits mods into two groups:
    - Required: top 2-3 priority stats with "and" mode (must all match)
    - Flexible: remaining mods with "count" mode (most should match)

    Priority stats get higher min values (80% of roll) vs flexible (60%).
    """
    # Classify each explicit mod as priority or non-priority
    priority_filters: list[StatFilter] = []
    flexible_filters: list[StatFilter] = []

    # Track which priorities have been matched so we use top ones first
    top_priorities = item.stat_priority[:3]  # Focus on first 3 priorities

    for mod in item.explicits:
        stat_type = "crafted" if mod.is_crafted else "explicit"
        entry = stat_cache.match_mod(_clean_mod_text(mod.text), stat_type)
        if entry is None:
            logger.warning("No stat match for mod: '%s' — skipping", _clean_mod_text(mod.text))
            continue

        num = _extract_numeric_value(mod.text)
        is_priority = any(
            _mod_matches_priority(mod.text, p) for p in top_priorities
        )

        if is_priority and len(priority_filters) < 3:
            # Priority stat: require match with 80% minimum
            value_spec = None
            if num is not None and num > 0:
                value_spec = {"min": round(num * 0.8, 1)}
            priority_filters.append(StatFilter(id=entry.id, value=value_spec))
        else:
            # Flexible stat: lower minimum (60%)
            value_spec = None
            if num is not None and num > 0:
                value_spec = {"min": round(num * 0.6, 1)}
            flexible_filters.append(StatFilter(id=entry.id, value=value_spec))

    stat_groups: list[StatGroup] = []

    # Required group: all priority stats must match
    if priority_filters:
        stat_groups.append(StatGroup(
            type="and",
            filters=priority_filters,
        ))

    # Flexible group: at least 50% of remaining mods
    if flexible_filters:
        min_count = max(1, math.floor(len(flexible_filters) * 0.5))
        stat_groups.append(StatGroup(
            type="count",
            filters=flexible_filters,
            value={"min": min_count},
        ))

    # PoE trade API requires at least one stat group; provide an empty "and" group
    # if no filters were built (e.g. synthesized items with only stat_priority, no real mods)
    if not stat_groups:
        stat_groups = [StatGroup(type="and", filters=[])]

    query = TradeQuery(
        type=_sanitize_base_type(item.base_type, item.name, item.rarity),
        stats=stat_groups,
    )
    request = TradeSearchRequest(query=query)
    trade_url = f"https://www.pathofexile.com/trade/search/{league}"
    return request, trade_url


async def _build_rare_query(
    item: Item,
    stat_cache: StatCache,
    league: str,
) -> tuple[TradeSearchRequest, str]:
    """Build a stat-filtered query for rare/magic items (no guide context)."""
    filters: list[StatFilter] = []

    for mod in item.explicits:
        stat_type = "explicit"
        if mod.is_crafted:
            stat_type = "crafted"

        entry = stat_cache.match_mod(_clean_mod_text(mod.text), stat_type)
        if entry is None:
            logger.warning("No stat match for mod: '%s' — skipping", _clean_mod_text(mod.text))
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

    # PoE trade API requires at least one stat group
    if filters:
        stats = [stat_group]
    else:
        stats = [StatGroup(type="and", filters=[])]

    query = TradeQuery(
        type=_sanitize_base_type(item.base_type, item.name, item.rarity),
        stats=stats,
    )
    request = TradeSearchRequest(query=query)
    trade_url = f"https://www.pathofexile.com/trade/search/{league}"
    return request, trade_url


# -----------------------------------------------------------------------
# Progressive relaxation — drop stats until we find results
# -----------------------------------------------------------------------

def relax_query(
    request: TradeSearchRequest,
    level: int,
) -> tuple[TradeSearchRequest, list[str]]:
    """Create a relaxed version of a trade query by dropping stats.

    Level 0 = original query (no relaxation)
    Level 1 = lower min values to 50% and reduce count requirements
    Level 2 = drop the "and" group entirely (priority stats), keep "count"
    Level 3 = drop to just base type + top 2 stat filters
    Level 4 = base type only (no stat filters)

    Returns: (relaxed_request, list of descriptions of what was dropped)
    """
    import copy

    query = copy.deepcopy(request.query)
    dropped: list[str] = []

    if level <= 0:
        return request, []

    if level == 1:
        # Lower all min values by 40% and reduce count requirements
        for group in query.stats:
            for f in group.filters:
                if f.value and "min" in f.value:
                    f.value["min"] = round(f.value["min"] * 0.6, 1)
            if group.type == "count" and group.value and "min" in group.value:
                group.value["min"] = max(1, group.value["min"] - 1)
        dropped.append("Lowered stat minimums")

    elif level == 2:
        # Remove the "and" (required) group, keep "count" with lower requirements
        new_groups = []
        for group in query.stats:
            if group.type == "and" and group.filters:
                dropped.append(f"Dropped {len(group.filters)} required stat(s)")
                continue
            if group.type == "count" and group.value and "min" in group.value:
                group.value["min"] = max(1, group.value["min"] - 1)
                for f in group.filters:
                    if f.value and "min" in f.value:
                        f.value["min"] = round(f.value["min"] * 0.5, 1)
            new_groups.append(group)
        query.stats = new_groups or [StatGroup(type="and", filters=[])]

    elif level == 3:
        # Keep only 2 filters total with very low minimums
        all_filters: list[StatFilter] = []
        for group in query.stats:
            all_filters.extend(group.filters)
        top = all_filters[:2]
        for f in top:
            if f.value and "min" in f.value:
                f.value["min"] = round(f.value["min"] * 0.3, 1)
        query.stats = [StatGroup(type="count", filters=top, value={"min": 1})]
        n_dropped = len(all_filters) - len(top)
        if n_dropped > 0:
            dropped.append(f"Dropped {n_dropped} stat filter(s), kept top 2")

    else:  # level >= 4
        # Base type only
        query.stats = [StatGroup(type="and", filters=[])]
        dropped.append("Searching by base type only")

    relaxed = TradeSearchRequest(query=query, sort=request.sort)
    return relaxed, dropped
