"""
DPS estimator and item comparison for trade listings.

Provides simplified weapon DPS calculations and stat comparisons
between equipped items and trade listings.
"""

from __future__ import annotations

import re

from pop.trade.models import ItemComparison, StatDelta, WeaponDps

# Weapon slot names (PoE / PoB conventions)
WEAPON_SLOTS = {"Weapon 1", "Weapon 2", "weapon", "weapon2", "Weapon"}

# Base types that occupy weapon slots but are NOT weapons (shields, quivers)
_NON_WEAPON_BASES = re.compile(
    r"(?:Shield|Buckler|Spirit Shield|Kite Shield|Tower Shield|Quiver|Globe|Crest"
    r"|Spiked Shield|Bone Spirit Shield|Titanium Spirit Shield|Vaal Spirit Shield"
    r"|Monarch|Aegis|Ward|Thorium Spirit Shield|Fossilised Spirit Shield"
    r"|Archon Kite Shield|Colossal Tower Shield|Pinnacle Tower Shield)",
    re.IGNORECASE,
)

# Regex patterns for weapon mods
_RE_FLAT_PHYS = re.compile(r"Adds (\d+) to (\d+) Physical Damage", re.IGNORECASE)
_RE_PCT_PHYS = re.compile(r"(\d+)% increased Physical Damage", re.IGNORECASE)
_RE_FLAT_ELE = re.compile(
    r"Adds (\d+) to (\d+) (Fire|Cold|Lightning) Damage", re.IGNORECASE
)
_RE_PCT_APS = re.compile(r"(\d+)% increased Attack Speed", re.IGNORECASE)

# Regex patterns for flat damage mods (rings, amulets, gloves, etc.)
# These use a (min, max) capture — extract_stat_values averages them into a single value.
_FLAT_DMG_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Added Physical Damage", re.compile(
        r"Adds (\d+) to (\d+) Physical Damage", re.IGNORECASE
    )),
    ("Added Fire Damage", re.compile(
        r"Adds (\d+) to (\d+) Fire Damage", re.IGNORECASE
    )),
    ("Added Cold Damage", re.compile(
        r"Adds (\d+) to (\d+) Cold Damage", re.IGNORECASE
    )),
    ("Added Lightning Damage", re.compile(
        r"Adds (\d+) to (\d+) Lightning Damage", re.IGNORECASE
    )),
    ("Added Chaos Damage", re.compile(
        r"Adds (\d+) to (\d+) Chaos Damage", re.IGNORECASE
    )),
]

# Regex patterns for general stats (single-value captures)
_STAT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Maximum Life", re.compile(r"\+(\d+) to maximum Life", re.IGNORECASE)),
    ("Maximum Mana", re.compile(r"\+(\d+) to maximum Mana", re.IGNORECASE)),
    ("Fire Resistance", re.compile(r"\+(\d+)% to Fire Resistance", re.IGNORECASE)),
    ("Cold Resistance", re.compile(r"\+(\d+)% to Cold Resistance", re.IGNORECASE)),
    ("Lightning Resistance", re.compile(r"\+(\d+)% to Lightning Resistance", re.IGNORECASE)),
    ("Chaos Resistance", re.compile(r"\+(\d+)% to Chaos Resistance", re.IGNORECASE)),
    ("All Elemental Resistances", re.compile(
        r"\+(\d+)% to all Elemental Resistances", re.IGNORECASE
    )),
    ("Strength", re.compile(r"\+(\d+) to Strength", re.IGNORECASE)),
    ("Dexterity", re.compile(r"\+(\d+) to Dexterity", re.IGNORECASE)),
    ("Intelligence", re.compile(r"\+(\d+) to Intelligence", re.IGNORECASE)),
    ("All Attributes", re.compile(r"\+(\d+) to all Attributes", re.IGNORECASE)),
    ("Energy Shield", re.compile(r"\+(\d+) to maximum Energy Shield", re.IGNORECASE)),
    ("Movement Speed", re.compile(r"(\d+)% increased Movement Speed", re.IGNORECASE)),
    ("Attack Speed", re.compile(r"(\d+)% increased Attack Speed", re.IGNORECASE)),
    ("Cast Speed", re.compile(r"(\d+)% increased Cast Speed", re.IGNORECASE)),
    ("Critical Strike Chance", re.compile(
        r"(\d+)% increased (?:Global )?Critical Strike Chance", re.IGNORECASE
    )),
    ("Critical Strike Multiplier", re.compile(
        r"\+(\d+)% to (?:Global )?Critical Strike Multiplier", re.IGNORECASE
    )),
    ("Increased Physical Damage", re.compile(
        r"(\d+)% increased Physical Damage", re.IGNORECASE
    )),
    ("Increased Elemental Damage", re.compile(
        r"(\d+)% increased Elemental Damage", re.IGNORECASE
    )),
    ("Spell Damage", re.compile(
        r"(\d+)% increased Spell Damage", re.IGNORECASE
    )),
]


