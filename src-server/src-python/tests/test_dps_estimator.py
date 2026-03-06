"""Tests for the DPS estimator and item comparison module."""

from __future__ import annotations

import pytest

from pop.trade.dps_estimator import (
    calculate_weapon_dps,
    compare_items,
    extract_stat_values,
    extract_weapon_stats,
)
from pop.trade.models import ItemComparison, WeaponDps


class TestExtractWeaponStats:
    def test_physical_damage(self):
        mods = ["Adds 50 to 100 Physical Damage"]
        stats = extract_weapon_stats(mods)
        assert stats["flat_phys_min"] == 50.0
        assert stats["flat_phys_max"] == 100.0

    def test_percent_physical(self):
        mods = ["120% increased Physical Damage"]
        stats = extract_weapon_stats(mods)
        assert stats["pct_phys"] == 120.0

    def test_elemental_damage(self):
        mods = [
            "Adds 20 to 40 Fire Damage",
            "Adds 10 to 30 Cold Damage",
        ]
        stats = extract_weapon_stats(mods)
        assert stats["flat_ele_min"] == 30.0
        assert stats["flat_ele_max"] == 70.0

    def test_attack_speed(self):
        mods = ["10% increased Attack Speed"]
        stats = extract_weapon_stats(mods)
        assert stats["pct_aps"] == 10.0

    def test_combined_mods(self):
        mods = [
            "Adds 40 to 80 Physical Damage",
            "80% increased Physical Damage",
            "Adds 10 to 20 Lightning Damage",
            "15% increased Attack Speed",
        ]
        stats = extract_weapon_stats(mods)
        assert stats["flat_phys_min"] == 40.0
        assert stats["flat_phys_max"] == 80.0
        assert stats["pct_phys"] == 80.0
        assert stats["flat_ele_min"] == 10.0
        assert stats["flat_ele_max"] == 20.0
        assert stats["pct_aps"] == 15.0

    def test_no_recognizable_mods(self):
        mods = ["+30 to maximum Life", "Some random mod"]
        stats = extract_weapon_stats(mods)
        assert stats["flat_phys_min"] == 0.0
        assert stats["flat_phys_max"] == 0.0


class TestCalculateWeaponDps:
    def test_physical_only(self):
        stats = {
            "flat_phys_min": 50.0,
            "flat_phys_max": 100.0,
            "pct_phys": 0.0,
            "flat_ele_min": 0.0,
            "flat_ele_max": 0.0,
            "pct_aps": 0.0,
        }
        dps = calculate_weapon_dps(stats, base_aps=1.5)
        # avg_phys = 75, aps = 1.5, phys_dps = 75 * 1.0 * 1.5 = 112.5
        assert dps.physical_dps == 112.5
        assert dps.elemental_dps == 0.0
        assert dps.total_dps == 112.5
        assert dps.attacks_per_second == 1.5

    def test_physical_with_percent(self):
        stats = {
            "flat_phys_min": 60.0,
            "flat_phys_max": 100.0,
            "pct_phys": 100.0,
            "flat_ele_min": 0.0,
            "flat_ele_max": 0.0,
            "pct_aps": 0.0,
        }
        dps = calculate_weapon_dps(stats, base_aps=1.2)
        # avg_phys = 80, phys_dps = 80 * 2.0 * 1.2 = 192.0
        assert dps.physical_dps == 192.0
        assert dps.total_dps == 192.0

    def test_physical_plus_elemental(self):
        stats = {
            "flat_phys_min": 40.0,
            "flat_phys_max": 80.0,
            "pct_phys": 50.0,
            "flat_ele_min": 20.0,
            "flat_ele_max": 40.0,
            "pct_aps": 10.0,
        }
        dps = calculate_weapon_dps(stats, base_aps=1.4)
        # aps = 1.4 * 1.1 = 1.54
        # avg_phys = 60, phys_dps = 60 * 1.5 * 1.54 = 138.6
        # avg_ele = 30, ele_dps = 30 * 1.54 = 46.2
        assert dps.physical_dps == 138.6
        assert dps.elemental_dps == 46.2
        assert dps.total_dps == 184.8
        assert dps.attacks_per_second == 1.54

    def test_attack_speed_mod(self):
        stats = {
            "flat_phys_min": 100.0,
            "flat_phys_max": 100.0,
            "pct_phys": 0.0,
            "flat_ele_min": 0.0,
            "flat_ele_max": 0.0,
            "pct_aps": 20.0,
        }
        dps = calculate_weapon_dps(stats, base_aps=1.0)
        # aps = 1.0 * 1.2 = 1.2, phys_dps = 100 * 1.0 * 1.2 = 120.0
        assert dps.attacks_per_second == 1.2
        assert dps.physical_dps == 120.0


