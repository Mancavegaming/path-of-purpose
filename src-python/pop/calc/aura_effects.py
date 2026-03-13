"""
Aura and herald effect database for the DPS calculator.

When the main skill group is being calculated, auras/heralds in OTHER
skill groups should contribute their flat damage, more multipliers,
and increased modifiers. This module provides those effects.

Values are level-20 base values (before aura effect modifiers).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pop.calc.models import DamageType, Modifier


@dataclass
class AuraEffect:
    """Effects granted by an aura or herald at level 20."""

    name: str
    flat_added_attacks: dict[DamageType, float] = field(default_factory=dict)
    flat_added_spells: dict[DamageType, float] = field(default_factory=dict)
    flat_added: dict[DamageType, float] = field(default_factory=dict)  # generic (both)
    modifiers: list[Modifier] = field(default_factory=list)
    increased_attack_speed: float = 0.0
    increased_cast_speed: float = 0.0
    increased_crit: float = 0.0


_AURA_EFFECTS: dict[str, AuraEffect] = {}


def _ae(name: str, **kw: object) -> None:
    _AURA_EFFECTS[name] = AuraEffect(name=name, **kw)  # type: ignore[arg-type]


def _mod(stat: str, value: float, mod_type: str = "more",
         damage_types: list[DamageType] | None = None) -> Modifier:
    return Modifier(stat=stat, value=value, mod_type=mod_type,
                    damage_types=damage_types or [], source="aura")


# ===================================================================
# Offensive Auras
# ===================================================================

_ae("Wrath",
    flat_added_attacks={DamageType.LIGHTNING: 22.5},  # Adds 5-40 (avg 22.5)
    flat_added_spells={DamageType.LIGHTNING: 36.0},   # Adds 18-54 (avg 36)
    modifiers=[_mod("more_spell_lightning", 13,
                     damage_types=[DamageType.LIGHTNING])])

_ae("Anger",
    flat_added_attacks={DamageType.FIRE: 60.5},   # Adds 33-88 (avg 60.5)
    flat_added_spells={DamageType.FIRE: 45.0})    # Adds 30-60 (avg 45)

_ae("Hatred",
    modifiers=[
        # 25% of physical damage as extra cold
        _mod("phys_as_extra_cold", 25, mod_type="more",
             damage_types=[DamageType.COLD]),
        _mod("more_cold_damage", 18,
             damage_types=[DamageType.COLD]),
    ])

_ae("Zealotry",
    modifiers=[_mod("more_spell_damage", 15)])

_ae("Malevolence",
    modifiers=[_mod("more_dot_damage", 20)])

_ae("Pride",
    modifiers=[
        # Nearby enemies take 19-39% more phys (use average ~29%)
        _mod("more_physical_damage_taken", 29,
             damage_types=[DamageType.PHYSICAL]),
    ])

_ae("Haste",
    increased_attack_speed=16.0,
    increased_cast_speed=16.0)

# ===================================================================
# Heralds (25% mana reservation)
# ===================================================================

_ae("Herald of Ash",
    modifiers=[
        # 15% of phys as extra fire
        _mod("phys_as_extra_fire", 15, mod_type="more",
             damage_types=[DamageType.FIRE]),
    ])

_ae("Herald of Ice",
    flat_added={DamageType.COLD: 43.5})  # Adds 27-60 (avg 43.5)

_ae("Herald of Thunder",
    flat_added={DamageType.LIGHTNING: 30.5})  # Adds 12-49 (avg 30.5)

_ae("Herald of Purity",
    flat_added_attacks={DamageType.PHYSICAL: 18.0})  # Adds 12-24 (avg 18)

# ===================================================================
# Defensive auras — no DPS contribution, but listed for completeness
# ===================================================================

_ae("Determination")
_ae("Grace")
_ae("Discipline")
_ae("Vitality")
_ae("Clarity")
_ae("Purity of Elements")
_ae("Purity of Fire")
_ae("Purity of Ice")
_ae("Purity of Lightning")
_ae("Defiance Banner")
_ae("Dread Banner")
_ae("War Banner")
_ae("Precision",
    increased_crit=40.0)  # Flat accuracy omitted, just crit

# ===================================================================
# Public API
# ===================================================================

# Names of gems that are auras or heralds (for detection in skill groups)
AURA_GEM_NAMES: set[str] = set(_AURA_EFFECTS.keys())


def get_aura_effect(name: str) -> AuraEffect | None:
    """Look up aura/herald effects by gem name."""
    return _AURA_EFFECTS.get(name)
