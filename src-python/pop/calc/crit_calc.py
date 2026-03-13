"""
Critical strike calculation.

Computes effective crit chance and the DPS multiplier from crit.
"""

from __future__ import annotations


def calc_effective_crit(
    base_crit: float,
    increased_crit: float,
    is_poe2: bool = False,
    lucky: bool = False,
) -> float:
    """Calculate effective crit chance (0.0 to 1.0).

    Args:
        base_crit: Base critical strike chance in % (e.g. 6.0 for 6%).
        increased_crit: Total increased critical strike chance in % (e.g. 200.0).
        is_poe2: If True, cap at 80% instead of 100%.
        lucky: If True (Diamond Flask), crit rolls twice and takes the better.
    """
    cap = 80.0 if is_poe2 else 100.0
    effective_pct = min(base_crit * (1.0 + increased_crit / 100.0), cap)
    # Floor at 0
    chance = max(effective_pct / 100.0, 0.0)

    # Lucky crit (Diamond Flask): roll twice, take better result
    # P(lucky) = 1 - (1 - p)^2
    if lucky and chance < 1.0:
        chance = 1.0 - (1.0 - chance) ** 2

    return chance


def calc_crit_dps_multi(crit_chance: float, crit_multi: float) -> float:
    """Calculate the effective DPS multiplier from crit.

    Args:
        crit_chance: Effective crit chance as decimal (0.0 to 1.0).
        crit_multi: Total crit multiplier in % (base 150%).

    Returns:
        Multiplier ≥ 1.0. E.g. with 50% crit and 200% multi → 1.5.
    """
    multi_decimal = crit_multi / 100.0  # 150% → 1.5
    return 1.0 + crit_chance * (multi_decimal - 1.0)
