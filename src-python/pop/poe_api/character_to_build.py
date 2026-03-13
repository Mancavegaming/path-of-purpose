"""Convert PoE public API character data into our Build model.

Takes the raw EquippedItem list (with socketed gems) and PassiveData
from the public character-window API and produces a Build object
compatible with the DPS calculator, trade search, and UI display.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from pop.build_parser.models import (
    Build,
    Gem,
    Item,
    ItemMod,
    PassiveSpec,
    SkillGroup,
)
from pop.poe_api.models import CharacterEntry, EquippedItem, PassiveData

logger = logging.getLogger(__name__)


def character_to_build(
    char: CharacterEntry,
    items: list[EquippedItem],
    passives: PassiveData,
) -> Build:
    """Convert PoE API character data into a Build model."""
    build_items: list[Item] = []
    skill_groups: list[SkillGroup] = []
    next_id = 1

    for eq_item in items:
        slot = eq_item.slot
        if not slot or slot.startswith("Weapon") and "Swap" in slot:
            continue  # Skip swap weapons for now

        # Convert to our Item model
        item = _convert_item(eq_item, next_id)
        build_items.append(item)
        next_id += 1

        # Extract skill groups from socketed gems
        groups = _extract_skill_groups(eq_item)
        skill_groups.extend(groups)

    # Build passive spec
    all_nodes = list(passives.hashes) + list(passives.hashes_ex)
    passive_spec = PassiveSpec(
        title="Current",
        nodes=all_nodes,
        total_points=len(all_nodes),
    )

    # Determine main skill group (largest group with an active gem)
    main_idx = _find_main_skill_group(skill_groups)

    # Determine ascendancy from class name
    # The API returns the ascendancy name directly in the class field
    # (e.g., "Necromancer" not "Witch")
    class_name, ascendancy = _resolve_class(char.class_name)

    build = Build(
        class_name=class_name,
        ascendancy_name=ascendancy,
        level=char.level,
        main_socket_group=main_idx + 1,  # 1-based
        passive_specs=[passive_spec],
        skill_groups=skill_groups,
        items=build_items,
        build_name=char.name,
    )

    logger.info(
        "Converted character '%s': %d items, %d skill groups, %d passives",
        char.name, len(build_items), len(skill_groups), len(all_nodes),
    )
    return build


def _convert_item(eq: EquippedItem, item_id: int) -> Item:
    """Convert an EquippedItem from the API into our Item model."""
    # Build raw_text for DPS calculator compatibility
    raw_lines: list[str] = []
    raw_lines.append(f"Rarity: {eq.rarity_name}")
    if eq.name:
        raw_lines.append(eq.name)
    raw_lines.append(eq.type_line or eq.base_type)

    # Add weapon properties to raw_text (Physical Damage, APS, Crit)
    for prop in eq.properties:
        if prop.values:
            val_str = prop.values[0][0] if prop.values[0] else ""
            if prop.name in (
                "Physical Damage", "Elemental Damage", "Chaos Damage",
                "Attacks per Second", "Critical Strike Chance",
                "Quality", "Armour", "Evasion Rating", "Energy Shield",
            ):
                raw_lines.append(f"{prop.name}: {val_str}")

    # Sockets string
    socket_str = _build_socket_string(eq)

    # Implicits
    implicits = [ItemMod(text=m, is_implicit=True) for m in eq.implicit_mods]

    # Explicits (includes crafted as is_crafted=True)
    explicits = [ItemMod(text=m) for m in eq.explicit_mods]
    explicits.extend(ItemMod(text=m, is_crafted=True) for m in eq.crafted_mods)

    # Add mod lines to raw_text
    raw_lines.append(f"Implicits: {len(implicits)}")
    for m in implicits:
        raw_lines.append(m.text)
    raw_lines.append("--------")
    for m in explicits:
        prefix = "{crafted}" if m.is_crafted else ""
        raw_lines.append(f"{prefix}{m.text}")

    return Item(
        id=item_id,
        slot=eq.slot,
        name=eq.name,
        base_type=eq.type_line or eq.base_type,
        rarity=eq.rarity_name,
        level=eq.ilvl,
        quality=0,
        sockets=socket_str,
        implicits=implicits,
        explicits=explicits,
        raw_text="\n".join(raw_lines),
        icon_url=eq.icon,
    )


def _build_socket_string(eq: EquippedItem) -> str:
    """Build a PoB-style socket string like 'R-R-G-B R G'."""
    if not eq.sockets:
        return ""
    parts: list[str] = []
    prev_group = -1
    for sock in eq.sockets:
        color = sock.colour or "W"
        if color == "S":
            color = "R"  # Normalize
        if color == "D":
            color = "G"
        if color == "A":
            color = "A"

        if prev_group >= 0 and sock.group == prev_group:
            parts.append(f"-{color}")
        elif prev_group >= 0:
            parts.append(f" {color}")
        else:
            parts.append(color)
        prev_group = sock.group
    return "".join(parts)


def _extract_skill_groups(eq: EquippedItem) -> list[SkillGroup]:
    """Extract linked gem groups from an item's socketed gems."""
    if not eq.socketed_items:
        return []

    # Group gems by socket link group
    groups_by_link: dict[int, list[Gem]] = defaultdict(list)

    for gem in eq.socketed_items:
        # Determine which link group this gem belongs to
        sock_idx = gem.socket
        if sock_idx < len(eq.sockets):
            link_group = eq.sockets[sock_idx].group
        else:
            link_group = 0

        gem_name = gem.type_line or gem.name
        if not gem_name:
            continue

        groups_by_link[link_group].append(Gem(
            name=gem_name,
            gem_id="",
            level=gem.gem_level,
            quality=gem.gem_quality,
            is_support=gem.support,
            is_enabled=True,
            icon_url=gem.icon,
        ))

    # Convert to SkillGroup objects
    result: list[SkillGroup] = []
    for _group_id, gems in sorted(groups_by_link.items()):
        if not gems:
            continue
        # Only create a skill group if there's at least one active gem
        has_active = any(not g.is_support for g in gems)
        if not has_active:
            continue

        result.append(SkillGroup(
            slot=eq.slot,
            label="",
            is_enabled=True,
            gems=gems,
        ))

    return result


