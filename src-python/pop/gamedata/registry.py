"""Centralized game data registry.

Single source of truth for all PoE game data. Lazy-loads from RePoE
on first access, falls back to hardcoded gem_data.py if offline.

Usage:
    from pop.gamedata import registry
    gem = registry.get_active_gem("Fireball")
    support = registry.get_support_gem("Melee Physical Damage Support")
    weapon_bases = registry.get_weapon_bases()
"""

from __future__ import annotations

import logging
from typing import Any

from pop.calc.gem_data import (
    ActiveGemStats,
    SupportGemEffect,
    get_active_gem_stats as _hardcoded_active,
    get_support_effect as _hardcoded_support,
    list_active_gems as _hardcoded_active_list,
    list_support_gems as _hardcoded_support_list,
    _ACTIVE_GEMS as _HC_ACTIVE,
    _SUPPORT_GEMS as _HC_SUPPORT,
)
from pop.calc.models import DamageType, Modifier

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Module-level state (populated on first access or explicit sync)
# -----------------------------------------------------------------------

_synced_active: dict[str, ActiveGemStats] | None = None
_synced_support: dict[str, SupportGemEffect] | None = None
_synced_weapon_bases: dict[str, tuple] | None = None
_synced_armour_bases: dict[str, dict[str, tuple]] | None = None
_sync_attempted: bool = False


def _ensure_synced() -> None:
    """Try to load RePoE data once. If it fails, we use hardcoded data."""
    global _synced_active, _synced_support, _synced_weapon_bases, _synced_armour_bases, _sync_attempted

    if _sync_attempted:
        return
    _sync_attempted = True

    try:
        from pop.gamedata.repoe_sync import sync_all
        data = sync_all()

        # Convert RePoE active gems to ActiveGemStats
        raw_active = data.get("active_gems", {})
        if raw_active:
            _synced_active = {}
            for name, info in raw_active.items():
                tags = info.get("tags", [])
                base_damage_raw = info.get("base_damage", {})
                base_damage = {}
                for dtype_str, val in base_damage_raw.items():
                    try:
                        base_damage[DamageType(dtype_str)] = float(val)
                    except (ValueError, KeyError):
                        pass

                _synced_active[name] = ActiveGemStats(
                    name=name,
                    tags=tags,
                    is_attack="attack" in tags,
                    is_spell="spell" in tags,
                    base_damage=base_damage,
                    base_crit=info.get("base_crit", 5.0),
                    base_cast_time=info.get("base_cast_time", 1.0),
                    damage_effectiveness=info.get("damage_effectiveness", 1.0),
                    attack_speed_multiplier=info.get("attack_speed_multiplier", 1.0),
                )
            logger.info("Registry loaded %d active gems from RePoE", len(_synced_active))

        # Convert RePoE support gems to SupportGemEffect
        raw_support = data.get("support_gems", {})
        if raw_support:
            _synced_support = {}
            for name, info in raw_support.items():
                modifiers = []
                for m in info.get("modifiers", []):
                    modifiers.append(Modifier(
                        type=m.get("type", "more_damage"),
                        value=m.get("value", 0.0),
                        damage_types=[
                            DamageType(dt) for dt in m.get("damage_types", [])
                            if dt in DamageType.__members__.values()
                        ] if m.get("damage_types") else [],
                    ))

                added_damage = {}
                for dtype_str, val in info.get("added_damage", {}).items():
                    try:
                        added_damage[DamageType(dtype_str)] = float(val)
                    except (ValueError, KeyError):
                        pass

                penetration = {}
                for dtype_str, val in info.get("penetration", {}).items():
                    try:
                        penetration[DamageType(dtype_str)] = float(val)
                    except (ValueError, KeyError):
                        pass

                _synced_support[name] = SupportGemEffect(
                    name=name,
                    modifiers=modifiers,
                    added_damage=added_damage,
                    attack_speed_mod=info.get("attack_speed_mod", 0.0),
                    cast_speed_mod=info.get("cast_speed_mod", 0.0),
                    less_attack_speed=info.get("less_attack_speed", 0.0),
                    penetration=penetration,
                    increased_crit=info.get("increased_crit", 0.0),
                    impale_chance=info.get("impale_chance", 0.0),
                    increased_impale_effect=info.get("increased_impale_effect", 0.0),
                )
            logger.info("Registry loaded %d support gems from RePoE", len(_synced_support))

        # Base items
        raw_bases = data.get("base_items", {})
        if raw_bases:
            _synced_weapon_bases = raw_bases.get("weapons", {})
            _synced_armour_bases = raw_bases.get("armour", {})
            logger.info(
                "Registry loaded %d weapon bases, %d armour slots from RePoE",
                len(_synced_weapon_bases or {}),
                len(_synced_armour_bases or {}),
            )

    except Exception:
        logger.debug("RePoE sync unavailable, using hardcoded game data", exc_info=True)


