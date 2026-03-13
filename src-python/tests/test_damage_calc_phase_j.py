"""
Phase J tests: Enemy map mods, Gem quality bonuses, Awakened support variants.

These tests validate 3 additional PoB-alignment features.
"""

from __future__ import annotations

import pytest

from pop.calc.gem_data import get_support_effect
from pop.calc.gem_quality import QualityBonus, apply_quality_bonus, get_quality_bonus
from pop.calc.map_mods import MapMod, apply_map_mods, get_map_mod, list_map_mods
from pop.calc.mod_parser import ParsedMods
from pop.calc.models import CalcConfig, DamageType


# ===================================================================
# Feature: Enemy Map Mods
# ===================================================================


class TestMapModDatabase:
    """Test map mod preset database."""

    def test_elemental_resist_30(self):
        mod = get_map_mod("monsters_resist_elemental_30")
        assert mod is not None
        assert mod.enemy_all_resist_bonus == 30.0

    def test_fire_resist_40(self):
        mod = get_map_mod("monsters_resist_fire_40")
        assert mod is not None
        assert mod.enemy_resist_bonus[DamageType.FIRE] == 40.0

    def test_less_damage_12(self):
        mod = get_map_mod("players_deal_less_damage_12")
        assert mod is not None
        assert mod.player_less_damage == 12.0

    def test_hexproof(self):
        mod = get_map_mod("monsters_hexproof")
        assert mod is not None
        assert mod.enemy_immune_to_curses is True

    def test_unknown_returns_none(self):
        assert get_map_mod("nonexistent") is None

    def test_list_map_mods(self):
        mods = list_map_mods()
        assert len(mods) >= 10
        assert "monsters_resist_elemental_30" in mods


class TestApplyMapMods:
    """Test applying map mods to CalcConfig."""

    def test_apply_elemental_resist(self):
        config = CalcConfig()
        warnings, less_dmg = apply_map_mods(config, ["monsters_resist_elemental_30"])
        assert len(warnings) == 0
        assert config.enemy_fire_resist == 30.0
        assert config.enemy_cold_resist == 30.0
        assert config.enemy_lightning_resist == 30.0

    def test_apply_single_resist(self):
        config = CalcConfig()
        apply_map_mods(config, ["monsters_resist_fire_40"])
        assert config.enemy_fire_resist == 40.0
        assert config.enemy_cold_resist == 0.0

    def test_apply_hexproof_disables_curses(self):
        config = CalcConfig(use_curses=True)
        apply_map_mods(config, ["monsters_hexproof"])
        assert config.use_curses is False

    def test_apply_less_damage(self):
        config = CalcConfig()
        warnings, less_dmg = apply_map_mods(config, ["players_deal_less_damage_12"])
        assert less_dmg == pytest.approx(12.0)

    def test_apply_multiple_mods(self):
        config = CalcConfig()
        warnings, less_dmg = apply_map_mods(
            config,
            ["monsters_resist_elemental_30", "players_deal_less_damage_15"],
        )
        assert config.enemy_fire_resist == 30.0
        assert less_dmg == pytest.approx(15.0)

    def test_apply_unknown_mod_warns(self):
        config = CalcConfig()
        warnings, _ = apply_map_mods(config, ["nonexistent_mod"])
        assert len(warnings) == 1
        assert "Unknown map mod" in warnings[0]

    def test_apply_curse_effectiveness_reduction(self):
        config = CalcConfig(curse_effectiveness=1.0)
        apply_map_mods(config, ["less_curse_effect_60"])
        # 1.0 * (1 - 0.6) = 0.4
        assert config.curse_effectiveness == pytest.approx(0.4)

    def test_apply_phys_reduction(self):
        config = CalcConfig()
        apply_map_mods(config, ["monsters_phys_reduction_20"])
        assert config.enemy_phys_reduction == 20.0

    def test_stacking_resist_mods(self):
        """Multiple resist mods should stack."""
        config = CalcConfig(enemy_fire_resist=40.0)  # boss fire resist
        apply_map_mods(config, ["monsters_resist_elemental_30"])
        assert config.enemy_fire_resist == 70.0  # 40 + 30

    def test_map_mods_with_boss(self):
        """Map mods should stack with boss resists."""
        config = CalcConfig(
            enemy_fire_resist=40.0,
            enemy_cold_resist=40.0,
            enemy_lightning_resist=40.0,
        )
        apply_map_mods(config, ["monsters_resist_elemental_40"])
        assert config.enemy_fire_resist == 80.0


