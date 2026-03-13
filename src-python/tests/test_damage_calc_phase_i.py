"""
Phase I tests: Accuracy formula, Aura effect scaling, Endurance charges,
Player defence calculations.

These tests validate the 4 lower-impact PoB-alignment features.
"""

from __future__ import annotations

import pytest

from pop.calc.mod_parser import ParsedMods, parse_mods
from pop.calc.models import CalcConfig, DefenceResult
from pop.calc.player_defense_calc import (
    calc_evasion_chance,
    calc_phys_reduction_from_armour,
    calc_player_defences,
)


# ===================================================================
# Feature 11: Accurate Accuracy Formula
# ===================================================================


class TestAccuracyModParsing:
    """Test accuracy-related mod text parsing."""

    def test_parse_flat_accuracy(self):
        mods = parse_mods(["+300 to Accuracy Rating"])
        assert mods.flat_accuracy == 300.0

    def test_parse_increased_accuracy(self):
        mods = parse_mods(["40% increased Accuracy Rating"])
        assert mods.increased_accuracy == 40.0

    def test_parse_multiple_accuracy_sources(self):
        mods = parse_mods([
            "+200 to Accuracy Rating",
            "+150 to Accuracy Rating",
            "30% increased Accuracy Rating",
        ])
        assert mods.flat_accuracy == 350.0
        assert mods.increased_accuracy == 30.0

    def test_accuracy_merge(self):
        a = ParsedMods()
        a.flat_accuracy = 100.0
        a.increased_accuracy = 20.0
        b = ParsedMods()
        b.flat_accuracy = 200.0
        b.increased_accuracy = 30.0
        a.merge(b)
        assert a.flat_accuracy == 300.0
        assert a.increased_accuracy == 50.0


class TestAccuracyFormula:
    """Test the PoB accuracy → hit chance formula."""

    def test_default_no_evasion_returns_95(self):
        """When enemy evasion is 0, fall back to 95% hit chance."""
        from pop.calc.engine import _calc_hit_chance
        parsed = ParsedMods()
        config = CalcConfig()
        assert _calc_hit_chance(parsed, config) == 0.95

    def test_high_accuracy_high_hit_chance(self):
        """High accuracy vs moderate evasion → high hit chance."""
        from pop.calc.engine import _calc_hit_chance
        parsed = ParsedMods()
        parsed.flat_accuracy = 2000.0  # +2000 flat
        config = CalcConfig(enemy_evasion=1000.0)
        hc = _calc_hit_chance(parsed, config)
        assert hc > 0.90

    def test_low_accuracy_low_hit_chance(self):
        """Low accuracy vs high evasion → lower hit chance."""
        from pop.calc.engine import _calc_hit_chance
        parsed = ParsedMods()
        config = CalcConfig(enemy_evasion=5000.0)
        hc = _calc_hit_chance(parsed, config)
        assert hc < 0.50

    def test_increased_accuracy_boosts_hit(self):
        """Increased accuracy% should improve hit chance."""
        from pop.calc.engine import _calc_hit_chance
        parsed_base = ParsedMods()
        parsed_base.flat_accuracy = 500.0
        parsed_inc = ParsedMods()
        parsed_inc.flat_accuracy = 500.0
        parsed_inc.increased_accuracy = 100.0  # double accuracy
        config = CalcConfig(enemy_evasion=2000.0)
        hc_base = _calc_hit_chance(parsed_base, config)
        hc_inc = _calc_hit_chance(parsed_inc, config)
        assert hc_inc > hc_base

    def test_hit_chance_clamped_min(self):
        """Hit chance should never go below 5%."""
        from pop.calc.engine import _calc_hit_chance
        parsed = ParsedMods()
        config = CalcConfig(enemy_evasion=999999.0)
        hc = _calc_hit_chance(parsed, config)
        assert hc == pytest.approx(0.05, abs=0.01)

    def test_hit_chance_clamped_max(self):
        """Hit chance should never exceed 100%."""
        from pop.calc.engine import _calc_hit_chance
        parsed = ParsedMods()
        parsed.flat_accuracy = 999999.0
        config = CalcConfig(enemy_evasion=1.0)
        hc = _calc_hit_chance(parsed, config)
        assert hc <= 1.0


