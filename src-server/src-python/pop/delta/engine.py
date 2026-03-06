"""
Delta Engine — the core orchestrator.

Takes a guide build (PoB) and a live character (API), runs all three
diff modules, and produces a ranked DeltaReport with the top gaps.
"""

from __future__ import annotations

from pop.build_parser.models import Build
from pop.poe_api.models import CharacterDetail
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
from pop.delta.gear_diff import diff_gear
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
    Run the full Delta Engine analysis.

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
    # Build character gem map from equipment socketedItems (simplified)
    char_gem_map = _build_character_gem_map(character)
    enabled_groups = [g for g in guide.skill_groups if g.is_enabled]
    gem_delta = diff_gems(enabled_groups, char_gem_map)

    # --- Rank all gaps ---
    gaps = _collect_gaps(passive_delta, gear_delta, gem_delta)
    gaps.sort(key=lambda g: g.score, reverse=True)

    # Assign ranks
    for i, gap in enumerate(gaps):
        gap.rank = i + 1

    return DeltaReport(
        passive_delta=passive_delta,
        gear_delta=gear_delta,
        gem_delta=gem_delta,
        top_gaps=gaps[:3],
        guide_build_name=guide.build_name or guide.ascendancy_name or "Guide",
        character_name=character.name,
    )


def _build_character_gem_map(character: CharacterDetail) -> dict[str, list[str]]:
    """
    Extract gem names from character equipment, grouped by slot.

    The PoE API nests socketed gems inside each item's socketedItems array.
    Since we're building against mocked data, this returns a best-effort
    mapping that will be refined with live API data.
    """
    # TODO: Parse socketedItems from the API response when available.
    # For now, return empty — gem diff will report all guide gems as missing,
    # which is the safe default (over-report rather than under-report).
    return {}


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
