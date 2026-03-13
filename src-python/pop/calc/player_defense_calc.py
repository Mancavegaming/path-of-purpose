"""
Player defence calculations for PoB-like defence display.

Calculates:
- Life (base from level + flat + increased%)
- Armour, Evasion, Energy Shield (flat + increased%)
- Block / Spell Block chance
- Elemental resistances (capped at 75%)
- Chaos resistance
- Physical damage reduction from endurance charges
- Spell suppression
"""

from __future__ import annotations

from pop.calc.mod_parser import ParsedMods
from pop.calc.models import CalcConfig, DefenceResult

# Base life per class (PoE1 values — Marauder/Templar highest, Shadow/Ranger lowest)
# Simplified: use average base of 12 life per level + 50 base
_BASE_LIFE_PER_LEVEL = 12.0
_BASE_LIFE_START = 50.0


def calc_player_defences(
    parsed: ParsedMods,
    config: CalcConfig,
) -> DefenceResult:
    """Calculate player defence stats from collected modifiers.

    Args:
        parsed: Aggregated ParsedMods from all sources (items, tree, gems).
        config: Calculator configuration.

    Returns:
        DefenceResult with calculated defence values.
    """
    result = DefenceResult()

    # --- Life ---
    # Base life from level (approximate: 50 + 12 * level)
    base_life = _BASE_LIFE_START + _BASE_LIFE_PER_LEVEL * config.enemy_level
    # Use a reasonable player level estimate (typically ~90 for endgame)
    # config.enemy_level is the enemy, but we use it as a proxy for player level
    flat_life = parsed.flat_life
    total_base_life = base_life + flat_life
    inc_life = parsed.increased_life
    result.life = round(total_base_life * (1.0 + inc_life / 100.0))

    # --- Energy Shield ---
    flat_es = parsed.flat_energy_shield
    inc_es = parsed.increased_energy_shield
    result.energy_shield = round(flat_es * (1.0 + inc_es / 100.0))

    # --- Armour ---
    flat_armour = parsed.flat_armour
    inc_armour = parsed.increased_armour
    result.armour = round(flat_armour * (1.0 + inc_armour / 100.0))

    # --- Evasion ---
    flat_evasion = parsed.flat_evasion
    inc_evasion = parsed.increased_evasion
    result.evasion = round(flat_evasion * (1.0 + inc_evasion / 100.0))

    # --- Block ---
    result.block_chance = min(
        float(parsed.special_flags.get("block_chance", 0.0)), 75.0,
    )
    result.spell_block_chance = min(
        float(parsed.special_flags.get("spell_block_chance", 0.0)), 75.0,
    )

    # --- Spell suppression ---
    result.spell_suppression = min(parsed.spell_suppression, 100.0)

    # --- Physical damage reduction from endurance charges ---
    endurance_phys_red = 0.0
    if config.use_endurance_charges and config.endurance_charges > 0:
        endurance_phys_red = config.endurance_charges * 4.0
    result.phys_damage_reduction = endurance_phys_red

    # --- Resistances ---
    all_ele = parsed.all_elemental_resistance
    endurance_ele_resist = 0.0
    if config.use_endurance_charges and config.endurance_charges > 0:
        endurance_ele_resist = config.endurance_charges * 4.0

    fire_total = parsed.fire_resistance + all_ele + endurance_ele_resist
    cold_total = parsed.cold_resistance + all_ele + endurance_ele_resist
    light_total = parsed.lightning_resistance + all_ele + endurance_ele_resist
    chaos_total = parsed.chaos_resistance

    # Cap at 75% (default cap, keystones can modify but we don't track that yet)
    result.elemental_resistances = {
        "fire": min(fire_total, 75.0),
        "cold": min(cold_total, 75.0),
        "lightning": min(light_total, 75.0),
    }
    result.chaos_resistance = min(chaos_total, 75.0)

    return result


def calc_phys_reduction_from_armour(armour: float, hit_damage: float) -> float:
    """Calculate physical damage reduction % from armour.

    PoE formula: reduction = armour / (armour + 5 * damage)
    Capped at 90%.
    """
    if armour <= 0 or hit_damage <= 0:
        return 0.0
    reduction = armour / (armour + 5.0 * hit_damage)
    return min(reduction * 100.0, 90.0)


def calc_evasion_chance(evasion: float, accuracy: float) -> float:
    """Calculate chance to evade an attack.

    PoE formula: evade_chance = 1 - accuracy / (accuracy + (evasion/4)^0.8)
    Clamped 0-95%.
    """
    if evasion <= 0 or accuracy <= 0:
        return 0.0
    evasion_term = (evasion / 4.0) ** 0.8
    hit_chance = accuracy / (accuracy + evasion_term)
    evade_chance = 1.0 - hit_chance
    return max(0.0, min(95.0, evade_chance * 100.0))