# ===================================================================
# Feature 12: Aura Effect Scaling
# ===================================================================


class TestAuraEffectModParsing:
    """Test aura effect mod text parsing."""

    def test_parse_increased_aura_effect(self):
        mods = parse_mods(["25% increased Aura Effect"])
        assert mods.increased_aura_effect == 25.0

    def test_parse_non_curse_aura_effect(self):
        mods = parse_mods(["15% increased effect of Non-Curse Auras from your Skills"])
        assert mods.increased_aura_effect == 15.0

    def test_aura_effect_merge(self):
        a = ParsedMods()
        a.increased_aura_effect = 10.0
        b = ParsedMods()
        b.increased_aura_effect = 20.0
        a.merge(b)
        assert a.increased_aura_effect == 30.0

    def test_aura_effect_stacks_from_multiple_sources(self):
        mods = parse_mods([
            "25% increased Aura Effect",
            "15% increased Aura Effect",
        ])
        assert mods.increased_aura_effect == 40.0


class TestAuraEffectScaling:
    """Test that aura values are scaled by increased aura effect."""

    def test_aura_flat_damage_scaled(self):
        """Aura flat added damage should be scaled by aura effect."""
        from pop.calc.aura_effects import get_aura_effect

        # Herald of Ice adds 43.5 cold base
        effect = get_aura_effect("Herald of Ice")
        assert effect is not None
        from pop.calc.models import DamageType
        base_cold = effect.flat_added[DamageType.COLD]
        assert base_cold == pytest.approx(43.5)

        # With 50% aura effect, should be 43.5 * 1.5 = 65.25
        scaled = base_cold * 1.5
        assert scaled == pytest.approx(65.25)


# ===================================================================
# Feature 13: Endurance Charges
# ===================================================================


class TestEnduranceCharges:
    """Test endurance charge effects."""

    def test_endurance_config_defaults(self):
        cfg = CalcConfig()
        assert cfg.use_endurance_charges is False
        assert cfg.endurance_charges == 0

    def test_endurance_phys_reduction(self):
        """Each endurance charge gives 4% phys damage reduction."""
        parsed = ParsedMods()
        config = CalcConfig(use_endurance_charges=True, endurance_charges=3)
        defence = calc_player_defences(parsed, config)
        assert defence.phys_damage_reduction == pytest.approx(12.0)  # 3 * 4%

    def test_endurance_ele_resist(self):
        """Each endurance charge gives 4% all elemental resist."""
        parsed = ParsedMods()
        config = CalcConfig(use_endurance_charges=True, endurance_charges=4)
        defence = calc_player_defences(parsed, config)
        assert defence.elemental_resistances["fire"] == pytest.approx(16.0)
        assert defence.elemental_resistances["cold"] == pytest.approx(16.0)
        assert defence.elemental_resistances["lightning"] == pytest.approx(16.0)

    def test_endurance_disabled_no_effect(self):
        """Endurance charges should have no effect when disabled."""
        parsed = ParsedMods()
        config = CalcConfig(use_endurance_charges=False, endurance_charges=3)
        defence = calc_player_defences(parsed, config)
        assert defence.phys_damage_reduction == 0.0
        assert defence.elemental_resistances["fire"] == 0.0

    def test_endurance_does_not_affect_dps(self):
        """Endurance charges are purely defensive — no DPS change."""
        from pop.calc.models import StatPool, Modifier
        from pop.calc.engine import _apply_charge_bonuses
        pool = StatPool()
        config = CalcConfig(use_endurance_charges=True, endurance_charges=5)
        _apply_charge_bonuses(pool, config)
        # No more mods or speed changes from endurance
        assert len(pool.more_mods) == 0
        assert pool.increased_speed == 0.0


# ===================================================================
# Feature 14: Player Defence Calculations
# ===================================================================


