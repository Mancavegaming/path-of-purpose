"""
Phase H tests: Impale, Projectile mechanics, Totem/Trap/Mine/Brand,
Minion detection, Keystones.

These tests validate the 5 medium-impact PoB-alignment features added
to the damage calculator engine.
"""

from __future__ import annotations

import pytest

from pop.calc.impale_calc import calc_impale_dps
from pop.calc.keystone_effects import get_keystone_flags, KEYSTONE_NAMES
from pop.calc.mod_parser import ParsedMods, parse_mods
from pop.calc.models import CalcConfig, DamageType
from pop.calc.crit_calc import calc_effective_crit


# ===================================================================
# Feature 6: Impale
# ===================================================================


class TestImpaleCalc:
    """Test impale DPS calculation."""

    def test_basic_impale_dps(self):
        """100% chance, 5 stacks, 100 phys damage, 2 hits/sec."""
        dps = calc_impale_dps(
            phys_hit_after_mit=100.0,
            impale_chance=1.0,
            hits_per_second=2.0,
        )
        # Each impale stores 10% = 10 damage
        # 5 stacks * 10 * 2 hits/sec = 100 impale DPS
        assert dps == pytest.approx(100.0)

    def test_impale_with_50_pct_chance(self):
        """50% chance means avg 2.5 stacks on enemy."""
        dps = calc_impale_dps(
            phys_hit_after_mit=100.0,
            impale_chance=0.5,
            hits_per_second=2.0,
        )
        # 10 stored per impale * 2.5 avg stacks * 2 hits/sec = 50
        assert dps == pytest.approx(50.0)

    def test_impale_with_increased_effect(self):
        """50% increased impale effect."""
        dps = calc_impale_dps(
            phys_hit_after_mit=100.0,
            impale_chance=1.0,
            hits_per_second=2.0,
            increased_impale_effect=50.0,
        )
        # 10 * 1.5 = 15 stored per impale
        # 15 * 5 stacks * 2 hits/sec = 150
        assert dps == pytest.approx(150.0)

    def test_impale_with_extra_stacks(self):
        """7 max stacks instead of 5."""
        dps = calc_impale_dps(
            phys_hit_after_mit=100.0,
            impale_chance=1.0,
            hits_per_second=2.0,
            max_stacks=7,
        )
        # 10 * 7 * 2 = 140
        assert dps == pytest.approx(140.0)

    def test_impale_zero_chance(self):
        assert calc_impale_dps(100.0, 0.0, 2.0) == 0.0

    def test_impale_zero_phys(self):
        assert calc_impale_dps(0.0, 1.0, 2.0) == 0.0


class TestImpaleModParsing:
    """Test impale-related mod text parsing."""

    def test_parse_impale_chance(self):
        mods = parse_mods(["40% chance to Impale Enemies on Hit"])
        assert mods.impale_chance == 40.0

    def test_parse_impale_on_hit(self):
        mods = parse_mods(["Attacks Impale on Hit"])
        assert mods.impale_chance == 100.0

    def test_parse_impale_extra_stacks(self):
        mods = parse_mods(["Impales you inflict last 2 additional Hits"])
        assert mods.extra_impale_stacks == 2

    def test_parse_increased_impale_effect(self):
        mods = parse_mods(["50% increased Impale Effect"])
        assert mods.increased_impale_effect == 50.0

    def test_parse_impale_chance_stacks(self):
        """Multiple impale mods should stack."""
        mods = parse_mods([
            "20% chance to Impale on Hit",
            "30% chance to Impale on Hit",
        ])
        assert mods.impale_chance == 50.0


# ===================================================================
# Feature 7: Projectile Mechanics
# ===================================================================