class TestExtractStatValues:
    def test_life(self):
        mods = ["+80 to maximum Life"]
        vals = extract_stat_values(mods)
        assert vals["Maximum Life"] == 80.0

    def test_resistances(self):
        mods = [
            "+40% to Fire Resistance",
            "+35% to Cold Resistance",
            "+10% to all Elemental Resistances",
        ]
        vals = extract_stat_values(mods)
        assert vals["Fire Resistance"] == 40.0
        assert vals["Cold Resistance"] == 35.0
        assert vals["All Elemental Resistances"] == 10.0

    def test_attributes(self):
        mods = ["+30 to Strength", "+20 to Intelligence"]
        vals = extract_stat_values(mods)
        assert vals["Strength"] == 30.0
        assert vals["Intelligence"] == 20.0

    def test_movement_speed(self):
        mods = ["25% increased Movement Speed"]
        vals = extract_stat_values(mods)
        assert vals["Movement Speed"] == 25.0

    def test_flat_damage_mods(self):
        mods = [
            "Adds 10 to 20 Physical Damage",
            "Adds 5 to 15 Fire Damage",
            "Adds 3 to 7 Cold Damage",
        ]
        vals = extract_stat_values(mods)
        assert vals["Added Physical Damage"] == 15.0  # avg(10, 20)
        assert vals["Added Fire Damage"] == 10.0  # avg(5, 15)
        assert vals["Added Cold Damage"] == 5.0  # avg(3, 7)

    def test_no_recognizable_stats(self):
        mods = ["Some gibberish", "Another random mod"]
        vals = extract_stat_values(mods)
        assert len(vals) == 0


