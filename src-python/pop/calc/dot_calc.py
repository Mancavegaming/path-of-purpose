"""
Damage over Time (ailment) calculations: Ignite, Bleed, Poison.

PoE ailment mechanics:
- Ignite: 50% of fire hit per second for 4s. Only strongest applies.
- Bleed: 70% of phys hit per second for 5s. Attacks only. 3x while moving.
- Poison: 20% of (phys+chaos) hit per second for 2s. Stacks infinitely.

Ailment modifiers: type-specific increased/more, burning damage, DoT,
DoT multiplier. "Increased Attack/Spell Damage" does NOT apply.
Penetration does NOT apply to DoT. Bleed ignores enemy armour/phys reduction.
"""

from __future__ import annotations

from pop.calc.models import CalcConfig, DamageType, Modifier, StatPool

# Stat names that do NOT apply to ailments (hit-only modifiers)
_HIT_ONLY_STATS = frozenset({
    "increased_attack_damage",
    "increased_spell_damage",
    "increased_melee_damage",
    "increased_projectile_damage",
    "increased_area_damage",
    "increased_damage_with_hits",
    "more_attack_damage",
    "more_spell_damage",
    "more_melee_damage",
    "more_projectile_damage",
    "more_area_damage",
    "more_damage_with_hits",
})


# ---------------------------------------------------------------------------
# Ailment chance
# ---------------------------------------------------------------------------


def calc_effective_ailment_chance(
    base_chance: float,
    crit_chance: float,
    ailment_type: str,
) -> float:
    """Calculate effective ailment application chance (0-1).

    Args:
        base_chance: Base ailment chance in % (0-100).
        crit_chance: Effective crit chance as fraction (0-1).
        ailment_type: "ignite", "bleed", or "poison".

    For ignite: crits always ignite in PoE1, so effective chance =
    base/100 + (1 - base/100) * crit_chance.
    For bleed/poison: just base/100.
    """
    base = min(base_chance, 100.0) / 100.0
    if ailment_type == "ignite":
        # Crits always ignite: P(ignite) = P(base) + P(crit) * P(not base)
        return min(base + (1.0 - base) * crit_chance, 1.0)
    return min(base, 1.0)


# ---------------------------------------------------------------------------
# Modifier helpers — filter hit mods for ailment applicability
# ---------------------------------------------------------------------------


def _ailment_increased(pool: StatPool, dtype: DamageType) -> float:
    """Sum increased% mods applicable to ailments of the given type.

    Includes type-specific and generic from the HIT increased pool,
    plus all DoT-specific increased mods. Excludes hit-only categories
    (attack, spell, melee, projectile, area, hits).
    """
    total = 0.0

    # From hit increased pool — type-matched but not hit-only
    for mod in pool.increased_mods:
        if mod.stat in _HIT_ONLY_STATS:
            continue
        if not mod.damage_types or dtype in mod.damage_types:
            total += mod.value

    # From DoT-specific increased pool
    for mod in pool.increased_dot_mods:
        if not mod.damage_types or dtype in mod.damage_types:
            total += mod.value

    return total


def _ailment_more(pool: StatPool, dtype: DamageType) -> float:
    """Compute product of all more multipliers applicable to ailments of the given type."""
    product = 1.0

    # From hit more pool — type-matched but not hit-only
    for mod in pool.more_mods:
        if mod.stat in _HIT_ONLY_STATS:
            continue
        if not mod.damage_types or dtype in mod.damage_types:
            product *= 1.0 + mod.value / 100.0

    # From DoT-specific more pool
    for mod in pool.more_dot_mods:
        if not mod.damage_types or dtype in mod.damage_types:
            product *= 1.0 + mod.value / 100.0

    return product


def _dot_multiplier(pool: StatPool, dtype: DamageType) -> float:
    """Calculate the DoT multiplier for a damage type.

    All DoT multi bonuses are additive with each other, then applied
    as a single multiplicative factor: (1 + total/100).
    """
    total = pool.dot_multi  # generic
    if dtype == DamageType.FIRE:
        total += pool.dot_multi_fire
    elif dtype == DamageType.PHYSICAL:
        total += pool.dot_multi_phys
    elif dtype == DamageType.CHAOS:
        total += pool.dot_multi_chaos
    return 1.0 + total / 100.0