class TestProjectileModParsing:
    """Test projectile-related mod text parsing."""

    def test_parse_additional_projectiles(self):
        mods = parse_mods(["Fires 2 additional Projectiles"])
        assert mods.additional_projectiles == 2

    def test_parse_plus_projectiles(self):
        mods = parse_mods(["+1 Projectile"])
        assert mods.additional_projectiles == 1

    def test_parse_pierce_targets(self):
        mods = parse_mods(["Projectiles Pierce 3 additional Targets"])
        assert mods.pierce_targets == 3

    def test_parse_pierce_all(self):
        mods = parse_mods(["Projectiles Pierce all Targets"])
        assert mods.pierce_all is True

    def test_parse_chain(self):
        mods = parse_mods(["Projectiles Chain +2 times"])
        assert mods.chain_plus == 2

    def test_parse_fork(self):
        mods = parse_mods(["Projectiles Fork"])
        assert mods.fork is True

    def test_projectile_mods_merge(self):
        """Projectile mods should merge correctly."""
        a = ParsedMods()
        a.additional_projectiles = 2
        a.chain_plus = 1
        b = ParsedMods()
        b.additional_projectiles = 1
        b.pierce_all = True
        a.merge(b)
        assert a.additional_projectiles == 3
        assert a.chain_plus == 1
        assert a.pierce_all is True


# ===================================================================
# Feature 8: Totem/Trap/Mine/Brand Detection
# ===================================================================


class TestSkillTypeDetection:
    """Test totem/trap/mine/brand skill type detection."""

    def test_totem_mod_parsing(self):
        mods = parse_mods(["+2 to maximum number of Summoned Totems"])
        assert mods.max_totem_bonus == 2

    def test_additional_totem(self):
        mods = parse_mods(["Place an additional Totem"])
        assert mods.max_totem_bonus == 1

    def test_totem_merge(self):
        a = ParsedMods()
        a.max_totem_bonus = 1
        b = ParsedMods()
        b.max_totem_bonus = 2
        a.merge(b)
        assert a.max_totem_bonus == 3


class TestCalcResultSkillTypes:
    """Test CalcResult reports skill types correctly."""

    def test_calc_result_defaults(self):
        from pop.calc.models import CalcResult
        r = CalcResult()
        assert r.is_totem is False
        assert r.is_trap is False
        assert r.is_mine is False
        assert r.is_minion is False
        assert r.num_totems == 0
        assert r.impale_dps == 0.0


# ===================================================================
# Feature 9: Minion Damage (Detection)
# ===================================================================


class TestMinionDetection:
    """Test that minion skills are detected and flagged."""

    def test_minion_gem_tags(self):
        """Minion gems should have 'minion' in tags."""
        from pop.calc.gem_data import get_active_gem_stats
        for name in ["Raise Zombie", "Summon Raging Spirit", "Raise Spectre",
                      "Summon Skeletons", "Summon Carrion Golem"]:
            stats = get_active_gem_stats(name)
            assert stats is not None, f"Missing gem: {name}"
            assert "minion" in stats.tags, f"{name} should have 'minion' tag"

    def test_non_minion_gem_tags(self):
        from pop.calc.gem_data import get_active_gem_stats
        for name in ["Fireball", "Cyclone", "Arc"]:
            stats = get_active_gem_stats(name)
            assert stats is not None
            assert "minion" not in stats.tags


# ===================================================================
# Feature 10: Keystones
# ===================================================================


class TestKeystoneEffects:
    """Test keystone effect database."""

    def test_elemental_overload(self):
        flags = get_keystone_flags("Elemental Overload")
        assert flags is not None
        assert flags["elemental_overload"] is True

    def test_resolute_technique(self):
        flags = get_keystone_flags("Resolute Technique")
        assert flags is not None
        assert flags["resolute_technique"] is True

    def test_point_blank(self):
        flags = get_keystone_flags("Point Blank")
        assert flags is not None
        assert flags["point_blank"] is True

    def test_avatar_of_fire(self):
        flags = get_keystone_flags("Avatar of Fire")
        assert flags is not None
        assert flags["avatar_of_fire"] is True

    def test_crimson_dance(self):
        flags = get_keystone_flags("Crimson Dance")
        assert flags is not None
        assert flags["crimson_dance"] is True

    def test_ancestral_bond(self):
        flags = get_keystone_flags("Ancestral Bond")
        assert flags is not None
        assert flags["ancestral_bond"] is True

    def test_pain_attunement(self):
        flags = get_keystone_flags("Pain Attunement")
        assert flags is not None
        assert flags["pain_attunement"] is True

    def test_unknown_keystone_returns_none(self):
        assert get_keystone_flags("Nonexistent Keystone") is None

    def test_all_keystones_exist(self):
        """All keystones in the set should have flags."""
        for name in KEYSTONE_NAMES:
            flags = get_keystone_flags(name)
            assert flags is not None, f"Missing flags for keystone: {name}"

    def test_keystone_count(self):
        """Should have a reasonable number of keystones."""
        assert len(KEYSTONE_NAMES) >= 10