# ===================================================================
# Feature: Gem Quality Bonuses
# ===================================================================


class TestGemQualityDatabase:
    """Test quality bonus database."""

    def test_cyclone_quality(self):
        bonus = get_quality_bonus("Cyclone")
        assert bonus is not None
        assert bonus.increased_attack_speed == 0.5

    def test_fireball_quality(self):
        bonus = get_quality_bonus("Fireball")
        assert bonus is not None
        assert bonus.increased_damage == 1.0
        assert DamageType.FIRE in bonus.increased_damage_types

    def test_brutality_support_quality(self):
        bonus = get_quality_bonus("Brutality Support")
        assert bonus is not None
        assert bonus.increased_damage == 0.5

    def test_fire_pen_support_quality(self):
        bonus = get_quality_bonus("Fire Penetration Support")
        assert bonus is not None
        assert bonus.penetration[DamageType.FIRE] == 0.5

    def test_awakened_variant_quality(self):
        bonus = get_quality_bonus("Awakened Brutality Support")
        assert bonus is not None
        assert bonus.increased_damage == 0.5

    def test_unknown_gem_returns_none(self):
        assert get_quality_bonus("Nonexistent Gem") is None

    def test_multistrike_quality(self):
        bonus = get_quality_bonus("Multistrike Support")
        assert bonus is not None
        assert bonus.increased_attack_speed == 0.5


class TestApplyQualityBonus:
    """Test applying quality bonuses to ParsedMods."""

    def test_apply_20q_cyclone(self):
        """20% quality Cyclone → +10% increased attack speed."""
        out = ParsedMods()
        apply_quality_bonus("Cyclone", 20, out)
        assert out.increased_attack_speed == pytest.approx(10.0)

    def test_apply_20q_fireball(self):
        """20% quality Fireball → +20% increased fire damage."""
        out = ParsedMods()
        apply_quality_bonus("Fireball", 20, out)
        assert len(out.increased) == 1
        mod = out.increased[0]
        assert mod.value == pytest.approx(20.0)
        assert DamageType.FIRE in mod.damage_types
        assert "quality:" in mod.source

    def test_apply_0_quality_no_effect(self):
        out = ParsedMods()
        apply_quality_bonus("Cyclone", 0, out)
        assert out.increased_attack_speed == 0.0

    def test_apply_23q_anomalous(self):
        """23% quality (anomalous/divergent) should scale linearly."""
        out = ParsedMods()
        apply_quality_bonus("Cyclone", 23, out)
        # 23 * 0.5 = 11.5
        assert out.increased_attack_speed == pytest.approx(11.5)

    def test_apply_fire_pen_quality(self):
        """20% quality Fire Pen → +10% fire penetration."""
        out = ParsedMods()
        apply_quality_bonus("Fire Penetration Support", 20, out)
        assert out.penetration.get(DamageType.FIRE, 0.0) == pytest.approx(10.0)

    def test_apply_unknown_gem_no_effect(self):
        out = ParsedMods()
        apply_quality_bonus("Unknown Gem", 20, out)
        assert out.increased_attack_speed == 0.0
        assert len(out.increased) == 0

    def test_apply_dot_quality(self):
        """20% quality Essence Drain → +10% increased DoT."""
        out = ParsedMods()
        apply_quality_bonus("Essence Drain", 20, out)
        assert len(out.increased_dot) == 1
        assert out.increased_dot[0].value == pytest.approx(10.0)

    def test_apply_crit_quality(self):
        """20% quality Power Siphon → +10% increased crit."""
        out = ParsedMods()
        apply_quality_bonus("Power Siphon", 20, out)
        assert out.increased_crit == pytest.approx(10.0)


# ===================================================================
# Feature: Awakened Support Variants
# ===================================================================


