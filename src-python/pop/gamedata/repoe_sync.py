"""Fetch and parse RePoE data into calc-engine-compatible formats.

This module auto-generates all the game data that was previously hardcoded:
- Active gem stats (base damage, crit, cast time, tags, effectiveness)
- Support gem effects (more/less multipliers, added damage, penetration, speed)
- Base item types (weapons with damage/APS/crit, armour with AR/EV/ES)

Data is cached to disk and refreshed when stale (>24h or on demand).
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

REPOE_BASE = "https://repoe-fork.github.io"
GEMS_URL = f"{REPOE_BASE}/gems.min.json"
BASE_ITEMS_URL = f"{REPOE_BASE}/base_items.min.json"
UNIQUES_URL = f"{REPOE_BASE}/uniques.min.json"

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_MAX_AGE = 24 * 3600  # 24 hours

_HEADERS = {"User-Agent": "PathOfPurpose/1.0", "Accept": "application/json"}


def _cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{name}.json"


def _is_stale(path: Path) -> bool:
    if not path.exists():
        return True
    return (time.time() - path.stat().st_mtime) > CACHE_MAX_AGE


def _load_cache(name: str) -> dict | list | None:
    path = _cache_path(name)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _save_cache(name: str, data: Any) -> None:
    path = _cache_path(name)
    path.write_text(json.dumps(data), encoding="utf-8")


# -----------------------------------------------------------------------
# Fetch raw RePoE data
# -----------------------------------------------------------------------

def fetch_raw_gems(force: bool = False) -> dict:
    """Fetch raw gems.min.json from RePoE (sync, cached)."""
    if not force and not _is_stale(_cache_path("repoe_gems_raw")):
        cached = _load_cache("repoe_gems_raw")
        if cached:
            return cached
    resp = httpx.get(GEMS_URL, headers=_HEADERS, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    _save_cache("repoe_gems_raw", data)
    logger.info("Fetched %d gem entries from RePoE", len(data))
    return data


def fetch_raw_base_items(force: bool = False) -> dict:
    """Fetch raw base_items.min.json from RePoE (sync, cached)."""
    if not force and not _is_stale(_cache_path("repoe_bases_raw")):
        cached = _load_cache("repoe_bases_raw")
        if cached:
            return cached
    resp = httpx.get(BASE_ITEMS_URL, headers=_HEADERS, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    _save_cache("repoe_bases_raw", data)
    logger.info("Fetched %d base item entries from RePoE", len(data))
    return data


# -----------------------------------------------------------------------
# Parse active gems → calc engine format
# -----------------------------------------------------------------------

# Map RePoE stat IDs to DamageType
_DAMAGE_TYPE_MAP = {
    "fire": "FIRE",
    "cold": "COLD",
    "lightning": "LIGHTNING",
    "chaos": "CHAOS",
    "physical": "PHYSICAL",
}


def parse_active_gems(raw: dict) -> dict[str, dict]:
    """Parse RePoE gems into ActiveGemStats-compatible dicts.

    Returns: {gem_name: {tags, base_damage, base_crit, base_cast_time,
                         damage_effectiveness, attack_speed_multiplier}}
    """
    result: dict[str, dict] = {}

    for _key, gem in raw.items():
        if not isinstance(gem, dict):
            continue
        if gem.get("is_support"):
            continue

        bi = gem.get("base_item", {})
        if not isinstance(bi, dict) or bi.get("release_state") != "released":
            continue

        name = bi.get("display_name", "") or gem.get("display_name", "")
        if not name:
            continue

        # Tags
        tags: list[str] = []
        ask = gem.get("active_skill", {})
        if isinstance(ask, dict):
            types = ask.get("types", [])
            if isinstance(types, list):
                tags = [str(t).lower() for t in types]
        if not tags:
            raw_tags = gem.get("tags", [])
            if isinstance(raw_tags, list):
                tags = [str(t).lower() for t in raw_tags]

        # Level 20 stats
        per_level = gem.get("per_level", {})
        lvl20 = per_level.get("20", per_level.get("1", {}))
        if not isinstance(lvl20, dict):
            continue

        # Damage effectiveness (RePoE stores as integer, e.g., 270 = 270%)
        effectiveness_raw = lvl20.get("damage_effectiveness", 100)
        effectiveness = effectiveness_raw / 100.0 if effectiveness_raw else 1.0

        # Base crit (stored as int * 100, e.g., 600 = 6.0%)
        static = gem.get("static", {})
        crit_raw = static.get("crit_chance", 0)
        base_crit = crit_raw / 100.0 if crit_raw else 5.0

        # Cast time (stored in ms, e.g., 750 = 0.75s)
        cast_time_ms = gem.get("cast_time", 1000)
        base_cast_time = cast_time_ms / 1000.0 if cast_time_ms else 1.0

        # Base damage — extract from static stat IDs
        base_damage: dict[str, float] = {}
        static_stats = static.get("stats", [])
        stat_ids = [s.get("id", "") if isinstance(s, dict) else "" for s in static_stats]

        # Level 20 stat values
        lvl20_stats = lvl20.get("stats", [])
        for i, sid in enumerate(stat_ids):
            if i >= len(lvl20_stats) or lvl20_stats[i] is None:
                continue
            val = lvl20_stats[i]
            if isinstance(val, dict):
                val = val.get("value", 0)
            if not val:
                continue

            sid_lower = sid.lower()
            # Spell damage: spell_minimum_base_X_damage / spell_maximum_base_X_damage
            for dtype_key, dtype_name in _DAMAGE_TYPE_MAP.items():
                if f"minimum_base_{dtype_key}_damage" in sid_lower:
                    base_damage.setdefault(dtype_name, 0.0)
                    # Average = (min + max) / 2 — we'll get max from the next stat
                    base_damage[f"_min_{dtype_name}"] = float(val)
                elif f"maximum_base_{dtype_key}_damage" in sid_lower:
                    min_val = base_damage.pop(f"_min_{dtype_name}", 0.0)
                    base_damage[dtype_name] = (min_val + float(val)) / 2.0

        # Clean up temp keys
        base_damage = {k: v for k, v in base_damage.items() if not k.startswith("_min_")}

        # Attack speed multiplier (for attack skills like Cyclone)
        attack_speed_mult = 1.0
        for i, sid in enumerate(stat_ids):
            if "active_skill_attack_speed" in sid.lower() and "%" in sid:
                if i < len(lvl20_stats) and lvl20_stats[i] is not None:
                    val = lvl20_stats[i]
                    if isinstance(val, dict):
                        val = val.get("value", 0)
                    if val:
                        attack_speed_mult = val / 100.0

        entry = {
            "tags": tags,
            "base_damage": base_damage,
            "base_crit": base_crit,
            "base_cast_time": base_cast_time,
            "damage_effectiveness": effectiveness,
            "attack_speed_multiplier": attack_speed_mult,
        }
        result[name] = entry

    logger.info("Parsed %d active gems from RePoE", len(result))
    return result


# -----------------------------------------------------------------------
# Parse support gems → calc engine format
# -----------------------------------------------------------------------

def parse_support_gems(raw: dict) -> dict[str, dict]:
    """Parse RePoE gems into SupportGemEffect-compatible dicts.

    Returns: {gem_name: {modifiers, added_damage, attack_speed_mod,
                         cast_speed_mod, penetration, increased_crit, ...}}
    """
    result: dict[str, dict] = {}

    for _key, gem in raw.items():
        if not isinstance(gem, dict):
            continue
        if not gem.get("is_support"):
            continue

        bi = gem.get("base_item", {})
        if not isinstance(bi, dict) or bi.get("release_state") != "released":
            continue

        name = bi.get("display_name", "") or gem.get("display_name", "")
        if not name:
            continue

        # Get static stat IDs and level 20 values
        static = gem.get("static", {})
        static_stats = static.get("stats", [])
        stat_ids = [s.get("id", "") if isinstance(s, dict) else "" for s in static_stats]
        stat_types = [s.get("type", "") if isinstance(s, dict) else "" for s in static_stats]

        # Also check for constant values in static
        static_values = []
        for s in static_stats:
            if isinstance(s, dict) and "value" in s:
                static_values.append(s["value"])
            else:
                static_values.append(None)

        per_level = gem.get("per_level", {})
        lvl20 = per_level.get("20", per_level.get("1", {}))
        if not isinstance(lvl20, dict):
            continue

        lvl20_stats = lvl20.get("stats", [])

        # Build effect dict
        modifiers: list[dict] = []
        added_damage: dict[str, float] = {}
        attack_speed_mod = 0.0
        cast_speed_mod = 0.0
        less_attack_speed = 0.0
        penetration: dict[str, float] = {}
        increased_crit = 0.0
        impale_chance = 0.0
        increased_impale_effect = 0.0

        for i, sid in enumerate(stat_ids):
            # Get value: prefer lvl20, fall back to static constant
            val = None
            if i < len(lvl20_stats) and lvl20_stats[i] is not None:
                v = lvl20_stats[i]
                val = v.get("value", v) if isinstance(v, dict) else v
            elif i < len(static_values) and static_values[i] is not None:
                val = static_values[i]

            if val is None:
                continue

            sid_lower = sid.lower()

            # More/less damage multipliers (stat IDs ending in "_final" or "+%_final")
            if "_final" in sid_lower and "damage" in sid_lower:
                _parse_damage_modifier(sid_lower, float(val), modifiers)

            # Added damage
            elif "additional_" in sid_lower and "damage" in sid_lower:
                for dtype_key, dtype_name in _DAMAGE_TYPE_MAP.items():
                    if dtype_key in sid_lower:
                        if "minimum" in sid_lower:
                            added_damage[f"_min_{dtype_name}"] = float(val)
                        elif "maximum" in sid_lower:
                            min_v = added_damage.pop(f"_min_{dtype_name}", float(val))
                            added_damage[dtype_name] = (min_v + float(val)) / 2.0

            # Attack speed
            elif "attack_speed" in sid_lower and "final" in sid_lower:
                if val < 0:
                    less_attack_speed = abs(float(val))
                else:
                    attack_speed_mod = float(val)

            # Cast speed
            elif "cast_speed" in sid_lower:
                cast_speed_mod = float(val)

            # Penetration
            elif "penetrat" in sid_lower or "resist" in sid_lower:
                for dtype_key, dtype_name in _DAMAGE_TYPE_MAP.items():
                    if dtype_key in sid_lower:
                        penetration[dtype_name] = abs(float(val))

            # Crit
            elif "critical_strike_chance" in sid_lower and "increased" in sid_lower:
                increased_crit = float(val)

            # Impale
            elif "impale" in sid_lower:
                if "chance" in sid_lower:
                    impale_chance = float(val)
                elif "effect" in sid_lower:
                    increased_impale_effect = float(val)

        # Clean up temp keys in added_damage
        added_damage = {k: v for k, v in added_damage.items() if not k.startswith("_min_")}

        entry: dict[str, Any] = {"modifiers": modifiers}
        if added_damage:
            entry["added_damage"] = added_damage
        if attack_speed_mod:
            entry["attack_speed_mod"] = attack_speed_mod
        if cast_speed_mod:
            entry["cast_speed_mod"] = cast_speed_mod
        if less_attack_speed:
            entry["less_attack_speed"] = less_attack_speed
        if penetration:
            entry["penetration"] = penetration
        if increased_crit:
            entry["increased_crit"] = increased_crit
        if impale_chance:
            entry["impale_chance"] = impale_chance
        if increased_impale_effect:
            entry["increased_impale_effect"] = increased_impale_effect

        result[name] = entry

    logger.info("Parsed %d support gems from RePoE", len(result))
    return result


def _parse_damage_modifier(sid: str, value: float, modifiers: list[dict]) -> None:
    """Convert a RePoE stat ID + value into a calc engine modifier."""
    # Determine damage types from stat ID
    damage_types: list[str] = []
    for dtype_key, dtype_name in _DAMAGE_TYPE_MAP.items():
        if dtype_key in sid:
            damage_types.append(dtype_name)

    # Determine modifier type
    if "more" in sid or value > 0:
        mod_type = f"more_{'_'.join(dt.lower() for dt in damage_types)}_damage" if damage_types else "more_damage"
    else:
        mod_type = f"less_{'_'.join(dt.lower() for dt in damage_types)}_damage" if damage_types else "less_damage"

    # Handle melee/spell/attack specificity
    if "melee" in sid:
        mod_type = "more_melee_physical_damage" if "physical" in sid else "more_melee_damage"
    elif "spell" in sid:
        mod_type = "more_spell_damage"
    elif "attack" in sid:
        mod_type = "more_attack_damage"

    modifiers.append({
        "type": mod_type,
        "value": abs(value),
        "damage_types": damage_types,
    })


# -----------------------------------------------------------------------
# Parse base items → synthetic item format
# -----------------------------------------------------------------------

# Item classes that map to weapon slots
_WEAPON_CLASSES = {
    "Claw", "Dagger", "Wand", "One Hand Sword", "Thrusting One Hand Sword",
    "One Hand Axe", "One Hand Mace", "Sceptre", "Staff", "Warstaff",
    "Two Hand Sword", "Two Hand Axe", "Two Hand Mace", "Bow",
    "Rune Dagger", "Fishing Rod",
}

# Item classes that map to armour slots
_ARMOUR_CLASSES = {
    "Helmet", "Body Armour", "Gloves", "Boots", "Shield",
}

# Item classes for jewelry/belt
_JEWELRY_CLASSES = {"Amulet", "Ring", "Belt"}


def parse_base_items(raw: dict) -> dict:
    """Parse RePoE base items into weapon/armour base dicts.

    Returns:
        {
            "weapons": {name: (name, phys_min, phys_max, aps, crit, implicit_text)},
            "armour": {slot: {name: (name, armour, evasion, es, implicit_text)}},
            "jewelry": {slot: {name: (name, implicit_text)}},
        }
    """
    weapons: dict[str, tuple] = {}
    armour: dict[str, dict[str, tuple]] = {}
    jewelry: dict[str, dict[str, tuple]] = {}

    for _key, item in raw.items():
        if not isinstance(item, dict):
            continue
        if item.get("release_state") != "released":
            continue
        if item.get("domain") != "item":
            continue

        name = item.get("name", "")
        item_class = item.get("item_class", "")
        props = item.get("properties", {})
        if not name or not item_class:
            continue

        # Implicit text (we don't resolve the mod ID, just store it for reference)
        implicits = item.get("implicits", [])
        implicit_text = implicits[0] if implicits else ""

        if item_class in _WEAPON_CLASSES:
            phys_min = props.get("physical_damage_min", 0)
            phys_max = props.get("physical_damage_max", 0)
            attack_time = props.get("attack_time", 1000)
            aps = round(1000.0 / attack_time, 2) if attack_time else 1.2
            crit_raw = props.get("critical_strike_chance", 500)
            crit = crit_raw / 100.0

            weapons[name] = (name, phys_min, phys_max, aps, crit, implicit_text)

        elif item_class in _ARMOUR_CLASSES:
            # Armour values can be int or dict with min/max
            ar = props.get("armour", 0)
            if isinstance(ar, dict):
                ar = (ar.get("min", 0) + ar.get("max", 0)) // 2
            ev = props.get("evasion", 0)
            if isinstance(ev, dict):
                ev = (ev.get("min", 0) + ev.get("max", 0)) // 2
            es = props.get("energy_shield", 0)
            if isinstance(es, dict):
                es = (es.get("min", 0) + es.get("max", 0)) // 2

            slot = item_class
            if slot not in armour:
                armour[slot] = {}
            armour[slot][name] = (name, ar, ev, es, implicit_text)

    logger.info(
        "Parsed %d weapon bases, %d armour slots from RePoE",
        len(weapons), sum(len(v) for v in armour.values()),
    )
    return {"weapons": weapons, "armour": armour, "jewelry": jewelry}


# -----------------------------------------------------------------------
# Public sync API
# -----------------------------------------------------------------------

def sync_all(force: bool = False) -> dict:
    """Sync all game data from RePoE. Returns parsed data dict.

    Call this on app startup and when user clicks 'Refresh Knowledge'.
    Results are cached for 24 hours.
    """
    cache_path = _cache_path("parsed_gamedata")
    if not force and not _is_stale(cache_path):
        cached = _load_cache("parsed_gamedata")
        if cached:
            logger.info("Using cached game data (%d active, %d support gems)",
                        len(cached.get("active_gems", {})),
                        len(cached.get("support_gems", {})))
            return cached

    logger.info("Syncing game data from RePoE...")

    raw_gems = fetch_raw_gems(force)
    raw_bases = fetch_raw_base_items(force)

    result = {
        "active_gems": parse_active_gems(raw_gems),
        "support_gems": parse_support_gems(raw_gems),
        "base_items": parse_base_items(raw_bases),
        "synced_at": time.time(),
    }

    _save_cache("parsed_gamedata", result)
    logger.info(
        "Game data synced: %d active gems, %d support gems, %d weapon bases",
        len(result["active_gems"]),
        len(result["support_gems"]),
        len(result["base_items"].get("weapons", {})),
    )
    return result
