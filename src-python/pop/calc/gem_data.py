"""
Comprehensive PoE 1 gem database for damage calculations.

Every active skill gem and support gem with level 20 stats:
- Active gems: base damage, crit, cast time, damage effectiveness, tags
- Support gems: more/less multipliers, added damage, speed mods

Data sourced from PoE 1 (3.25 Settlers of Kalguur era).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pop.calc.models import DamageType, Modifier

@dataclass
class ActiveGemStats:
    """Stats for an active skill gem at a given level."""

    name: str
    tags: list[str] = field(default_factory=list)
    is_attack: bool = False
    is_spell: bool = False
    base_damage: dict[DamageType, float] = field(default_factory=dict)
    base_crit: float = 5.0
    base_cast_time: float = 1.0
    damage_effectiveness: float = 1.0
    attack_speed_multiplier: float = 1.0

@dataclass
class SupportGemEffect:
    """Modifier grants from a support gem at level 20."""

    name: str
    modifiers: list[Modifier] = field(default_factory=list)
    added_damage: dict[DamageType, float] = field(default_factory=dict)
    attack_speed_mod: float = 0.0
    cast_speed_mod: float = 0.0
    less_attack_speed: float = 0.0
    penetration: dict[DamageType, float] = field(default_factory=dict)
    increased_crit: float = 0.0
    impale_chance: float = 0.0  # 0-100%
    increased_impale_effect: float = 0.0

# ===================================================================
# Active gem database — level 20 stats
# ===================================================================

_ACTIVE_GEMS: dict[str, ActiveGemStats] = {}

def _a(name: str, **kw) -> None:
    """Register an active gem."""
    _ACTIVE_GEMS[name] = ActiveGemStats(name=name, **kw)

# -------------------------------------------------------------------
# MELEE ATTACKS
# -------------------------------------------------------------------

_a("Cyclone", tags=["attack", "melee", "area", "channelling", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=3.0, damage_effectiveness=0.56)

_a("Lacerate", tags=["attack", "melee", "area", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.85, damage_effectiveness=0.93)

_a("Double Strike", tags=["attack", "melee", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.8, damage_effectiveness=0.91)

_a("Blade Flurry", tags=["attack", "melee", "area", "channelling", "physical"],
   is_attack=True, base_crit=6.0, attack_speed_multiplier=1.6, damage_effectiveness=0.47)

_a("Molten Strike", tags=["attack", "melee", "area", "projectile", "fire"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.95, damage_effectiveness=1.3)

_a("Flicker Strike", tags=["attack", "melee", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.2, damage_effectiveness=1.42)

_a("Boneshatter", tags=["attack", "melee", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.9, damage_effectiveness=1.98)

_a("Lightning Strike", tags=["attack", "melee", "projectile", "lightning"],
   is_attack=True, base_crit=6.0, attack_speed_multiplier=0.9, damage_effectiveness=1.35)

_a("Frost Blades", tags=["attack", "melee", "projectile", "cold"],
   is_attack=True, base_crit=6.0, attack_speed_multiplier=0.9, damage_effectiveness=1.22)

_a("Elemental Hit", tags=["attack", "melee", "projectile", "fire", "cold", "lightning", "area"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=1.5,
   base_damage={DamageType.FIRE: 166.5, DamageType.COLD: 166.5, DamageType.LIGHTNING: 166.5})

_a("Wild Strike", tags=["attack", "melee", "fire", "cold", "lightning"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.1, damage_effectiveness=1.5)

_a("Smite", tags=["attack", "melee", "area", "lightning"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.85, damage_effectiveness=1.0,
   base_damage={DamageType.LIGHTNING: 319.0})

_a("Reave", tags=["attack", "melee", "area", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=1.15)

_a("Viper Strike", tags=["attack", "melee", "chaos"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.95, damage_effectiveness=1.15)

_a("Puncture", tags=["attack", "melee", "projectile", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=1.35)

_a("Cleave", tags=["attack", "melee", "area", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.8, damage_effectiveness=1.45)

_a("Ground Slam", tags=["attack", "melee", "area", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.9, damage_effectiveness=1.5)

_a("Earthquake", tags=["attack", "melee", "area", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.7, damage_effectiveness=1.5)

_a("Sunder", tags=["attack", "melee", "area", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.85, damage_effectiveness=1.65)

_a("Tectonic Slam", tags=["attack", "melee", "area", "fire"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.9, damage_effectiveness=1.5)

_a("Consecrated Path", tags=["attack", "melee", "area", "fire"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.7, damage_effectiveness=1.47)

_a("Glacial Hammer", tags=["attack", "melee", "cold"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.95, damage_effectiveness=1.65)

_a("Ice Crash", tags=["attack", "melee", "area", "cold"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.7, damage_effectiveness=2.3)

_a("Infernal Blow", tags=["attack", "melee", "area", "fire"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.95, damage_effectiveness=1.55)

_a("Heavy Strike", tags=["attack", "melee", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.85, damage_effectiveness=1.98)

_a("Dominating Blow", tags=["attack", "melee", "minion"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.9, damage_effectiveness=1.5)

_a("Ancestral Protector", tags=["attack", "melee", "totem"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.9, damage_effectiveness=1.1)

_a("Ancestral Warchief", tags=["attack", "melee", "area", "totem"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.75, damage_effectiveness=1.8)

_a("Vaal Ancestral Warchief", tags=["attack", "melee", "area", "totem", "vaal"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.75, damage_effectiveness=1.8)

_a("Static Strike", tags=["attack", "melee", "area", "lightning"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.85, damage_effectiveness=1.1)

_a("Dual Strike", tags=["attack", "melee", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.8, damage_effectiveness=0.95)

_a("Vigilant Strike", tags=["attack", "melee", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.7, damage_effectiveness=2.1)

_a("Pestilent Strike", tags=["attack", "melee", "chaos"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.95, damage_effectiveness=1.35)

_a("Rage Vortex", tags=["attack", "melee", "area"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.7, damage_effectiveness=0.75)

_a("Perforate", tags=["attack", "melee", "area", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=1.35)

_a("Bladestorm", tags=["attack", "melee", "area", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.85, damage_effectiveness=1.35)

_a("Lancing Steel", tags=["attack", "projectile", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.9)

_a("Shattering Steel", tags=["attack", "projectile", "area", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.9, damage_effectiveness=0.95)

_a("Splitting Steel", tags=["attack", "projectile", "area", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=1.0)

_a("Shield Charge", tags=["attack", "melee", "area", "movement"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.65, damage_effectiveness=1.5)

_a("Leap Slam", tags=["attack", "melee", "area", "movement"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.64, damage_effectiveness=1.0)

_a("Whirling Blades", tags=["attack", "melee", "movement"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.6, damage_effectiveness=0.8)

_a("Charged Dash", tags=["attack", "melee", "area", "channelling", "lightning", "movement"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.8, damage_effectiveness=0.9)

_a("Dash", tags=["movement", "spell"],
   is_spell=True, base_crit=0.0, base_cast_time=0.15, damage_effectiveness=0.0)

_a("Frenzy", tags=["attack", "melee", "projectile"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=1.0)

_a("Vengeance", tags=["attack", "melee", "area", "trigger"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.75)

_a("Riposte", tags=["attack", "melee", "trigger"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=1.15)

_a("Reckoning", tags=["attack", "melee", "area", "trigger"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=1.15)

_a("Shield Crush", tags=["attack", "melee", "area", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.8, damage_effectiveness=1.0)

_a("Spectral Helix", tags=["attack", "projectile"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.95, damage_effectiveness=1.35)

_a("Spectral Throw", tags=["attack", "projectile"],
   is_attack=True, base_crit=6.0, attack_speed_multiplier=1.1, damage_effectiveness=0.8)

_a("Cobra Lash", tags=["attack", "projectile", "chaos", "chaining"],
   is_attack=True, base_crit=6.0, attack_speed_multiplier=1.1, damage_effectiveness=0.8)

_a("Ethereal Knives", tags=["spell", "projectile", "physical"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 670.0}, base_crit=5.0,
   base_cast_time=0.6, damage_effectiveness=1.0)

_a("Blade Vortex", tags=["spell", "area", "physical"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 161.0}, base_crit=6.0,
   base_cast_time=0.5, damage_effectiveness=0.45)

_a("Bladefall", tags=["spell", "area", "physical"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 977.0}, base_crit=5.0,
   base_cast_time=0.75, damage_effectiveness=1.2)

_a("Blade Blast", tags=["spell", "area", "physical"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 302.0}, base_crit=6.0,
   base_cast_time=0.5, damage_effectiveness=0.5)

# -------------------------------------------------------------------
# RANGED / BOW ATTACKS
# -------------------------------------------------------------------

_a("Tornado Shot", tags=["attack", "projectile"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=1.1)

_a("Lightning Arrow", tags=["attack", "projectile", "area", "lightning"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=1.04)

_a("Ice Shot", tags=["attack", "projectile", "area", "cold"],
   is_attack=True, base_crit=6.0, attack_speed_multiplier=1.0, damage_effectiveness=1.36)

_a("Barrage", tags=["attack", "projectile"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.476)

_a("Kinetic Blast", tags=["attack", "projectile", "area"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.63)

_a("Rain of Arrows", tags=["attack", "projectile", "area"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.73)

_a("Split Arrow", tags=["attack", "projectile"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.85)

_a("Burning Arrow", tags=["attack", "projectile", "fire"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=1.61)

_a("Caustic Arrow", tags=["attack", "projectile", "area", "chaos"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.64)

_a("Toxic Rain", tags=["attack", "projectile", "area", "chaos"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.05, damage_effectiveness=0.7)

_a("Scourge Arrow", tags=["attack", "projectile", "area", "channelling", "chaos"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=2.0, damage_effectiveness=0.5)

_a("Galvanic Arrow", tags=["attack", "projectile", "area", "lightning"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.85)

_a("Shrapnel Ballista", tags=["attack", "projectile", "area", "totem"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.8, damage_effectiveness=1.0)

_a("Artillery Ballista", tags=["attack", "projectile", "area", "totem", "fire"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.5, damage_effectiveness=0.64)

_a("Siege Ballista", tags=["attack", "projectile", "totem"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.8, damage_effectiveness=1.0)

_a("Blast Rain", tags=["attack", "projectile", "area", "fire"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.55)

_a("Explosive Arrow", tags=["attack", "projectile", "area", "fire"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.55)

_a("Ensnaring Arrow", tags=["attack", "projectile"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.85)


_a("Power Siphon", tags=["attack", "projectile"],
   is_attack=True, base_crit=7.0, attack_speed_multiplier=1.0, damage_effectiveness=1.25)

_a("Barrage Support", tags=["attack", "projectile"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.476)

_a("Kinetic Bolt", tags=["attack", "projectile"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.85)

# -------------------------------------------------------------------
# LIGHTNING SPELLS
# -------------------------------------------------------------------

_a("Arc", tags=["spell", "lightning", "chaining"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 560.5}, base_crit=5.0,
   base_cast_time=0.7, damage_effectiveness=0.8)

_a("Spark", tags=["spell", "projectile", "lightning"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 345.0}, base_crit=5.0,
   base_cast_time=0.65, damage_effectiveness=0.7)

_a("Ball Lightning", tags=["spell", "projectile", "lightning", "area"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 94.5}, base_crit=5.0,
   base_cast_time=0.75, damage_effectiveness=0.5)

_a("Storm Brand", tags=["spell", "lightning", "area", "brand"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 327.0}, base_crit=5.0,
   base_cast_time=0.75, damage_effectiveness=0.6)

_a("Orb of Storms", tags=["spell", "lightning", "area"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 165.0}, base_crit=5.0,
   base_cast_time=0.5, damage_effectiveness=0.5)

_a("Storm Call", tags=["spell", "lightning", "area"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 1380.0}, base_crit=5.0,
   base_cast_time=0.5, damage_effectiveness=2.0)

_a("Shock Nova", tags=["spell", "lightning", "area"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 640.0}, base_crit=5.0,
   base_cast_time=0.75, damage_effectiveness=1.0)

_a("Wrath", tags=["spell", "aura", "lightning"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Conductivity", tags=["spell", "curse", "lightning"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Crackling Lance", tags=["spell", "lightning"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 700.0}, base_crit=6.0,
   base_cast_time=0.6, damage_effectiveness=1.0)

_a("Voltaxic Burst", tags=["spell", "lightning", "chaos", "area"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 440.0, DamageType.CHAOS: 440.0},
   base_crit=5.0, base_cast_time=0.7, damage_effectiveness=0.9)

_a("Lightning Conduit", tags=["spell", "lightning", "area"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 600.0}, base_crit=5.0,
   base_cast_time=0.6, damage_effectiveness=1.1)

_a("Galvanic Field", tags=["spell", "lightning"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 200.0}, base_crit=5.0,
   base_cast_time=0.5, damage_effectiveness=0.5)

# -------------------------------------------------------------------
# FIRE SPELLS
# -------------------------------------------------------------------

_a("Fireball", tags=["spell", "projectile", "area", "fire"],
   is_spell=True, base_damage={DamageType.FIRE: 1095.0}, base_crit=6.0,
   base_cast_time=0.75, damage_effectiveness=2.4)

_a("Incinerate", tags=["spell", "fire", "channelling"],
   is_spell=True, base_damage={DamageType.FIRE: 110.0}, base_crit=5.0,
   base_cast_time=0.2, damage_effectiveness=0.3)

_a("Flame Surge", tags=["spell", "fire", "area"],
   is_spell=True, base_damage={DamageType.FIRE: 900.0}, base_crit=6.0,
   base_cast_time=0.5, damage_effectiveness=1.2)

_a("Firestorm", tags=["spell", "fire", "area"],
   is_spell=True, base_damage={DamageType.FIRE: 200.0}, base_crit=5.0,
   base_cast_time=0.9, damage_effectiveness=0.45)

_a("Magma Orb", tags=["spell", "fire", "projectile", "area"],
   is_spell=True, base_damage={DamageType.FIRE: 760.0}, base_crit=5.0,
   base_cast_time=0.7, damage_effectiveness=1.5)

_a("Flame Dash", tags=["spell", "fire", "movement"],
   is_spell=True, base_damage={DamageType.FIRE: 820.0}, base_crit=5.0,
   base_cast_time=0.7, damage_effectiveness=1.2)

_a("Rolling Magma", tags=["spell", "fire", "projectile", "area"],
   is_spell=True, base_damage={DamageType.FIRE: 350.0}, base_crit=5.0,
   base_cast_time=0.75, damage_effectiveness=0.7)

_a("Flameblast", tags=["spell", "fire", "area", "channelling"],
   is_spell=True, base_damage={DamageType.FIRE: 135.0}, base_crit=5.0,
   base_cast_time=0.2, damage_effectiveness=0.5)

_a("Fire Trap", tags=["spell", "fire", "area", "trap"],
   is_spell=True, base_damage={DamageType.FIRE: 1300.0}, base_crit=5.0,
   base_cast_time=1.0, damage_effectiveness=1.6)

_a("Flamethrower Trap", tags=["spell", "fire", "area", "trap"],
   is_spell=True, base_damage={DamageType.FIRE: 240.0}, base_crit=5.0,
   base_cast_time=1.0, damage_effectiveness=0.4)

_a("Flame Wall", tags=["spell", "fire", "area"],
   is_spell=True, base_damage={DamageType.FIRE: 215.0}, base_crit=5.0,
   base_cast_time=0.5, damage_effectiveness=0.5)

_a("Armageddon Brand", tags=["spell", "fire", "area", "brand"],
   is_spell=True, base_damage={DamageType.FIRE: 520.0}, base_crit=5.0,
   base_cast_time=0.75, damage_effectiveness=0.8)

_a("Cremation", tags=["spell", "fire", "area", "projectile"],
   is_spell=True, base_damage={DamageType.FIRE: 680.0}, base_crit=5.0,
   base_cast_time=0.6, damage_effectiveness=0.9)

_a("Righteous Fire", tags=["spell", "fire", "area", "dot"],
   is_spell=True, base_damage={DamageType.FIRE: 183.0}, base_crit=0.0,
   base_cast_time=1.0, damage_effectiveness=0.0)

_a("Scorching Ray", tags=["spell", "fire", "channelling"],
   is_spell=True, base_damage={DamageType.FIRE: 250.0}, base_crit=0.0,
   base_cast_time=0.5, damage_effectiveness=0.0)  # DoT — no hit

_a("Anger", tags=["spell", "aura", "fire"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Flammability", tags=["spell", "curse", "fire"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Wave of Conviction", tags=["spell", "fire", "lightning", "physical", "area"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 300.0, DamageType.FIRE: 150.0, DamageType.LIGHTNING: 150.0},
   base_crit=5.0, base_cast_time=0.75, damage_effectiveness=1.4)

_a("Purifying Flame", tags=["spell", "fire", "area", "physical"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 340.0, DamageType.FIRE: 510.0},
   base_crit=5.0, base_cast_time=0.6, damage_effectiveness=1.4)

_a("Penance Brand", tags=["spell", "fire", "lightning", "area", "brand"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 200.0}, base_crit=5.0,
   base_cast_time=0.65, damage_effectiveness=0.4)

_a("Flame Link", tags=["spell", "fire"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

# -------------------------------------------------------------------
# COLD SPELLS
# -------------------------------------------------------------------

_a("Freezing Pulse", tags=["spell", "projectile", "cold"],
   is_spell=True, base_damage={DamageType.COLD: 904.0}, base_crit=6.0,
   base_cast_time=0.65, damage_effectiveness=1.8)

_a("Ice Spear", tags=["spell", "projectile", "cold"],
   is_spell=True, base_damage={DamageType.COLD: 720.0}, base_crit=7.0,
   base_cast_time=0.7, damage_effectiveness=1.0)

_a("Ice Nova", tags=["spell", "cold", "area"],
   is_spell=True, base_damage={DamageType.COLD: 680.0}, base_crit=6.0,
   base_cast_time=0.7, damage_effectiveness=1.0)

_a("Frostbolt", tags=["spell", "projectile", "cold"],
   is_spell=True, base_damage={DamageType.COLD: 778.0}, base_crit=5.0,
   base_cast_time=0.75, damage_effectiveness=1.6)

_a("Vortex", tags=["spell", "cold", "area"],
   is_spell=True, base_damage={DamageType.COLD: 850.0}, base_crit=6.0,
   base_cast_time=1.0, damage_effectiveness=0.6)

_a("Glacial Cascade", tags=["spell", "cold", "area", "physical"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 268.0, DamageType.COLD: 402.0},
   base_crit=5.0, base_cast_time=0.6, damage_effectiveness=0.6)

_a("Cold Snap", tags=["spell", "cold", "area"],
   is_spell=True, base_damage={DamageType.COLD: 1050.0}, base_crit=5.0,
   base_cast_time=0.85, damage_effectiveness=1.5)

_a("Arctic Breath", tags=["spell", "projectile", "cold", "area"],
   is_spell=True, base_damage={DamageType.COLD: 700.0}, base_crit=5.0,
   base_cast_time=0.7, damage_effectiveness=1.5)

_a("Winter Orb", tags=["spell", "cold", "projectile", "channelling"],
   is_spell=True, base_damage={DamageType.COLD: 300.0}, base_crit=5.0,
   base_cast_time=0.3, damage_effectiveness=0.5)

_a("Frost Bomb", tags=["spell", "cold", "area"],
   is_spell=True, base_damage={DamageType.COLD: 700.0}, base_crit=0.0,
   base_cast_time=0.5, damage_effectiveness=0.0)

_a("Wintertide Brand", tags=["spell", "cold", "area", "brand"],
   is_spell=True, base_damage={DamageType.COLD: 120.0}, base_crit=0.0,
   base_cast_time=0.75, damage_effectiveness=0.0)  # DoT brand

_a("Creeping Frost", tags=["spell", "cold", "area", "projectile"],
   is_spell=True, base_damage={DamageType.COLD: 600.0}, base_crit=5.0,
   base_cast_time=0.6, damage_effectiveness=1.0)

_a("Hatred", tags=["spell", "aura", "cold"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Frostbite", tags=["spell", "curse", "cold"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Hydrosphere", tags=["spell", "cold", "lightning", "area"],
   is_spell=True, base_damage={DamageType.COLD: 350.0}, base_crit=5.0,
   base_cast_time=0.6, damage_effectiveness=0.6)

# -------------------------------------------------------------------
# CHAOS SPELLS
# -------------------------------------------------------------------

_a("Forbidden Rite", tags=["spell", "projectile", "area", "chaos"],
   is_spell=True, base_damage={DamageType.CHAOS: 1200.0}, base_crit=6.0,
   base_cast_time=0.75, damage_effectiveness=1.2)

_a("Essence Drain", tags=["spell", "projectile", "chaos", "dot"],
   is_spell=True, base_damage={DamageType.CHAOS: 1170.0}, base_crit=5.0,
   base_cast_time=0.7, damage_effectiveness=0.9)

_a("Contagion", tags=["spell", "chaos", "area"],
   is_spell=True, base_damage={DamageType.CHAOS: 240.0}, base_crit=0.0,
   base_cast_time=1.0, damage_effectiveness=0.0)  # DoT

_a("Bane", tags=["spell", "chaos", "area"],
   is_spell=True, base_damage={DamageType.CHAOS: 640.0}, base_crit=0.0,
   base_cast_time=0.6, damage_effectiveness=0.0)  # DoT

_a("Soulrend", tags=["spell", "chaos", "projectile"],
   is_spell=True, base_damage={DamageType.CHAOS: 800.0}, base_crit=5.0,
   base_cast_time=0.6, damage_effectiveness=0.8)

_a("Dark Pact", tags=["spell", "chaos", "area"],
   is_spell=True, base_damage={DamageType.CHAOS: 600.0}, base_crit=5.0,
   base_cast_time=0.5, damage_effectiveness=1.5)

_a("Blight", tags=["spell", "chaos", "channelling", "area"],
   is_spell=True, base_damage={DamageType.CHAOS: 90.0}, base_crit=0.0,
   base_cast_time=0.3, damage_effectiveness=0.0)  # DoT channelling

_a("Wither", tags=["spell", "chaos", "channelling"],
   is_spell=True, base_crit=0.0, base_cast_time=0.28, damage_effectiveness=0.0)

_a("Despair", tags=["spell", "curse", "chaos"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Temporal Chains", tags=["spell", "curse"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Enfeeble", tags=["spell", "curse"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Vulnerability", tags=["spell", "curse"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Ele Weakness", tags=["spell", "curse"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Elemental Weakness", tags=["spell", "curse"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Hexblast", tags=["spell", "chaos", "area"],
   is_spell=True, base_damage={DamageType.CHAOS: 1300.0}, base_crit=5.0,
   base_cast_time=0.6, damage_effectiveness=2.3)

# -------------------------------------------------------------------
# PHYSICAL SPELLS
# -------------------------------------------------------------------

_a("Exsanguinate", tags=["spell", "physical"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 600.0}, base_crit=5.0,
   base_cast_time=0.7, damage_effectiveness=0.6)

_a("Reap", tags=["spell", "physical", "area"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 1200.0}, base_crit=5.0,
   base_cast_time=0.6, damage_effectiveness=2.0)

_a("Corrupting Fever", tags=["spell", "physical"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 45.0}, base_crit=0.0,
   base_cast_time=0.6, damage_effectiveness=0.0)  # DoT

# -------------------------------------------------------------------
# TRAP / MINE SPELLS
# -------------------------------------------------------------------

_a("Lightning Trap", tags=["spell", "lightning", "trap"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 580.0}, base_crit=6.0,
   base_cast_time=1.0, damage_effectiveness=1.0)

_a("Ice Trap", tags=["spell", "cold", "trap", "area"],
   is_spell=True, base_damage={DamageType.COLD: 900.0}, base_crit=6.0,
   base_cast_time=1.0, damage_effectiveness=1.4)

_a("Explosive Trap", tags=["spell", "fire", "trap", "area"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 250.0, DamageType.FIRE: 375.0},
   base_crit=5.0, base_cast_time=1.0, damage_effectiveness=1.5)

_a("Seismic Trap", tags=["spell", "physical", "trap", "area"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 400.0}, base_crit=5.0,
   base_cast_time=1.0, damage_effectiveness=0.6)

_a("Bear Trap", tags=["spell", "physical", "trap"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 1800.0}, base_crit=5.0,
   base_cast_time=1.0, damage_effectiveness=3.0)

_a("Stormblast Mine", tags=["spell", "lightning", "mine", "area"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 160.0}, base_crit=5.0,
   base_cast_time=0.75, damage_effectiveness=0.4)

_a("Pyroclast Mine", tags=["spell", "fire", "mine", "projectile", "area"],
   is_spell=True, base_damage={DamageType.FIRE: 800.0}, base_crit=5.0,
   base_cast_time=0.75, damage_effectiveness=1.6)

_a("Icicle Mine", tags=["spell", "cold", "mine", "projectile"],
   is_spell=True, base_damage={DamageType.COLD: 525.0}, base_crit=6.0,
   base_cast_time=0.75, damage_effectiveness=0.9)

_a("Blazing Salvo", tags=["spell", "fire", "projectile", "area"],
   is_spell=True, base_damage={DamageType.FIRE: 280.0}, base_crit=5.0,
   base_cast_time=0.6, damage_effectiveness=0.55)

_a("Eye of Winter", tags=["spell", "cold", "projectile"],
   is_spell=True, base_damage={DamageType.COLD: 450.0}, base_crit=5.0,
   base_cast_time=0.7, damage_effectiveness=0.65)

# -------------------------------------------------------------------
# TOTEM SPELLS
# -------------------------------------------------------------------

_a("Freezing Totem", tags=["spell", "cold", "totem", "projectile"],
   is_spell=True, base_damage={DamageType.COLD: 250.0}, base_crit=5.0,
   base_cast_time=0.6, damage_effectiveness=0.5)

_a("Holy Flame Totem", tags=["spell", "fire", "totem", "projectile"],
   is_spell=True, base_damage={DamageType.FIRE: 470.0}, base_crit=5.0,
   base_cast_time=0.25, damage_effectiveness=0.6)

_a("Flame Totem", tags=["spell", "fire", "totem", "projectile"],
   is_spell=True, base_damage={DamageType.FIRE: 470.0}, base_crit=5.0,
   base_cast_time=0.25, damage_effectiveness=0.6)

# -------------------------------------------------------------------
# MINION SKILLS
# -------------------------------------------------------------------

_a("Summon Raging Spirit", tags=["spell", "minion", "fire"],
   is_spell=True, base_crit=5.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Raise Zombie", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=0.85, damage_effectiveness=0.0)

_a("Raise Spectre", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=0.85, damage_effectiveness=0.0)

_a("Summon Skeletons", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Summon Holy Relic", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Summon Carrion Golem", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Summon Stone Golem", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Summon Flame Golem", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Summon Ice Golem", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Summon Lightning Golem", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Summon Chaos Golem", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Absolution", tags=["spell", "minion", "lightning", "area"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 210.0, DamageType.LIGHTNING: 315.0},
   base_crit=5.0, base_cast_time=0.75, damage_effectiveness=1.5)

_a("Herald of Agony", tags=["spell", "minion", "chaos"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Herald of Purity", tags=["spell", "minion", "physical"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Animate Guardian", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=0.6, damage_effectiveness=0.0)

_a("Animate Weapon", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=0.6, damage_effectiveness=0.0)

_a("Summon Phantasm", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=1.0, damage_effectiveness=0.0)

# -------------------------------------------------------------------
# AURAS / BUFFS / UTILITY (no direct damage but tracked for calc)
# -------------------------------------------------------------------

_a("Grace", tags=["spell", "aura"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Determination", tags=["spell", "aura"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Discipline", tags=["spell", "aura"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Purity of Elements", tags=["spell", "aura"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Purity of Fire", tags=["spell", "aura", "fire"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Purity of Ice", tags=["spell", "aura", "cold"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Purity of Lightning", tags=["spell", "aura", "lightning"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Clarity", tags=["spell", "aura"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Vitality", tags=["spell", "aura"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Haste", tags=["spell", "aura"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Zealotry", tags=["spell", "aura"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Malevolence", tags=["spell", "aura", "chaos"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Pride", tags=["spell", "aura", "physical"],
   is_spell=True, base_crit=0.0, base_cast_time=1.2, damage_effectiveness=0.0)

_a("Defiance Banner", tags=["spell", "aura"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Dread Banner", tags=["spell", "aura"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("War Banner", tags=["spell", "aura"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Herald of Ash", tags=["spell", "fire"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Herald of Ice", tags=["spell", "cold"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Herald of Thunder", tags=["spell", "lightning"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Petrified Blood", tags=["spell"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Molten Shell", tags=["spell", "fire"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Steelskin", tags=["spell"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Immortal Call", tags=["spell"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Blood Rage", tags=["spell"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Berserk", tags=["spell"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Bone Offering", tags=["spell", "minion"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Flesh Offering", tags=["spell", "minion"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Spirit Offering", tags=["spell", "minion"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Convocation", tags=["spell", "minion"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Desecrate", tags=["spell", "area"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Assassin's Mark", tags=["spell", "curse"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Warlord's Mark", tags=["spell", "curse"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Poacher's Mark", tags=["spell", "curse"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Sniper's Mark", tags=["spell", "curse"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Punishment", tags=["spell", "curse"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Projectile Weakness", tags=["spell", "curse"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Storm Burst", tags=["spell", "lightning", "area", "channelling"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 160.0, DamageType.LIGHTNING: 240.0},
   base_crit=5.0, base_cast_time=0.25, damage_effectiveness=0.4)

_a("Divine Ire", tags=["spell", "lightning", "area", "channelling"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 320.0, DamageType.LIGHTNING: 480.0},
   base_crit=6.0, base_cast_time=0.22, damage_effectiveness=0.8)

_a("Power Siphon", tags=["attack", "projectile"],
   is_attack=True, base_crit=7.0, attack_speed_multiplier=1.0, damage_effectiveness=1.25)

_a("Bodyswap", tags=["spell", "fire", "area", "movement"],
   is_spell=True, base_damage={DamageType.FIRE: 700.0}, base_crit=5.0,
   base_cast_time=0.7, damage_effectiveness=1.5)

_a("Lightning Warp", tags=["spell", "lightning", "area", "movement"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 500.0}, base_crit=5.0,
   base_cast_time=1.0, damage_effectiveness=0.9)

_a("Frostblink", tags=["spell", "cold", "area", "movement"],
   is_spell=True, base_damage={DamageType.COLD: 400.0}, base_crit=5.0,
   base_cast_time=0.5, damage_effectiveness=0.6)

_a("Siphoning Trap", tags=["spell", "cold", "trap", "area"],
   is_spell=True, base_damage={DamageType.COLD: 200.0}, base_crit=0.0,
   base_cast_time=1.0, damage_effectiveness=0.0)

_a("Tornado", tags=["spell", "area"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 100.0}, base_crit=5.0,
   base_cast_time=0.5, damage_effectiveness=0.0)

_a("Detonate Dead", tags=["spell", "fire", "area"],
   is_spell=True, base_damage={DamageType.FIRE: 480.0}, base_crit=5.0,
   base_cast_time=0.6, damage_effectiveness=2.0)

_a("Volatile Dead", tags=["spell", "fire", "area"],
   is_spell=True, base_damage={DamageType.FIRE: 480.0}, base_crit=5.0,
   base_cast_time=0.8, damage_effectiveness=1.8)

_a("Unearth", tags=["spell", "projectile", "physical"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 480.0}, base_crit=5.0,
   base_cast_time=0.5, damage_effectiveness=0.8)

_a("General's Cry", tags=["attack", "melee"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=1.0)

_a("Battlemage's Cry", tags=["attack"],
   is_attack=True, base_crit=5.0, damage_effectiveness=1.0)

_a("Intimidating Cry", tags=["attack"],
   is_attack=True, base_crit=5.0, damage_effectiveness=1.0)

_a("Seismic Cry", tags=["attack"],
   is_attack=True, base_crit=5.0, damage_effectiveness=1.0)

_a("Ancestral Cry", tags=["attack"],
   is_attack=True, base_crit=5.0, damage_effectiveness=1.0)

_a("Enduring Cry", tags=[],
   base_crit=0.0, damage_effectiveness=0.0)

_a("Rallying Cry", tags=["attack"],
   is_attack=True, base_crit=5.0, damage_effectiveness=1.0)

_a("Infernal Cry", tags=["attack", "fire"],
   is_attack=True, base_crit=5.0, damage_effectiveness=1.0)

# Vaal variants
_a("Vaal Cyclone", tags=["attack", "melee", "area", "channelling", "vaal"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=3.0, damage_effectiveness=0.56)

_a("Vaal Double Strike", tags=["attack", "melee", "vaal"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.8, damage_effectiveness=0.91)

_a("Vaal Lightning Strike", tags=["attack", "melee", "projectile", "lightning", "vaal"],
   is_attack=True, base_crit=6.0, attack_speed_multiplier=0.9, damage_effectiveness=1.35)

_a("Vaal Arc", tags=["spell", "lightning", "chaining", "vaal"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 1200.0}, base_crit=5.0,
   base_cast_time=0.7, damage_effectiveness=0.8)

_a("Vaal Fireball", tags=["spell", "projectile", "area", "fire", "vaal"],
   is_spell=True, base_damage={DamageType.FIRE: 1095.0}, base_crit=6.0,
   base_cast_time=0.75, damage_effectiveness=2.4)

_a("Vaal Spark", tags=["spell", "projectile", "lightning", "vaal"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 345.0}, base_crit=5.0,
   base_cast_time=0.65, damage_effectiveness=0.7)

_a("Vaal Ice Nova", tags=["spell", "cold", "area", "vaal"],
   is_spell=True, base_damage={DamageType.COLD: 680.0}, base_crit=6.0,
   base_cast_time=0.7, damage_effectiveness=1.0)

_a("Vaal Flameblast", tags=["spell", "fire", "area", "vaal"],
   is_spell=True, base_damage={DamageType.FIRE: 2000.0}, base_crit=5.0,
   base_cast_time=0.2, damage_effectiveness=0.5)

_a("Vaal Cold Snap", tags=["spell", "cold", "area", "vaal"],
   is_spell=True, base_damage={DamageType.COLD: 1050.0}, base_crit=5.0,
   base_cast_time=0.85, damage_effectiveness=1.5)

_a("Vaal Righteous Fire", tags=["spell", "fire", "area", "vaal"],
   is_spell=True, base_damage={DamageType.FIRE: 183.0}, base_crit=0.0,
   base_cast_time=1.0, damage_effectiveness=0.0)

_a("Vaal Blade Vortex", tags=["spell", "area", "physical", "vaal"],
   is_spell=True, base_damage={DamageType.PHYSICAL: 161.0}, base_crit=6.0,
   base_cast_time=0.5, damage_effectiveness=0.45)

_a("Vaal Grace", tags=["spell", "aura", "vaal"],
   is_spell=True, base_crit=0.0, base_cast_time=0.6, damage_effectiveness=0.0)

_a("Vaal Haste", tags=["spell", "aura", "vaal"],
   is_spell=True, base_crit=0.0, base_cast_time=0.6, damage_effectiveness=0.0)

_a("Vaal Discipline", tags=["spell", "aura", "vaal"],
   is_spell=True, base_crit=0.0, base_cast_time=0.6, damage_effectiveness=0.0)

_a("Vaal Molten Shell", tags=["spell", "fire", "vaal"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Vaal Rain of Arrows", tags=["attack", "projectile", "area", "vaal"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.73)

_a("Vaal Summon Skeletons", tags=["spell", "minion", "vaal"],
   is_spell=True, base_crit=5.0, base_cast_time=0.5, damage_effectiveness=0.0)

_a("Vaal Detonate Dead", tags=["spell", "fire", "area", "vaal"],
   is_spell=True, base_damage={DamageType.FIRE: 480.0}, base_crit=5.0,
   base_cast_time=0.6, damage_effectiveness=2.0)

_a("Vaal Ground Slam", tags=["attack", "melee", "area", "vaal"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.9, damage_effectiveness=1.5)

_a("Vaal Earthquake", tags=["attack", "melee", "area", "vaal"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.7, damage_effectiveness=1.5)

_a("Vaal Reave", tags=["attack", "melee", "area", "vaal"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=1.15)

_a("Vaal Power Siphon", tags=["attack", "projectile", "vaal"],
   is_attack=True, base_crit=7.0, attack_speed_multiplier=1.0, damage_effectiveness=1.25)

_a("Vaal Storm Call", tags=["spell", "lightning", "area", "vaal"],
   is_spell=True, base_damage={DamageType.LIGHTNING: 1380.0}, base_crit=5.0,
   base_cast_time=0.5, damage_effectiveness=2.0)

# Additional skills
_a("Soulwrest", tags=["spell", "minion"],
   is_spell=True, base_crit=5.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Spellslinger", tags=["spell"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Cast when Damage Taken", tags=["spell", "trigger"],
   is_spell=True, base_crit=0.0, base_cast_time=0.25, damage_effectiveness=0.0)

_a("Cast on Critical Strike", tags=["spell", "trigger"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Arcanist Brand", tags=["spell", "brand"],
   is_spell=True, base_crit=0.0, base_cast_time=0.75, damage_effectiveness=0.0)

_a("Kinetic Bolt", tags=["attack", "projectile"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=1.0, damage_effectiveness=0.85)

_a("Phantasmal Might", tags=["spell", "minion"],
   is_spell=True, base_crit=0.0, base_cast_time=1.0, damage_effectiveness=0.0)

_a("Flame Surge", tags=["spell", "fire", "area"],
   is_spell=True, base_damage={DamageType.FIRE: 900.0}, base_crit=6.0,
   base_cast_time=0.5, damage_effectiveness=1.2)

# --- SST / other ---
_a("Spectral Shield Throw", tags=["attack", "projectile", "physical"],
   is_attack=True, base_crit=5.0, attack_speed_multiplier=0.8, damage_effectiveness=1.0)

_a("Energy Blade", tags=["spell"],
   is_spell=True, base_crit=0.0, base_cast_time=0.5, damage_effectiveness=0.0)

# Clean up helper
del _a

# ===================================================================
# Support gem database — level 20 effects
# ===================================================================

_SUPPORT_GEMS: dict[str, SupportGemEffect] = {}

def _s(name: str, **kw) -> None:
    """Register a support gem."""
    _SUPPORT_GEMS[name] = SupportGemEffect(name=name, **kw)

def _mod(stat: str, value: float, mod_type: str = "more",
         damage_types: list[DamageType] | None = None,
         source: str = "") -> Modifier:
    return Modifier(stat=stat, value=value, mod_type=mod_type,
                    damage_types=damage_types or [], source=source)

# -------------------------------------------------------------------
# DAMAGE SUPPORT GEMS
# -------------------------------------------------------------------

_s("Brutality Support", modifiers=[
    _mod("more_physical_damage", 59, damage_types=[DamageType.PHYSICAL],
         source="gem:Brutality Support")])

_s("Melee Physical Damage Support", modifiers=[
    _mod("more_melee_physical_damage", 49, damage_types=[DamageType.PHYSICAL],
         source="gem:Melee Physical Damage Support")],
   less_attack_speed=10.0)

_s("Added Fire Damage Support")  # Gain 44% of phys as extra fire — via mod parser

_s("Elemental Damage with Attacks Support", modifiers=[
    _mod("more_elemental_attack_damage", 54,
         damage_types=[DamageType.FIRE, DamageType.COLD, DamageType.LIGHTNING],
         source="gem:Elemental Damage with Attacks Support")])

_s("Concentrated Effect Support", modifiers=[
    _mod("more_area_damage", 54, source="gem:Concentrated Effect Support")])

_s("Increased Critical Damage Support", modifiers=[
    _mod("more_crit_damage", 88, source="gem:Increased Critical Damage Support")])

_s("Multistrike Support", modifiers=[
    _mod("more_attack_damage", -26, source="gem:Multistrike Support")],
   attack_speed_mod=44.0)

_s("Faster Attacks Support", attack_speed_mod=44.0)

_s("Spell Echo Support", modifiers=[
    _mod("more_spell_damage", -10, source="gem:Spell Echo Support")])

_s("Controlled Destruction Support", modifiers=[
    _mod("more_spell_damage", 44, source="gem:Controlled Destruction Support")])

_s("Void Manipulation Support", modifiers=[
    _mod("more_chaos_damage", 39, damage_types=[DamageType.CHAOS],
         source="gem:Void Manipulation Support")])

_s("Swift Affliction Support", modifiers=[
    _mod("more_dot_damage", 44, source="gem:Swift Affliction Support")])

_s("Minion Damage Support", modifiers=[
    _mod("more_minion_damage", 49, source="gem:Minion Damage Support")])

_s("Greater Multiple Projectiles Support", modifiers=[
    _mod("less_projectile_damage", -26, source="gem:Greater Multiple Projectiles Support")])

_s("Less Multiple Projectiles Support", modifiers=[
    _mod("less_projectile_damage", -10, source="gem:Less Multiple Projectiles Support")])

_s("Mirage Archer Support", modifiers=[
    _mod("less_damage", -11, source="gem:Mirage Archer Support")])

_s("Predator Support", modifiers=[
    _mod("more_minion_damage", 39, source="gem:Predator Support")])

_s("Unleash Support")  # Repeats casts

_s("Melee Splash Support", modifiers=[
    _mod("less_damage_to_other_targets", -26, source="gem:Melee Splash Support")])

_s("Generosity Support")  # Aura effect modifier

_s("Close Combat Support", modifiers=[
    _mod("more_melee_damage", 59, source="gem:Close Combat Support")])

_s("Deadly Ailments Support", modifiers=[
    _mod("more_ailment_damage", 64, source="gem:Deadly Ailments Support"),
    _mod("less_hit_damage", -80, source="gem:Deadly Ailments Support")])

_s("Vicious Projectiles Support", modifiers=[
    _mod("more_physical_projectile_damage", 49, damage_types=[DamageType.PHYSICAL],
         source="gem:Vicious Projectiles Support")],
   less_attack_speed=10.0)

_s("Hypothermia Support", modifiers=[
    _mod("more_cold_damage_vs_chilled", 39, damage_types=[DamageType.COLD],
         source="gem:Hypothermia Support")])

_s("Elemental Focus Support", modifiers=[
    _mod("more_elemental_damage", 54,
         damage_types=[DamageType.FIRE, DamageType.COLD, DamageType.LIGHTNING],
         source="gem:Elemental Focus Support")])

_s("Trinity Support", modifiers=[
    _mod("more_elemental_damage", 33,
         damage_types=[DamageType.FIRE, DamageType.COLD, DamageType.LIGHTNING],
         source="gem:Trinity Support")])

_s("Inspiration Support", modifiers=[
    _mod("more_elemental_damage", 39,
         damage_types=[DamageType.FIRE, DamageType.COLD, DamageType.LIGHTNING],
         source="gem:Inspiration Support")])

_s("Added Lightning Damage Support",
   added_damage={DamageType.LIGHTNING: 225.0})

_s("Added Cold Damage Support",
   added_damage={DamageType.COLD: 295.0})

_s("Damage on Full Life Support", modifiers=[
    _mod("more_damage_on_full_life", 49, source="gem:Damage on Full Life Support")])

_s("Increased Critical Strikes Support", increased_crit=88.0)

_s("Combustion Support", modifiers=[
    _mod("more_fire_damage", 29, damage_types=[DamageType.FIRE],
         source="gem:Combustion Support")])

_s("Immolate Support",
   added_damage={DamageType.FIRE: 410.0})

_s("Physical to Lightning Support", modifiers=[
    _mod("more_lightning_damage", 29, damage_types=[DamageType.LIGHTNING],
         source="gem:Physical to Lightning Support")])
# Also 50% phys→lightning conversion, handled by mod_parser

_s("Faster Casting Support", cast_speed_mod=39.0)

_s("Faster Projectiles Support", modifiers=[
    _mod("more_projectile_speed", 29, source="gem:Faster Projectiles Support")])
# Proj speed doesn't directly increase damage but listed for completeness

_s("Impale Support", modifiers=[
    _mod("more_physical_damage", 20, damage_types=[DamageType.PHYSICAL],
         source="gem:Impale Support")],
    impale_chance=59.0, increased_impale_effect=59.0)

_s("Chance to Bleed Support", modifiers=[
    _mod("more_physical_damage", 25, damage_types=[DamageType.PHYSICAL],
         source="gem:Chance to Bleed Support")])

_s("Chance to Poison Support", modifiers=[
    _mod("more_chaos_damage", 28, damage_types=[DamageType.CHAOS],
         source="gem:Chance to Poison Support")])

_s("Ignite Proliferation Support", modifiers=[
    _mod("more_burning_damage", 29, source="gem:Ignite Proliferation Support")])

_s("Innervate Support",
   added_damage={DamageType.LIGHTNING: 41.5})
# Adds 15-68 avg lightning while innervated

_s("Withering Touch Support", modifiers=[
    _mod("more_chaos_damage", 29, damage_types=[DamageType.CHAOS],
         source="gem:Withering Touch Support")])
# Also applies wither stacks (6% increased chaos taken per stack)

_s("Arcane Surge Support", modifiers=[
    _mod("more_spell_damage", 10, source="gem:Arcane Surge Support")])
# 10% more spell damage while arcane surge active

_s("Culling Strike Support", modifiers=[
    _mod("more_damage", 10, source="gem:Culling Strike Support")])
# Kills at 10% HP = effective ~11.1% more, approximated as 10% more

_s("Onslaught Support", attack_speed_mod=20.0)
# 20% attack/cast/movement speed when onslaught active

_s("Nightblade Support")
# Crit multi while elusive — too conditional to estimate without elusive status

_s("Ancestral Call Support", modifiers=[
    _mod("less_damage", -25, source="gem:Ancestral Call Support")])

_s("Awakened Ancestral Call Support", modifiers=[
    _mod("less_damage", -15, source="gem:Awakened Ancestral Call Support")])

_s("Fork Support", modifiers=[
    _mod("less_projectile_damage", -15, source="gem:Fork Support")])

_s("Awakened Fork Support", modifiers=[
    _mod("less_projectile_damage", -10, source="gem:Awakened Fork Support")])

_s("Overcharge Support", increased_crit=60.0)

_s("Empower Support")  # +3 gem levels — complex interaction

_s("Enhance Support")  # +quality — complex interaction

_s("Enlighten Support")  # Reduced mana reservation

_s("Power Charge on Critical Support")  # Utility (power charges via crit)

_s("Cast on Critical Strike Support")  # Trigger

_s("Cast when Damage Taken Support")  # Trigger

# --- Penetration supports ---
_s("Lightning Penetration Support",
   penetration={DamageType.LIGHTNING: 37.0})

_s("Cold Penetration Support",
   penetration={DamageType.COLD: 37.0})

_s("Fire Penetration Support",
   penetration={DamageType.FIRE: 37.0})

_s("Spell Cascade Support", modifiers=[
    _mod("less_area_damage", -17, source="gem:Spell Cascade Support")])

_s("Intensify Support", modifiers=[
    _mod("more_area_damage", 40, source="gem:Intensify Support")])

_s("Awakened Elemental Damage with Attacks Support", modifiers=[
    _mod("more_elemental_attack_damage", 54,
         damage_types=[DamageType.FIRE, DamageType.COLD, DamageType.LIGHTNING],
         source="gem:Awakened Elemental Damage with Attacks Support")])

_s("Awakened Added Lightning Damage Support",
   added_damage={DamageType.LIGHTNING: 270.0})

_s("Awakened Added Fire Damage Support",
   added_damage={DamageType.FIRE: 385.0})

_s("Awakened Added Cold Damage Support",
   added_damage={DamageType.COLD: 340.0})

_s("Awakened Melee Physical Damage Support", modifiers=[
    _mod("more_melee_physical_damage", 54, damage_types=[DamageType.PHYSICAL],
         source="gem:Awakened Melee Physical Damage Support")],
   less_attack_speed=10.0)

_s("Awakened Brutality Support", modifiers=[
    _mod("more_physical_damage", 64, damage_types=[DamageType.PHYSICAL],
         source="gem:Awakened Brutality Support")])

_s("Awakened Multistrike Support", modifiers=[
    _mod("more_attack_damage", -22, source="gem:Awakened Multistrike Support")],
   attack_speed_mod=44.0)

_s("Awakened Controlled Destruction Support", modifiers=[
    _mod("more_spell_damage", 49, source="gem:Awakened Controlled Destruction Support")])

_s("Awakened Spell Echo Support", modifiers=[
    _mod("more_spell_damage", -6, source="gem:Awakened Spell Echo Support")])

_s("Awakened Greater Multiple Projectiles Support", modifiers=[
    _mod("less_projectile_damage", -21, source="gem:Awakened GMP Support")])

_s("Awakened Void Manipulation Support", modifiers=[
    _mod("more_chaos_damage", 44, damage_types=[DamageType.CHAOS],
         source="gem:Awakened Void Manipulation Support")])

_s("Awakened Swift Affliction Support", modifiers=[
    _mod("more_dot_damage", 49, source="gem:Awakened Swift Affliction Support")])

_s("Awakened Elemental Focus Support", modifiers=[
    _mod("more_elemental_damage", 59,
         damage_types=[DamageType.FIRE, DamageType.COLD, DamageType.LIGHTNING],
         source="gem:Awakened Elemental Focus Support")])

_s("Awakened Deadly Ailments Support", modifiers=[
    _mod("more_ailment_damage", 69, source="gem:Awakened Deadly Ailments Support"),
    _mod("less_hit_damage", -80, source="gem:Awakened Deadly Ailments Support")])

_s("Awakened Vicious Projectiles Support", modifiers=[
    _mod("more_physical_projectile_damage", 54, damage_types=[DamageType.PHYSICAL],
         source="gem:Awakened Vicious Projectiles Support")],
   less_attack_speed=10.0)

_s("Awakened Minion Damage Support", modifiers=[
    _mod("more_minion_damage", 54, source="gem:Awakened Minion Damage Support")])

_s("Awakened Concentrated Effect Support", modifiers=[
    _mod("more_area_damage", 59, source="gem:Awakened Concentrated Effect Support")])

_s("Awakened Hypothermia Support", modifiers=[
    _mod("more_cold_damage_vs_chilled", 44, damage_types=[DamageType.COLD],
         source="gem:Awakened Hypothermia Support")])

_s("Awakened Combustion Support", modifiers=[
    _mod("more_fire_damage", 34, damage_types=[DamageType.FIRE],
         source="gem:Awakened Combustion Support")])

# -------------------------------------------------------------------
# PROJECTILE / AREA SUPPORTS
# -------------------------------------------------------------------

_s("Chain Support", modifiers=[
    _mod("less_damage_per_chain", -12, source="gem:Chain Support")])

_s("Pierce Support")  # Projectile pierce — no direct damage mod

_s("Volley Support")  # Extra projectiles — no damage mod

_s("Barrage Support", modifiers=[
    _mod("less_projectile_damage", -24, source="gem:Barrage Support")])

_s("Returning Projectiles Support", modifiers=[
    _mod("less_projectile_damage", -15, source="gem:Returning Projectiles Support")])

_s("Increased Area of Effect Support")  # Area increase — no direct damage mod

_s("Awakened Chain Support", modifiers=[
    _mod("less_damage_per_chain", -8, source="gem:Awakened Chain Support")])

# -------------------------------------------------------------------
# SPEED / UTILITY SUPPORTS
# -------------------------------------------------------------------

_s("Increased Duration Support")  # Duration — no direct damage

_s("Less Duration Support")  # Duration — no direct damage

_s("Efficacy Support", modifiers=[
    _mod("more_dot_damage", 34, source="gem:Efficacy Support")])

_s("Bloodlust Support", modifiers=[
    _mod("more_melee_damage_vs_bleeding", 59, source="gem:Bloodlust Support")])

_s("Chance to Flee Support")  # Utility

_s("Item Rarity Support")  # Utility

_s("Item Quantity Support")  # Utility

_s("Slower Projectiles Support", modifiers=[
    _mod("more_projectile_damage", 49, source="gem:Slower Projectiles Support")])

_s("Summon Phantasm Support")  # Minion — no direct damage mod

_s("Bonechill Support")  # Cold DoT buff

_s("Infused Channelling Support", modifiers=[
    _mod("more_channelling_damage", 39, source="gem:Infused Channelling Support")])

_s("Energy Leech Support", modifiers=[
    _mod("more_damage_while_leeching", 39, source="gem:Energy Leech Support")])

_s("Cruelty Support", modifiers=[
    _mod("more_dot_damage", 40, source="gem:Cruelty Support")])

_s("Lifetap Support")  # Cost life — no damage mod

_s("Hextouch Support")  # Trigger curses — no damage mod

_s("Arcanist Brand Support")  # Brand trigger — no damage mod

_s("Spellslinger Support")  # Trigger — no damage mod

_s("Tribal Fury Support")  # Strike range — no direct damage mod

_s("Mark on Hit Support")  # Apply marks — utility

_s("Fresh Meat Support", modifiers=[
    _mod("more_damage", 59, source="gem:Fresh Meat Support")])

_s("Momentum Support", attack_speed_mod=30.0)

_s("Awakened Increased Area of Effect Support")

_s("Awakened Hextouch Support")

_s("Rage Support", attack_speed_mod=10.0)  # Grants rage on hit

_s("Second Wind Support")  # Cooldown — no damage

_s("Bloodthirst Support", modifiers=[
    _mod("more_damage", 30, source="gem:Bloodthirst Support")])

_s("Prismatic Burst Support", modifiers=[
    _mod("more_elemental_damage", 44,
         damage_types=[DamageType.FIRE, DamageType.COLD, DamageType.LIGHTNING],
         source="gem:Prismatic Burst Support")])

# -------------------------------------------------------------------
# TRAP / MINE / TOTEM SUPPORTS
# -------------------------------------------------------------------

_s("Trap Support")  # Grants trap tag — no damage mod

_s("Cluster Traps Support", modifiers=[
    _mod("less_trap_damage", -25, source="gem:Cluster Traps Support")])

_s("Multiple Traps Support", modifiers=[
    _mod("less_trap_damage", -15, source="gem:Multiple Traps Support")])

_s("Advanced Traps Support")  # Trap cooldown + duration

_s("Charged Traps Support")  # Power/frenzy charges on trap trigger

_s("Trap and Mine Damage Support", modifiers=[
    _mod("more_trap_mine_damage", 39, source="gem:Trap and Mine Damage Support")])

_s("High-Impact Mine Support", modifiers=[
    _mod("more_mine_damage", 39, source="gem:High-Impact Mine Support")])

_s("Minefield Support", modifiers=[
    _mod("less_mine_damage", -30, source="gem:Minefield Support")])

_s("Blastchain Mine Support", modifiers=[
    _mod("more_mine_damage", 15, source="gem:Blastchain Mine Support")])

_s("Swift Assembly Support")  # Extra throws — no damage mod

_s("Spell Totem Support", modifiers=[
    _mod("less_damage", -26, source="gem:Spell Totem Support")])

_s("Ballista Totem Support", modifiers=[
    _mod("less_damage", -26, source="gem:Ballista Totem Support")])

_s("Multiple Totems Support", modifiers=[
    _mod("less_damage", -21, source="gem:Multiple Totems Support")])

_s("Focused Ballista Support", modifiers=[
    _mod("more_damage", 39, source="gem:Focused Ballista Support")],
   less_attack_speed=25.0)

_s("Awakened Trap and Mine Damage Support", modifiers=[
    _mod("more_trap_mine_damage", 44, source="gem:Awakened Trap and Mine Damage Support")])

# -------------------------------------------------------------------
# OTHER / MISC SUPPORTS
# -------------------------------------------------------------------

_s("Summon Skitterbots")  # Not really a support but sometimes listed

_s("Blind Support")  # Utility

_s("Block Chance Reduction Support")  # Utility

_s("Stun Support")  # Utility

_s("Knockback Support")  # Utility

_s("Added Chaos Damage Support",
   added_damage={DamageType.CHAOS: 285.0})

_s("Awakened Added Chaos Damage Support",
   added_damage={DamageType.CHAOS: 340.0})

_s("Decay Support")  # Chaos DoT — fixed value, not scaled normally

_s("Maim Support", modifiers=[
    _mod("more_physical_damage", 15, damage_types=[DamageType.PHYSICAL],
         source="gem:Maim Support")])

_s("Ruthless Support", modifiers=[
    _mod("more_melee_damage", 32, source="gem:Ruthless Support")])

_s("Fist of War Support", modifiers=[
    _mod("more_damage", 80, source="gem:Fist of War Support")])

_s("Pulverise Support", modifiers=[
    _mod("more_area_damage", 39, source="gem:Pulverise Support")],
   less_attack_speed=15.0)

_s("Awakened Melee Splash Support", modifiers=[
    _mod("less_damage_to_other_targets", -21,
         source="gem:Awakened Melee Splash Support")])

_s("Unbound Ailments Support", modifiers=[
    _mod("more_ailment_damage", 44, source="gem:Unbound Ailments Support")])

_s("Burning Damage Support", modifiers=[
    _mod("more_burning_damage", 59, source="gem:Burning Damage Support")])

_s("Awakened Burning Damage Support", modifiers=[
    _mod("more_burning_damage", 64, source="gem:Awakened Burning Damage Support")])

_s("Awakened Unbound Ailments Support", modifiers=[
    _mod("more_ailment_damage", 49, source="gem:Awakened Unbound Ailments Support")])

_s("Volatility Support", modifiers=[
    _mod("more_damage", 30, source="gem:Volatility Support")])

_s("Awakened Generosity Support")  # Aura effect

_s("Awakened Enlighten Support")  # Mana reservation

_s("Awakened Empower Support")  # +4 gem levels

_s("Awakened Enhance Support")  # +quality

# Clean up helpers
del _s, _mod

# ===================================================================
# Public API
# ===================================================================

def get_active_gem_stats(name: str) -> ActiveGemStats | None:
    """Look up active gem stats by name. Returns None if not found."""
    return _ACTIVE_GEMS.get(name)

def get_support_effect(name: str) -> SupportGemEffect | None:
    """Look up support gem effects by name.

    Resolution order:
    1. Exact match
    2. Append " Support" (PoB often strips the suffix)
    3. Normalized prepositions (On→on, Of→of, etc.)
    4. For Awakened gems: try the Awakened name first, fall back to base name
    """
    result = _SUPPORT_GEMS.get(name)
    if result is not None:
        return result
    # PoB XML stores supports without the suffix: "Added Cold Damage" → "Added Cold Damage Support"
    if not name.endswith(" Support"):
        result = _SUPPORT_GEMS.get(name + " Support")
        if result is not None:
            return result
    # Normalize title-case prepositions: "On" → "on", "Of" → "of", etc.
    normalized = name
    for word in (" On ", " Of ", " The ", " In ", " At ", " To ", " As "):
        normalized = normalized.replace(word, word.lower())
    result = _SUPPORT_GEMS.get(normalized)
    if result is not None:
        return result
    if not normalized.endswith(" Support"):
        result = _SUPPORT_GEMS.get(normalized + " Support")
        if result is not None:
            return result
    # Awakened fallback: "Awakened X Support" → "X Support"
    if name.startswith("Awakened "):
        base_name = name[len("Awakened "):]
        result = _SUPPORT_GEMS.get(base_name)
        if result is not None:
            return result
        if not base_name.endswith(" Support"):
            result = _SUPPORT_GEMS.get(base_name + " Support")
            if result is not None:
                return result
    return None

def is_known_gem(name: str) -> bool:
    """Check if a gem name is in our database (with Support suffix fallback)."""
    if name in _ACTIVE_GEMS or name in _SUPPORT_GEMS:
        return True
    if not name.endswith(" Support"):
        return (name + " Support") in _SUPPORT_GEMS
    return False

def list_active_gems() -> list[str]:
    """Return all known active gem names."""
    return sorted(_ACTIVE_GEMS.keys())

def list_support_gems() -> list[str]:
    """Return all known support gem names."""
    return sorted(_SUPPORT_GEMS.keys())
