"""
Decode Path of Building export codes into structured Build objects.

PoB export codes are Base64url-encoded, zlib-compressed XML documents.
This module handles the full pipeline:

    export code (str) → Base64 decode → zlib decompress → XML → Build model

Supports:
- Standard PoB export codes (pasted from "Export" button)
- pastebin.com and pobb.in URLs (fetches the raw paste content)
"""

from __future__ import annotations

import base64
import re
import zlib
from typing import TYPE_CHECKING

from lxml import etree

from pop.build_parser.models import (
    Build,
    BuildConfig,
    Gem,
    Item,
    ItemMod,
    ItemSet,
    PassiveSpec,
    SkillGroup,
    SkillSet,
)

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def decode_pob_code(code: str) -> Build:
    """
    Decode a PoB export code string into a Build object.

    Accepts either a raw Base64 export code or a pobb.in / pastebin URL.

    Args:
        code: Base64url-encoded PoB export string, or a pobb.in/pastebin URL.

    Returns:
        Fully populated Build model.

    Raises:
        ValueError: If the code cannot be decoded or parsed.
    """
    code = code.strip()

    # Auto-fetch if the input is a URL
    if code.startswith(("http://", "https://")):
        import urllib.request
        raw_url = decode_pob_url(code)
        req = urllib.request.Request(raw_url, headers={"User-Agent": "PathOfPurpose/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.read().decode("utf-8").strip()

    xml_bytes = _decompress_code(code)
    root = _parse_xml(xml_bytes)
    return _xml_to_build(root)


def decode_pob_url(url: str) -> str:
    """
    Extract the raw PoB export code from a pastebin/pobb.in URL.

    This returns the code string — call decode_pob_code() on the result.

    Args:
        url: A pastebin.com or pobb.in URL.

    Returns:
        The raw export code string.

    Raises:
        ValueError: If the URL format is not recognized.
    """
    # pastebin.com/XXXXX → pastebin.com/raw/XXXXX
    match = re.match(r"https?://pastebin\.com/(?:raw/)?(\w+)", url)
    if match:
        return f"https://pastebin.com/raw/{match.group(1)}"

    # pobb.in/XXXXX → pobb.in/XXXXX/raw
    match = re.match(r"https?://pobb\.in/([\w-]+)(?:/raw)?", url)
    if match:
        return f"https://pobb.in/{match.group(1)}/raw"

    raise ValueError(f"Unrecognized PoB URL format: {url}")


def xml_to_string(code: str) -> str:
    """Decode a PoB code and return the raw XML as a formatted string (for debugging)."""
    xml_bytes = _decompress_code(code.strip())
    root = _parse_xml(xml_bytes)
    return etree.tostring(root, pretty_print=True, encoding="unicode")


# ---------------------------------------------------------------------------
# Decompression
# ---------------------------------------------------------------------------


def _decompress_code(code: str) -> bytes:
    """Base64url decode → zlib decompress."""
    # Strip whitespace/newlines from copy-paste
    code = code.strip().replace("\n", "").replace("\r", "").replace(" ", "")

    # PoB uses URL-safe Base64 (- and _ instead of + and /)
    # but some exports use standard Base64. Handle both.
    code = code.replace("-", "+").replace("_", "/")

    # Add padding if needed
    padding = 4 - (len(code) % 4)
    if padding != 4:
        code += "=" * padding

    try:
        raw = base64.b64decode(code)
    except Exception as exc:
        raise ValueError(f"Base64 decode failed: {exc}") from exc

    try:
        # Try raw deflate first (wbits=-15), which is what PoB uses
        return zlib.decompress(raw, -15)
    except zlib.error:
        pass

    try:
        # Fall back to zlib header (wbits=15) or auto-detect (wbits=47)
        return zlib.decompress(raw, 47)
    except zlib.error as exc:
        raise ValueError(f"Zlib decompress failed: {exc}") from exc


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------


def _parse_xml(xml_bytes: bytes) -> etree._Element:
    """Parse XML bytes into an lxml element tree."""
    try:
        return etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"XML parse failed: {exc}") from exc


# ---------------------------------------------------------------------------
# XML → Build model
# ---------------------------------------------------------------------------


def _xml_to_build(root: etree._Element) -> Build:
    """Convert a PoB XML root element into a Build model."""
    build_el = root.find("Build")
    if build_el is None:
        raise ValueError("Missing <Build> element in PoB XML")

    build = Build(
        class_name=build_el.get("className", ""),
        ascendancy_name=build_el.get("ascClassName", ""),
        level=_int(build_el.get("level", "1")),
        main_socket_group=_int(build_el.get("mainSocketGroup", "0")),
        pob_version=root.get("version", ""),
        build_name=build_el.get("buildName", ""),
    )

    # Parse each section
    build.passive_specs = _parse_passive_specs(root)

    skill_sets, active_skill_set, flat_skills = _parse_skills(root)
    build.skill_sets = skill_sets
    build.active_skill_set = active_skill_set
    build.skill_groups = flat_skills

    items_by_id, item_sets, active_item_set = _parse_items(root)
    build.item_sets = item_sets
    build.active_item_set = active_item_set
    build.items = list(items_by_id.values())

    build.config = _parse_config(root)

    return build


# ---------------------------------------------------------------------------
# Passive tree parsing
# ---------------------------------------------------------------------------


def _parse_passive_specs(root: etree._Element) -> list[PassiveSpec]:
    """Parse <Tree> element containing one or more <Spec> children."""
    tree_el = root.find("Tree")
    if tree_el is None:
        return []

    specs: list[PassiveSpec] = []
    for spec_el in tree_el.findall("Spec"):
        # Node IDs are stored in a <URL> child element as a PoE passive tree URL
        # e.g., https://www.pathofexile.com/passive-skill-tree/3.21.0/AAAA...
        # OR as plain text list of node IDs
        nodes = _parse_spec_nodes(spec_el)

        # Extract full URL for "view on pathofexile.com" linking
        url_el = spec_el.find("URL")
        tree_url = (url_el.text or "").strip() if url_el is not None else ""

        spec = PassiveSpec(
            title=spec_el.get("title", "Default"),
            tree_version=spec_el.get("treeVersion", ""),
            class_id=_int(spec_el.get("classId", "0")),
            ascendancy_id=_int(spec_el.get("ascendClassId", "0")),
            nodes=nodes,
            url=tree_url,
        )

        # Parse overrides (jewel sockets, cluster jewels, etc.)
        for override_el in spec_el.findall("Override"):
            node_id = _int(override_el.get("nodeId", "0"))
            override_id = _int(override_el.get("overrideNodeId", "0"))
            if node_id and override_id:
                spec.overrides[node_id] = override_id

        specs.append(spec)

    return specs


def _parse_spec_nodes(spec_el: etree._Element) -> list[int]:
    """
    Extract node IDs from a <Spec> element.

    PoB stores the passive tree in a <URL> child as a full path-of-exile URL.
    The node IDs are encoded in the URL's hash/path. We also handle newer
    formats that store nodes directly.
    """
    # Try <URL> element (most common format)
    url_el = spec_el.find("URL")
    if url_el is not None and url_el.text:
        url_text = url_el.text.strip()
        return _decode_tree_url(url_text)

    # Try Nodes attribute or child elements
    nodes_text = spec_el.get("nodes", "")
    if nodes_text:
        return [int(n) for n in nodes_text.split(",") if n.strip().isdigit()]

    return []


def _decode_tree_url(url: str) -> list[int]:
    """
    Decode node IDs from a PoE passive tree URL.

    The URL ends with a Base64-encoded binary payload containing the
    allocated node IDs as big-endian 16-bit integers.
    """
    # Extract the encoded portion after the last /
    parts = url.rstrip("/").split("/")
    encoded = parts[-1] if parts else ""

    if not encoded or encoded.startswith("http"):
        return []

    # URL-safe Base64 decode
    encoded = encoded.replace("-", "+").replace("_", "/")
    padding = 4 - (len(encoded) % 4)
    if padding != 4:
        encoded += "=" * padding

    try:
        data = base64.b64decode(encoded)
    except Exception:
        return []

    if len(data) < 7:
        return []

    # Header: version (4 bytes) + class (1 byte) + ascendancy (1 byte) + fullscreen (1 byte)
    # Remaining bytes: node IDs as big-endian uint16
    node_data = data[7:]
    nodes: list[int] = []
    for i in range(0, len(node_data) - 1, 2):
        node_id = int.from_bytes(node_data[i : i + 2], byteorder="big")
        if node_id > 0:
            nodes.append(node_id)

    return nodes


# ---------------------------------------------------------------------------
# Skill / gem parsing
# ---------------------------------------------------------------------------


def _parse_skills(
    root: etree._Element,
) -> tuple[list[SkillSet], int, list[SkillGroup]]:
    """
    Parse <Skills> element containing <Skill> groups with <Gem> children.

    Builds with variants wrap skills in <SkillSet> elements. Simple builds
    have <Skill> directly under <Skills>.

    Returns:
        (skill_sets, active_skill_set_index, flat_skill_groups_from_active_set)
    """
    skills_el = root.find("Skills")
    if skills_el is None:
        return [], 0, []

    active_set_idx = _int(skills_el.get("activeSkillSet", "1")) - 1  # 1-based → 0-based

    # Check for <SkillSet> children (variant builds)
    skill_set_els = skills_el.findall("SkillSet")

    if skill_set_els:
        skill_sets: list[SkillSet] = []
        for ss_el in skill_set_els:
            groups = _parse_skill_elements(ss_el)
            skill_sets.append(SkillSet(
                title=ss_el.get("title", ""),
                skills=groups,
            ))

        # Also collect any <Skill> directly under <Skills> (shared skills)
        shared = _parse_skill_elements(skills_el)

        # Active set's skills + shared skills for backward compat
        if 0 <= active_set_idx < len(skill_sets):
            flat = skill_sets[active_set_idx].skills + shared
        else:
            flat = shared

        return skill_sets, active_set_idx, flat
    else:
        # Simple build — no SkillSet wrappers
        flat = _parse_skill_elements(skills_el)
        return [], 0, flat


def _parse_skill_elements(parent: etree._Element) -> list[SkillGroup]:
    """Parse <Skill> children of a given parent element into SkillGroups."""
    groups: list[SkillGroup] = []
    for skill_el in parent.findall("Skill"):
        group = SkillGroup(
            slot=skill_el.get("slot", ""),
            label=skill_el.get("label", ""),
            is_enabled=_bool(skill_el.get("enabled", "true")),
        )

        for gem_el in skill_el.findall("Gem"):
            gem = Gem(
                name=gem_el.get("nameSpec", gem_el.get("name", "")),
                gem_id=gem_el.get("gemId", ""),
                level=_int(gem_el.get("level", "20")),
                quality=_int(gem_el.get("quality", "0")),
                is_support="Support" in gem_el.get("gemId", "")
                or _bool(gem_el.get("isSupport", "false")),
                is_enabled=_bool(gem_el.get("enabled", "true")),
            )
            group.gems.append(gem)

        groups.append(group)

    return groups


# ---------------------------------------------------------------------------
# Item parsing
# ---------------------------------------------------------------------------


def _parse_items(
    root: etree._Element,
) -> tuple[dict[int, Item], list[ItemSet], int]:
    """
    Parse <Items> element.

    Items in PoB XML are stored as raw text blocks (the same format as
    in-game item copy/paste), nested inside <Item> elements. Slot
    assignments are in <Slot> sibling elements OR inside <ItemSet> children
    for variant builds.

    Returns:
        (items_by_id, item_sets, active_item_set_index)
    """
    items_el = root.find("Items")
    if items_el is None:
        return {}, [], 0

    active_set_idx = _int(items_el.get("activeItemSet", "1")) - 1  # 1-based → 0-based

    # First, parse all items by their id attribute
    items_by_id: dict[int, Item] = {}
    for item_el in items_el.findall("Item"):
        item_id = _int(item_el.get("id", "0"))
        raw_text = (item_el.text or "").strip()
        item = _parse_item_text(raw_text)
        item.id = item_id
        items_by_id[item_id] = item

    # Check for <ItemSet> children (variant builds)
    item_set_els = items_el.findall("ItemSet")

    if item_set_els:
        item_sets: list[ItemSet] = []
        for is_el in item_set_els:
            slot_map: dict[str, int] = {}
            for slot_el in is_el.findall("Slot"):
                slot_name = slot_el.get("name", "")
                item_id = _int(slot_el.get("itemId", "0"))
                if slot_name and item_id:
                    slot_map[slot_name] = item_id
            item_sets.append(ItemSet(
                title=is_el.get("title", ""),
                slot_map=slot_map,
            ))

        # Apply the active set's slot assignments for backward compat
        if 0 <= active_set_idx < len(item_sets):
            for slot_name, item_id in item_sets[active_set_idx].slot_map.items():
                if item_id in items_by_id:
                    items_by_id[item_id].slot = slot_name

        # Also apply any <Slot> directly under <Items> (shared slots)
        for slot_el in items_el.findall("Slot"):
            slot_name = slot_el.get("name", "")
            item_id = _int(slot_el.get("itemId", "0"))
            if item_id in items_by_id:
                items_by_id[item_id].slot = slot_name

        return items_by_id, item_sets, active_set_idx
    else:
        # Simple build — slots directly under <Items>
        for slot_el in items_el.findall("Slot"):
            slot_name = slot_el.get("name", "")
            item_id = _int(slot_el.get("itemId", "0"))
            if item_id in items_by_id:
                items_by_id[item_id].slot = slot_name

        return items_by_id, [], 0


def _parse_item_text(raw: str) -> Item:
    """
    Parse a single item from its raw text representation.

    PoB item format example:
        Rarity: RARE
        Glyph Hold
        Titanium Spirit Shield
        Quality: 20
        Implicits: 1
        15% increased Spell Damage
        +120 to maximum Life
        +45% to Fire Resistance
        ...
    """
    if not raw:
        return Item()

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    item = Item(raw_text=raw)

    # State machine for parsing
    rarity = ""
    implicit_count = 0
    implicits_remaining = 0
    parsing_implicits = False
    name_lines: list[str] = []
    header_done = False

    for line in lines:
        # Rarity line
        if line.startswith("Rarity:"):
            rarity = line.split(":", 1)[1].strip().upper()
            item.rarity = rarity
            continue

        # Quality
        if line.startswith("Quality:"):
            item.quality = _int(line.split(":", 1)[1].strip().replace("%", ""))
            continue

        # Level requirement
        if line.startswith("LevelReq:"):
            item.level = _int(line.split(":", 1)[1].strip())
            continue

        # Parse sockets line (e.g. "Sockets: R-R-R-R-B-G")
        if line.startswith("Sockets:"):
            item.sockets = line.split(":", 1)[1].strip()
            continue

        # Skip metadata lines that shouldn't be displayed
        # Catch all *BasePercentile variants (EvasionBasePercentile, etc.)
        if "BasePercentile:" in line:
            continue
        if line.startswith(("Unique ID:", "Item Level:",
                           "Selected Variant:", "Variant:", "Has Alt Variant",
                           "Has Variant", "Crafted:", "Prefix:", "Suffix:",
                           "ArmourData:", "Evasion:", "EnergyShield:",
                           "Ward:", "Block:",
                           "CraftedQuality:",
                           "Armour:", "MovementPenalty:",
                           "PhysicalDamage:", "ElementalDamage:",
                           "CriticalStrikeChance:", "AttacksPerSecond:",
                           "Range:", "Shaper Item", "Elder Item",
                           "Crusader Item", "Hunter Item",
                           "Redeemer Item", "Warlord Item",
                           "Synthesised Item", "Fractured Item")):
            continue

        # Implicits count marker
        if line.startswith("Implicits:"):
            implicit_count = _int(line.split(":", 1)[1].strip())
            implicits_remaining = implicit_count
            parsing_implicits = True
            header_done = True
            continue

        # Before Implicits marker: collect name/base type
        if not header_done:
            name_lines.append(line)
            continue

        # Implicit mods
        if parsing_implicits and implicits_remaining > 0:
            is_crafted, mod_text = _strip_crafted(line)
            item.implicits.append(ItemMod(
                text=mod_text,
                is_implicit=True,
                is_crafted=is_crafted,
            ))
            implicits_remaining -= 1
            if implicits_remaining == 0:
                parsing_implicits = False
            continue

        # Explicit mods (everything after implicits)
        is_crafted, mod_text = _strip_crafted(line)
        item.explicits.append(ItemMod(
            text=mod_text,
            is_crafted=is_crafted,
        ))

    # Assign name and base type from header lines
    # PoB format: line 1 = item name (for named items), line 2 = base type
    # For magic/normal items there's only 1 line (the base type)
    if len(name_lines) >= 2:
        item.name = name_lines[0]
        item.base_type = name_lines[-1]  # last line is always the base type
    elif len(name_lines) == 1:
        item.base_type = name_lines[0]

    return item


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------


def _parse_config(root: etree._Element) -> BuildConfig:
    """Parse <Config> element containing build configuration toggles."""
    config_el = root.find("Config")
    if config_el is None:
        return BuildConfig()

    entries: dict[str, str] = {}
    for input_el in config_el.findall("Input"):
        name = input_el.get("name", "")
        value = input_el.get("string", input_el.get("number", input_el.get("boolean", "")))
        if name:
            entries[name] = value

    return BuildConfig(entries=entries)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_crafted(line: str) -> tuple[bool, str]:
    """
    Detect and strip PoB mod tag prefixes.

    PoB can prefix mods with multiple tags like:
    - {crafted}Mod text here
    - {tags:attack,speed}{crafted}{range:0.5}(8-10)% increased Attack Speed
    - {Mod text here}           (whole line wrapped — treated as crafted)

    Strips ALL {key:value} and {keyword} prefixes, returning (is_crafted, clean_text).
    """
    import re

    is_crafted = "{crafted}" in line

    # Strip all {tag} prefixes (tags, crafted, range, variant, etc.)
    clean = re.sub(r"\{[^}]*\}", "", line).strip()

    # Handle case where whole line was wrapped in {} with no other content
    if not clean and line.startswith("{") and line.endswith("}"):
        return True, line[1:-1]

    # Convert PoB range format "(min-max)" to just the max value
    # e.g. "(8-10)% increased Attack Speed" → "10% increased Attack Speed"
    clean = re.sub(r"\((\d+)-(\d+)\)", lambda m: m.group(2), clean)

    return is_crafted, clean if clean else line


def _int(value: str) -> int:
    """Safely parse an integer, defaulting to 0."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _bool(value: str) -> bool:
    """Parse PoB-style boolean strings."""
    return value.lower() in ("true", "1", "yes")
