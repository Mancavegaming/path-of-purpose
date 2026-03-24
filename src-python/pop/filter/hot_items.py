"""Fetch high-value items from poe.ninja for dynamic loot filter rules."""

from __future__ import annotations

import asyncio
import datetime

import httpx
from pydantic import BaseModel, Field

NINJA_BASE = "https://poe.ninja/poe1/api/economy/stash/current"
USER_AGENT = "PathOfPurpose/0.11.0"

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
    item_type: str  # "unique", "divcard", "gem", "base"
    chaos_value: float


class HotItemsResult(BaseModel):
    tier1: list[HotItem] = Field(default_factory=list)
    tier2: list[HotItem] = Field(default_factory=list)
    tier3: list[HotItem] = Field(default_factory=list)
    divine_ratio: float = 180.0
    fetched_at: str = ""
    total_count: int = 0


async def _fetch_category(
    client: httpx.AsyncClient, league: str, ninja_type: str, item_type: str,
) -> list[tuple[str, str, float]]:
    """Fetch one poe.ninja category. Returns [(name, item_type, chaosValue)]."""
    try:
        if ninja_type == "Currency":
            url = f"{NINJA_BASE}/currency/overview"
        else:
            url = f"{NINJA_BASE}/item/overview"
        resp = await client.get(url, params={"league": league, "type": ninja_type})
        resp.raise_for_status()
        data = resp.json()
        lines = data.get("lines", [])
        results = []
        for line in lines:
            # Currency uses "currencyTypeName", items use "name"
            name = line.get("name", line.get("currencyTypeName", ""))
            chaos = line.get("chaosValue", line.get("chaosEquivalent", 0))
            if not name or not chaos or chaos <= 0:
                continue
            # Clean up names that aren't valid PoE filter BaseTypes
            # Skip enchantment text (cluster jewels, etc.)
            if "%" in name or "increased" in name.lower() or "reduced" in name.lower():
                continue
            # Strip transfigured gem suffixes: "Bladefall of Trarthus" -> skip
            # (PoE filter BaseType is just "Bladefall", but we can't reliably strip)
            if item_type == "gem" and " of " in name:
                continue
            # Strip map tier suffixes: "The Enslaver Map (Tier 14)" -> "The Enslaver Map"
            import re
            name = re.sub(r"\s*\(Tier \d+\)", "", name).strip()
            # Skip names with weird characters
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
    """Fetch hot items from poe.ninja, bucketed into three price tiers."""
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
        # Also fetch currency categories
        tasks.extend([
            _fetch_category(client, league, ninja_type, item_type)
            for ninja_type, item_type in CURRENCY_CATEGORIES
        ])
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Flatten and de-duplicate (keep highest value per name)
    best: dict[str, tuple[str, float]] = {}
    for result in results:
        if isinstance(result, Exception) or not isinstance(result, list):
            continue
        for name, item_type, chaos in result:
            if name not in best or chaos > best[name][1]:
                best[name] = (item_type, chaos)

    tier1: list[HotItem] = []
    tier2: list[HotItem] = []
    tier3: list[HotItem] = []

    for name, (item_type, chaos) in best.items():
        if chaos < tier3_min:
            continue
        item = HotItem(name=name, item_type=item_type, chaos_value=round(chaos, 1))
        if chaos >= tier1_min:
            tier1.append(item)
        elif chaos >= tier2_min:
            tier2.append(item)
        else:
            tier3.append(item)

    # Sort each tier by value descending
    tier1.sort(key=lambda x: x.chaos_value, reverse=True)
    tier2.sort(key=lambda x: x.chaos_value, reverse=True)
    tier3.sort(key=lambda x: x.chaos_value, reverse=True)

    return HotItemsResult(
        tier1=tier1,
        tier2=tier2,
        tier3=tier3,
        divine_ratio=divine_ratio,
        fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        total_count=len(tier1[:50]) + len(tier2[:50]) + len(tier3[:50]),
    )
