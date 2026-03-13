"""
Impale damage calculation.

Impale stores a portion of physical hit damage on the enemy. On subsequent
hits, all stored impales deal their recorded damage.

PoB formula:
    impale_stored = phys_hit * 0.10 * (1 + increased_effect / 100)
    avg_stacks = max_stacks * min(1.0, impale_chance)
    impale_dps = impale_stored * avg_stacks * hits_per_second

Impale DPS is added on top of normal hit DPS as a separate component.
"""

from __future__ import annotations

# Base impale: stores 10% of physical hit damage
BASE_IMPALE_STORED_PCT = 10.0

# Default max impale stacks
DEFAULT_MAX_STACKS = 5


def calc_impale_dps(
    phys_hit_after_mit: float,
    impale_chance: float,
    hits_per_second: float,
    increased_impale_effect: float = 0.0,
    max_stacks: int = DEFAULT_MAX_STACKS,
) -> float:
    """Calculate DPS contribution from impale.

    Args:
        phys_hit_after_mit: Physical hit damage after enemy mitigation.
        impale_chance: Chance to impale (0.0 to 1.0).
        hits_per_second: Number of hits per second.
        increased_impale_effect: Total increased impale effect in %.
        max_stacks: Maximum impale stacks (default 5, can be 7 with modifiers).

    Returns:
        Impale DPS contribution (added to total DPS).
    """
    if impale_chance <= 0 or phys_hit_after_mit <= 0:
        return 0.0

    # Each impale stores this much damage
    stored_per_impale = phys_hit_after_mit * (
        BASE_IMPALE_STORED_PCT / 100.0
    ) * (1.0 + increased_impale_effect / 100.0)

    # Average stacks on enemy at steady state
    avg_stacks = max_stacks * min(1.0, impale_chance)

    # Each hit triggers all stored impales
    impale_dps = stored_per_impale * avg_stacks * hits_per_second

    return impale_dps