def _enemy_dot_resist_multi(dtype: DamageType, config: CalcConfig) -> float:
    """Calculate enemy resistance multiplier for DoT.

    Penetration does NOT apply to DoT. Physical DoT ignores armour.
    """
    if dtype == DamageType.PHYSICAL:
        return 1.0  # Bleed ignores armour/phys reduction
    resist = config.enemy_resist_for(dtype)
    return 1.0 - resist / 100.0


# ---------------------------------------------------------------------------
# Individual ailment calculations
# ---------------------------------------------------------------------------


def calc_ignite_dps(
    hit_fire_damage: float,
    pool: StatPool,
    config: CalcConfig,
    effective_ignite_chance: float,
) -> float:
    """Calculate ignite DPS.

    Base: 50% of fire hit damage per second, over 4 seconds.
    Only the strongest ignite applies (no stacking).
    """
    if hit_fire_damage <= 0 or effective_ignite_chance <= 0:
        return 0.0

    base_dps = hit_fire_damage * 0.5

    # Increased% (fire + generic + DoT + burning, but not attack/spell)
    inc = _ailment_increased(pool, DamageType.FIRE)
    after_inc = base_dps * (1.0 + inc / 100.0)

    # More multipliers
    more = _ailment_more(pool, DamageType.FIRE)
    after_more = after_inc * more

    # DoT multiplier
    dot_multi = _dot_multiplier(pool, DamageType.FIRE)
    after_dot_multi = after_more * dot_multi

    # Enemy fire resistance (no penetration for DoT)
    resist_multi = _enemy_dot_resist_multi(DamageType.FIRE, config)
    after_resist = after_dot_multi * resist_multi

    return after_resist * effective_ignite_chance


def calc_bleed_dps(
    hit_phys_damage: float,
    pool: StatPool,
    config: CalcConfig,
    effective_bleed_chance: float,
    is_attack: bool,
) -> float:
    """Calculate bleed DPS.

    Base: 70% of phys hit damage per second, over 5 seconds.
    Attacks only. 3x damage while enemy is moving.
    Physical DoT ignores armour/phys reduction.
    """
    if not is_attack or hit_phys_damage <= 0 or effective_bleed_chance <= 0:
        return 0.0

    base_dps = hit_phys_damage * 0.7

    # Moving multiplier
    if config.enemy_is_moving:
        base_dps *= 3.0

    # Increased% (physical + generic + DoT, not attack/spell)
    inc = _ailment_increased(pool, DamageType.PHYSICAL)
    after_inc = base_dps * (1.0 + inc / 100.0)

    # More multipliers
    more = _ailment_more(pool, DamageType.PHYSICAL)
    after_more = after_inc * more

    # DoT multiplier
    dot_multi = _dot_multiplier(pool, DamageType.PHYSICAL)
    after_dot_multi = after_more * dot_multi

    # Bleed ignores enemy phys reduction (resist_multi = 1.0)
    return after_dot_multi * effective_bleed_chance


def calc_poison_dps(
    hit_phys_damage: float,
    hit_chaos_damage: float,
    pool: StatPool,
    config: CalcConfig,
    effective_poison_chance: float,
    hits_per_second: float,
) -> float:
    """Calculate total poison DPS (all concurrent stacks).

    Base per stack: 20% of (phys + chaos) per second, over 2 seconds.
    Stacks infinitely. Total stacks = duration * hits/sec * chance.
    """
    combined = hit_phys_damage + hit_chaos_damage
    if combined <= 0 or effective_poison_chance <= 0:
        return 0.0

    base_dps_per_stack = combined * 0.2

    # Increased% (chaos + generic + DoT + poison, not attack/spell)
    inc = _ailment_increased(pool, DamageType.CHAOS)
    after_inc = base_dps_per_stack * (1.0 + inc / 100.0)

    # More multipliers
    more = _ailment_more(pool, DamageType.CHAOS)
    after_more = after_inc * more

    # DoT multiplier
    dot_multi = _dot_multiplier(pool, DamageType.CHAOS)
    after_dot_multi = after_more * dot_multi

    # Enemy chaos resistance (no penetration for DoT)
    resist_multi = _enemy_dot_resist_multi(DamageType.CHAOS, config)
    after_resist = after_dot_multi * resist_multi

    # Stacking: duration * hits_per_second * poison_chance
    base_duration = 2.0
    duration = base_duration * (1.0 + pool.increased_poison_duration / 100.0)
    stacks = duration * hits_per_second * effective_poison_chance

    return after_resist * stacks
