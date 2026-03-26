"""Filter configuration models for loot filter generation."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Strictness(str, Enum):
    LEVELING = "leveling"
    MAPPING = "mapping"
    ENDGAME = "endgame"
    ULTRA_STRICT = "ultra_strict"


class CurrencyTierConfig(BaseModel):
    """Config for a single currency tier."""

    show: bool = True
    sound: int = 0         # 0 = no sound, 1-16 = built-in PoE sounds
    volume: int = 300      # 0-300
    beam: str = ""         # "Red", "Yellow", etc. or "" for none
    icon: str = ""         # "0 Red Star", "1 Yellow Circle", etc. or ""
    font_size: int = 38
    text_color: str = ""   # PoE format "R G B", empty = no SetTextColor
    bg_color: str = ""     # PoE format "R G B A", empty = no SetBackgroundColor
    border_color: str = "" # PoE format "R G B", empty = no SetBorderColor


class CurrencyConfig(BaseModel):
    """Granular currency tier settings."""

    tier1: CurrencyTierConfig = Field(
        default_factory=lambda: CurrencyTierConfig(
            show=True, sound=1, volume=300, beam="Red",
            icon="0 Red Star", font_size=45,
            text_color="255 0 0", bg_color="255 255 255 255", border_color="255 0 0",
        ))
    tier2: CurrencyTierConfig = Field(
        default_factory=lambda: CurrencyTierConfig(
            show=True, sound=2, volume=300, beam="Yellow",
            icon="1 Yellow Circle", font_size=38,
            text_color="255 170 0", bg_color="0 0 0 220", border_color="255 170 0",
        ))
    tier3: CurrencyTierConfig = Field(
        default_factory=lambda: CurrencyTierConfig(
            show=True, sound=0, beam="", font_size=32,
            text_color="200 200 100", bg_color="0 0 0 200", border_color="200 200 100",
        ))
    tier4: CurrencyTierConfig = Field(
        default_factory=lambda: CurrencyTierConfig(
            show=True, sound=0, font_size=26,
            text_color="170 158 130",
        ))
    tier5: CurrencyTierConfig = Field(
        default_factory=lambda: CurrencyTierConfig(
            show=False, sound=0, font_size=20,
            text_color="120 120 120",
        ))
    show_essences: bool = True
    show_fossils: bool = True
    show_catalysts: bool = True
    show_oils: bool = True
    show_delirium_orbs: bool = True
    show_fragments: bool = True


class EquipmentConfig(BaseModel):
    """Equipment display settings."""

    show_rare_jewellery: bool = True
    rare_jewellery_ilvl: int = 75
    show_rare_weapons: bool = True
    rare_weapon_ilvl: int = 82
    show_six_links: bool = True
    six_link_sound: int = 1
    six_link_beam: str = "Red"
    show_five_links: bool = True
    show_rgb_items: bool = False


class MapConfig(BaseModel):
    """Map display settings."""

    min_tier: int = 1         # 1 = show all, 11 = T11+, 14 = T14+, 16 = T16 only
    show_unique_maps: bool = True
    sound: int = 4
    beam: str = "White"


class GemConfig(BaseModel):
    """Gem display settings."""

    min_quality: int = 0      # 0 = all, 10 = 10%+, 15 = 15%+, 20 = 20 only
    min_level: int = 1        # 1 = all, 19 = 19+, 20 = 20+


class FlaskConfig(BaseModel):
    """Flask display settings."""

    show_utility: bool = True
    show_life_mana: bool = False


class SoundConfig(BaseModel):
    """Sound assignments for non-currency categories."""

    unique_drop: int = 3
    unique_volume: int = 200
    map_drop: int = 4
    map_volume: int = 200
    build_gear: int = 6
    build_gear_volume: int = 200


class BuildTailoredConfig(BaseModel):
    """Build-specific filter options (only used when enabled)."""

    enabled: bool = False
    highlight_weapon_bases: bool = True
    highlight_build_gems: bool = True
    highlight_resist_fillers: bool = True
    highlight_cluster_jewels: bool = True


class HotItemsConfig(BaseModel):
    """Hot items from poe.ninja, pre-categorized by price tier."""

    enabled: bool = False
    tier1: list[dict] = Field(default_factory=list)  # 10+ div, guaranteed
    tier2: list[dict] = Field(default_factory=list)  # 1-10 div, guaranteed
    tier3: list[dict] = Field(default_factory=list)  # 50c+, no uniques
    tier4: list[dict] = Field(default_factory=list)  # price-check: mixed unique bases


class FilterConfig(BaseModel):
    """Complete configuration for filter generation."""

    strictness: Strictness = Strictness.MAPPING
    currency: CurrencyConfig = Field(default_factory=CurrencyConfig)
    equipment: EquipmentConfig = Field(default_factory=EquipmentConfig)
    maps: MapConfig = Field(default_factory=MapConfig)
    gems: GemConfig = Field(default_factory=GemConfig)
    flasks: FlaskConfig = Field(default_factory=FlaskConfig)
    sounds: SoundConfig = Field(default_factory=SoundConfig)
    build_tailored: BuildTailoredConfig = Field(default_factory=BuildTailoredConfig)
    hot_items: HotItemsConfig = Field(default_factory=HotItemsConfig)
    filter_name: str = "PathOfPurpose"
