"""
Delta Engine — the core orchestrator.

Takes a guide build and a character build, runs all three
diff modules, and produces a ranked DeltaReport with the top gaps.
"""

from __future__ import annotations

from pop.build_parser.models import Build, PassiveSpec, SkillGroup
from pop.poe_api.models import CharacterDetail, PassiveData
from pop.delta.models import (
    DeltaGap,
    DeltaReport,
    GapCategory,
    GearDelta,
    GemDelta,
    PassiveDelta,
    Severity,
)
from pop.delta.passive_diff import diff_passives
from pop.delta.gear_diff import diff_gear, diff_gear_builds
from pop.delta.gem_diff import diff_gems


# ---------------------------------------------------------------------------
# Severity → base score mapping
# ---------------------------------------------------------------------------

_SEVERITY_SCORES = {
    Severity.CRITICAL: 90,
    Severity.HIGH: 65,
    Severity.MEDIUM: 35,
    Severity.LOW: 10,
}


def analyze(guide: Build, character: CharacterDetail) -> DeltaReport:
    """
    Run the full Delta Engine analysis (legacy API-based path).

    Args:
        guide: Decoded PoB build (the target).
        character: Live character from the API.

    Returns:
        DeltaReport with passive/gear/gem analysis and ranked top gaps.
    """
    # --- Passive diff ---
    passive_delta = PassiveDelta()
    guide_spec = guide.active_passive_spec
    if guide_spec:
        passive_delta = diff_passives(
            guide_spec,
            character.passives,
            character_level=character.level,
            guide_level=guide.level,
        )

    # --- Gear diff ---
    guide_items = guide.items_by_slot()
    char_items = character.items_by_slot()
    gear_delta = diff_gear(guide_items, char_items)

    # --- Gem diff ---
    char_gem_map = _build_character_gem_map(character)
    enabled_groups = [g for g in guide.skill_groups if g.is_enabled]
    gem_delta = diff_gems(enabled_groups, char_gem_map)

    # --- Rank all gaps ---
    return _build_report(
        passive_delta, gear_delta, gem_delta,
        guide_name=guide.build_name or guide.ascendancy_name or "Guide",
        character_name=character.name,
    )


def analyze_builds(guide: Build, character: Build) -> DeltaReport:
    """
    Compare two Build objects — guide vs character (imported from public API).

    This is the primary path now that Character Import provides Build objects
    without needing OAuth.
    """
    # --- Passive diff ---
    passive_delta = PassiveDelta()
    guide_spec = guide.active_passive_spec
    char_spec = character.active_passive_spec
    if guide_spec:
        char_passive = PassiveData(
            hashes=char_spec.nodes if char_spec else [],
        )
        passive_delta = diff_passives(
            guide_spec,
            char_passive,
            character_level=character.level,
            guide_level=guide.level,
        )

    # --- Gear diff (Build vs Build) ---
    gear_delta = diff_gear_builds(guide.items_by_slot(), character.items_by_slot())

    # --- Gem diff ---
    char_gem_map = _build_gem_map_from_build(character)
    enabled_groups = [g for g in guide.skill_groups if g.is_enabled]
    gem_delta = diff_gems(enabled_groups, char_gem_map)

    return _build_report(
        passive_delta, gear_delta, gem_delta,
        guide_name=guide.build_name or guide.ascendancy_name or "Guide",
        character_name=character.build_name or character.ascendancy_name or "Character",
    )


def _build_report(
    passive_delta: PassiveDelta,
    gear_delta: GearDelta,
    gem_delta: GemDelta,
    guide_name: str,
    character_name: str,
) -> DeltaReport:
    """Collect gaps, rank them, and build the report."""
    gaps = _collect_gaps(passive_delta, gear_delta, gem_delta)
    gaps.sort(key=lambda g: g.score, reverse=True)
    for i, gap in enumerate(gaps):
        gap.rank = i + 1

    return DeltaReport(
        passive_delta=passive_delta,
        gear_delta=gear_delta,
        gem_delta=gem_delta,
        top_gaps=gaps[:3],
        guide_build_name=guide_name,
        character_name=character_name,
    )