class TestCompareItems:
    def test_weapon_comparison(self):
        equipped = {
            "name": "Rustic Sword",
            "base_type": "Corsair Sword",
            "slot": "Weapon 1",
            "attacks_per_second": 1.5,
            "explicit_mods": [
                "Adds 30 to 60 Physical Damage",
            ],
        }
        trade = {
            "item_name": "Corsair Sword",
            "base_type": "Corsair Sword",
            "attacks_per_second": 1.5,
            "explicit_mods": [
                "Adds 50 to 100 Physical Damage",
            ],
        }
        result = compare_items(equipped, trade, "Weapon 1")

        assert result.is_weapon is True
        assert result.equipped_dps is not None
        assert result.trade_dps is not None
        assert result.trade_dps.total_dps > result.equipped_dps.total_dps
        assert result.dps_change_pct > 0

    def test_shield_in_weapon2_not_treated_as_weapon(self):
        """Shields in Weapon 2 slot should NOT show DPS comparison."""
        equipped = {
            "name": "Rathpith Globe",
            "base_type": "Titanium Spirit Shield",
            "slot": "Weapon 2",
            "explicits": [{"text": "+25% to Lightning Resistance"}],
        }
        trade = {
            "item_name": "Rathpith Globe",
            "type_line": "Titanium Spirit Shield",
            "explicit_mods": ["+25% to Lightning Resistance"],
        }
        result = compare_items(equipped, trade, "Weapon 2")

        assert result.is_weapon is False
        assert result.equipped_dps is None
        assert result.trade_dps is None
        assert "DPS" not in result.summary

    def test_non_weapon_comparison(self):
        equipped = {
            "name": "Iron Ring",
            "explicits": [{"text": "+50 to maximum Life"}, {"text": "+30% to Fire Resistance"}],
        }
        trade = {
            "item_name": "Gold Ring",
            "explicit_mods": ["+80 to maximum Life", "+20% to Fire Resistance"],
        }
        result = compare_items(equipped, trade, "Ring 1")

        assert result.is_weapon is False
        assert result.equipped_dps is None
        assert result.trade_dps is None
        assert len(result.stat_deltas) > 0

        life_delta = next(d for d in result.stat_deltas if d.stat_name == "Maximum Life")
        assert life_delta.difference == 30.0  # 80 - 50

        fire_delta = next(d for d in result.stat_deltas if d.stat_name == "Fire Resistance")
        assert fire_delta.difference == -10.0  # 20 - 30

    def test_no_mods(self):
        equipped = {"name": "Empty Item"}
        trade = {"item_name": "Also Empty"}
        result = compare_items(equipped, trade, "Helmet")

        assert result.is_weapon is False
        assert len(result.stat_deltas) == 0
        assert "No comparable stats" in result.summary

    def test_weapon_dps_change_pct(self):
        equipped = {
            "name": "Old Sword",
            "base_type": "Jewelled Foil",
            "attacks_per_second": 1.2,
            "explicit_mods": ["Adds 40 to 60 Physical Damage"],
        }
        trade = {
            "item_name": "New Sword",
            "base_type": "Jewelled Foil",
            "attacks_per_second": 1.2,
            "explicit_mods": ["Adds 80 to 120 Physical Damage"],
        }
        result = compare_items(equipped, trade, "Weapon 1")

        # old DPS: avg=50, aps=1.2, dps=60
        # new DPS: avg=100, aps=1.2, dps=120
        # change = (120-60)/60 * 100 = 100%
        assert result.dps_change_pct == 100.0

    def test_weapon_with_elemental_and_phys(self):
        equipped = {
            "name": "Ele Sword",
            "base_type": "Vaal Rapier",
            "attacks_per_second": 1.4,
            "explicit_mods": [
                "Adds 30 to 50 Physical Damage",
                "100% increased Physical Damage",
                "Adds 20 to 40 Fire Damage",
                "10% increased Attack Speed",
            ],
        }
        trade = {
            "item_name": "Better Ele Sword",
            "base_type": "Vaal Rapier",
            "attacks_per_second": 1.4,
            "explicit_mods": [
                "Adds 50 to 80 Physical Damage",
                "120% increased Physical Damage",
                "Adds 30 to 50 Lightning Damage",
                "15% increased Attack Speed",
            ],
        }
        result = compare_items(equipped, trade, "Weapon 1")

        assert result.is_weapon is True
        assert result.equipped_dps is not None
        assert result.trade_dps is not None
        assert result.trade_dps.total_dps > result.equipped_dps.total_dps
        assert result.dps_change_pct > 0
        assert "DPS" in result.summary

    def test_ring_with_damage_mods(self):
        """Rings with flat damage mods should show damage deltas."""
        equipped = {
            "name": "Coral Ring",
            "explicits": [
                {"text": "+50 to maximum Life"},
                {"text": "Adds 5 to 10 Physical Damage"},
                {"text": "Adds 10 to 20 Fire Damage"},
            ],
        }
        trade = {
            "item_name": "Diamond Ring",
            "explicit_mods": [
                "+60 to maximum Life",
                "Adds 10 to 20 Physical Damage",
                "Adds 15 to 30 Lightning Damage",
            ],
        }
        result = compare_items(equipped, trade, "Ring 1")

        assert result.is_weapon is False

        # Flat phys: trade avg 15 vs equipped avg 7.5 → +7.5
        phys = next(d for d in result.stat_deltas if d.stat_name == "Added Physical Damage")
        assert phys.equipped_value == 7.5
        assert phys.trade_value == 15.0
        assert phys.difference == 7.5

        # Fire on equipped only → negative delta
        fire = next(d for d in result.stat_deltas if d.stat_name == "Added Fire Damage")
        assert fire.trade_value == 0.0
        assert fire.difference < 0

        # Lightning on trade only → positive delta
        light = next(d for d in result.stat_deltas if d.stat_name == "Added Lightning Damage")
        assert light.equipped_value == 0.0
        assert light.difference > 0

        # Life still works
        life = next(d for d in result.stat_deltas if d.stat_name == "Maximum Life")
        assert life.difference == 10.0

    def test_ring_flat_dps_contribution_with_weapon_aps(self):
        """Rings should show flat DPS contribution when weapon_aps is provided."""
        equipped = {
            "name": "Coral Ring",
            "explicits": [
                {"text": "Adds 5 to 10 Physical Damage"},
                {"text": "Adds 10 to 20 Fire Damage"},
            ],
        }
        trade = {
            "item_name": "Diamond Ring",
            "explicit_mods": [
                "Adds 10 to 20 Physical Damage",
                "Adds 20 to 40 Lightning Damage",
            ],
        }
        # Weapon APS = 1.5
        result = compare_items(equipped, trade, "Ring 1", weapon_aps=1.5)

        assert result.is_weapon is False
        # Equipped: avg_phys=7.5 + avg_fire=15 = 22.5 total avg dmg
        #   flat_dps = 22.5 * 1.5 = 33.75 → 33.8
        assert result.equipped_flat_dps == 33.8
        # Trade: avg_phys=15 + avg_light=30 = 45 total avg dmg
        #   flat_dps = 45 * 1.5 = 67.5
        assert result.trade_flat_dps == 67.5
        assert result.flat_dps_change == 33.7  # 67.5 - 33.8
        assert "Flat DPS" in result.summary

    def test_ring_no_dps_without_weapon_aps(self):
        """Without weapon_aps, non-weapon items should not show flat DPS."""
        equipped = {
            "name": "Coral Ring",
            "explicits": [{"text": "Adds 5 to 10 Physical Damage"}],
        }
        trade = {
            "item_name": "Diamond Ring",
            "explicit_mods": ["Adds 10 to 20 Physical Damage"],
        }
        result = compare_items(equipped, trade, "Ring 1")  # no weapon_aps

        assert result.equipped_flat_dps == 0.0
        assert result.trade_flat_dps == 0.0
        assert "Flat DPS" not in result.summary

    def test_comparison_summary_stats(self):
        equipped = {
            "name": "Old Helm",
            "explicit_mods": ["+60 to maximum Life", "+30% to Fire Resistance"],
        }
        trade = {
            "item_name": "New Helm",
            "explicit_mods": ["+90 to maximum Life", "+40% to Cold Resistance"],
        }
        result = compare_items(equipped, trade, "Helmet")

        assert "better" in result.summary
        assert "worse" in result.summary
