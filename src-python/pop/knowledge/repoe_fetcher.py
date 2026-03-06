"""Fetch gem and unique item data from RePoE (community PoE data export)."""

from __future__ import annotations

import logging

import httpx

from pop.knowledge.models import GemInfo, UniqueInfo

logger = logging.getLogger(__name__)

REPOE_BASE = "https://repoe-fork.github.io"
GEMS_URL = f"{REPOE_BASE}/gems.min.json"
UNIQUES_URL = f"{REPOE_BASE}/uniques.min.json"

_HEADERS = {
    "User-Agent": "PathOfPurpose/1.0 (build advisor)",
    "Accept": "application/json",
}


async def fetch_gems(client: httpx.AsyncClient | None = None) -> list[GemInfo]:
    """Fetch all released gems from RePoE and distill to compact references.

    RePoE gems.json is keyed by gem name. Each entry has:
    - base_item.display_name + base_item.release_state
    - per_level."1".required_level
    - is_support: bool
    - active_skill.types: list of tag strings (for active skills)
    - Tags for supports are in the "support_gem" or top-level "tags" field
    """
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(headers=_HEADERS, timeout=60)

    try:
        resp = await client.get(GEMS_URL)
        resp.raise_for_status()
        data = resp.json()
    finally:
        if owns_client:
            await client.aclose()

    gems: list[GemInfo] = []
    for _gem_key, gem_data in data.items():
        if not isinstance(gem_data, dict):
            continue

        # Only include released gems
        base_item = gem_data.get("base_item", {})
        if not isinstance(base_item, dict):
            continue
        if base_item.get("release_state") != "released":
            continue

        # Extract display name — try base_item.display_name, then top-level display_name
        name = base_item.get("display_name", "") or gem_data.get("display_name", "")
        if not name:
            continue

        # Extract required level at gem level 1
        per_level = gem_data.get("per_level", {})
        req_level = 0
        if isinstance(per_level, dict):
            lvl1 = per_level.get("1", {})
            if isinstance(lvl1, dict):
                req_level = lvl1.get("required_level", 0)

        is_support = bool(gem_data.get("is_support", False))

        # Extract tags — from active_skill.types for active gems, or tags field
        tags: list[str] = []
        active_skill = gem_data.get("active_skill", {})
        if isinstance(active_skill, dict):
            types = active_skill.get("types", [])
            if isinstance(types, list):
                tags = [str(t) for t in types]

        # Fallback to top-level tags
        if not tags:
            raw_tags = gem_data.get("tags", [])
            if isinstance(raw_tags, list):
                tags = [str(t) for t in raw_tags]

        gems.append(GemInfo(
            name=name,
            required_level=req_level,
            is_support=is_support,
            tags=tags,
        ))

    # Deduplicate by name (some gems have multiple variants like Vaal versions)
    seen: set[str] = set()
    unique_gems: list[GemInfo] = []
    for gem in gems:
        if gem.name not in seen:
            seen.add(gem.name)
            unique_gems.append(gem)

    logger.info("Fetched %d gems from RePoE", len(unique_gems))
    return sorted(unique_gems, key=lambda g: (g.is_support, g.required_level, g.name))


async def fetch_uniques(client: httpx.AsyncClient | None = None) -> list[UniqueInfo]:
    """Fetch all unique items from RePoE.

    RePoE uniques.json is a dict keyed by numeric ID. Each entry has:
    - name: unique item name
    - item_class: e.g. "Axe", "Body Armour", "Amulet"
    - No base_type field (only name and item_class are reliable)
    """
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(headers=_HEADERS, timeout=60)

    try:
        resp = await client.get(UNIQUES_URL)
        resp.raise_for_status()
        data = resp.json()
    finally:
        if owns_client:
            await client.aclose()

    uniques: list[UniqueInfo] = []
    entries = data.values() if isinstance(data, dict) else data if isinstance(data, list) else []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name", "") or entry.get("id", "")
        if not name:
            continue
        # Skip alternate art versions
        if entry.get("is_alternate_art", False):
            continue
        uniques.append(UniqueInfo(
            name=name,
            base_type=entry.get("base_type", ""),
            item_class=entry.get("item_class", ""),
        ))

    # Deduplicate by name
    seen: set[str] = set()
    unique_items: list[UniqueInfo] = []
    for u in uniques:
        if u.name not in seen:
            seen.add(u.name)
            unique_items.append(u)

    logger.info("Fetched %d unique items from RePoE", len(unique_items))
    return sorted(unique_items, key=lambda u: (u.item_class, u.name))
