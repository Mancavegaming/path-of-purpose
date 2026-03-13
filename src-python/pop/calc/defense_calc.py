"""
Enemy defense mitigation calculations.

Handles:
- Elemental/chaos resistance with penetration and exposure
- Resistance floor (-200% in PoE 1, configurable)
- Physical damage reduction from armour (PoE formula)
- Physical damage reduction from flat %
"""

from __future__ import annotations

from pop.calc.models import CalcConfig, DamageType

# PoE 1 resist floor is -200% for enemies
DEFAULT_RESIST_FLOOR = -200.0


def calc_mitigation_multi(
    dtype: DamageType,
    config: CalcConfig,
    penetration: float = 0.0,
    hit_damage: float = 0.0,
    exposure: float = 0.0,
    curse_reduction: float = 0.0,
) -> float:
    """Calculate the damage multiplier after enemy mitigation for a type.

    Args:
        dtype: The damage type.
        config: Calculator configuration with enemy stats.
        penetration: Penetration value for this type in %.
        hit_damage: Raw hit damage (used for armour calc on physical).
        exposure: Exposure value for this type in % (reduces enemy resist).
        curse_reduction: Curse resist reduction for this type in %.

    Returns:
        Multiplier (can be > 1 if resist is negative after penetration).
    """
    if dtype == DamageType.PHYSICAL:
        return _calc_phys_mitigation(config, hit_damage)

    # Elemental and Chaos:
    #   effective_resist = base - curse_reduction - exposure - penetration
    # All three debuff categories stack additively against resist.
    base_resist = config.enemy_resist_for(dtype)

    # Curse reduction is a debuff on the enemy (separate from exposure)
    resist_after_curse = base_resist - curse_reduction

    # Exposure reduces the enemy's base resistance (before penetration)
    resist_after_exposure = resist_after_curse - exposure

    # Penetration is applied on hit and further reduces effective resistance
    effective_resist = resist_after_exposure - penetration

    # Resist floor
    resist_floor = DEFAULT_RESIST_FLOOR
    effective_resist = max(effective_resist, resist_floor)

    return 1.0 - effective_resist / 100.0


def _calc_phys_mitigation(config: CalcConfig, hit_damage: float) -> float:
    """Calculate physical damage multiplier from armour / phys reduction.

    PoE armour formula:
        reduction = armour / (armour + 5 * damage)
        capped at 90%

    If a flat phys reduction % is set in config, that takes priority.
    If both armour and flat reduction are set, use the higher reduction.
    """
    flat_reduction = 0.0
    if config.enemy_phys_reduction > 0:
        flat_reduction = config.enemy_phys_reduction / 100.0

    armour_reduction = 0.0
    if config.enemy_armour > 0 and hit_damage > 0:
        armour_reduction = config.enemy_armour / (config.enemy_armour + 5.0 * hit_damage)
        armour_reduction = min(armour_reduction, 0.9)

    # Use whichever gives more reduction
    total_reduction = max(flat_reduction, armour_reduction)

    # Cap at 90%
    total_reduction = min(total_reduction, 0.9)

    return 1.0 - total_reduction
