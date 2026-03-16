"""Analyze a Build to extract data relevant for loot filter generation."""

from __future__ import annotations

from dataclasses import dataclass, field

from pop.build_parser.models import Build


# Map weapon base types to PoE item filter Class names
_WEAPON_CLASS_KEYWORDS: dict[str, list[str]] = {
    "bow": ["Bows"],
    "wand": ["Wands"],
    "one hand sword": ["One Hand Swords", "Thrusting One Hand Swords"],
    "two hand sword": ["Two Hand Swords"],
    "one hand axe": ["One Hand Axes"],
    "two hand axe": ["Two Hand Axes"],
    "one hand mace": ["One Hand Maces", "Sceptres"],
    "two hand mace": ["Two Hand Maces"],
    "staff": ["Staves", "Warstaves"],
    "dagger": ["Daggers", "Rune Daggers"],
    "claw": ["Claws"],
    "sceptre": ["Sceptres"],
}

# Map armour base keywords to defence type
_ARMOUR_KEYWORDS: dict[str, str] = {
    "energy shield": "es",
    "evasion": "evasion",
    "armour": "armour",
}


@dataclass
class BuildFilterData:
    """Extracted build data relevant for filter generation."""

    weapon_classes: list[str] = field(default_factory=list)
    damage_types: list[str] = field(default_factory=list)
    active_gem_names: list[str] = field(default_factory=list)
    support_gem_names: list[str] = field(default_factory=list)
    resist_gaps: dict[str, float] = field(default_factory=dict)
    armour_type: str = ""  # "es", "evasion", "armour", or "hybrid"
    ascendancy: str = ""
    level: int = 1
    socket_colors_needed: list[str] = field(default_factory=list)


def analyze_build_for_filter(build: Build) -> BuildFilterData:
    """Extract filter-relevant data from a Build object."""
    data = BuildFilterData()
    data.ascendancy = build.ascendancy_name
    data.level = build.level

    items_by_slot = build.items_by_slot()

    # Weapon class detection
    weapon = items_by_slot.get("Weapon 1")
    if weapon:
        bt = (weapon.base_type or "").lower()
        for keyword, classes in _WEAPON_CLASS_KEYWORDS.items():
            if keyword in bt:
                data.weapon_classes = classes
                break
        if not data.weapon_classes:
            # Try raw text for weapon type hints
            raw = (weapon.raw_text or "").lower()
            for keyword, classes in _WEAPON_CLASS_KEYWORDS.items():
                if keyword in raw:
                    data.weapon_classes = classes
                    break

    # Armour type from body armour
    body = items_by_slot.get("Body Armour")
    if body:
        raw = (body.raw_text or body.base_type or "").lower()
        types_found = []
        for keyword, atype in _ARMOUR_KEYWORDS.items():
            if keyword in raw:
                types_found.append(atype)
        if len(types_found) > 1:
            data.armour_type = "hybrid"
        elif types_found:
            data.armour_type = types_found[0]

    # Extract gem names from all skill groups
    for sg in build.skill_groups:
        for gem in sg.gems:
            if not gem.is_enabled:
                continue
            if gem.is_support:
                data.support_gem_names.append(gem.name)
            else:
                data.active_gem_names.append(gem.name)

    # Detect damage types from gem tags and item mods
    _detect_damage_types(build, data)

    # Compute resist gaps from items (lightweight — no full calc pipeline)
    _compute_resist_gaps(build, data)

    return data


def _detect_damage_types(build: Build, data: BuildFilterData) -> None:
    """Infer primary damage types from gem names and item mods."""
    import re

    elemental_keywords = {
        "fire": ["fire", "ignite", "burning", "infernal", "flame"],
        "cold": ["cold", "ice", "freeze", "frost", "glacial", "winter"],
        "lightning": ["lightning", "shock", "thunder", "storm", "galvanic", "arc"],
        "chaos": ["chaos", "poison", "toxic", "blight", "wither", "viper"],
        "physical": ["physical", "bleed", "impale", "lacerate", "puncture"],
    }

    all_names = " ".join(data.active_gem_names + data.support_gem_names).lower()
    for dtype, keywords in elemental_keywords.items():
        if any(kw in all_names for kw in keywords):
            data.damage_types.append(dtype)

    # Also check weapon mods for damage types
    items_by_slot = build.items_by_slot()
    weapon = items_by_slot.get("Weapon 1")
    if weapon:
        for mod in weapon.all_mods:
            text = mod.text.lower()
            for dtype, keywords in elemental_keywords.items():
                if any(kw in text for kw in keywords) and dtype not in data.damage_types:
                    data.damage_types.append(dtype)

    if not data.damage_types:
        data.damage_types = ["physical"]


def _compute_resist_gaps(build: Build, data: BuildFilterData) -> None:
    """Quick resist gap calculation from item mods only."""
    import re

    total_fire = 0.0
    total_cold = 0.0
    total_lightning = 0.0
    total_chaos = 0.0

    for item in build.items:
        if not item.slot:
            continue
        for mod in item.all_mods:
            text = mod.text
            m = re.search(r"\+(\d+)% to Fire Resistance", text, re.IGNORECASE)
            if m:
                total_fire += float(m.group(1))
            m = re.search(r"\+(\d+)% to Cold Resistance", text, re.IGNORECASE)
            if m:
                total_cold += float(m.group(1))
            m = re.search(r"\+(\d+)% to Lightning Resistance", text, re.IGNORECASE)
            if m:
                total_lightning += float(m.group(1))
            m = re.search(r"\+(\d+)% to Chaos Resistance", text, re.IGNORECASE)
            if m:
                total_chaos += float(m.group(1))
            m = re.search(r"\+(\d+)% to all Elemental Resistances", text, re.IGNORECASE)
            if m:
                v = float(m.group(1))
                total_fire += v
                total_cold += v
                total_lightning += v

    cap = 75.0
    if total_fire < cap:
        data.resist_gaps["fire"] = total_fire - cap
    if total_cold < cap:
        data.resist_gaps["cold"] = total_cold - cap
    if total_lightning < cap:
        data.resist_gaps["lightning"] = total_lightning - cap
    if total_chaos < cap:
        data.resist_gaps["chaos"] = total_chaos - cap