def _build_character_gem_map(character: CharacterDetail) -> dict[str, list[str]]:
    """Extract gem names from character equipment (legacy API path)."""
    gem_map: dict[str, list[str]] = {}
    for item in character.equipment:
        if not item.socketed_items:
            continue
        slot = item.slot
        names = [g.type_line or g.name for g in item.socketed_items if g.type_line or g.name]
        if names:
            gem_map[slot] = names
    return gem_map


def _build_gem_map_from_build(character: Build) -> dict[str, list[str]]:
    """Extract gem names from a Build's skill_groups, keyed by slot."""
    gem_map: dict[str, list[str]] = {}
    for group in character.skill_groups:
        if not group.is_enabled:
            continue
        slot = group.slot
        names = [g.name for g in group.gems if g.name]
        if names:
            existing = gem_map.get(slot, [])
            existing.extend(names)
            gem_map[slot] = existing
    return gem_map


def _collect_gaps(
    passive: PassiveDelta,
    gear: GearDelta,
    gems: GemDelta,
) -> list[DeltaGap]:
    """Collect and score all gaps from the three diff modules."""
    gaps: list[DeltaGap] = []

    # --- Passive gaps ---
    if passive.missing_count > 0:
        sev = passive.severity
        # Scale score by how far off we are
        score = _SEVERITY_SCORES[sev] + (100 - passive.match_pct) * 0.1
        gaps.append(DeltaGap(
            category=GapCategory.PASSIVE,
            severity=sev,
            title=f"Passive tree {passive.match_pct:.0f}% — {passive.missing_count} nodes to fix",
            detail=(
                f"Allocate {passive.missing_count} missing nodes. "
                f"Respec {passive.extra_count} extra nodes."
                if passive.extra_count
                else f"Allocate {passive.missing_count} missing nodes."
            ),
            score=round(score, 1),
        ))

    # --- Gear gaps (one per bad slot) ---
    for slot_delta in gear.worst_slots:
        if slot_delta.match_pct >= 95:
            continue  # close enough

        sev = slot_delta.severity
        score = _SEVERITY_SCORES[sev] + slot_delta.priority_score * 0.3

        if not slot_delta.has_item:
            title = f"{slot_delta.slot}: EMPTY"
            detail = f"Guide expects '{slot_delta.guide_item_name}'"
        else:
            top_mods = slot_delta.missing_mods[:3]
            mod_list = ", ".join(m.mod_text for m in top_mods)
            title = f"{slot_delta.slot}: {slot_delta.match_pct:.0f}% match"
            detail = f"Missing: {mod_list}"

        gaps.append(DeltaGap(
            category=GapCategory.GEAR,
            severity=sev,
            title=title,
            detail=detail,
            score=round(score, 1),
        ))

    # --- Gem gaps ---
    for group_delta in gems.group_deltas:
        if group_delta.match_pct >= 100 and not group_delta.is_missing_entirely:
            continue

        sev = group_delta.severity
        score = _SEVERITY_SCORES[sev]

        if group_delta.is_missing_entirely:
            title = f"Skill '{group_delta.skill_name}' not found"
            detail = "This entire skill group is missing from your character."
            score += 5  # boost missing skills
        elif group_delta.missing_supports:
            title = f"'{group_delta.skill_name}' missing {len(group_delta.missing_supports)} supports"
            detail = f"Add: {', '.join(group_delta.missing_supports)}"
        else:
            title = f"'{group_delta.skill_name}' gem levels behind"
            detail = f"{len(group_delta.level_gaps)} gems need leveling"

        gaps.append(DeltaGap(
            category=GapCategory.GEM,
            severity=sev,
            title=title,
            detail=detail,
            score=round(score, 1),
        ))

    return gaps
