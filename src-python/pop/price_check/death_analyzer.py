"""Analyze player deaths against defence stats and suggest improvements.

Reads existing DefenceResult fields and death event data from the log watcher.
"""

from __future__ import annotations

import re
import random

from pop.log_watcher.monster_names import MONSTER_ELEMENTS, BOSS_ZONE_ELEMENTS

# Grace verses for comfort after death — sourced from various translations
_GRACE_VERSES = [
    ("For I know the plans I have for you, declares the Lord, plans to prosper you and not to harm you.", "Jeremiah 29:11"),
    ("The Lord is close to the brokenhearted and saves those who are crushed in spirit.", "Psalm 34:18"),
    ("I can do all things through Christ who strengthens me.", "Philippians 4:13"),
    ("Be strong and courageous. Do not be afraid; do not be discouraged.", "Joshua 1:9"),
    ("The righteous may fall seven times but still get up.", "Proverbs 24:16"),
    ("God is our refuge and strength, an ever-present help in trouble.", "Psalm 46:1"),
    ("Cast all your anxiety on him because he cares for you.", "1 Peter 5:7"),
    ("When you pass through the waters, I will be with you.", "Isaiah 43:2"),
    ("He heals the brokenhearted and binds up their wounds.", "Psalm 147:3"),
    ("My grace is sufficient for you, for my power is made perfect in weakness.", "2 Corinthians 12:9"),
]


def analyze_death(
    death_event: dict,
    defence: dict,
    zone_name: str = "",
) -> dict:
    """Analyze a death event against the player's defence stats.

    Args:
        death_event: Dict with 'killer', 'zone', 'timestamp' from log watcher.
        defence: Dict matching DefenceResult fields (life, armour, evasion,
                 energy_shield, elemental_resistances, chaos_resistance,
                 spell_suppression, block_chance, etc.).
        zone_name: Current zone name (overrides death_event zone if set).

    Returns:
        Dict with killer, zone, weaknesses, suggestions, grace_verse, grace_ref.
    """
    killer = death_event.get("killer", "Unknown")
    killer_raw = death_event.get("killer_raw", "")
    zone = zone_name or death_event.get("zone", "Unknown")

    # Infer damage element from killer metadata path, resolved name, or zone
    damage_element = _infer_element(killer_raw, killer, zone)

    weaknesses: list[dict] = []
    suggestions: list[str] = []

    # Determine content tier from zone name
    is_boss = _is_boss_zone(zone)
    life_threshold = 5500 if is_boss else 4000

    # --- Life check ---
    life = defence.get("life", 0)
    if life > 0 and life < life_threshold:
        weaknesses.append({
            "stat": "Life",
            "current": life,
            "target": life_threshold,
            "severity": "critical" if life < 3000 else "warning",
        })
        suggestions.append(f"Increase maximum life — aim for at least {life_threshold}")

    # --- Elemental resistances ---
    ele_res = defence.get("elemental_resistances", {})
    for element in ("fire", "cold", "lightning"):
        res = ele_res.get(element, 0)
        if res < 75:
            deficit = 75 - res
            weaknesses.append({
                "stat": f"{element.capitalize()} Resistance",
                "current": res,
                "target": 75,
                "severity": "critical" if deficit > 30 else "warning",
            })
            if not any("elemental resistances" in s.lower() for s in suggestions):
                suggestions.append("Cap elemental resistances at 75% — prioritize resist gear")

    # --- Chaos resistance ---
    chaos_res = defence.get("chaos_resistance", 0)
    if chaos_res < 0:
        weaknesses.append({
            "stat": "Chaos Resistance",
            "current": chaos_res,
            "target": 0,
            "severity": "critical" if chaos_res < -30 else "warning",
        })
        suggestions.append("Chaos resistance is negative — add chaos res on rings/amulet")

    # --- Spell suppression (non-ES builds) ---
    energy_shield = defence.get("energy_shield", 0)
    suppression = defence.get("spell_suppression", 0)
    if energy_shield < 2000 and suppression < 100:
        if suppression < 50:
            weaknesses.append({
                "stat": "Spell Suppression",
                "current": suppression,
                "target": 100,
                "severity": "warning",
            })
            suggestions.append("Invest in spell suppression on evasion gear — aim for 100%")

    # --- Armour check ---
    armour = defence.get("armour", 0)
    if armour > 0 and armour < 10000 and is_boss:
        weaknesses.append({
            "stat": "Armour",
            "current": armour,
            "target": 20000,
            "severity": "warning",
        })
        suggestions.append("Armour is low for boss content — consider Determination aura or armour flasks")
    elif armour > 0 and armour < 5000 and not is_boss:
        weaknesses.append({
            "stat": "Armour",
            "current": armour,
            "target": 10000,
            "severity": "warning",
        })

    # --- Evasion check ---
    evasion = defence.get("evasion", 0)
    if evasion > 0 and evasion < 10000 and is_boss:
        weaknesses.append({
            "stat": "Evasion",
            "current": evasion,
            "target": 20000,
            "severity": "warning",
        })

    # Select a grace verse
    verse, ref = random.choice(_GRACE_VERSES)

    # If we know the element, prioritize the matching resistance weakness
    if damage_element and damage_element != "Physical":
        ele_key = damage_element.lower()
        if ele_key == "chaos":
            if chaos_res < 20:
                if not any("chaos" in s.lower() for s in suggestions):
                    suggestions.insert(0, f"You died to {damage_element} damage — prioritize chaos resistance")
        elif ele_key in ("fire", "cold", "lightning"):
            res_val = ele_res.get(ele_key, 0)
            if res_val < 75:
                suggestions.insert(0, f"You died to {damage_element} damage — cap your {ele_key} resistance")

    return {
        "killer": killer,
        "zone": zone,
        "damage_element": damage_element,
        "weaknesses": weaknesses,
        "suggestions": suggestions[:3],  # max 3 actionable suggestions
        "grace_verse": verse,
        "grace_ref": ref,
    }


