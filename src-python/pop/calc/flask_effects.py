"""
Flask effect database for the DPS calculator.

Unique flasks have hardcoded effects. Non-unique flask mods are parsed
via mod_parser from their mod text (suffixes like "of the Order" etc.).

When use_flasks is enabled in CalcConfig, flask effects from Flask 1-5
item slots are collected by stat_aggregator.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pop.calc.models import DamageType, Modifier


@dataclass
class FlaskEffect:
    """Effects granted by a flask while active."""

    name: str
    flat_added: dict[DamageType, float] = field(default_factory=dict)
    modifiers: list[Modifier] = field(default_factory=list)
    conversions_gained_as: list[tuple[DamageType, DamageType, float]] = field(
        default_factory=list
    )  # (from, to, %)
    penetration: dict[DamageType, float] = field(default_factory=dict)
    increased_crit: float = 0.0
    crit_multi: float = 0.0
    increased_attack_speed: float = 0.0
    increased_cast_speed: float = 0.0
    # Special flags
    lucky_crit: bool = False  # Diamond Flask
    enemy_increased_damage_taken: float = 0.0  # Bottled Faith
    # Additional projectiles (Dying Sun)
    additional_projectiles: int = 0


_FLASK_EFFECTS: dict[str, FlaskEffect] = {}


def _mod(
    stat: str,
    value: float,
    mod_type: str = "more",
    damage_types: list[DamageType] | None = None,
) -> Modifier:
    return Modifier(
        stat=stat,
        value=value,
        mod_type=mod_type,
        damage_types=damage_types or [],
        source="flask",
    )


def _fe(name: str, **kw: object) -> None:
    _FLASK_EFFECTS[name] = FlaskEffect(name=name, **kw)  # type: ignore[arg-type]


# ===================================================================
# Base Flask Types (non-unique)
# ===================================================================

_fe("Diamond Flask", lucky_crit=True)
_fe("Silver Flask")  # Onslaught handled via config
_fe("Sulphur Flask",
    modifiers=[_mod("increased_damage", 40, mod_type="increased")])

# ===================================================================
# Unique Flasks
# ===================================================================

# Bottled Faith: Consecrated Ground + crit + enemy damage taken
_fe("Bottled Faith",
    increased_crit=100.0,
    enemy_increased_damage_taken=10.0)

# Atziri's Promise: phys as extra chaos + ele as extra chaos
_fe("Atziri's Promise",
    conversions_gained_as=[
        (DamageType.PHYSICAL, DamageType.CHAOS, 15.0),
        (DamageType.FIRE, DamageType.CHAOS, 15.0),
        (DamageType.COLD, DamageType.CHAOS, 15.0),
        (DamageType.LIGHTNING, DamageType.CHAOS, 15.0),
    ])

# Taste of Hate: phys as extra cold
_fe("Taste of Hate",
    conversions_gained_as=[
        (DamageType.PHYSICAL, DamageType.COLD, 20.0),
    ])

# Lion's Roar: 20% more melee physical damage
_fe("Lion's Roar",
    modifiers=[
        _mod("more_melee_physical_damage", 20,
             damage_types=[DamageType.PHYSICAL]),
    ])

# Dying Sun: +2 projectiles, 20% increased area damage
_fe("Dying Sun",
    additional_projectiles=2,
    modifiers=[_mod("increased_area_damage", 20, mod_type="increased")])

# Sin's Rebirth: 30% of phys as extra chaos during flask
_fe("Sin's Rebirth",
    conversions_gained_as=[
        (DamageType.PHYSICAL, DamageType.CHAOS, 30.0),
    ])

# Vessel of Vinktar (Lightning variant): pen + added lightning
_fe("Vessel of Vinktar",
    flat_added={DamageType.LIGHTNING: 55.0},
    penetration={DamageType.LIGHTNING: 10.0})

# The Wise Oak: 10% pen for lowest uncapped resist element (simplified to generic elemental)
_fe("The Wise Oak",
    penetration={
        DamageType.FIRE: 10.0,
        DamageType.COLD: 10.0,
        DamageType.LIGHTNING: 10.0,
    })

# Cinderswallow Urn: enemies ignited take 10% increased damage
_fe("Cinderswallow Urn",
    enemy_increased_damage_taken=10.0)


# ===================================================================
# Public API
# ===================================================================


def get_flask_effect(name: str) -> FlaskEffect | None:
    """Look up unique flask effects by name.

    For non-unique flasks, returns None (their mods are parsed via mod_parser).
    Partial name matching for base flask types (e.g. "Diamond Flask").
    """
    # Direct lookup first
    if name in _FLASK_EFFECTS:
        return _FLASK_EFFECTS[name]
    # Check if the item name contains a known base type
    for base_name, effect in _FLASK_EFFECTS.items():
        if base_name in name:
            return effect
    return None