class TestAwakenedSupportVariants:
    """Test Awakened support gem resolution and higher values."""

    def test_awakened_melee_phys_exists(self):
        effect = get_support_effect("Awakened Melee Physical Damage Support")
        assert effect is not None
        # Awakened version has higher value
        more_mods = [m for m in effect.modifiers if m.mod_type == "more"]
        assert len(more_mods) >= 1

    def test_awakened_higher_than_base(self):
        """Awakened supports should have higher values than base."""
        base = get_support_effect("Melee Physical Damage Support")
        awakened = get_support_effect("Awakened Melee Physical Damage Support")
        assert base is not None
        assert awakened is not None
        base_more = [m for m in base.modifiers if m.mod_type == "more"][0].value
        awk_more = [m for m in awakened.modifiers if m.mod_type == "more"][0].value
        assert awk_more > base_more

    def test_awakened_brutality_higher(self):
        base = get_support_effect("Brutality Support")
        awakened = get_support_effect("Awakened Brutality Support")
        assert base is not None
        assert awakened is not None
        base_more = [m for m in base.modifiers if m.mod_type == "more"][0].value
        awk_more = [m for m in awakened.modifiers if m.mod_type == "more"][0].value
        assert awk_more > base_more

    def test_awakened_fallback_to_base(self):
        """Unknown Awakened gem should fall back to base version."""
        # "Awakened Faster Attacks Support" isn't in DB but
        # "Faster Attacks Support" is
        base = get_support_effect("Faster Attacks Support")
        fallback = get_support_effect("Awakened Faster Attacks Support")
        # Should resolve to the base version
        assert base is not None
        assert fallback is not None
        assert fallback.name == base.name

    def test_awakened_chain_in_db(self):
        effect = get_support_effect("Awakened Chain Support")
        assert effect is not None

    def test_awakened_fork_in_db(self):
        effect = get_support_effect("Awakened Fork Support")
        assert effect is not None

    def test_awakened_added_fire_in_db(self):
        effect = get_support_effect("Awakened Added Fire Damage Support")
        assert effect is not None

    def test_awakened_quality_bonus(self):
        """Awakened gems should also have quality bonuses."""
        bonus = get_quality_bonus("Awakened Melee Physical Damage Support")
        assert bonus is not None


# ===================================================================
# Integration Tests
# ===================================================================


class TestPhaseJIntegration:
    """Integration tests for map mods, quality, and awakened gems."""

    def test_map_mods_affect_dps_via_resist(self):
        """Map mods adding resist should reduce damage dealt."""
        from pop.calc.defense_calc import calc_mitigation_multi

        config_base = CalcConfig()
        config_map = CalcConfig(enemy_fire_resist=30.0)

        mit_base = calc_mitigation_multi(DamageType.FIRE, config_base)
        mit_map = calc_mitigation_multi(DamageType.FIRE, config_map)

        # Higher resist → lower multiplier
        assert mit_map < mit_base

    def test_quality_stacks_with_support_mods(self):
        """Quality bonus should stack with support gem base modifiers."""
        effect = get_support_effect("Brutality Support")
        assert effect is not None

        out = ParsedMods()
        # Apply base support effect
        for mod in effect.modifiers:
            if mod.mod_type == "more":
                out.more.append(mod)
            else:
                out.increased.append(mod)

        # Apply quality bonus
        apply_quality_bonus("Brutality Support", 20, out)

        # Should have more mods from base AND increased from quality
        assert len(out.more) >= 1
        assert len(out.increased) >= 1
        quality_mod = out.increased[0]
        assert quality_mod.value == pytest.approx(10.0)  # 20 * 0.5

    def test_hexproof_and_less_damage_combined(self):
        """Hexproof + less damage should stack."""
        config = CalcConfig(use_curses=True)
        warnings, less_dmg = apply_map_mods(
            config,
            ["monsters_hexproof", "players_deal_less_damage_12"],
        )
        assert config.use_curses is False
        assert less_dmg == pytest.approx(12.0)
        assert len(warnings) == 0

    def test_all_three_features_coexist(self):
        """Map mods, quality, and awakened should all work together."""
        # Map mods
        config = CalcConfig()
        apply_map_mods(config, ["monsters_resist_elemental_30"])
        assert config.enemy_fire_resist == 30.0

        # Quality bonus
        out = ParsedMods()
        apply_quality_bonus("Awakened Brutality Support", 20, out)
        assert len(out.increased) >= 1

        # Awakened support
        effect = get_support_effect("Awakened Brutality Support")
        assert effect is not None