def extract_weapon_stats(mods: list[str]) -> dict[str, float]:
    """Extract weapon-relevant stats from a list of mod strings.

    Returns dict with keys: flat_phys_min, flat_phys_max, pct_phys,
    flat_ele_min, flat_ele_max, pct_aps.
    """
    stats: dict[str, float] = {
        "flat_phys_min": 0.0,
        "flat_phys_max": 0.0,
        "pct_phys": 0.0,
        "flat_ele_min": 0.0,
        "flat_ele_max": 0.0,
        "pct_aps": 0.0,
    }

    for mod in mods:
        m = _RE_FLAT_PHYS.search(mod)
        if m:
            stats["flat_phys_min"] += float(m.group(1))
            stats["flat_phys_max"] += float(m.group(2))
            continue

        m = _RE_PCT_PHYS.search(mod)
        if m:
            stats["pct_phys"] += float(m.group(1))
            continue

        m = _RE_FLAT_ELE.search(mod)
        if m:
            stats["flat_ele_min"] += float(m.group(1))
            stats["flat_ele_max"] += float(m.group(2))
            continue

        m = _RE_PCT_APS.search(mod)
        if m:
            stats["pct_aps"] += float(m.group(1))

    return stats


def calculate_weapon_dps(stats: dict[str, float], base_aps: float = 1.2) -> WeaponDps:
    """Calculate weapon DPS from extracted stats.

    Args:
        stats: Dict from extract_weapon_stats().
        base_aps: Base attacks per second of the weapon.
    """
    avg_phys = (stats["flat_phys_min"] + stats["flat_phys_max"]) / 2.0
    avg_ele = (stats["flat_ele_min"] + stats["flat_ele_max"]) / 2.0

    aps = base_aps * (1.0 + stats["pct_aps"] / 100.0)
    phys_dps = avg_phys * (1.0 + stats["pct_phys"] / 100.0) * aps
    ele_dps = avg_ele * aps

    return WeaponDps(
        physical_dps=round(phys_dps, 1),
        elemental_dps=round(ele_dps, 1),
        total_dps=round(phys_dps + ele_dps, 1),
        attacks_per_second=round(aps, 2),
    )


def extract_stat_values(mods: list[str]) -> dict[str, float]:
    """Extract general stat values from mod strings.

    Handles both single-value stats (life, res, attributes, %damage, etc.)
    and flat damage ranges (averaged to a single value for comparison).
    """
    result: dict[str, float] = {}

    for mod in mods:
        # Flat damage ranges — average min+max for a comparable single value
        for stat_name, pattern in _FLAT_DMG_PATTERNS:
            m = pattern.search(mod)
            if m:
                avg = (float(m.group(1)) + float(m.group(2))) / 2.0
                result[stat_name] = result.get(stat_name, 0.0) + avg

        # Single-value stats
        for stat_name, pattern in _STAT_PATTERNS:
            m = pattern.search(mod)
            if m:
                result[stat_name] = result.get(stat_name, 0.0) + float(m.group(1))

    return result


def _get_all_mods(item: dict) -> list[str]:
    """Get all mods from an item dict (supports both build items and trade listings)."""
    mods: list[str] = []

    # Trade listing style
    mods.extend(item.get("explicit_mods", []))
    mods.extend(item.get("implicit_mods", []))
    mods.extend(item.get("crafted_mods", []))

    # Build item style (ItemMod objects with .text)
    for impl in item.get("implicits", []):
        if isinstance(impl, dict) and "text" in impl:
            mods.append(impl["text"])
        elif isinstance(impl, str):
            mods.append(impl)

    for expl in item.get("explicits", []):
        if isinstance(expl, dict) and "text" in expl:
            mods.append(expl["text"])
        elif isinstance(expl, str):
            mods.append(expl)

    return mods


def _get_item_name(item: dict) -> str:
    """Get display name from an item dict."""
    return (
        item.get("name")
        or item.get("item_name")
        or item.get("base_type")
        or item.get("type_line")
        or "Unknown"
    )


def _is_weapon_item(item: dict, slot: str) -> bool:
    """Check if an item in a weapon slot is actually a weapon (not a shield/quiver)."""
    if slot not in WEAPON_SLOTS:
        return False
    # Check base_type and name for shield/quiver keywords
    base = item.get("base_type", "") or ""
    name = item.get("name", "") or item.get("item_name", "") or ""
    type_line = item.get("type_line", "") or ""
    for text in (base, name, type_line):
        if _NON_WEAPON_BASES.search(text):
            return False
    return True


