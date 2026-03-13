"""
Enemy map modifier presets for the damage calculator.

Map mods affect enemy stats and player effectiveness. Common DPS-relevant
map mods are captured here as presets that modify CalcConfig.

PoB handles these via the "Map Modifiers" config section.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pop.calc.models import CalcConfig, DamageType


@dataclass
class MapMod:
    """A single map modifier affecting enemy or player stats."""

    name: str
    description: str = ""

    # Enemy resistance additions (flat %)
    enemy_resist_bonus: dict[DamageType, float] = field(default_factory=dict)
    enemy_all_resist_bonus: float = 0.0  # added to all elemental resists

    # Player damage reduction (% less)
    player_less_damage: float = 0.0  # e.g. "Players deal 20% less Damage"

    # Enemy extra damage (informational — doesn't affect DPS calc)
    enemy_extra_damage: float = 0.0

    # Enemy extra life (informational — affects time-to-kill)
    enemy_extra_life: float = 0.0

    # Player curse reduction (additional penalty to curse effect)
    player_curse_effectiveness_reduction: float = 0.0

    # Enemy cannot be affected by certain debuffs
    enemy_immune_to_curses: bool = False
    enemy_cannot_be_slowed: bool = False

    # Monster extra evasion (affects accuracy)
    enemy_extra_evasion: float = 0.0

    # Player penetration reduction
    less_penetration: float = 0.0


# ===================================================================
# Map mod presets — common DPS-impacting mods
# ===================================================================

_MAP_MODS: dict[str, MapMod] = {}


def _mm(name: str, **kw: object) -> None:
    _MAP_MODS[name] = MapMod(name=name, **kw)  # type: ignore[arg-type]


# Elemental resist mods
_mm("monsters_resist_elemental_30",
    description="Monsters have +30% to Elemental Resistances",
    enemy_all_resist_bonus=30.0)

_mm("monsters_resist_elemental_40",
    description="Monsters have +40% to Elemental Resistances",
    enemy_all_resist_bonus=40.0)

_mm("monsters_resist_fire_40",
    description="Monsters have +40% to Fire Resistance",
    enemy_resist_bonus={DamageType.FIRE: 40.0})

_mm("monsters_resist_cold_40",
    description="Monsters have +40% to Cold Resistance",
    enemy_resist_bonus={DamageType.COLD: 40.0})

_mm("monsters_resist_lightning_40",
    description="Monsters have +40% to Lightning Resistance",
    enemy_resist_bonus={DamageType.LIGHTNING: 40.0})

_mm("monsters_resist_chaos_25",
    description="Monsters have +25% to Chaos Resistance",
    enemy_resist_bonus={DamageType.CHAOS: 25.0})

# Player damage reduction mods
_mm("players_deal_less_damage_12",
    description="Players deal 12% less Damage",
    player_less_damage=12.0)

_mm("players_deal_less_damage_15",
    description="Players deal 15% less Damage",
    player_less_damage=15.0)

# Curse immunity
_mm("monsters_hexproof",
    description="Monsters are Hexproof",
    enemy_immune_to_curses=True)

# Curse effectiveness reduction
_mm("less_curse_effect_60",
    description="60% less effect of Curses on Monsters",
    player_curse_effectiveness_reduction=60.0)

# Monster extra life
_mm("monsters_extra_life_20",
    description="Monsters have 20% increased Maximum Life",
    enemy_extra_life=20.0)

_mm("monsters_extra_life_40",
    description="Monsters have 40% increased Maximum Life",
    enemy_extra_life=40.0)

# Monster evasion
_mm("monsters_evasion_30",
    description="Monsters have 30% increased Evasion Rating",
    enemy_extra_evasion=30.0)

# Monster physical damage reduction (armour)
_mm("monsters_phys_reduction_20",
    description="Monsters have 20% additional Physical Damage Reduction",
    enemy_resist_bonus={DamageType.PHYSICAL: 20.0})

# Elemental equilibrium / map boss variants
_mm("boss_resist_elemental_extra",
    description="Boss has +20% to Elemental Resistances",
    enemy_all_resist_bonus=20.0)


# ===================================================================
# Public API
# ===================================================================


def get_map_mod(name: str) -> MapMod | None:
    """Look up a map mod preset by name."""
    return _MAP_MODS.get(name)


def list_map_mods() -> list[str]:
    """Return all map mod preset names."""
    return sorted(_MAP_MODS.keys())


def apply_map_mods(
    config: CalcConfig, mod_names: list[str],
) -> tuple[list[str], float]:
    """Apply map modifier presets to a CalcConfig.

    Args:
        config: The CalcConfig to modify in-place.
        mod_names: List of map mod preset names to apply.

    Returns:
        Tuple of (warning strings, total player_less_damage %).
    """
    warnings: list[str] = []
    total_less_damage = 0.0

    for name in mod_names:
        mod = get_map_mod(name)
        if not mod:
            warnings.append(f"Unknown map mod '{name}' — skipped.")
            continue

        # Enemy resist bonuses
        for dtype, val in mod.enemy_resist_bonus.items():
            if dtype == DamageType.FIRE:
                config.enemy_fire_resist += val
            elif dtype == DamageType.COLD:
                config.enemy_cold_resist += val
            elif dtype == DamageType.LIGHTNING:
                config.enemy_lightning_resist += val
            elif dtype == DamageType.CHAOS:
                config.enemy_chaos_resist += val
            elif dtype == DamageType.PHYSICAL:
                config.enemy_phys_reduction += val

        if mod.enemy_all_resist_bonus > 0:
            config.enemy_fire_resist += mod.enemy_all_resist_bonus
            config.enemy_cold_resist += mod.enemy_all_resist_bonus
            config.enemy_lightning_resist += mod.enemy_all_resist_bonus

        # Player less damage — accumulated for engine to apply
        if mod.player_less_damage > 0:
            total_less_damage += mod.player_less_damage

        # Curse immunity → disable curses
        if mod.enemy_immune_to_curses:
            config.use_curses = False

        # Curse effectiveness reduction
        if mod.player_curse_effectiveness_reduction > 0:
            reduction = mod.player_curse_effectiveness_reduction / 100.0
            config.curse_effectiveness *= (1.0 - reduction)

        # Enemy evasion bonus
        if mod.enemy_extra_evasion > 0 and config.enemy_evasion > 0:
            config.enemy_evasion *= (1.0 + mod.enemy_extra_evasion / 100.0)

    return warnings, total_less_damage