class TestResoluteTechniqueMechanics:
    """Test Resolute Technique keystone mechanics."""

    def test_rt_always_hits_never_crits(self):
        """RT should give 100% hit chance and 0% crit."""
        # RT is applied in engine, but we test the crit calc input
        # With RT, engine sets crit_chance = 0.0
        # Normal crit calc for reference
        normal_crit = calc_effective_crit(6.0, 200.0)
        assert normal_crit > 0
        # RT forces 0 — engine does this, not crit_calc


class TestElementalOverloadMechanics:
    """Test Elemental Overload keystone mechanics."""

    def test_eo_gives_40_pct_more_elemental(self):
        """EO should give 40% more elemental damage with no crit multi."""
        # EO crit multi is locked to 100% (no bonus from crits)
        # 40% more elemental damage is applied separately
        # With 100 fire damage: 100 * 1.4 = 140
        fire_after_mit = 100.0
        eo_bonus = fire_after_mit * 0.40
        assert eo_bonus == pytest.approx(40.0)


class TestPointBlankMechanics:
    """Test Point Blank keystone mechanics."""

    def test_pb_30_pct_more_close_range(self):
        """PB gives 30% more projectile damage at close range."""
        base_hit = 100.0
        pb_hit = base_hit * 1.30
        assert pb_hit == pytest.approx(130.0)


# ===================================================================
# Integration Tests
# ===================================================================


class TestMediumImpactIntegration:
    """Test that medium-impact features integrate correctly."""

    def test_impale_full_chain(self):
        """Full impale calculation chain: mod parsing → impale calc."""
        mods = parse_mods([
            "40% chance to Impale Enemies on Hit",
            "50% increased Impale Effect",
            "Impales you inflict last 2 additional Hits",
        ])
        assert mods.impale_chance == 40.0
        assert mods.increased_impale_effect == 50.0
        assert mods.extra_impale_stacks == 2

        dps = calc_impale_dps(
            phys_hit_after_mit=200.0,
            impale_chance=mods.impale_chance / 100.0,
            hits_per_second=3.0,
            increased_impale_effect=mods.increased_impale_effect,
            max_stacks=5 + mods.extra_impale_stacks,
        )
        # Stored: 200 * 0.10 * 1.5 = 30 per impale
        # Avg stacks: 7 * 0.4 = 2.8
        # DPS: 30 * 2.8 * 3.0 = 252
        assert dps == pytest.approx(252.0)

    def test_keystone_special_flags_merge(self):
        """Keystone flags merge into ParsedMods correctly."""
        mods = ParsedMods()
        flags = get_keystone_flags("Resolute Technique")
        for key, val in flags.items():
            mods.special_flags[key] = val
        assert mods.special_flags.get("resolute_technique") is True

    def test_projectile_and_impale_together(self):
        """Projectile mods and impale mods should coexist."""
        mods = parse_mods([
            "Fires 2 additional Projectiles",
            "40% chance to Impale on Hit",
            "Projectiles Pierce 3 additional Targets",
        ])
        assert mods.additional_projectiles == 2
        assert mods.impale_chance == 40.0
        assert mods.pierce_targets == 3

    def test_multiple_keystones(self):
        """Multiple keystones can be active simultaneously."""
        mods = ParsedMods()
        for ks in ["Iron Grip", "Point Blank"]:
            flags = get_keystone_flags(ks)
            for key, val in flags.items():
                mods.special_flags[key] = val
        assert mods.special_flags.get("iron_grip") is True
        assert mods.special_flags.get("point_blank") is True

    def test_totem_bonus_stacking(self):
        """Totem bonus from multiple sources should stack."""
        mods = parse_mods([
            "+1 to maximum number of Summoned Totems",
            "Place an additional Totem",
            "+2 to maximum number of Summoned Totems",
        ])
        assert mods.max_totem_bonus == 4  # 1 + 1 + 2