def _calc_flat_dps(mods: list[str], aps: float) -> float:
    """Calculate DPS contribution from flat added damage mods × weapon APS."""
    total_avg = 0.0
    for mod in mods:
        m = _RE_FLAT_PHYS.search(mod)
        if m:
            total_avg += (float(m.group(1)) + float(m.group(2))) / 2.0
            continue
        m = _RE_FLAT_ELE.search(mod)
        if m:
            total_avg += (float(m.group(1)) + float(m.group(2))) / 2.0
    return round(total_avg * aps, 1)


def compare_items(
    equipped_item: dict,
    trade_listing: dict,
    slot: str,
    weapon_aps: float = 0.0,
) -> ItemComparison:
    """Compare an equipped item against a trade listing.

    Args:
        equipped_item: Equipped item data (from build parser).
        trade_listing: Trade listing data.
        slot: Item slot name.
        weapon_aps: Weapon attacks per second from build (for non-weapon DPS calc).

    Returns:
        ItemComparison with DPS and/or stat deltas.
    """
    is_weapon = _is_weapon_item(equipped_item, slot)

    eq_mods = _get_all_mods(equipped_item)
    tr_mods = _get_all_mods(trade_listing)

    eq_name = _get_item_name(equipped_item)
    tr_name = _get_item_name(trade_listing)

    equipped_dps = None
    trade_dps = None
    dps_change_pct = 0.0
    equipped_flat_dps = 0.0
    trade_flat_dps = 0.0
    flat_dps_change = 0.0

    if is_weapon:
        eq_stats = extract_weapon_stats(eq_mods)
        tr_stats = extract_weapon_stats(tr_mods)

        # Get base APS — prefer explicit values from the item data
        eq_aps = equipped_item.get("attacks_per_second", 1.2)
        tr_aps = trade_listing.get("attacks_per_second", 1.2)

        equipped_dps = calculate_weapon_dps(eq_stats, base_aps=eq_aps)
        trade_dps = calculate_weapon_dps(tr_stats, base_aps=tr_aps)

        if equipped_dps.total_dps > 0:
            dps_change_pct = round(
                (trade_dps.total_dps - equipped_dps.total_dps)
                / equipped_dps.total_dps
                * 100.0,
                1,
            )
    elif weapon_aps > 0:
        # Non-weapon items: calculate DPS contribution from flat added damage
        equipped_flat_dps = _calc_flat_dps(eq_mods, weapon_aps)
        trade_flat_dps = _calc_flat_dps(tr_mods, weapon_aps)
        flat_dps_change = round(trade_flat_dps - equipped_flat_dps, 1)

    # Stat comparison (for all items)
    eq_vals = extract_stat_values(eq_mods)
    tr_vals = extract_stat_values(tr_mods)

    all_stats = sorted(set(eq_vals.keys()) | set(tr_vals.keys()))
    stat_deltas: list[StatDelta] = []

    for stat_name in all_stats:
        eq_v = eq_vals.get(stat_name, 0.0)
        tr_v = tr_vals.get(stat_name, 0.0)
        diff = tr_v - eq_v
        pct = round(diff / eq_v * 100.0, 1) if eq_v != 0 else 0.0
        stat_deltas.append(StatDelta(
            stat_name=stat_name,
            equipped_value=eq_v,
            trade_value=tr_v,
            difference=diff,
            pct_change=pct,
        ))

    # Summary
    parts: list[str] = []
    if is_weapon and equipped_dps and trade_dps:
        direction = "more" if dps_change_pct > 0 else "less"
        parts.append(f"DPS: {trade_dps.total_dps} vs {equipped_dps.total_dps} "
                      f"({dps_change_pct:+.1f}% {direction})")
    elif flat_dps_change != 0:
        direction = "more" if flat_dps_change > 0 else "less"
        parts.append(f"Flat DPS: {trade_flat_dps} vs {equipped_flat_dps} "
                      f"({flat_dps_change:+.1f} {direction})")

    better = [d for d in stat_deltas if d.difference > 0]
    worse = [d for d in stat_deltas if d.difference < 0]
    if better:
        parts.append(f"{len(better)} stat(s) better")
    if worse:
        parts.append(f"{len(worse)} stat(s) worse")

    return ItemComparison(
        equipped_name=eq_name,
        trade_name=tr_name,
        slot=slot,
        is_weapon=is_weapon,
        equipped_dps=equipped_dps,
        trade_dps=trade_dps,
        dps_change_pct=dps_change_pct,
        equipped_flat_dps=equipped_flat_dps,
        trade_flat_dps=trade_flat_dps,
        flat_dps_change=flat_dps_change,
        stat_deltas=stat_deltas,
        summary=". ".join(parts) if parts else "No comparable stats found.",
    )
