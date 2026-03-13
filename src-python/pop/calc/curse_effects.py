"""
Curse effect database for the DPS calculator.

When curses are active (linked in non-main skill groups), they reduce
enemy resistances or apply "increased damage taken" debuffs.

Values are level-20 base values (before curse effectiveness modifiers).
Boss curse effectiveness is applied by the engine via CalcConfig.curse_effectiveness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pop.calc.models import DamageType


@dataclass
class CurseEffect:
    """Effects applied by a curse at level 20."""

    name: str
    # Resist reduction per type (positive = reduces enemy resist)
    resist_reduction: dict[DamageType, float] = field(default_factory=dict)
    # Increased damage taken per type (for Vulnerability/Punishment)
    increased_damage_taken: dict[DamageType, float] = field(default_factory=dict)
    # Generic increased damage taken (all types)
    increased_damage_taken_generic: float = 0.0
    # DoT-specific damage taken (for Despair, Vulnerability)
    increased_dot_taken: float = 0.0


_CURSE_EFFECTS: dict[str, CurseEffect] = {}


def _ce(name: str, **kw: object) -> None:
    _CURSE_EFFECTS[name] = CurseEffect(name=name, **kw)  # type: ignore[arg-type]


# ===================================================================
# Offensive Curses (Hexes)
# ===================================================================

# Elemental Weakness: -44% to all elemental resistances
_ce("Elemental Weakness",
    resist_reduction={
        DamageType.FIRE: 44.0,
        DamageType.COLD: 44.0,
        DamageType.LIGHTNING: 44.0,
    })

# Flammability: -44% to fire resistance
_ce("Flammability",
    resist_reduction={DamageType.FIRE: 44.0})

# Frostbite: -44% to cold resistance
_ce("Frostbite",
    resist_reduction={DamageType.COLD: 44.0})

# Conductivity: -44% to lightning resistance
_ce("Conductivity",
    resist_reduction={DamageType.LIGHTNING: 44.0})

# Vulnerability: enemies take 29% increased physical damage
# and 33% increased physical DoT
_ce("Vulnerability",
    increased_damage_taken={DamageType.PHYSICAL: 29.0},
    increased_dot_taken=33.0)

# Despair: -20% to chaos resistance, enemies take 15% increased DoT
_ce("Despair",
    resist_reduction={DamageType.CHAOS: 20.0},
    increased_dot_taken=15.0)

# Punishment: 29% more damage when hitting cursed enemies at low life
# Simplified: enemies take 29% more melee damage (close range only)
_ce("Punishment",
    increased_damage_taken={DamageType.PHYSICAL: 29.0})

# Temporal Chains: 29% reduced action speed (defensive, no direct DPS)
_ce("Temporal Chains")

# Enfeeble: enemies deal less damage (defensive)
_ce("Enfeeble")

# ===================================================================
# Marks (PoE2-style, also valid in PoE1 late versions)
# ===================================================================

# Assassin's Mark: +X% to crit chance/multi against marked enemy
# Handled separately in engine since it affects player stats
_ce("Assassin's Mark")

# Sniper's Mark: 21% increased damage taken by projectiles
_ce("Sniper's Mark",
    increased_damage_taken_generic=21.0)

# Warlord's Mark: covered under leech (defensive)
_ce("Warlord's Mark")

# Poacher's Mark: covered under flask charges (utility)
_ce("Poacher's Mark")


# ===================================================================
# Public API
# ===================================================================

CURSE_GEM_NAMES: set[str] = set(_CURSE_EFFECTS.keys())


def get_curse_effect(name: str) -> CurseEffect | None:
    """Look up curse effects by gem name."""
    return _CURSE_EFFECTS.get(name)
