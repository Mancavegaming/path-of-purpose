"""
Pydantic models for PoE API responses.

These represent the *live character* side of the Delta Engine comparison.
The build_parser models represent the *guide build* side.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class Profile(BaseModel):
    """Account profile from GET /api/profile."""

    name: str = ""
    realm: str = "pc"
    uuid: str = ""


# ---------------------------------------------------------------------------
# Character listing
# ---------------------------------------------------------------------------


class CharacterEntry(BaseModel):
    """A single character from the character list."""

    id: str = ""
    name: str = ""
    class_name: str = Field(default="", alias="class")
    level: int = 0
    league: str = ""
    experience: int = 0

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Equipped items (from character detail)
# ---------------------------------------------------------------------------


class ItemSocket(BaseModel):
    """A single socket on an item."""

    group: int = 0
    colour: str = ""  # R, G, B, W, A (abyss)


class ItemProperty(BaseModel):
    """A display property on an item (e.g., 'Physical Damage: 50-80')."""

    name: str = ""
    values: list[list[str | int]] = Field(default_factory=list)


class SocketedGem(BaseModel):
    """A gem socketed inside an item, from the PoE API get-items response."""

    name: str = ""
    type_line: str = Field(default="", alias="typeLine")
    support: bool = False  # True for support gems
    socket: int = 0  # Index into the parent item's sockets array
    colour: str = ""  # S for skill, D for support
    properties: list[ItemProperty] = Field(default_factory=list)
    icon: str = ""

    model_config = {"populate_by_name": True}

    @property
    def gem_level(self) -> int:
        for prop in self.properties:
            if prop.name == "Level":
                try:
                    return int(str(prop.values[0][0]).replace(" (Max)", ""))
                except (IndexError, ValueError):
                    pass
        return 20

    @property
    def gem_quality(self) -> int:
        for prop in self.properties:
            if prop.name == "Quality":
                try:
                    return int(str(prop.values[0][0]).strip("+%"))
                except (IndexError, ValueError):
                    pass
        return 0


class EquippedItem(BaseModel):
    """An item equipped on a character, from the PoE API."""

    id: str = ""
    name: str = ""
    type_line: str = Field(default="", alias="typeLine")
    base_type: str = Field(default="", alias="baseType")
    inventory_id: str = Field(default="", alias="inventoryId")
    ilvl: int = 0
    rarity: int = 0  # 0=normal, 1=magic, 2=rare, 3=unique

    @field_validator("rarity", mode="before")
    @classmethod
    def _coerce_rarity(cls, v: object) -> int:
        if isinstance(v, str):
            return {"Normal": 0, "Magic": 1, "Rare": 2, "Unique": 3}.get(v, 0)
        return int(v) if v is not None else 0
    x: int = 0  # Position (used for flask slot numbering)
    icon: str = ""
    frame_type: int = Field(default=0, alias="frameType")

    # Mods
    implicit_mods: list[str] = Field(default_factory=list, alias="implicitMods")
    explicit_mods: list[str] = Field(default_factory=list, alias="explicitMods")
    crafted_mods: list[str] = Field(default_factory=list, alias="craftedMods")
    enchant_mods: list[str] = Field(default_factory=list, alias="enchantMods")
    fractured_mods: list[str] = Field(default_factory=list, alias="fracturedMods")

    # Sockets & socketed gems
    sockets: list[ItemSocket] = Field(default_factory=list)
    socketed_items: list[SocketedGem] = Field(default_factory=list, alias="socketedItems")

    # Properties (display)
    properties: list[ItemProperty] = Field(default_factory=list)

    # Requirements
    requirements: list[ItemProperty] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @property
    def rarity_name(self) -> str:
        return {0: "NORMAL", 1: "MAGIC", 2: "RARE", 3: "UNIQUE"}.get(self.rarity, "UNKNOWN")

    @property
    def all_mods(self) -> list[str]:
        return (
            self.implicit_mods
            + self.explicit_mods
            + self.crafted_mods
            + self.enchant_mods
            + self.fractured_mods
        )

    @property
    def slot(self) -> str:
        """Map API inventory_id to our canonical slot names."""
        mapping = {
            "Weapon": "Weapon 1",
            "Weapon2": "Weapon 1 Swap",
            "Offhand": "Weapon 2",
            "Offhand2": "Weapon 2 Swap",
            "Helm": "Helmet",
            "BodyArmour": "Body Armour",
            "Gloves": "Gloves",
            "Boots": "Boots",
            "Amulet": "Amulet",
            "Ring": "Ring 1",
            "Ring2": "Ring 2",
            "Belt": "Belt",
        }
        if self.inventory_id == "Flask":
            return f"Flask {self.x + 1}"
        return mapping.get(self.inventory_id, self.inventory_id)


# ---------------------------------------------------------------------------
# Passive tree (from character detail)
# ---------------------------------------------------------------------------


class PassiveData(BaseModel):
    """Passive tree allocation from the character API."""

    hashes: list[int] = Field(default_factory=list)
    hashes_ex: list[int] = Field(default_factory=list)  # extended (cluster jewels etc.)


# ---------------------------------------------------------------------------
# Full character detail
# ---------------------------------------------------------------------------


class CharacterDetail(BaseModel):
    """Full character data from GET /api/character/{name}."""

    id: str = ""
    name: str = ""
    class_name: str = Field(default="", alias="class")
    level: int = 0
    league: str = ""
    experience: int = 0
    equipment: list[EquippedItem] = Field(default_factory=list)
    passives: PassiveData = Field(default_factory=PassiveData)

    model_config = {"populate_by_name": True}

    def items_by_slot(self) -> dict[str, EquippedItem]:
        return {item.slot: item for item in self.equipment}

    def summary(self) -> str:
        return (
            f"Level {self.level} {self.class_name} "
            f"| Items: {len(self.equipment)} "
            f"| Passives: {len(self.passives.hashes)}"
        )


# ---------------------------------------------------------------------------
# League
# ---------------------------------------------------------------------------


class League(BaseModel):
    """A PoE league."""

    id: str = ""
    text: str = ""
    realm: str = "pc"
    start_at: str = Field(default="", alias="startAt")
    end_at: str | None = Field(default=None, alias="endAt")

    model_config = {"populate_by_name": True}