# -----------------------------------------------------------------------
# Public API — gems
# -----------------------------------------------------------------------

def get_active_gem(name: str) -> ActiveGemStats | None:
    """Look up active gem stats by name. Checks RePoE first, then hardcoded."""
    _ensure_synced()
    if _synced_active:
        result = _synced_active.get(name)
        if result is not None:
            return result
    return _hardcoded_active(name)


def get_support_gem(name: str) -> SupportGemEffect | None:
    """Look up support gem effects by name. Checks RePoE first, then hardcoded."""
    _ensure_synced()
    if _synced_support:
        result = _synced_support.get(name)
        if result is not None:
            return result
    return _hardcoded_support(name)


def list_active_gem_names() -> list[str]:
    """Return all known active gem names (merged RePoE + hardcoded)."""
    _ensure_synced()
    names = set(_HC_ACTIVE.keys())
    if _synced_active:
        names.update(_synced_active.keys())
    return sorted(names)


def list_support_gem_names() -> list[str]:
    """Return all known support gem names (merged RePoE + hardcoded)."""
    _ensure_synced()
    names = set(_HC_SUPPORT.keys())
    if _synced_support:
        names.update(_synced_support.keys())
    return sorted(names)


def is_known_gem(name: str) -> bool:
    """Check if a gem name is in any database (RePoE or hardcoded)."""
    _ensure_synced()
    if _synced_active and name in _synced_active:
        return True
    if _synced_support and name in _synced_support:
        return True
    return name in _HC_ACTIVE or name in _HC_SUPPORT


# -----------------------------------------------------------------------
# Public API — base items
# -----------------------------------------------------------------------

def get_weapon_bases() -> dict[str, tuple]:
    """Return all weapon base types: {name: (name, phys_min, phys_max, aps, crit, implicit)}.

    Returns RePoE data if available, otherwise empty dict (hardcoded weapon
    bases are in synthetic_items.py for now).
    """
    _ensure_synced()
    return _synced_weapon_bases or {}


def get_armour_bases() -> dict[str, dict[str, tuple]]:
    """Return armour base types: {slot: {name: (name, ar, ev, es, implicit)}}.

    Returns RePoE data if available, otherwise empty dict.
    """
    _ensure_synced()
    return _synced_armour_bases or {}


def get_weapon_base(name: str) -> tuple | None:
    """Look up a specific weapon base type by name."""
    _ensure_synced()
    if _synced_weapon_bases:
        return _synced_weapon_bases.get(name)
    return None


# -----------------------------------------------------------------------
# Admin
# -----------------------------------------------------------------------

def force_refresh() -> dict[str, int]:
    """Force re-sync from RePoE. Returns counts of loaded items."""
    global _sync_attempted
    _sync_attempted = False

    # Clear cached data
    global _synced_active, _synced_support, _synced_weapon_bases, _synced_armour_bases
    _synced_active = None
    _synced_support = None
    _synced_weapon_bases = None
    _synced_armour_bases = None

    _ensure_synced()

    return {
        "active_gems": len(_synced_active or {}),
        "support_gems": len(_synced_support or {}),
        "weapon_bases": len(_synced_weapon_bases or {}),
        "armour_slots": len(_synced_armour_bases or {}),
    }
