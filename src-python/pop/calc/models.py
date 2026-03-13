"""
Pydantic models for the damage calculation engine.

Covers damage types, modifier classification, stat aggregation,
configuration, and the full calculation result breakdown.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Damage types
# ---------------------------------------------------------------------------


class DamageType(str, Enum):
    PHYSICAL = "physical"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    CHAOS = "chaos"


# Canonical conversion order (PoE conversion chain)
CONVERSION_ORDER: list[DamageType] = [
    DamageType.PHYSICAL,
    DamageType.LIGHTNING,
    DamageType.COLD,
    DamageType.FIRE,
    DamageType.CHAOS,
]


# ---------------------------------------------------------------------------
# Modifier representation
# ---------------------------------------------------------------------------


class ModCategory(str, Enum):
    """Categories for grouping 'increased' modifiers.

    In PoE all 'increased' are additive in a single pool, but we track
    categories for debugging / source attribution.
    """

    GENERIC = "generic"
    TYPE_SPECIFIC = "type"
    SKILL_SPECIFIC = "skill"
    WEAPON_TYPE = "weapon_type"


class Modifier(BaseModel):
    """A single parsed modifier ready for aggregation."""

    stat: str  # canonical name, e.g. "increased_fire_damage"
    value: float
    mod_type: Literal["flat", "increased", "more"] = "increased"
    damage_types: list[DamageType] = Field(default_factory=list)
    category: ModCategory = ModCategory.GENERIC
    source: str = ""  # e.g. "item:Helmet", "gem:Brutality", "tree:12345"


# ---------------------------------------------------------------------------
# Conversion entry
# ---------------------------------------------------------------------------


class ConversionEntry(BaseModel):
    """A single damage conversion: X% of type_from converted to type_to."""

    type_from: DamageType
    type_to: DamageType
    percent: float  # 0-100
    is_gained_as: bool = False  # "gained as extra" doesn't consume original
    source: str = ""


# ---------------------------------------------------------------------------
# Stat pool — all aggregated modifiers from the entire build
# ---------------------------------------------------------------------------


class StatPool(BaseModel):
    """All modifiers collected from every source, ready for computation."""

    # Flat added damage per type (for attacks or spells depending on context)
    flat_added: dict[DamageType, float] = Field(default_factory=dict)

    # All increased% modifiers (additive within the pool)
    # Keyed by the damage types they apply to; empty list = generic (all types)
    increased_mods: list[Modifier] = Field(default_factory=list)

    # Each 'more' multiplier is separate
    more_mods: list[Modifier] = Field(default_factory=list)

    # Conversion entries
    conversions: list[ConversionEntry] = Field(default_factory=list)

    # Crit
    base_crit_chance: float = 5.0  # % from weapon or gem
    increased_crit: float = 0.0  # total increased crit chance %
    crit_multiplier: float = 150.0  # base 150%

    # Speed
    base_speed: float = 1.0  # weapon APS or gem casts/sec
    increased_speed: float = 0.0  # total increased attack/cast speed %
    more_speed: list[float] = Field(default_factory=list)  # each more% speed

    # Penetration per element
    penetration: dict[DamageType, float] = Field(default_factory=dict)

    # Exposure per element (flat resist reduction applied to enemy)
    exposure: dict[DamageType, float] = Field(default_factory=dict)

    # DoT / ailment modifiers
    increased_dot_mods: list[Modifier] = Field(default_factory=list)
    more_dot_mods: list[Modifier] = Field(default_factory=list)
    dot_multi: float = 0.0  # generic "+X% to Damage over Time Multiplier"
    dot_multi_fire: float = 0.0
    dot_multi_phys: float = 0.0
    dot_multi_chaos: float = 0.0

    # Ailment chance (0-100%)
    chance_to_ignite: float = 0.0
    chance_to_bleed: float = 0.0
    chance_to_poison: float = 0.0

    # Ailment duration (increased %)
    increased_ignite_duration: float = 0.0
    increased_bleed_duration: float = 0.0
    increased_poison_duration: float = 0.0

    def total_increased_for_type(self, dtype: DamageType) -> float:
        """Sum all increased% mods applicable to a given damage type."""
        total = 0.0
        for mod in self.increased_mods:
            if not mod.damage_types or dtype in mod.damage_types:
                total += mod.value
        return total

    def total_increased_for_types(self, types: set[DamageType]) -> float:
        """Sum all increased% mods applicable to ANY of the given damage types.

        Used for conversion: when phys converts to fire, both "increased Physical"
        and "increased Fire" apply. A mod matching either type counts once.
        """
        total = 0.0
        for mod in self.increased_mods:
            if not mod.damage_types:
                # Generic — applies to all types
                total += mod.value
            elif set(mod.damage_types) & types:
                # Applies to at least one of the relevant types
                total += mod.value
        return total

    def total_more_for_types(self, types: set[DamageType]) -> float:
        """Compute product of all more multipliers applicable to ANY of the given types."""
        product = 1.0
        for mod in self.more_mods:
            if not mod.damage_types:
                product *= 1.0 + mod.value / 100.0
            elif set(mod.damage_types) & types:
                product *= 1.0 + mod.value / 100.0
        return product

    def total_more_for_type(self, dtype: DamageType) -> float:
        """Compute the product of all more multipliers for a damage type."""
        product = 1.0
        for mod in self.more_mods:
            if not mod.damage_types or dtype in mod.damage_types:
                product *= 1.0 + mod.value / 100.0
        return product


# ---------------------------------------------------------------------------
# Calculation configuration (from PoB config / user settings)
# ---------------------------------------------------------------------------


class CalcConfig(BaseModel):
    """Resolved configuration toggles for the calculation."""

    # Enemy
    enemy_is_boss: bool = False
    enemy_level: int = 84
    enemy_fire_resist: float = 0.0
    enemy_cold_resist: float = 0.0
    enemy_lightning_resist: float = 0.0
    enemy_chaos_resist: float = 0.0
    enemy_phys_reduction: float = 0.0
    enemy_armour: float = 0.0
    enemy_evasion: float = 0.0  # for accuracy formula

    # Charges
    power_charges: int = 0
    frenzy_charges: int = 0
    endurance_charges: int = 0
    use_power_charges: bool = False
    use_frenzy_charges: bool = False
    use_endurance_charges: bool = False

    # Buffs
    onslaught: bool = False

    # Curses
    use_curses: bool = True
    curse_effectiveness: float = 1.0  # reduced for bosses (0.34 Shaper-tier)

    # Enemy conditions / debuffs
    shock_value: float = 0.0  # 0-50% increased damage taken
    enemy_is_shocked: bool = False
    enemy_is_chilled: bool = False
    enemy_is_intimidated: bool = False  # 10% increased attack damage taken
    enemy_is_unnerved: bool = False  # 10% increased spell damage taken
    wither_stacks: int = 0  # 0-15, each stack = 6% increased chaos damage taken

    # Flasks
    use_flasks: bool = False

    # Ascendancy
    ascendancy_class: str = ""

    # DoT
    enemy_is_moving: bool = True  # bleed deals 3x when enemy is moving

    # Map mods (preset names to apply)
    map_mod_names: list[str] = Field(default_factory=list)

    # Game version
    is_poe2: bool = False

    def enemy_resist_for(self, dtype: DamageType) -> float:
        """Get enemy resistance for a damage type."""
        return {
            DamageType.PHYSICAL: self.enemy_phys_reduction,
            DamageType.FIRE: self.enemy_fire_resist,
            DamageType.COLD: self.enemy_cold_resist,
            DamageType.LIGHTNING: self.enemy_lightning_resist,
            DamageType.CHAOS: self.enemy_chaos_resist,
        }.get(dtype, 0.0)


# Boss resistance presets
BOSS_PRESETS: dict[str, dict[DamageType, float]] = {
    "shaper": {
        DamageType.FIRE: 40.0,
        DamageType.COLD: 40.0,
        DamageType.LIGHTNING: 40.0,
        DamageType.CHAOS: 25.0,
        DamageType.PHYSICAL: 0.0,
    },
    "uber": {
        DamageType.FIRE: 50.0,
        DamageType.COLD: 50.0,
        DamageType.LIGHTNING: 50.0,
        DamageType.CHAOS: 30.0,
        DamageType.PHYSICAL: 0.0,
    },
    "normal": {
        DamageType.FIRE: 0.0,
        DamageType.COLD: 0.0,
        DamageType.LIGHTNING: 0.0,
        DamageType.CHAOS: 0.0,
        DamageType.PHYSICAL: 0.0,
    },
}


# ---------------------------------------------------------------------------
# Per-type damage breakdown
# ---------------------------------------------------------------------------


class TypeDamage(BaseModel):
    """Damage for one damage type through the full pipeline."""

    damage_type: DamageType
    base: float = 0.0
    after_flat: float = 0.0
    after_conversion: float = 0.0
    after_increased: float = 0.0
    after_more: float = 0.0
    final_hit: float = 0.0  # before enemy mitigation
    after_mitigation: float = 0.0


# ---------------------------------------------------------------------------
# Source contribution tracking
# ---------------------------------------------------------------------------


class SourceContribution(BaseModel):
    """Attribution of DPS to a specific source."""

    source: str  # "Weapon", "Added Fire Support", "Passive Tree", etc.
    dps_contribution: float = 0.0
    pct_of_total: float = 0.0


# ---------------------------------------------------------------------------
# Player defence result
# ---------------------------------------------------------------------------


class DefenceResult(BaseModel):
    """Player defence stats (armour, evasion, ES, block)."""

    armour: float = 0.0
    evasion: float = 0.0
    energy_shield: float = 0.0
    life: float = 0.0
    block_chance: float = 0.0  # 0-75%
    spell_block_chance: float = 0.0  # 0-75%
    dodge_chance: float = 0.0  # 0-75% (deprecated in 3.16+, but some builds)
    spell_suppression: float = 0.0  # 0-100%
    phys_damage_reduction: float = 0.0  # % from endurance charges + other sources
    elemental_resistances: dict[str, float] = Field(default_factory=dict)  # fire/cold/lightning
    chaos_resistance: float = 0.0


# ---------------------------------------------------------------------------
# Top-level calculation result
# ---------------------------------------------------------------------------


class CalcResult(BaseModel):
    """Full damage calculation result with detailed breakdown."""

    # Summary
    total_dps: float = 0.0
    hit_damage: float = 0.0
    hits_per_second: float = 0.0
    effective_crit_multi: float = 1.0
    crit_chance: float = 0.0
    hit_chance: float = 100.0  # attacks need accuracy; spells always 100%

    # Per-type breakdown
    type_breakdown: list[TypeDamage] = Field(default_factory=list)

    # DoT (Phase D)
    ignite_dps: float = 0.0
    bleed_dps: float = 0.0
    poison_dps: float = 0.0
    total_dot_dps: float = 0.0

    # Impale (Phase H)
    impale_dps: float = 0.0

    # Combined
    combined_dps: float = 0.0  # hit DPS + DoT DPS + impale DPS

    # Skill metadata
    skill_name: str = ""
    is_attack: bool = True
    is_totem: bool = False
    is_trap: bool = False
    is_mine: bool = False
    is_minion: bool = False
    num_totems: int = 0  # active totems (DPS already multiplied)

    # Enemy damage taken multiplier (shock, wither, vulnerability, intimidate, etc.)
    enemy_damage_taken_multi: float = 1.0

    # Warnings for things we couldn't handle or approximated
    warnings: list[str] = Field(default_factory=list)

    # Defence summary
    defence: DefenceResult | None = None

    # Source attribution
    top_sources: list[SourceContribution] = Field(default_factory=list)
