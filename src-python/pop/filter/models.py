"""Filter configuration models for loot filter generation."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Strictness(str, Enum):
    LEVELING = "leveling"
    MAPPING = "mapping"
    ENDGAME = "endgame"
    ULTRA_STRICT = "ultra_strict"


class FilterTheme(BaseModel):
    """Visual customization for the filter."""

    # RGBA color strings: "R G B" or "R G B A"
    currency_high_text: str = "255 0 0"
    currency_high_bg: str = "255 255 255 255"
    currency_high_border: str = "255 0 0"
    currency_mid_text: str = "255 170 0"
    currency_mid_bg: str = "0 0 0 220"
    currency_mid_border: str = "255 170 0"
    currency_low_text: str = "170 158 130"
    build_gear_text: str = "0 255 0"
    build_gear_bg: str = "0 0 0 220"
    build_gear_border: str = "0 255 0"
    resist_filler_text: str = "100 200 255"
    resist_filler_border: str = "100 200 255"
    gem_text: str = "27 162 155"
    gem_border: str = "27 162 155"
    unique_text: str = "175 96 37"
    unique_border: str = "175 96 37"
    map_text: str = "240 240 240"
    map_border: str = "200 200 200"
    font_size_high: int = 45
    font_size_medium: int = 38
    font_size_low: int = 32
    font_size_tiny: int = 26


class SoundConfig(BaseModel):
    """Sound alert assignments per category (PoE built-in 1-16)."""

    currency_high: int = 1       # Mirror, Divine, Exalted
    currency_mid: int = 2        # Chaos, Vaal, etc.
    build_gear: int = 6          # Build-specific base drops
    unique_drop: int = 3         # Unique items
    map_drop: int = 4            # Map drops
    gem_drop: int = 0            # 0 = no sound
    custom_sound_path: str = ""  # Optional .mp3/.wav path


class FilterConfig(BaseModel):
    """Complete configuration for filter generation."""

    strictness: Strictness = Strictness.MAPPING
    theme: FilterTheme = Field(default_factory=FilterTheme)
    sounds: SoundConfig = Field(default_factory=SoundConfig)
    show_resist_fillers: bool = True
    show_cluster_jewels: bool = True
    show_leveling_gems: bool = True
    filter_name: str = "PathOfPurpose"
