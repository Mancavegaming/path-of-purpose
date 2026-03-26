"""Fetch high-value items from poe.ninja for dynamic loot filter rules."""

from __future__ import annotations

import asyncio
import datetime
from collections import defaultdict

import httpx
from pydantic import BaseModel, Field

NINJA_BASE = "https://poe.ninja/poe1/api/economy/stash/current"
USER_AGENT = "PathOfPurpose/0.12.0"

# poe.ninja item/overview categories and what filter item_type they map to
ITEM_CATEGORIES = [
    # Uniques (all slots)
    ("UniqueWeapon", "unique"),
    ("UniqueArmour", "unique"),
    ("UniqueAccessory", "unique"),
    ("UniqueJewel", "unique"),
    ("UniqueFlask", "unique"),
    ("UniqueMap", "unique"),
    # Cards, gems, bases
    ("DivinationCard", "divcard"),
    ("SkillGem", "gem"),
    ("BaseType", "base"),
    # Crafting materials
    ("Scarab", "base"),
    ("Fossil", "base"),
    ("Essence", "base"),
    ("Oil", "base"),
    ("Resonator", "base"),
    ("Incubator", "base"),
    ("Vial", "base"),
    ("DeliriumOrb", "base"),
    # Misc
    ("Invitation", "base"),
    ("Tattoo", "base"),
    ("Omen", "base"),
]

# currency/overview categories (different response format)
CURRENCY_CATEGORIES = [
    ("Currency", "currency"),
    ("Fragment", "fragment"),
]


class HotItem(BaseModel):
    name: str
    item_type: str  # "unique", "divcard", "gem", "base", "currency", "fragment"
    chaos_value: float


class HotItemsResult(BaseModel):
    tier1: list[HotItem] = Field(default_factory=list)  # 10+ div, guaranteed
    tier2: list[HotItem] = Field(default_factory=list)  # 1-10 div, guaranteed
    tier3: list[HotItem] = Field(default_factory=list)  # 50c+, no uniques
    tier4: list[HotItem] = Field(default_factory=list)  # price-check: mixed unique bases
    divine_ratio: float = 180.0
    fetched_at: str = ""
    total_count: int = 0


async def _fetch_category(
    client: httpx.AsyncClient, league: str, ninja_type: str, item_type: str,
) -> list[tuple[str, str, float]]:
    """Fetch one poe.ninja category. Returns [(name/baseType, item_type, chaosValue)]."""
    try:
        if ninja_type in ("Currency", "Fragment"):
            url = f"{NINJA_BASE}/currency/overview"
        else:
            url = f"{NINJA_BASE}/item/overview"
        resp = await client.get(url, params={"league": league, "type": ninja_type})
        resp.raise_for_status()
        data = resp.json()
        lines = data.get("lines", [])
        results = []
        for line in lines:
            chaos = line.get("chaosValue", line.get("chaosEquivalent", 0))
            if not chaos or chaos <= 0:
                continue
            # For uniques: use baseType (actual item base), not unique name
            if item_type == "unique":
                name = line.get("baseType", "")
            else:
                name = line.get("name", line.get("currencyTypeName", ""))
            if not name:
                continue
            # Skip transfigured gem variants
            if item_type == "gem" and " of " in name:
                continue
            # Skip stat text (enchantments etc.)
            if "%" in name:
                continue
            # Skip names with embedded quotes
            if '"' in name:
                continue
            results.append((name, item_type, float(chaos)))
        return results
    except Exception:
        return []


async def fetch_hot_items(
    league: str = "Standard",
    divine_ratio: float | None = None,
) -> HotItemsResult:
    """Fetch hot items from poe.ninja, bucketed into four price tiers.

    For uniques, we group by base type and use the MINIMUM value to determine
    the tier. This prevents false positives from shared base types (e.g.,
    Leather Belt = Mageblood AND Wurm's Molt). If any cheap unique shares
    the base, the base drops to T4 (price-check) instead of T1/T2.

    T3 excludes uniques entirely (too noisy) — only div cards, currency, etc.
    T4 is for unique base types with mixed values — "pick up and price check".
    """
    if divine_ratio is None or divine_ratio <= 0:
        divine_ratio = 180.0

    tier1_min = divine_ratio * 10   # 10+ div
    tier2_min = divine_ratio        # 1-10 div
    tier3_min = 50                  # 50c - 1 div

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=20.0,
    ) as client:
        tasks = [
            _fetch_category(client, league, ninja_type, item_type)
            for ninja_type, item_type in ITEM_CATEGORIES
        ]
        tasks.extend([
            _fetch_category(client, league, ninja_type, item_type)
            for ninja_type, item_type in CURRENCY_CATEGORIES
        ])
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Separate uniques from everything else
    unique_entries: list[tuple[str, float]] = []  # (baseType, chaosValue)
    non_unique: dict[str, tuple[str, float]] = {}  # name -> (item_type, max_chaos)

    for result in results:
        if isinstance(result, Exception) or not isinstance(result, list):
            continue
        for name, item_type, chaos in result:
            if item_type == "unique":
                unique_entries.append((name, chaos))
            else:
                # For non-uniques, keep highest value per name
                if name not in non_unique or chaos > non_unique[name][1]:
                    non_unique[name] = (item_type, chaos)

    # --- Unique base type analysis ---
    # Group by base type: find min AND max value per base
    base_values: dict[str, list[float]] = defaultdict(list)
    for base_type, chaos in unique_entries:
        base_values[base_type].append(chaos)

    tier1: list[HotItem] = []
    tier2: list[HotItem] = []
    tier3: list[HotItem] = []
    tier4: list[HotItem] = []

    # Unique bases: tier is determined by the MINIMUM value unique on that base
    for base_type, values in base_values.items():
        min_val = min(values)
        max_val = max(values)
        if min_val >= tier1_min:
            # ALL uniques on this base are 10+ div — safe for T1
            tier1.append(HotItem(name=base_type, item_type="unique", chaos_value=round(max_val, 1)))
        elif min_val >= tier2_min:
            # ALL uniques on this base are 1+ div — safe for T2
            tier2.append(HotItem(name=base_type, item_type="unique", chaos_value=round(max_val, 1)))
        elif max_val >= tier2_min:
            # Some uniques on this base are valuable but others are cheap
            # Put in T4 (price-check tier)
            tier4.append(HotItem(name=base_type, item_type="unique", chaos_value=round(max_val, 1)))

    # Non-unique items: straightforward tiering (no base-sharing problem)
    for name, (item_type, chaos) in non_unique.items():
        if chaos < tier3_min:
            continue
        item = HotItem(name=name, item_type=item_type, chaos_value=round(chaos, 1))
        if chaos >= tier1_min:
            tier1.append(item)
        elif chaos >= tier2_min:
            tier2.append(item)
        else:
            # T3: no uniques (already handled above)
            tier3.append(item)

    # Sort each tier by value descending
    for t in (tier1, tier2, tier3, tier4):
        t.sort(key=lambda x: x.chaos_value, reverse=True)

    total = len(tier1) + len(tier2) + len(tier3) + len(tier4)

    return HotItemsResult(
        tier1=tier1,
        tier2=tier2,
        tier3=tier3,
        tier4=tier4,
        divine_ratio=divine_ratio,
        fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        total_count=total,
    )
