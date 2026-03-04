"""
Pydantic models for Path of Building export data.

These models represent the structured output of decoding a PoB export code.
They are also used as the "guide build" side of the Delta Engine comparison.
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CharClass(str, Enum):
    """PoE character classes (shared across PoE 1 and PoE 2)."""

    MARAUDER = "Marauder"
    RANGER = "Ranger"
    WITCH = "Witch"
    DUELIST = "Duelist"
    TEMPLAR = "Templar"
    SHADOW = "Shadow"
    SCION = "Scion"
    # PoE 2 classes
    WARRIOR = "Warrior"
    MONK = "Monk"
    MERCENARY = "Mercenary"
    HUNTRESS = "Huntress"
    SORCERESS = "Sorceress"
    DRUID = "Druid"


class ItemSlot(str, Enum):
    """Standard gear slots used by both PoB and the PoE API."""

    WEAPON1 = "Weapon 1"
    WEAPON2 = "Weapon 2"
    OFFHAND1 = "Weapon 1 Swap"
    OFFHAND2 = "Weapon 2 Swap"
    HELMET = "Helmet"
    BODY_ARMOUR = "Body Armour"
    GLOVES = "Gloves"
    BOOTS = "Boots"
    AMULET = "Amulet"
    RING1 = "Ring 1"
    RING2 = "Ring 2"
    BELT = "Belt"
    FLASK1 = "Flask 1"
    FLASK2 = "Flask 2"
    FLASK3 = "Flask 3"
    FLASK4 = "Flask 4"
    FLASK5 = "Flask 5"


# ---------------------------------------------------------------------------
# Item model
# ---------------------------------------------------------------------------


class ItemMod(BaseModel):
    """A single modifier line on an item."""

    text: str
    is_implicit: bool = False
    is_crafted: bool = False


class Item(BaseModel):
    """A single item from a PoB build export."""

    id: int = 0
    slot: str = ""
    name: str = ""
    base_type: str = ""
    rarity: str = "RARE"
    level: int = 0
    quality: int = 0
    sockets: str = ""
    implicits: list[ItemMod] = Field(default_factory=list)
    explicits: list[ItemMod] = Field(default_factory=list)
    raw_text: str = ""

    @property
    def all_mods(self) -> list[ItemMod]:
        return self.implicits + self.explicits


# ---------------------------------------------------------------------------
# Passive tree
# ---------------------------------------------------------------------------


class PassiveSpec(BaseModel):
    """A passive tree specification — a set of allocated node IDs."""

    title: str = "Default"
    tree_version: str = ""
    class_id: int = 0
    ascendancy_id: int = 0
    nodes: list[int] = Field(default_factory=list)
    overrides: dict[int, int] = Field(default_factory=dict)
    url: str = ""

    @property
    def node_count(self) -> int:
        return len(self.nodes)


# ---------------------------------------------------------------------------
# Skill gems
# ---------------------------------------------------------------------------


class Gem(BaseModel):
    """A single gem (active or support) within a skill group."""

    name: str = ""
    gem_id: str = ""
    level: int = 20
    quality: int = 0
    is_support: bool = False
    is_enabled: bool = True

    @property
    def display_name(self) -> str:
        parts = [self.name]
        if self.level != 20:
            parts.append(f"(Lv {self.level})")
        if self.quality > 0:
            parts.append(f"({self.quality}%)")
        return " ".join(parts)


class SkillGroup(BaseModel):
    """
    A group of linked gems (one active skill + its supports).

    In PoB XML, this is a <Skill> element containing multiple <Gem> children.
    """

    slot: str = ""
    label: str = ""
    is_enabled: bool = True
    gems: list[Gem] = Field(default_factory=list)

    @property
    def active_gem(self) -> Gem | None:
        for g in self.gems:
            if not g.is_support and g.is_enabled:
                return g
        return None

    @property
    def support_gems(self) -> list[Gem]:
        return [g for g in self.gems if g.is_support and g.is_enabled]


# ---------------------------------------------------------------------------
# Variant sets (builds with multiple variants wrap skills/items in sets)
# ---------------------------------------------------------------------------


class SkillSet(BaseModel):
    """A named set of skill groups (one per build variant)."""

    title: str = ""
    skills: list[SkillGroup] = Field(default_factory=list)


class ItemSet(BaseModel):
    """A named set of slot→item assignments (one per build variant)."""

    title: str = ""
    slot_map: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Top-level Build model
# ---------------------------------------------------------------------------


class BuildConfig(BaseModel):
    """PoB configuration toggles (enemy type, charges, etc.)."""

    entries: dict[str, str] = Field(default_factory=dict)


class Build(BaseModel):
    """
    Complete representation of a Path of Building export.

    This is the top-level model returned by decode_pob_code().
    """

    # Identity
    class_name: str = ""
    ascendancy_name: str = ""
    level: int = 1
    main_socket_group: int = 0

    # Build contents (active set — backward compatible)
    passive_specs: list[PassiveSpec] = Field(default_factory=list)
    skill_groups: list[SkillGroup] = Field(default_factory=list)
    items: list[Item] = Field(default_factory=list)
    config: BuildConfig = Field(default_factory=BuildConfig)

    # Variant sets
    skill_sets: list[SkillSet] = Field(default_factory=list)
    item_sets: list[ItemSet] = Field(default_factory=list)
    active_skill_set: int = 0
    active_item_set: int = 0

    # Metadata
    pob_version: str = ""
    build_name: str = ""

    @property
    def active_passive_spec(self) -> PassiveSpec | None:
        return self.passive_specs[0] if self.passive_specs else None

    @property
    def total_passive_points(self) -> int:
        spec = self.active_passive_spec
        return spec.node_count if spec else 0

    @property
    def main_skill(self) -> SkillGroup | None:
        idx = self.main_socket_group - 1
        if 0 <= idx < len(self.skill_groups):
            return self.skill_groups[idx]
        return None

    def items_by_slot(self) -> dict[str, Item]:
        return {item.slot: item for item in self.items if item.slot}

    def summary(self) -> str:
        main = self.main_skill
        main_name = main.active_gem.name if main and main.active_gem else "Unknown"
        return (
            f"Level {self.level} {self.ascendancy_name or self.class_name} "
            f"| Main: {main_name} "
            f"| Passives: {self.total_passive_points} "
            f"| Items: {len(self.items)} "
            f"| Skill groups: {len(self.skill_groups)}"
        )
