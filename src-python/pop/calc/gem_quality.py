"""
Gem quality bonus database.

Each gem has a quality bonus that grants a small stat per 1% quality.
At 20% quality, the bonus is 20× the per-quality value.

PoE quality bonuses are gem-specific. This module provides a lookup
of common quality bonuses for active and support gems.

Data sourced from PoE 1 (3.25 era).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pop.calc.models import DamageType, Modifier


@dataclass
class QualityBonus:
    """Quality bonus for a gem. Values are per 1% quality."""

    # Damage modifiers (per 1% quality)
    increased_damage: float = 0.0  # generic increased damage
    increased_damage_types: list[DamageType] = field(default_factory=list)

    # Speed (per 1% quality)
    increased_attack_speed: float = 0.0
    increased_cast_speed: float = 0.0

    # Crit (per 1% quality)
    increased_crit: float = 0.0

    # Area/projectile (per 1% quality)
    increased_area_damage: float = 0.0
    increased_projectile_damage: float = 0.0

    # DoT (per 1% quality)
    increased_dot: float = 0.0

    # Accuracy (per 1% quality)
    increased_accuracy: float = 0.0

    # Ailment chance (per 1% quality)
    chance_to_ignite: float = 0.0
    chance_to_bleed: float = 0.0
    chance_to_poison: float = 0.0

    # Penetration (per 1% quality, rare)
    penetration: dict[DamageType, float] = field(default_factory=dict)

    # Area of effect (per 1% quality) — cosmetic, no DPS impact
    increased_area_of_effect: float = 0.0


# ===================================================================
# Quality bonus database
# ===================================================================

_QUALITY_DB: dict[str, QualityBonus] = {}


def _q(name: str, **kw: object) -> None:
    _QUALITY_DB[name] = QualityBonus(**kw)  # type: ignore[arg-type]


# -------------------------------------------------------------------
# Active skill gems — common quality bonuses
# -------------------------------------------------------------------

# Melee attacks — most give 0.5% increased attack speed per quality
_q("Cyclone", increased_attack_speed=0.5)
_q("Lacerate", increased_attack_speed=0.5)
_q("Blade Flurry", increased_attack_speed=0.5)
_q("Double Strike", increased_attack_speed=0.5)
_q("Flicker Strike", increased_attack_speed=0.5)
_q("Frost Blades", increased_attack_speed=0.5)
_q("Lightning Strike", increased_attack_speed=0.5)
_q("Molten Strike", increased_attack_speed=0.5)
_q("Wild Strike", increased_attack_speed=0.5)
_q("Reave", increased_area_of_effect=0.5)
_q("Cleave", increased_area_of_effect=0.5)
_q("Earthquake", increased_area_of_effect=0.5)
_q("Ground Slam", increased_area_of_effect=0.5)
_q("Sunder", increased_area_of_effect=0.5)
_q("Tectonic Slam", increased_area_of_effect=0.5)
_q("Ice Crash", increased_area_of_effect=0.5)
_q("Consecrated Path", increased_area_of_effect=0.5)
_q("Smite", increased_area_of_effect=0.5)
_q("Viper Strike", increased_damage=0.5, increased_damage_types=[DamageType.CHAOS])

# Ranged attacks — most give 1% increased damage per quality
_q("Tornado Shot", increased_damage=1.0)
_q("Lightning Arrow", increased_damage=1.0)
_q("Ice Shot", increased_damage=1.0)
_q("Barrage", increased_attack_speed=0.5)
_q("Rain of Arrows", increased_area_of_effect=0.5)
_q("Split Arrow", increased_damage=1.0)
_q("Galvanic Arrow", increased_damage=1.0)
_q("Elemental Hit", increased_damage=1.0)
_q("Spectral Throw", increased_projectile_damage=1.0)
_q("Kinetic Blast", increased_damage=1.0)
_q("Power Siphon", increased_crit=0.5)
_q("Puncture", increased_damage=1.0)

# Spells — most give 0.5% increased damage per quality
_q("Fireball", increased_damage=1.0, increased_damage_types=[DamageType.FIRE])
_q("Arc", increased_damage=1.0, increased_damage_types=[DamageType.LIGHTNING])
_q("Spark", increased_damage=1.0, increased_damage_types=[DamageType.LIGHTNING])
_q("Freezing Pulse", increased_damage=1.0, increased_damage_types=[DamageType.COLD])
_q("Ice Nova", increased_area_of_effect=0.5)
_q("Glacial Cascade", increased_damage=1.0, increased_damage_types=[DamageType.COLD])
_q("Firestorm", increased_damage=1.0, increased_damage_types=[DamageType.FIRE])
_q("Ball Lightning", increased_damage=1.0, increased_damage_types=[DamageType.LIGHTNING])
_q("Storm Brand", increased_damage=1.0)
_q("Armageddon Brand", increased_damage=1.0)
_q("Blade Vortex", increased_area_of_effect=0.5)
_q("Ethereal Knives", increased_projectile_damage=1.0)
_q("Divine Ire", increased_damage=1.0)
_q("Wave of Conviction", increased_area_of_effect=0.5)
_q("Essence Drain", increased_dot=0.5)
_q("Contagion", increased_area_of_effect=0.5)
_q("Blight", increased_dot=0.5)
_q("Soulrend", increased_damage=1.0, increased_damage_types=[DamageType.CHAOS])
_q("Bane", increased_damage=1.0, increased_damage_types=[DamageType.CHAOS])
_q("Flame Surge", increased_damage=1.0, increased_damage_types=[DamageType.FIRE])
_q("Incinerate", increased_damage=1.0, increased_damage_types=[DamageType.FIRE])
_q("Winter Orb", increased_projectile_damage=1.0)
_q("Penance Brand", increased_area_of_effect=0.5)
_q("Crackling Lance", increased_damage=1.0, increased_damage_types=[DamageType.LIGHTNING])
_q("Forbidden Rite", increased_damage=1.0, increased_damage_types=[DamageType.CHAOS])

# DoT spells
_q("Scorching Ray", increased_dot=0.5)
_q("Righteous Fire", increased_dot=0.5)
_q("Caustic Arrow", increased_dot=0.5)
_q("Toxic Rain", increased_dot=0.5)

# Minion gems — typically increased minion damage
_q("Raise Zombie", increased_damage=1.0)
_q("Summon Raging Spirit", increased_damage=1.0)
_q("Raise Spectre", increased_damage=1.0)
_q("Summon Skeletons", increased_damage=1.0)
_q("Summon Carrion Golem", increased_damage=1.0)

# -------------------------------------------------------------------
# Support gems — common quality bonuses
# -------------------------------------------------------------------

# Damage supports — typically 0.5% increased damage per quality
_q("Brutality Support", increased_damage=0.5, increased_damage_types=[DamageType.PHYSICAL])
_q("Melee Physical Damage Support", increased_damage=0.5, increased_damage_types=[DamageType.PHYSICAL])
_q("Elemental Damage with Attacks Support", increased_damage=0.5)
_q("Controlled Destruction Support", increased_damage=0.5)
_q("Concentrated Effect Support", increased_area_damage=0.5)
_q("Void Manipulation Support", increased_damage=0.5, increased_damage_types=[DamageType.CHAOS])
_q("Minion Damage Support", increased_damage=0.5)
_q("Hypothermia Support", increased_damage=0.5, increased_damage_types=[DamageType.COLD])
_q("Immolate Support", increased_damage=0.5, increased_damage_types=[DamageType.FIRE])
_q("Added Fire Damage Support", increased_damage=0.5, increased_damage_types=[DamageType.FIRE])
_q("Added Cold Damage Support", increased_damage=0.5, increased_damage_types=[DamageType.COLD])
_q("Added Lightning Damage Support", increased_damage=0.5, increased_damage_types=[DamageType.LIGHTNING])

# Crit supports
_q("Increased Critical Strikes Support", increased_crit=0.5)
_q("Increased Critical Damage Support", increased_damage=0.5)

# Speed supports
_q("Multistrike Support", increased_attack_speed=0.5)
_q("Spell Echo Support", increased_cast_speed=0.5)
_q("Faster Attacks Support", increased_attack_speed=0.5)
_q("Faster Casting Support", increased_cast_speed=0.5)

# Projectile supports
_q("Greater Multiple Projectiles Support", increased_projectile_damage=0.5)
_q("Lesser Multiple Projectiles Support", increased_projectile_damage=0.5)
_q("Fork Support", increased_projectile_damage=0.5)
_q("Chain Support", increased_projectile_damage=0.5)
_q("Pierce Support", increased_projectile_damage=0.5)
_q("Vicious Projectiles Support", increased_dot=0.5)

# DoT supports
_q("Deadly Ailments Support", increased_dot=0.5)
_q("Swift Affliction Support", increased_dot=0.5)
_q("Unbound Ailments Support", increased_dot=0.5)
_q("Burning Damage Support", increased_dot=0.5)

# Elemental focus
_q("Elemental Focus Support", increased_damage=0.5)

# Penetration supports
_q("Fire Penetration Support", penetration={DamageType.FIRE: 0.5})
_q("Cold Penetration Support", penetration={DamageType.COLD: 0.5})
_q("Lightning Penetration Support", penetration={DamageType.LIGHTNING: 0.5})

# Awakened variants (same quality bonuses as base, typically)
_q("Awakened Brutality Support", increased_damage=0.5, increased_damage_types=[DamageType.PHYSICAL])
_q("Awakened Melee Physical Damage Support", increased_damage=0.5, increased_damage_types=[DamageType.PHYSICAL])
_q("Awakened Elemental Damage with Attacks Support", increased_damage=0.5)
_q("Awakened Controlled Destruction Support", increased_damage=0.5)
_q("Awakened Concentrated Effect Support", increased_area_damage=0.5)
_q("Awakened Void Manipulation Support", increased_damage=0.5, increased_damage_types=[DamageType.CHAOS])
_q("Awakened Minion Damage Support", increased_damage=0.5)
_q("Awakened Hypothermia Support", increased_damage=0.5, increased_damage_types=[DamageType.COLD])
_q("Awakened Added Fire Damage Support", increased_damage=0.5, increased_damage_types=[DamageType.FIRE])
_q("Awakened Added Cold Damage Support", increased_damage=0.5, increased_damage_types=[DamageType.COLD])
_q("Awakened Added Lightning Damage Support", increased_damage=0.5, increased_damage_types=[DamageType.LIGHTNING])
_q("Awakened Multistrike Support", increased_attack_speed=0.5)
_q("Awakened Spell Echo Support", increased_cast_speed=0.5)
_q("Awakened Greater Multiple Projectiles Support", increased_projectile_damage=0.5)
_q("Awakened Fork Support", increased_projectile_damage=0.5)
_q("Awakened Chain Support", increased_projectile_damage=0.5)
_q("Awakened Deadly Ailments Support", increased_dot=0.5)
_q("Awakened Swift Affliction Support", increased_dot=0.5)
_q("Awakened Vicious Projectiles Support", increased_dot=0.5)
_q("Awakened Elemental Focus Support", increased_damage=0.5)
_q("Awakened Fire Penetration Support", penetration={DamageType.FIRE: 0.5})
_q("Awakened Cold Penetration Support", penetration={DamageType.COLD: 0.5})
_q("Awakened Lightning Penetration Support", penetration={DamageType.LIGHTNING: 0.5})


# ===================================================================
# Public API
# ===================================================================


def get_quality_bonus(gem_name: str) -> QualityBonus | None:
    """Look up quality bonus for a gem by name."""
    return _QUALITY_DB.get(gem_name)


def apply_quality_bonus(gem_name: str, quality: int, out: object) -> None:
    """Apply quality bonus to a ParsedMods-like object.

    Args:
        gem_name: Name of the gem.
        quality: Quality percentage (0-23 typically, 20 standard).
        out: ParsedMods object to accumulate bonuses into.
    """
    if quality <= 0:
        return

    bonus = get_quality_bonus(gem_name)
    if not bonus:
        return

    from pop.calc.mod_parser import ParsedMods
    if not isinstance(out, ParsedMods):
        return

    q = float(quality)

    # Damage modifiers
    if bonus.increased_damage > 0:
        types = bonus.increased_damage_types
        stat_name = "increased_damage"
        if types:
            type_word = types[0].value
            stat_name = f"increased_{type_word}_damage"
        out.increased.append(Modifier(
            stat=stat_name,
            value=bonus.increased_damage * q,
            mod_type="increased",
            damage_types=types,
            source=f"quality:{gem_name}",
        ))

    # Speed
    if bonus.increased_attack_speed > 0:
        out.increased_attack_speed += bonus.increased_attack_speed * q
    if bonus.increased_cast_speed > 0:
        out.increased_cast_speed += bonus.increased_cast_speed * q

    # Crit
    if bonus.increased_crit > 0:
        out.increased_crit += bonus.increased_crit * q

    # Area/projectile damage
    if bonus.increased_area_damage > 0:
        out.increased.append(Modifier(
            stat="increased_area_damage",
            value=bonus.increased_area_damage * q,
            mod_type="increased",
            source=f"quality:{gem_name}",
        ))
    if bonus.increased_projectile_damage > 0:
        out.increased.append(Modifier(
            stat="increased_projectile_damage",
            value=bonus.increased_projectile_damage * q,
            mod_type="increased",
            source=f"quality:{gem_name}",
        ))

    # DoT
    if bonus.increased_dot > 0:
        out.increased_dot.append(Modifier(
            stat="increased_dot",
            value=bonus.increased_dot * q,
            mod_type="increased",
            source=f"quality:{gem_name}",
        ))

    # Accuracy
    if bonus.increased_accuracy > 0:
        out.increased_accuracy += bonus.increased_accuracy * q

    # Ailment chance
    if bonus.chance_to_ignite > 0:
        out.chance_to_ignite += bonus.chance_to_ignite * q
    if bonus.chance_to_bleed > 0:
        out.chance_to_bleed += bonus.chance_to_bleed * q
    if bonus.chance_to_poison > 0:
        out.chance_to_poison += bonus.chance_to_poison * q

    # Penetration
    for dtype, val_per_q in bonus.penetration.items():
        out.penetration[dtype] = out.penetration.get(dtype, 0.0) + val_per_q * q