def _infer_element(killer_raw: str, killer_name: str, zone: str = "") -> str:
    """Infer the likely damage element from killer metadata path, name, or zone."""
    # 1. Direct lookup in MONSTER_ELEMENTS (authoritative)
    if killer_raw:
        clean = re.sub(r"@\d+$", "", killer_raw)
        if clean in MONSTER_ELEMENTS:
            return MONSTER_ELEMENTS[clean]
        if killer_raw in MONSTER_ELEMENTS:
            return MONSTER_ELEMENTS[killer_raw]

    # 2. Keyword matching on killer path + resolved name
    combined = (killer_raw + " " + killer_name).lower()
    if combined.strip():
        fire_keywords = ["fire", "flame", "burn", "ignit", "magma", "lava", "searing", "infernal", "scorch"]
        cold_keywords = ["cold", "frost", "ice", "chill", "freez", "blizzard", "avalanche", "glacial"]
        lightning_keywords = ["lightning", "storm", "shock", "thunder", "spark", "electr"]
        chaos_keywords = ["chaos", "caustic", "poison", "venom", "blight", "wither", "profane", "desecrat"]
        physical_keywords = ["physical", "bleed", "impale", "bone", "crush", "slam"]

        if any(kw in combined for kw in fire_keywords):
            return "Fire"
        if any(kw in combined for kw in cold_keywords):
            return "Cold"
        if any(kw in combined for kw in lightning_keywords):
            return "Lightning"
        if any(kw in combined for kw in chaos_keywords):
            return "Chaos"
        if any(kw in combined for kw in physical_keywords):
            return "Physical"

    # 3. Zone-based fallback for boss arenas
    if zone and zone in BOSS_ZONE_ELEMENTS:
        return BOSS_ZONE_ELEMENTS[zone]

    return ""


def _is_boss_zone(zone_name: str) -> bool:
    """Heuristic: check if zone is likely a boss encounter."""
    boss_keywords = [
        "shaper", "elder", "sirus", "maven", "uber",
        "cortex", "feared", "hidden", "formed", "twisted",
        "forgotten", "templar laboratory", "absence of value",
        "eye of the storm", "black star", "infinite hunger",
        "eater of worlds", "searing exarch",
    ]
    lower = zone_name.lower()
    return any(kw in lower for kw in boss_keywords)
