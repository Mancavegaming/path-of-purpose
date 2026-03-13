"""
Map PoB BuildConfig entries to CalcConfig for the damage calculator.

PoB stores config as a flat dict of string key-value pairs. This module
resolves them into typed CalcConfig fields.
"""

from __future__ import annotations

from pop.build_parser.models import BuildConfig
from pop.calc.models import BOSS_PRESETS, CalcConfig, DamageType


# PoB config key → CalcConfig field mapping
_BOOL_KEYS: dict[str, str] = {
    "enemyIsBoss": "enemy_is_boss",
    "usePowerCharges": "use_power_charges",
    "useFrenzyCharges": "use_frenzy_charges",
    "buffOnslaught": "onslaught",
    "useCurses": "use_curses",
    "useFlasks": "use_flasks",
    "useEnduranceCharges": "use_endurance_charges",
    "enemyCondition_Shocked": "enemy_is_shocked",
    "enemyCondition_Chilled": "enemy_is_chilled",
    "enemyCondition_Intimidated": "enemy_is_intimidated",
    "enemyCondition_Unnerved": "enemy_is_unnerved",
}

_INT_KEYS: dict[str, str] = {
    "enemyLevel": "enemy_level",
    "powerCharges": "power_charges",
    "frenzyCharges": "frenzy_charges",
    "enduranceCharges": "endurance_charges",
    "witherStacks": "wither_stacks",
}

_FLOAT_KEYS: dict[str, str] = {
    "enemyFireResist": "enemy_fire_resist",
    "enemyColdResist": "enemy_cold_resist",
    "enemyLightningResist": "enemy_lightning_resist",
    "enemyChaosResist": "enemy_chaos_resist",
    "enemyPhysicalDamageReduction": "enemy_phys_reduction",
    "enemyArmour": "enemy_armour",
    "enemyEvasion": "enemy_evasion",
    "shockValue": "shock_value",
}


def read_config(build_config: BuildConfig, tree_version: str = "") -> CalcConfig:
    """Convert PoB BuildConfig entries into a CalcConfig.

    Args:
        build_config: The BuildConfig from the parsed PoB build.
        tree_version: Passive tree version string (e.g. "3.25" or "poe2").
    """
    cfg = CalcConfig()
    entries = build_config.entries

    for pob_key, field_name in _BOOL_KEYS.items():
        val = entries.get(pob_key, "").lower()
        if val in ("true", "1", "yes"):
            setattr(cfg, field_name, True)

    for pob_key, field_name in _INT_KEYS.items():
        val = entries.get(pob_key, "")
        if val.isdigit():
            setattr(cfg, field_name, int(val))

    for pob_key, field_name in _FLOAT_KEYS.items():
        val = entries.get(pob_key, "")
        try:
            setattr(cfg, field_name, float(val))
        except (ValueError, TypeError):
            pass

    # Detect PoE 2 from tree version
    if tree_version:
        ver_lower = tree_version.lower()
        if "poe2" in ver_lower or ver_lower.startswith("2."):
            cfg.is_poe2 = True

    # Default shock to 15% if shocked but no value specified
    if cfg.enemy_is_shocked and cfg.shock_value == 0.0:
        cfg.shock_value = 15.0

    # Clamp wither stacks 0-15
    cfg.wither_stacks = max(0, min(cfg.wither_stacks, 15))

    # Apply boss resist presets if boss mode is on and resists are all zero
    if cfg.enemy_is_boss:
        # Bosses have 66% less curse effect (Shaper-tier)
        cfg.curse_effectiveness = 0.34
        all_zero = all(
            cfg.enemy_resist_for(dt) == 0.0
            for dt in DamageType
        )
        if all_zero:
            preset = BOSS_PRESETS["shaper"]
            cfg.enemy_fire_resist = preset[DamageType.FIRE]
            cfg.enemy_cold_resist = preset[DamageType.COLD]
            cfg.enemy_lightning_resist = preset[DamageType.LIGHTNING]
            cfg.enemy_chaos_resist = preset[DamageType.CHAOS]

    return cfg