class TestPlayerDefenceCalc:
    """Test player defence calculation functions."""

    def test_phys_reduction_from_armour(self):
        """Armour formula: reduction = armour / (armour + 5 * damage)."""
        # 10000 armour vs 1000 damage hit
        red = calc_phys_reduction_from_armour(10000.0, 1000.0)
        # 10000 / (10000 + 5000) = 0.6667 → 66.67%
        assert red == pytest.approx(66.67, abs=0.1)

    def test_phys_reduction_capped_at_90(self):
        """Armour reduction should cap at 90%."""
        red = calc_phys_reduction_from_armour(999999.0, 100.0)
        assert red == pytest.approx(90.0)

    def test_phys_reduction_zero_armour(self):
        assert calc_phys_reduction_from_armour(0.0, 1000.0) == 0.0

    def test_phys_reduction_zero_damage(self):
        assert calc_phys_reduction_from_armour(10000.0, 0.0) == 0.0

    def test_evasion_chance(self):
        """Evasion chance = 1 - acc/(acc + (eva/4)^0.8)."""
        evade = calc_evasion_chance(5000.0, 1000.0)
        # Should be meaningful evasion
        assert evade > 0.0
        assert evade < 95.0

    def test_evasion_chance_zero(self):
        assert calc_evasion_chance(0.0, 1000.0) == 0.0
        assert calc_evasion_chance(1000.0, 0.0) == 0.0

    def test_defence_result_defaults(self):
        result = DefenceResult()
        assert result.armour == 0.0
        assert result.evasion == 0.0
        assert result.energy_shield == 0.0
        assert result.block_chance == 0.0
        assert result.phys_damage_reduction == 0.0

    def test_calc_player_defences_basic(self):
        parsed = ParsedMods()
        parsed.flat_armour = 5000.0
        parsed.flat_evasion = 2000.0
        config = CalcConfig()
        defence = calc_player_defences(parsed, config)
        assert defence.armour == pytest.approx(5000.0)
        assert defence.evasion == pytest.approx(2000.0)

    def test_calc_player_defences_with_increased(self):
        """Increased% armour should scale flat armour."""
        parsed = ParsedMods()
        parsed.flat_armour = 5000.0
        parsed.increased_armour = 100.0
        config = CalcConfig()
        defence = calc_player_defences(parsed, config)
        # 5000 * (1 + 100/100) = 10000
        assert defence.armour == pytest.approx(10000.0)

    def test_block_chance_capped(self):
        parsed = ParsedMods()
        parsed.special_flags["block_chance"] = 80.0
        config = CalcConfig()
        defence = calc_player_defences(parsed, config)
        assert defence.block_chance == 75.0  # capped


# ===================================================================
# Integration Tests
# ===================================================================


class TestLowerImpactIntegration:
    """Test that lower-impact features integrate correctly."""

    def test_accuracy_and_endurance_coexist(self):
        """Accuracy mods and endurance charges should work together."""
        mods = parse_mods([
            "+500 to Accuracy Rating",
            "30% increased Accuracy Rating",
        ])
        assert mods.flat_accuracy == 500.0
        assert mods.increased_accuracy == 30.0

        config = CalcConfig(use_endurance_charges=True, endurance_charges=3)
        defence = calc_player_defences(mods, config)
        assert defence.phys_damage_reduction == 12.0

    def test_aura_effect_and_accuracy(self):
        """Aura effect and accuracy mods should coexist."""
        mods = parse_mods([
            "25% increased Aura Effect",
            "+300 to Accuracy Rating",
        ])
        assert mods.increased_aura_effect == 25.0
        assert mods.flat_accuracy == 300.0

    def test_defence_in_calc_result(self):
        """CalcResult should include defence data."""
        from pop.calc.models import CalcResult
        result = CalcResult()
        assert result.defence is None

    def test_full_defence_pipeline(self):
        """Defence calc from parsed mods to DefenceResult."""
        mods = parse_mods([
            "+500 to Accuracy Rating",
            "25% increased Aura Effect",
        ])
        config = CalcConfig(
            use_endurance_charges=True,
            endurance_charges=4,
        )
        mods.flat_armour = 8000.0
        mods.flat_evasion = 3000.0
        mods.flat_energy_shield = 500.0
        defence = calc_player_defences(mods, config)
        assert defence.armour == pytest.approx(8000.0)
        assert defence.evasion == pytest.approx(3000.0)
        assert defence.energy_shield == pytest.approx(500.0)
        assert defence.phys_damage_reduction == pytest.approx(16.0)  # 4 * 4%
        assert defence.elemental_resistances["fire"] == pytest.approx(16.0)
