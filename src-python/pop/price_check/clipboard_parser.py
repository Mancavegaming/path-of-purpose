"""Parse PoE in-game Ctrl+C item clipboard text.

This is *different* from PoB XML format — sections separated by '--------',
has 'Item Level:', 'Corrupted', influence markers, etc.

Clipboard section order:
  Header (Item Class, Rarity, Name, Base Type)
  --------
  Properties (Quality, Armour, etc.)
  --------
  Requirements
  --------
  Sockets
  --------
  Item Level
  --------
  Implicits (first mod section after ilvl)
  --------
  Explicits (second mod section after ilvl)
  --------
  Corrupted / Influence / Note
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ClipboardItem:
    """Parsed representation of a PoE clipboard item."""

    item_class: str = ""
    rarity: str = ""
    name: str = ""
    base_type: str = ""
    quality: int = 0
    ilvl: int = 0
    sockets: str = ""
    implicits: list[str] = field(default_factory=list)
    explicits: list[str] = field(default_factory=list)
    crafted_mods: list[str] = field(default_factory=list)
    corrupted: bool = False
    influences: list[str] = field(default_factory=list)
    unidentified: bool = False
    note: str = ""
    gem_level: int = 0
    gem_quality: int = 0
    stack_size: str = ""
    is_gem: bool = False
    is_currency: bool = False
    is_map: bool = False


SEPARATOR = "--------"

_INFLUENCE_LINES = {
    "Shaper Item": "Shaper",
    "Elder Item": "Elder",
    "Crusader Item": "Crusader",
    "Redeemer Item": "Redeemer",
    "Hunter Item": "Hunter",
    "Warlord Item": "Warlord",
}

_CURRENCY_CLASSES = {
    "Currency", "Stackable Currency", "Divination Card",
    "Map Fragments", "Fragments",
}

_GEM_CLASSES = {"Skill Gems", "Active Skill Gems", "Support Skill Gems", "Gems"}

_PROPERTY_PREFIXES = (
    "Quality:", "Armour:", "Evasion Rating:", "Energy Shield:",
    "Chance to Block:", "Physical Damage:", "Elemental Damage:",
    "Critical Strike Chance:", "Attacks per Second:", "Weapon Range:",
    "Level:", "Mana Cost:", "Cast Time:", "Cooldown Time:",
    "Map Tier:", "Stack Size:",
)


def parse_clipboard_item(text: str) -> ClipboardItem:
    """Parse a PoE clipboard text (from in-game Ctrl+C) into a ClipboardItem."""
    if not text or not text.strip():
        raise ValueError("Empty clipboard text")

    item = ClipboardItem()
    sections = text.strip().split(SEPARATOR)
    sections = [s.strip() for s in sections if s.strip()]

    if not sections:
        raise ValueError("No parseable sections in clipboard text")

    _parse_header(sections, item)
    _parse_body(sections, item)

    return item


def _parse_header(sections: list[str], item: ClipboardItem) -> None:
    """Parse the first section: rarity, name, base_type, item_class."""
    header = sections[0]
    lines = [ln.strip() for ln in header.splitlines() if ln.strip()]

    for line in lines:
        if line.startswith("Item Class:"):
            item.item_class = line.split(":", 1)[1].strip()
        elif line.startswith("Rarity:"):
            item.rarity = line.split(":", 1)[1].strip()

    # Determine name and base_type from remaining non-keyword lines
    name_lines = [
        ln for ln in lines
        if not ln.startswith("Item Class:") and not ln.startswith("Rarity:")
    ]

    if item.rarity in ("Rare", "Unique") and len(name_lines) >= 2:
        item.name = name_lines[0]
        item.base_type = name_lines[1]
    elif name_lines:
        item.base_type = name_lines[0]
        if item.rarity in ("Rare", "Unique"):
            item.name = name_lines[0]

    # Check item class for gems/currency
    if item.item_class in _GEM_CLASSES:
        item.is_gem = True
    elif item.item_class in _CURRENCY_CLASSES:
        item.is_currency = True
    elif item.item_class == "Maps":
        item.is_map = True


def _parse_body(sections: list[str], item: ClipboardItem) -> None:
    """Parse remaining sections for properties, mods, etc.

    Two-pass approach: first classify all sections, then assign implicits
    vs explicits based on how many mod sections appear after Item Level.
    """
    found_ilvl = False
    # Collect mod sections after ilvl as raw line lists
    mod_sections_after_ilvl: list[list[str]] = []

    for section in sections[1:]:
        lines = [ln.strip() for ln in section.splitlines() if ln.strip()]
        if not lines:
            continue

        # Check for marker lines (Corrupted, Unidentified, Influences, Note)
        if _try_parse_markers(lines, item):
            continue

        # Requirements section (must be checked before properties,
        # because Requirements contains "Level:" which looks like a property)
        if any(line.startswith("Requirements:") for line in lines):
            continue

        # Check for property sections
        if _try_parse_properties(lines, item):
            continue

        # Item Level
        if _try_parse_ilvl(lines, item):
            found_ilvl = True
            continue

        # Sockets
        if _try_parse_sockets(lines, item):
            continue

        # Mod sections
        if _is_mod_section(lines) and found_ilvl:
            mod_sections_after_ilvl.append(lines)

    # Assign implicits vs explicits:
    # - 2+ sections: first = implicits, rest = explicits
    # - 1 section:   all explicits (no implicits on this item)
    if len(mod_sections_after_ilvl) >= 2:
        _collect_mods(mod_sections_after_ilvl[0], item, target="implicit")
        for sec in mod_sections_after_ilvl[1:]:
            _collect_mods(sec, item, target="explicit")
    elif len(mod_sections_after_ilvl) == 1:
        _collect_mods(mod_sections_after_ilvl[0], item, target="explicit")


def _try_parse_markers(lines: list[str], item: ClipboardItem) -> bool:
    """Check if all lines in the section are markers (Corrupted, Influence, etc.)."""
    all_markers = True
    any_marker = False

    for line in lines:
        if line == "Corrupted":
            item.corrupted = True
            any_marker = True
        elif line == "Unidentified":
            item.unidentified = True
            any_marker = True
        elif line == "Mirrored":
            any_marker = True
        elif line in _INFLUENCE_LINES:
            item.influences.append(_INFLUENCE_LINES[line])
            any_marker = True
        elif line.startswith("Note:"):
            item.note = line.split(":", 1)[1].strip()
            any_marker = True
        else:
            all_markers = False

    return any_marker and all_markers


def _try_parse_properties(lines: list[str], item: ClipboardItem) -> bool:
    """Check if the section is a properties section, parse values if so."""
    has_property = any(_is_property_line(line) for line in lines)
    if not has_property:
        return False

    for line in lines:
        if _is_property_line(line):
            _parse_property(line, item)
    return True


def _try_parse_ilvl(lines: list[str], item: ClipboardItem) -> bool:
    """Check for and parse Item Level line."""
    for line in lines:
        m = re.match(r"Item Level:\s*(\d+)", line)
        if m:
            item.ilvl = int(m.group(1))
            return True
    return False


def _try_parse_sockets(lines: list[str], item: ClipboardItem) -> bool:
    """Check for and parse Sockets line."""
    for line in lines:
        m = re.match(r"Sockets:\s*(.+)", line)
        if m:
            item.sockets = m.group(1).strip()
            return True
    return False


def _collect_mods(lines: list[str], item: ClipboardItem, target: str) -> None:
    """Add mod lines to the appropriate list."""
    for line in lines:
        if line.endswith("(crafted)"):
            item.crafted_mods.append(line)
        elif target == "implicit":
            item.implicits.append(line)
        else:
            item.explicits.append(line)


def _is_property_line(line: str) -> bool:
    """Check if a line is a property (Quality, Energy Shield, etc.)."""
    return any(line.startswith(p) for p in _PROPERTY_PREFIXES)


def _parse_property(line: str, item: ClipboardItem) -> None:
    """Extract a value from a property line."""
    if line.startswith("Quality:"):
        m = re.search(r"\+?(\d+)%", line)
        if m:
            val = int(m.group(1))
            item.quality = val
            if item.is_gem:
                item.gem_quality = val
    elif line.startswith("Level:") and item.is_gem:
        m = re.search(r"(\d+)", line)
        if m:
            item.gem_level = int(m.group(1))
    elif line.startswith("Stack Size:"):
        item.stack_size = line.split(":", 1)[1].strip()


def _is_mod_section(lines: list[str]) -> bool:
    """Heuristic: lines that look like mods (not properties, not requirements)."""
    for line in lines:
        if _is_property_line(line):
            return False
        if line.startswith("Requirements:"):
            return False
        if line.startswith("Item Level:"):
            return False
        if line.startswith("Sockets:"):
            return False
        if line in _INFLUENCE_LINES:
            return False
        if line in ("Corrupted", "Unidentified", "Mirrored"):
            return False
    return True
