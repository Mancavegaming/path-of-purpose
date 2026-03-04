"""
Gem link diff — compare guide skill groups against live character gems.

The challenge: PoB organizes gems into named skill groups with explicit
active/support tagging, while the API returns gems socketed in items
without group labels. We match by active skill name using fuzzy matching.
"""

from __future__ import annotations

from rapidfuzz import fuzz

from pop.build_parser.models import SkillGroup, Gem as PobGem
from pop.poe_api.models import EquippedItem
from pop.delta.models import GemDelta, SkillGroupDelta, GemGap

# Fuzzy threshold for gem name matching
_GEM_MATCH_THRESHOLD = 80


def _normalize_gem_name(name: str) -> str:
    """Normalize gem name for comparison (lowercase, strip 'support' suffix)."""
    n = name.lower().strip()
    # Some API responses include "Support" in the name, some don't
    n = n.replace(" support", "")
    return n


def _find_support_in_list(
    support_name: str,
    available: list[str],
    used: set[int],
) -> int:
    """Find the best match for a support gem name. Returns index or -1."""
    norm_target = _normalize_gem_name(support_name)
    best_idx = -1
    best_score = 0.0

    for i, name in enumerate(available):
        if i in used:
            continue
        score = fuzz.ratio(norm_target, _normalize_gem_name(name))
        if score > best_score:
            best_score = score
            best_idx = i

    return best_idx if best_score >= _GEM_MATCH_THRESHOLD else -1


def _extract_gems_from_items(
    items: dict[str, EquippedItem],
) -> dict[str, list[str]]:
    """
    Extract gem names from character items, grouped by slot.

    This is a simplified extraction — the actual API provides gem data
    in the socket/gem arrays of each item. For now we work with mod
    data and will refine when we have live API access.

    Returns: {"slot_name": ["gem_name_1", "gem_name_2", ...]}
    """
    # Note: The actual PoE API includes a `socketedItems` array on each item
    # that contains full gem data. Since we're working with mocks, this
    # returns an empty structure that will be populated properly later.
    return {}


def diff_skill_group(
    guide_group: SkillGroup,
    character_gem_names: list[str],
) -> SkillGroupDelta:
    """
    Compare a single skill group from the guide against available gems.

    Args:
        guide_group: A PoB skill group (active + supports).
        character_gem_names: List of gem names the character has for
                            this skill group (matched by active skill).

    Returns:
        SkillGroupDelta with missing/extra supports and level gaps.
    """
    active = guide_group.active_gem
    skill_name = active.name if active else guide_group.label or "Unknown"

    if not character_gem_names:
        # Entire skill group is missing
        return SkillGroupDelta(
            skill_name=skill_name,
            slot=guide_group.slot,
            is_missing_entirely=True,
            missing_supports=[g.name for g in guide_group.support_gems],
            match_pct=0.0,
        )

    # Match support gems
    guide_supports = [g.name for g in guide_group.support_gems]
    used: set[int] = set()
    missing_supports: list[str] = []
    matched = 0

    for support_name in guide_supports:
        idx = _find_support_in_list(support_name, character_gem_names, used)
        if idx >= 0:
            used.add(idx)
            matched += 1
        else:
            missing_supports.append(support_name)

    # Extra supports (character has but guide doesn't)
    extra_supports: list[str] = []
    for i, name in enumerate(character_gem_names):
        if i not in used:
            norm = _normalize_gem_name(name)
            # Skip the active gem itself
            if active and fuzz.ratio(norm, _normalize_gem_name(active.name)) >= _GEM_MATCH_THRESHOLD:
                continue
            extra_supports.append(name)

    total = len(guide_supports)
    match_pct = (matched / total * 100) if total > 0 else 100.0

    return SkillGroupDelta(
        skill_name=skill_name,
        slot=guide_group.slot,
        missing_supports=missing_supports,
        extra_supports=extra_supports,
        match_pct=round(match_pct, 1),
    )


def diff_gems(
    guide_groups: list[SkillGroup],
    character_gems: dict[str, list[str]],
) -> GemDelta:
    """
    Compare all guide skill groups against character gems.

    Args:
        guide_groups: Skill groups from PoB build (only enabled ones).
        character_gems: Gem names per slot from the character.
                       {"Body Armour": ["Summon Raging Spirit", "Minion Damage", ...]}

    Returns:
        GemDelta with per-group analysis.
    """
    enabled_groups = [g for g in guide_groups if g.is_enabled and g.active_gem]

    deltas: list[SkillGroupDelta] = []
    total_missing = 0
    total_level_gaps = 0

    for group in enabled_groups:
        # Try to find character gems for this group's slot
        char_gems = character_gems.get(group.slot, [])

        # If no slot match, try matching by active gem name across all slots
        if not char_gems and group.active_gem:
            target = _normalize_gem_name(group.active_gem.name)
            for slot_gems in character_gems.values():
                for gname in slot_gems:
                    if fuzz.ratio(target, _normalize_gem_name(gname)) >= _GEM_MATCH_THRESHOLD:
                        char_gems = slot_gems
                        break
                if char_gems:
                    break

        delta = diff_skill_group(group, char_gems)
        deltas.append(delta)
        total_missing += len(delta.missing_supports)
        total_level_gaps += len(delta.level_gaps)

    return GemDelta(
        group_deltas=deltas,
        total_missing_supports=total_missing,
        total_level_gaps=total_level_gaps,
    )
