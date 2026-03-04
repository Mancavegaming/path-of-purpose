"""
Gear slot diff — compare guide items against live character items.

The core challenge: PoB mod text and API mod text often differ in wording.
For example:
    PoB:  "+120 to maximum Life"
    API:  "+112 to Maximum Life"

We use rapidfuzz for fuzzy matching to bridge this gap, combined with
a mod importance scoring system that weights defensive and offensive
mods differently.
"""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from pop.build_parser.models import Item as PobItem, ItemMod
from pop.poe_api.models import EquippedItem
from pop.delta.models import GearDelta, SlotDelta, ModGap

# ---------------------------------------------------------------------------
# Mod importance weights
# ---------------------------------------------------------------------------

# Keywords that indicate high-importance mods, with their weight multiplier.
# Higher weight = more impactful gap when missing.
_MOD_WEIGHTS: list[tuple[re.Pattern[str], float]] = [
    (re.compile(r"maximum Life", re.IGNORECASE), 1.0),
    (re.compile(r"maximum Energy Shield", re.IGNORECASE), 0.9),
    (re.compile(r"to Level of.*Gems", re.IGNORECASE), 0.95),
    (re.compile(r"Resistance", re.IGNORECASE), 0.7),
    (re.compile(r"increased.*Damage", re.IGNORECASE), 0.6),
    (re.compile(r"Attack Speed|Cast Speed", re.IGNORECASE), 0.55),
    (re.compile(r"Critical Strike", re.IGNORECASE), 0.5),
    (re.compile(r"Spell Damage", re.IGNORECASE), 0.6),
    (re.compile(r"Minion", re.IGNORECASE), 0.65),
    (re.compile(r"Trigger", re.IGNORECASE), 0.85),
]

# Fuzzy match threshold — below this, mods are considered "not matching"
_MATCH_THRESHOLD = 70


def _mod_importance(mod_text: str) -> float:
    """Score a mod's importance from 0-1 based on keyword matching."""
    for pattern, weight in _MOD_WEIGHTS:
        if pattern.search(mod_text):
            return weight
    return 0.3  # default for unrecognized mods


def _normalize_mod(text: str) -> str:
    """
    Normalize a mod string for fuzzy comparison.

    Strips numbers so "+120 to maximum Life" and "+85 to maximum Life"
    compare as the same mod type (the value difference doesn't matter
    for gap detection — any life roll is better than no life roll).
    """
    # Replace numbers with a placeholder
    normalized = re.sub(r"[\d.]+", "#", text)
    # Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.lower()


def _find_best_match(
    pob_mod: str,
    api_mods: list[str],
    used: set[int],
) -> tuple[int, float]:
    """
    Find the best fuzzy match for a PoB mod among API mods.

    Returns (index, score). Index is -1 if no match above threshold.
    """
    norm_pob = _normalize_mod(pob_mod)
    best_idx = -1
    best_score = 0.0

    for i, api_mod in enumerate(api_mods):
        if i in used:
            continue
        norm_api = _normalize_mod(api_mod)
        score = fuzz.ratio(norm_pob, norm_api)
        if score > best_score:
            best_score = score
            best_idx = i

    if best_score >= _MATCH_THRESHOLD:
        return best_idx, best_score
    return -1, 0.0


def diff_slot(
    slot_name: str,
    guide_item: PobItem | None,
    char_item: EquippedItem | None,
) -> SlotDelta:
    """
    Compare a single gear slot between guide and character.

    Args:
        slot_name: The canonical slot name (e.g., "Helmet").
        guide_item: The item from the PoB build (or None if guide has no item).
        char_item: The item from the API (or None if slot is empty).

    Returns:
        SlotDelta with mod gap analysis.
    """
    # No guide item for this slot — nothing to compare
    if guide_item is None:
        return SlotDelta(
            slot=slot_name,
            has_item=True,
            match_pct=100.0,
        )

    guide_name = guide_item.name or guide_item.base_type

    # Character has nothing in this slot
    if char_item is None:
        guide_mods = guide_item.all_mods
        return SlotDelta(
            slot=slot_name,
            guide_item_name=guide_name,
            character_item_name="(empty)",
            has_item=False,
            missing_mods=[
                ModGap(
                    mod_text=m.text,
                    is_implicit=m.is_implicit,
                    importance=_mod_importance(m.text),
                )
                for m in guide_mods
            ],
            matched_mods=0,
            total_guide_mods=len(guide_mods),
            match_pct=0.0,
            priority_score=100.0,
        )

    # Both sides have items — fuzzy-match mods
    char_name = char_item.name or char_item.type_line or char_item.base_type
    guide_mods = guide_item.all_mods
    api_mods = char_item.all_mods  # list[str]

    used_api: set[int] = set()
    missing: list[ModGap] = []
    matched = 0

    for pob_mod in guide_mods:
        idx, score = _find_best_match(pob_mod.text, api_mods, used_api)
        if idx >= 0:
            used_api.add(idx)
            matched += 1
        else:
            missing.append(ModGap(
                mod_text=pob_mod.text,
                is_implicit=pob_mod.is_implicit,
                importance=_mod_importance(pob_mod.text),
            ))

    total = len(guide_mods)
    match_pct = (matched / total * 100) if total > 0 else 100.0

    # Priority score: weighted by missing mod importance
    # Higher = worse gap = should be fixed first
    if missing:
        priority_score = sum(m.importance for m in missing) / len(missing) * (100 - match_pct)
    else:
        priority_score = 0.0

    return SlotDelta(
        slot=slot_name,
        guide_item_name=guide_name,
        character_item_name=char_name,
        has_item=True,
        missing_mods=missing,
        matched_mods=matched,
        total_guide_mods=total,
        match_pct=round(match_pct, 1),
        priority_score=round(priority_score, 1),
    )


def diff_gear(
    guide_items: dict[str, PobItem],
    char_items: dict[str, EquippedItem],
) -> GearDelta:
    """
    Compare all gear slots between guide and character.

    Args:
        guide_items: PoB items keyed by slot name.
        char_items: API items keyed by slot name.

    Returns:
        GearDelta with per-slot analysis.
    """
    all_slots = set(guide_items.keys()) | set(char_items.keys())
    # Only compare slots where the guide has an item
    compare_slots = sorted(s for s in all_slots if s in guide_items)

    deltas: list[SlotDelta] = []
    for slot in compare_slots:
        delta = diff_slot(
            slot,
            guide_items.get(slot),
            char_items.get(slot),
        )
        deltas.append(delta)

    # Overall match
    if deltas:
        overall = sum(d.match_pct for d in deltas) / len(deltas)
    else:
        overall = 100.0

    return GearDelta(
        slot_deltas=deltas,
        overall_match_pct=round(overall, 1),
    )
