"""
Scrape leveling guide data from mobalytics.gg build pages.

Mobalytics embeds an Apollo GraphQL cache in a ``window.__PRELOADED_STATE__``
script tag.  The build data lives at::

    poe2State.apollo.graphql

The cache is a flat dict of typed entries keyed by ``TypeName:id``.  Build
variants are ``Poe2UserGeneratedDocumentBuildVariant`` entries, each containing
``skillGems`` (with active skills + support sub-skills) and ``equipment``
(slot-keyed items with CDN icon URLs).

Variant titles (level brackets like "lv 1-5") come from matching
``NgfDocumentCmWidgetContentVariantsV1DataChildVariant`` entries whose ``id``
matches the variant's ``id``.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from pop.build_parser.models import (
    BuildGuide,
    GuideGem,
    GuideGemGroup,
    GuideItem,
    LevelBracket,
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Equipment slot key → display name
_SLOT_NAMES: dict[str, str] = {
    "mainHand": "Main Hand",
    "offHand": "Off Hand",
    "helmet": "Helmet",
    "body": "Body Armour",
    "gloves": "Gloves",
    "boots": "Boots",
    "amulet": "Amulet",
    "leftRing": "Left Ring",
    "rightRing": "Right Ring",
    "extraRing": "Extra Ring",
    "belt": "Belt",
    "flask1": "Flask 1",
    "flask2": "Flask 2",
    "charm1": "Charm 1",
    "charm2": "Charm 2",
    "charm3": "Charm 3",
}


# ---------------------------------------------------------------------------
# HTML / JSON extraction
# ---------------------------------------------------------------------------


def _extract_preloaded_state(html: str) -> dict[str, Any] | None:
    """Extract ``window.__PRELOADED_STATE__`` JSON from page HTML."""
    # Find the script containing __PRELOADED_STATE__
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
    for script in scripts:
        if "__PRELOADED_STATE__" not in script:
            continue
        # Find the opening brace and match braces to end
        idx = script.find("{")
        if idx < 0:
            continue
        depth = 0
        end = idx
        for i in range(idx, len(script)):
            if script[i] == "{":
                depth += 1
            elif script[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        try:
            return json.loads(script[idx:end])
        except json.JSONDecodeError:
            continue
    return None


def _resolve_refs(obj: Any, cache: dict[str, Any], max_depth: int = 12, _depth: int = 0) -> Any:
    """Recursively resolve Apollo ``__ref`` pointers."""
    if _depth > max_depth:
        return obj
    if isinstance(obj, dict):
        if "__ref" in obj and len(obj) == 1:
            resolved = cache.get(obj["__ref"])
            if resolved is not None and resolved is not obj:
                return _resolve_refs(resolved, cache, max_depth, _depth + 1)
            return obj
        return {k: _resolve_refs(v, cache, max_depth, _depth + 1) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_refs(item, cache, max_depth, _depth + 1) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# Variant / bracket parsing
# ---------------------------------------------------------------------------


def _slug_to_name(slug: str) -> str:
    """Best-effort conversion of a gem slug like 'supportunleashplayer' to 'Unleash'."""
    s = slug
    # Strip common prefixes/suffixes
    for prefix in ("support", "player"):
        if s.lower().startswith(prefix):
            s = s[len(prefix):]
    for suffix in ("player", "support"):
        if s.lower().endswith(suffix):
            s = s[: -len(suffix)]
    if not s:
        return slug
    # Insert spaces before uppercase letters: "PierceI" → "Pierce I"
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    # Insert space before trailing roman numerals
    s = re.sub(r"([a-zA-Z])([IVX]+)$", r"\1 \2", s)
    return s[:1].upper() + s[1:]


def _build_gem_name_map(skill_gems: dict[str, Any]) -> dict[str, str]:
    """Build a gemSlug → display name map from priorityGems (which have names)."""
    name_map: dict[str, str] = {}
    for pg in skill_gems.get("priorityGems") or []:
        if isinstance(pg, dict):
            slug = pg.get("gemSlug") or ""
            name = pg.get("name") or ""
            if slug and name:
                name_map[slug] = name
    return name_map


def _parse_gem_slot(
    slot: dict[str, Any],
    gem_name_map: dict[str, str],
) -> GuideGemGroup:
    """Parse a Poe2DocumentCmWidgetGemsSlotV1 entry into a GuideGemGroup.

    Each slot has an ``activeSkill`` (the main gem) and optional ``subSkills``
    (support gems linked to it).
    """
    gems: list[GuideGem] = []

    active = slot.get("activeSkill")
    if isinstance(active, dict):
        gems.append(GuideGem(
            name=active.get("name") or "",
            icon_url=active.get("gemIconURL") or active.get("iconURL") or "",
            is_support=False,
        ))

    subs = slot.get("subSkills") or []
    for sub in subs:
        if not isinstance(sub, dict):
            continue
        slug = sub.get("gemSlug") or ""
        name = sub.get("name") or gem_name_map.get(slug) or _slug_to_name(slug)
        gems.append(GuideGem(
            name=name,
            icon_url=sub.get("iconURL") or "",
            is_support=True,
        ))

    # Use the active skill name as the group label
    group_name = gems[0].name if gems else ""
    return GuideGemGroup(slot=group_name, gems=gems)


def _parse_equipment(equipment: dict[str, Any]) -> list[GuideItem]:
    """Parse the equipment dict (slot-keyed) into a list of GuideItems."""
    items: list[GuideItem] = []
    for slot_key, display_name in _SLOT_NAMES.items():
        slot_data = equipment.get(slot_key)
        if not isinstance(slot_data, dict):
            continue
        common = slot_data.get("commonItem")
        if not isinstance(common, dict):
            continue
        name = common.get("name") or ""
        if not name:
            continue
        items.append(GuideItem(
            slot=display_name,
            name=name,
            base_type=common.get("itemClassSlug") or "",
            icon_url=common.get("iconURL") or "",
        ))
    return items


def _parse_poe1_gem_group(group: dict[str, Any]) -> GuideGemGroup:
    """Parse a PoeUGDocumentBuildVariantSkillGemGroup (PoE 1 format)."""
    slot = group.get("slotSlug") or group.get("label") or ""
    gems: list[GuideGem] = []

    for gem_entry in group.get("gems") or []:
        if not isinstance(gem_entry, dict):
            continue
        gem_obj = gem_entry.get("skillGemObject", {})
        if not isinstance(gem_obj, dict):
            continue
        entity = gem_obj.get("entityV2", {})
        data = gem_obj.get("data", {})
        name = (
            gem_obj.get("title")
            or (data.get("name") if isinstance(data, dict) else "")
            or (entity.get("name") if isinstance(entity, dict) else "")
            or ""
        )
        icon = gem_obj.get("iconUrl") or ""
        if not icon and isinstance(entity, dict):
            icon = entity.get("icon") or entity.get("itemIcon") or ""
        is_support = bool(entity.get("isSupport")) if isinstance(entity, dict) else False
        if name:
            gems.append(GuideGem(name=name, icon_url=icon, is_support=is_support))

    return GuideGemGroup(slot=slot, gems=gems)


def _parse_poe1_items(generic_builder: dict[str, Any]) -> list[GuideItem]:
    """Parse genericBuilder.slots (PoE 1 format) into GuideItems."""
    items: list[GuideItem] = []
    slots = generic_builder.get("slots")
    if not isinstance(slots, list):
        return items

    for slot_entry in slots:
        if not isinstance(slot_entry, dict):
            continue
        slot_slug = slot_entry.get("gameSlotSlug") or ""
        entity = slot_entry.get("gameEntity", {})
        if not isinstance(entity, dict):
            continue
        name = entity.get("title") or ""
        if not name:
            continue
        display_slot = _SLOT_NAMES.get(slot_slug, slot_slug)
        items.append(GuideItem(
            slot=display_slot,
            name=name,
            base_type=entity.get("type") or "",
            icon_url=entity.get("iconUrl") or "",
        ))

    return items


def _parse_variant(
    variant: dict[str, Any],
    title_map: dict[str, str],
) -> LevelBracket:
    """Parse a build variant into a LevelBracket (handles both PoE 1 and PoE 2)."""
    vid = variant.get("id") or ""
    title = title_map.get(vid, vid)

    gem_groups: list[GuideGemGroup] = []
    items: list[GuideItem] = []

    # --- PoE 2 format: skillGems with activeSkill/subSkills ---
    skill_gems = variant.get("skillGems")
    if isinstance(skill_gems, dict) and skill_gems.get("gems"):
        gem_name_map = _build_gem_name_map(skill_gems)
        for slot in skill_gems.get("gems") or []:
            if isinstance(slot, dict):
                group = _parse_gem_slot(slot, gem_name_map)
                if group.gems:
                    gem_groups.append(group)

    # --- PoE 1 format: skills with gemGroups ---
    if not gem_groups:
        skills = variant.get("skills")
        if isinstance(skills, dict):
            for group in skills.get("gemGroups") or []:
                if isinstance(group, dict):
                    parsed = _parse_poe1_gem_group(group)
                    if parsed.gems:
                        gem_groups.append(parsed)

    # --- PoE 2 format: equipment (slot-keyed dict) ---
    equipment = variant.get("equipment")
    if isinstance(equipment, dict):
        items = _parse_equipment(equipment)

    # --- PoE 1 format: genericBuilder.slots ---
    if not items:
        gb = variant.get("genericBuilder")
        if isinstance(gb, dict):
            items = _parse_poe1_items(gb)

    return LevelBracket(title=title, gem_groups=gem_groups, items=items)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def scrape_build_guide(url: str) -> BuildGuide:
    """Fetch a mobalytics.gg build guide page and extract leveling data.

    Parameters
    ----------
    url:
        Full URL to a mobalytics.gg build guide page, e.g.
        ``https://mobalytics.gg/poe-2/builds/lightning-caster-leveling``

    Returns
    -------
    BuildGuide
        Structured leveling data with level brackets, gem groups, and items.

    Raises
    ------
    ValueError
        If the page cannot be fetched or the embedded data cannot be parsed.
    """
    async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True, timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    html = resp.text
    state = _extract_preloaded_state(html)
    if state is None:
        raise ValueError(
            "Could not find __PRELOADED_STATE__ in the page. "
            "Mobalytics may have changed their page structure."
        )

    # Navigate to the Apollo GraphQL cache — try multiple state keys
    cache: dict[str, Any] = {}
    for state_key in ("poe2State", "poeState", "lolState", "tftState"):
        candidate = state.get(state_key, {})
        if isinstance(candidate, dict):
            apollo = candidate.get("apollo", {})
            if isinstance(apollo, dict):
                cache = apollo.get("graphql") or apollo.get("cache") or apollo
                if cache and len(cache) > 2:
                    break

    # Fallback: search all top-level state values for an apollo cache
    if not cache or len(cache) <= 2:
        for val in state.values():
            if not isinstance(val, dict):
                continue
            apollo = val.get("apollo", {})
            if isinstance(apollo, dict):
                for sub_key in ("graphql", "cache"):
                    candidate = apollo.get(sub_key, {})
                    if isinstance(candidate, dict) and len(candidate) > 5:
                        cache = candidate
                        break
            if cache and len(cache) > 2:
                break

    if not cache or len(cache) <= 2:
        raise ValueError("Could not find Apollo GraphQL cache in page state.")

    # Build a title map from ChildVariant entries: id → title
    title_map: dict[str, str] = {}
    for key, val in cache.items():
        if "ChildVariant:" in key and isinstance(val, dict):
            cid = val.get("id", "")
            ctitle = val.get("title", "")
            if cid and ctitle:
                title_map[str(cid)] = ctitle

    # Locate the main document by following refs — try multiple query root keys
    documents: dict[str, Any] = {}
    for query_key in cache:
        if "Query:" in query_key or query_key == "ROOT_QUERY":
            query_obj = cache[query_key]
            if isinstance(query_obj, dict):
                docs = query_obj.get("documents", {})
                if isinstance(docs, dict) and docs:
                    documents = docs
                    break

    doc_ref = None
    for key, val in documents.items():
        if "userGeneratedDocumentBySlug" in key:
            doc_ref = val
            break

    if doc_ref is None:
        raise ValueError("Could not find build document in Apollo cache.")

    # Resolve all __ref pointers
    doc = _resolve_refs(doc_ref, cache)

    # Navigate to the build data
    doc_data = doc.get("data", {})
    inner_data = doc_data.get("data", {})

    # Extract metadata
    title = inner_data.get("name") or doc_data.get("slugifiedName") or ""
    class_name = ""
    ascendancy = ""
    tags = doc_data.get("tags")
    if isinstance(tags, dict):
        tag_list = tags.get("data", [])
        if isinstance(tag_list, list):
            for tag in tag_list:
                if not isinstance(tag, dict):
                    continue
                group = tag.get("groupSlug", "")
                if group == "class":
                    class_name = tag.get("name") or ""
                elif group == "ascendancy":
                    ascendancy = tag.get("name") or ""

    # Parse build variants
    build_variants = inner_data.get("buildVariants", {})
    variants_list = []
    if isinstance(build_variants, dict):
        variants_list = build_variants.get("values", [])
    elif isinstance(build_variants, list):
        variants_list = build_variants

    brackets: list[LevelBracket] = []
    for v in variants_list:
        if isinstance(v, dict):
            bracket = _parse_variant(v, title_map)
            brackets.append(bracket)

    if not brackets:
        raise ValueError(
            "No level brackets found in the build guide. "
            "The page structure may have changed."
        )

    return BuildGuide(
        url=url,
        title=title,
        class_name=class_name,
        ascendancy_name=ascendancy,
        brackets=brackets,
    )
