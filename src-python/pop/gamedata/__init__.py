"""Centralized game data registry.

Single source of truth for all PoE game data.
Auto-syncs from RePoE; manual overrides for day-0 patch data.

Usage:
    from pop.gamedata import registry
    gem = registry.get_active_gem("Fireball")
    support = registry.get_support_gem("Melee Physical Damage Support")
    bases = registry.get_weapon_bases()
"""

from pop.gamedata.registry import (  # noqa: F401
    get_active_gem,
    get_support_gem,
    list_active_gem_names,
    list_support_gem_names,
    is_known_gem,
    get_weapon_bases,
    get_armour_bases,
    get_weapon_base,
    force_refresh,
)
