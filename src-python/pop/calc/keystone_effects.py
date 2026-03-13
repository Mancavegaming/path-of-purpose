"""
Keystone passive effect database for the DPS calculator.

Keystones fundamentally change mechanics (crit, hit chance, conversions).
They are detected from the passive tree or from special_flags and applied
in the engine via the special_flags dict on ParsedMods.

Each keystone is represented as a dict of flag_name -> value, which gets
merged into ParsedMods.special_flags.
"""

from __future__ import annotations

from pop.calc.models import DamageType

# Each keystone maps to special_flags entries
KEYSTONE_EFFECTS: dict[str, dict[str, object]] = {
    # Elemental Overload: 40% more elemental damage, crit multi locked to 100%
    "Elemental Overload": {
        "elemental_overload": True,
    },

    # Resolute Technique: always hit, never crit
    "Resolute Technique": {
        "resolute_technique": True,
    },

    # Point Blank: 30% more projectile damage at close range,
    # less at far range. We assume close range for single target.
    "Point Blank": {
        "point_blank": True,
    },

    # Avatar of Fire: 50% of phys/lightning/cold converted to fire,
    # deal no non-fire damage
    "Avatar of Fire": {
        "avatar_of_fire": True,
    },

    # Crimson Dance: bleed stacks up to 8 times, 50% less bleed while moving
    "Crimson Dance": {
        "crimson_dance": True,
    },

    # Ancestral Bond: you cannot deal damage with hits yourself (totems only)
    "Ancestral Bond": {
        "ancestral_bond": True,
    },

    # Iron Will: strength's bonus to melee phys applies to spell damage
    "Iron Will": {
        "iron_will": True,
    },

    # Iron Grip: strength's bonus to melee phys applies to projectile attacks
    "Iron Grip": {
        "iron_grip": True,
    },

    # Vaal Pact: double leech rate, no life regen (no DPS impact)
    "Vaal Pact": {
        "vaal_pact": True,
    },

    # Zealot's Oath: life regen applies to ES (no DPS impact)
    "Zealot's Oath": {
        "zealots_oath": True,
    },

    # Mind Over Matter: 30% of damage taken from mana (no DPS impact)
    "Mind Over Matter": {
        "mind_over_matter": True,
    },

    # Acrobatics: 30% dodge, 50% less armour/ES (no DPS impact)
    "Acrobatics": {
        "acrobatics": True,
    },

    # Ghost Dance: ES recovery (no DPS impact)
    "Ghost Dance": {
        "ghost_dance": True,
    },

    # Eldritch Battery: ES protects mana (no DPS impact)
    "Eldritch Battery": {
        "eldritch_battery": True,
    },

    # Pain Attunement: 30% more spell damage on low life
    "Pain Attunement": {
        "pain_attunement": True,
    },

    # Wicked Ward: ES recharge not interrupted (no DPS impact)
    "Wicked Ward": {
        "wicked_ward": True,
    },

    # Precise Technique: 40% more attack damage if accuracy > life
    "Precise Technique": {
        "precise_technique": True,
    },
}


# Keystones that can be detected from passive tree node names
KEYSTONE_NAMES: set[str] = set(KEYSTONE_EFFECTS.keys())


def get_keystone_flags(name: str) -> dict[str, object] | None:
    """Get special_flags for a keystone by name."""
    return KEYSTONE_EFFECTS.get(name)