def _find_main_skill_group(groups: list[SkillGroup]) -> int:
    """Find the index of the main skill group (most supports)."""
    if not groups:
        return 0
    best_idx = 0
    best_supports = -1
    for i, g in enumerate(groups):
        n_supports = len(g.support_gems)
        if n_supports > best_supports:
            best_supports = n_supports
            best_idx = i
    return best_idx


# Map ascendancy names back to base class
_ASCENDANCY_TO_CLASS: dict[str, str] = {
    # Marauder
    "Juggernaut": "Marauder", "Berserker": "Marauder", "Chieftain": "Marauder",
    # Ranger
    "Deadeye": "Ranger", "Raider": "Ranger", "Pathfinder": "Ranger",
    # Witch
    "Necromancer": "Witch", "Elementalist": "Witch", "Occultist": "Witch",
    # Duelist
    "Slayer": "Duelist", "Gladiator": "Duelist", "Champion": "Duelist",
    # Templar
    "Inquisitor": "Templar", "Hierophant": "Templar", "Guardian": "Templar",
    # Shadow
    "Assassin": "Shadow", "Trickster": "Shadow", "Saboteur": "Shadow",
    # Scion
    "Ascendant": "Scion",
}


def _resolve_class(api_class: str) -> tuple[str, str]:
    """Resolve the API class name into (base_class, ascendancy).

    The API's 'class' field contains the ascendancy name if the player
    has ascended (e.g., "Necromancer"), or the base class if not (e.g., "Witch").
    """
    base = _ASCENDANCY_TO_CLASS.get(api_class)
    if base:
        return base, api_class
    # Not an ascendancy — it's the base class itself
    return api_class, ""
