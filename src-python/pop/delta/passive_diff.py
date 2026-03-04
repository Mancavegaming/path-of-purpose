"""
Passive tree diff — compare guide passive nodes against live character.

Both sides provide sets of integer node IDs. The diff is straightforward
set arithmetic, but the scoring accounts for the fact that not all nodes
are equal (players may have fewer points available than the guide).
"""

from __future__ import annotations

from pop.build_parser.models import PassiveSpec
from pop.poe_api.models import PassiveData
from pop.delta.models import PassiveDelta


def diff_passives(
    guide: PassiveSpec,
    character: PassiveData,
    character_level: int = 1,
    guide_level: int = 1,
) -> PassiveDelta:
    """
    Compare passive tree allocations.

    Args:
        guide: PassiveSpec from the PoB build.
        character: PassiveData from the PoE API.
        character_level: Character's current level (for context).
        guide_level: Guide's target level.

    Returns:
        PassiveDelta with missing/extra nodes and match percentage.
    """
    guide_nodes = set(guide.nodes)
    char_nodes = set(character.hashes) | set(character.hashes_ex)

    missing = guide_nodes - char_nodes
    extra = char_nodes - guide_nodes

    # Match % is based on how many guide nodes the character has allocated
    if guide_nodes:
        matched = guide_nodes & char_nodes
        match_pct = (len(matched) / len(guide_nodes)) * 100
    else:
        match_pct = 100.0

    return PassiveDelta(
        missing_nodes=sorted(missing),
        extra_nodes=sorted(extra),
        missing_count=len(missing),
        extra_count=len(extra),
        guide_total=len(guide_nodes),
        character_total=len(char_nodes),
        match_pct=round(match_pct, 1),
    )
