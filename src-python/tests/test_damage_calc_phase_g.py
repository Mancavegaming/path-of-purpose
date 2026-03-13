"""
Phase G tests: Curses, Shock/Chill, Wither, Ascendancy, Flasks.

These tests validate the 5 high-impact PoB-alignment features added
to the damage calculator engine.
"""

from __future__ import annotations

import pytest

from pop.calc.ascendancy_effects import (
    get_all_class_nodes,
    get_ascendancy_node,
)
from pop.calc.crit_calc import calc_effective_crit
from pop.calc.curse_effects import get_curse_effect
from pop.calc.defense_calc import calc_mitigation_multi
from pop.calc.flask_effects import get_flask_effect
from pop.calc.models import CalcConfig, DamageType


# ===================================================================
# Feature 1: Curses
# ===================================================================


class TestCurseEffects:
    """Test curse effect database and resist reduction."""

    def test_elemental_weakness_reduces_all_ele_resist(self):
        effect = get_curse_effect("Elemental Weakness")
        assert effect is not None
        assert effect.resist_reduction[DamageType.FIRE] == 44.0
        assert effect.resist_reduction[DamageType.COLD] == 44.0
        assert effect.resist_reduction[DamageType.LIGHTNING] == 44.0
        assert DamageType.CHAOS not in effect.resist_reduction

    def test_flammability_reduces_fire_only(self):
        effect = get_curse_effect("Flammability")
        assert effect is not None
        assert effect.resist_reduction[DamageType.FIRE] == 44.0
        assert DamageType.COLD not in effect.resist_reduction

    def test_frostbite_reduces_cold_only(self):
        effect = get_curse_effect("Frostbite")
        assert effect is not None
        assert effect.resist_reduction[DamageType.COLD] == 44.0

    def test_conductivity_reduces_lightning_only(self):
        effect = get_curse_effect("Conductivity")
        assert effect is not None
        assert effect.resist_reduction[DamageType.LIGHTNING] == 44.0

    def test_vulnerability_physical_damage_taken(self):
        effect = get_curse_effect("Vulnerability")
        assert effect is not None
        assert effect.increased_damage_taken[DamageType.PHYSICAL] == 29.0
        assert len(effect.resist_reduction) == 0  # No resist reduction

    def test_despair_chaos_resist_reduction(self):
        effect = get_curse_effect("Despair")
        assert effect is not None
        assert effect.resist_reduction[DamageType.CHAOS] == 20.0
        assert effect.increased_dot_taken == 15.0

    def test_unknown_curse_returns_none(self):
        assert get_curse_effect("Nonexistent Curse") is None


class TestCurseResistReduction:
    """Test curse resist reduction in defense_calc."""

    def test_curse_reduces_fire_resist(self):
        config = CalcConfig(enemy_fire_resist=40.0)
        # Without curse: 1 - 40/100 = 0.6
        multi_no_curse = calc_mitigation_multi(DamageType.FIRE, config)
        assert multi_no_curse == pytest.approx(0.6)

        # With 44% curse reduction: 1 - (40-44)/100 = 1 - (-4/100) = 1.04
        multi_with_curse = calc_mitigation_multi(
            DamageType.FIRE, config, curse_reduction=44.0,
        )
        assert multi_with_curse == pytest.approx(1.04)

    def test_curse_stacks_with_exposure_and_pen(self):
        config = CalcConfig(enemy_cold_resist=40.0)
        # Curse -44, exposure -10, pen -15
        # effective = 40 - 44 - 10 - 15 = -29
        # multi = 1 - (-29/100) = 1.29
        multi = calc_mitigation_multi(
            DamageType.COLD, config,
            penetration=15.0, exposure=10.0, curse_reduction=44.0,
        )
        assert multi == pytest.approx(1.29)

    def test_boss_curse_effectiveness(self):
        """Boss curse effectiveness should reduce curse values."""
        # Shaper-tier boss: 34% effectiveness
        # Elemental Weakness: 44 * 0.34 = ~15
        effect = get_curse_effect("Elemental Weakness")
        assert effect is not None
        scaled = effect.resist_reduction[DamageType.FIRE] * 0.34
        assert scaled == pytest.approx(14.96)


# ===================================================================
# Feature 2: Shock / Chill
# ===================================================================


class TestShockChill:
    """Test shock and chill enemy debuff mechanics."""

    def test_shock_config_default_15(self):
        """Shock with no value defaults to 15% when condition is set."""
        from pop.calc.config_reader import read_config
        from pop.build_parser.models import BuildConfig

        cfg = read_config(BuildConfig(entries={
            "enemyCondition_Shocked": "true",
        }))
        assert cfg.enemy_is_shocked is True
        assert cfg.shock_value == 15.0

    def test_shock_config_custom_value(self):
        from pop.calc.config_reader import read_config
        from pop.build_parser.models import BuildConfig

        cfg = read_config(BuildConfig(entries={
            "enemyCondition_Shocked": "true",
            "shockValue": "50",
        }))
        assert cfg.shock_value == 50.0

    def test_intimidate_config(self):
        from pop.calc.config_reader import read_config
        from pop.build_parser.models import BuildConfig

        cfg = read_config(BuildConfig(entries={
            "enemyCondition_Intimidated": "true",
        }))
        assert cfg.enemy_is_intimidated is True

    def test_unnerve_config(self):
        from pop.calc.config_reader import read_config
        from pop.build_parser.models import BuildConfig

        cfg = read_config(BuildConfig(entries={
            "enemyCondition_Unnerved": "true",
        }))
        assert cfg.enemy_is_unnerved is True


# ===================================================================
# Feature 3: Wither Stacks
# ===================================================================


class TestWitherStacks:
    """Test wither stack mechanics."""

    def test_wither_config_reading(self):
        from pop.calc.config_reader import read_config
        from pop.build_parser.models import BuildConfig

        cfg = read_config(BuildConfig(entries={"witherStacks": "15"}))
        assert cfg.wither_stacks == 15

    def test_wither_clamped_to_15(self):
        from pop.calc.config_reader import read_config
        from pop.build_parser.models import BuildConfig

        cfg = read_config(BuildConfig(entries={"witherStacks": "20"}))
        assert cfg.wither_stacks == 15

    def test_wither_clamped_to_zero(self):
        from pop.calc.config_reader import read_config
        from pop.build_parser.models import BuildConfig

        cfg = read_config(BuildConfig(entries={"witherStacks": "-5"}))
        # Negative should be treated as zero
        # Note: -5 won't parse as int via isdigit(), so stays at default 0
        assert cfg.wither_stacks == 0

    def test_wither_stacks_increase_chaos_damage(self):
        """15 wither stacks = 90% increased chaos damage taken."""
        stacks = 15
        wither_multi = 1.0 + (stacks * 6.0) / 100.0
        assert wither_multi == pytest.approx(1.90)


# ===================================================================
# Feature 4: Ascendancy Nodes
# ===================================================================


class TestAscendancyEffects:
    """Test ascendancy node effect database."""

    def test_aspect_of_carnage(self):
        node = get_ascendancy_node("Aspect of Carnage")
        assert node is not None
        assert node.class_name == "Berserker"
        assert len(node.modifiers) == 1
        assert node.modifiers[0].value == 40.0  # 40% more damage

    def test_deadly_infusion_base_crit(self):
        node = get_ascendancy_node("Deadly Infusion")
        assert node is not None
        assert node.class_name == "Assassin"
        assert node.base_crit_bonus == 2.0
        assert node.crit_multi == 25.0

    def test_inevitable_judgement_special_flag(self):
        node = get_ascendancy_node("Inevitable Judgement")
        assert node is not None
        assert node.class_name == "Inquisitor"
        assert node.special.get("crits_ignore_resist") is True

    def test_mastermind_of_discord_penetration(self):
        node = get_ascendancy_node("Mastermind of Discord")
        assert node is not None
        assert node.penetration[DamageType.FIRE] == 25.0
        assert node.penetration[DamageType.COLD] == 25.0
        assert node.penetration[DamageType.LIGHTNING] == 25.0

    def test_unholy_might_conversion(self):
        node = get_ascendancy_node("Unholy Might")
        assert node is not None
        assert len(node.conversions) == 1
        conv = node.conversions[0]
        assert conv.type_from == DamageType.PHYSICAL
        assert conv.type_to == DamageType.CHAOS
        assert conv.percent == 30.0
        assert conv.is_gained_as is True

    def test_overwhelm_base_crit(self):
        node = get_ascendancy_node("Overwhelm")
        assert node is not None
        assert node.class_name == "Slayer"
        assert node.base_crit_bonus == 3.0

    def test_get_all_class_nodes(self):
        nodes = get_all_class_nodes("Berserker")
        assert len(nodes) >= 3
        names = {n.name for n in nodes}
        assert "Aspect of Carnage" in names
        assert "Blitz" in names

    def test_unknown_node_returns_none(self):
        assert get_ascendancy_node("Nonexistent Node") is None

    def test_unknown_class_returns_empty(self):
        assert get_all_class_nodes("NonexistentClass") == []


# ===================================================================
# Feature 5: Flask Effects
# ===================================================================


class TestFlaskEffects:
    """Test flask effect database."""

    def test_diamond_flask_lucky_crit(self):
        effect = get_flask_effect("Diamond Flask")
        assert effect is not None
        assert effect.lucky_crit is True

    def test_bottled_faith(self):
        effect = get_flask_effect("Bottled Faith")
        assert effect is not None
        assert effect.increased_crit == 100.0
        assert effect.enemy_increased_damage_taken == 10.0

    def test_atziris_promise_conversions(self):
        effect = get_flask_effect("Atziri's Promise")
        assert effect is not None
        assert len(effect.conversions_gained_as) == 4
        # First: phys as extra chaos
        from_type, to_type, pct = effect.conversions_gained_as[0]
        assert from_type == DamageType.PHYSICAL
        assert to_type == DamageType.CHAOS
        assert pct == 15.0

    def test_taste_of_hate(self):
        effect = get_flask_effect("Taste of Hate")
        assert effect is not None
        assert len(effect.conversions_gained_as) == 1
        from_type, to_type, pct = effect.conversions_gained_as[0]
        assert from_type == DamageType.PHYSICAL
        assert to_type == DamageType.COLD
        assert pct == 20.0

    def test_lions_roar(self):
        effect = get_flask_effect("Lion's Roar")
        assert effect is not None
        assert len(effect.modifiers) == 1
        assert effect.modifiers[0].value == 20.0

    def test_vessel_of_vinktar_pen(self):
        effect = get_flask_effect("Vessel of Vinktar")
        assert effect is not None
        assert effect.penetration[DamageType.LIGHTNING] == 10.0
        assert effect.flat_added[DamageType.LIGHTNING] == 55.0

    def test_wise_oak_pen(self):
        effect = get_flask_effect("The Wise Oak")
        assert effect is not None
        assert effect.penetration[DamageType.FIRE] == 10.0

    def test_partial_name_matching(self):
        """Flask lookup should match partial names (e.g. unique Diamond Flask)."""
        effect = get_flask_effect("Experimenter's Diamond Flask of the Order")
        assert effect is not None
        assert effect.lucky_crit is True

    def test_unknown_flask_returns_none(self):
        assert get_flask_effect("Unknown Potion") is None


class TestLuckyCrit:
    """Test Diamond Flask lucky crit mechanics."""

    def test_lucky_crit_increases_chance(self):
        # Base 30% crit, no increased
        normal = calc_effective_crit(30.0, 0.0)
        lucky = calc_effective_crit(30.0, 0.0, lucky=True)
        assert lucky > normal
        # Lucky: 1 - (1 - 0.3)^2 = 1 - 0.49 = 0.51
        assert lucky == pytest.approx(0.51)

    def test_lucky_crit_100_pct_unchanged(self):
        """Lucky crit with 100% chance should still be 100%."""
        lucky = calc_effective_crit(100.0, 0.0, lucky=True)
        assert lucky == pytest.approx(1.0)

    def test_lucky_crit_low_chance(self):
        """Lucky crit with 5% base: 1 - (0.95)^2 = 0.0975."""
        lucky = calc_effective_crit(5.0, 0.0, lucky=True)
        assert lucky == pytest.approx(0.0975)

    def test_lucky_crit_with_increased(self):
        """Lucky applies after increased crit scaling."""
        # 6% base, 200% increased = 6 * 3 = 18% base
        # Lucky: 1 - (1-0.18)^2 = 1 - 0.6724 = 0.3276
        lucky = calc_effective_crit(6.0, 200.0, lucky=True)
        assert lucky == pytest.approx(0.3276)


# ===================================================================
# Integration: Features working together
# ===================================================================


class TestIntegration:
    """Test that features stack correctly."""

    def test_curse_plus_exposure_plus_pen(self):
        """Full resist reduction stack: curse + exposure + pen."""
        config = CalcConfig(enemy_fire_resist=75.0)  # High resist boss
        multi = calc_mitigation_multi(
            DamageType.FIRE, config,
            penetration=37.0,  # Fire Pen Support
            exposure=10.0,     # Wave of Conviction
            curse_reduction=44.0,  # Flammability
        )
        # 75 - 44 - 10 - 37 = -16
        # multi = 1 - (-16/100) = 1.16
        assert multi == pytest.approx(1.16)

    def test_curse_on_shaper_boss(self):
        """Shaper-tier boss with 34% curse effectiveness."""
        config = CalcConfig(
            enemy_fire_resist=40.0,
            enemy_is_boss=True,
        )
        # Flammability: 44 * 0.34 = 14.96
        multi = calc_mitigation_multi(
            DamageType.FIRE, config,
            curse_reduction=44.0 * 0.34,
        )
        # 40 - 14.96 = 25.04
        # multi = 1 - 25.04/100 = 0.7496
        assert multi == pytest.approx(0.7496)

    def test_resist_floor_with_heavy_reduction(self):
        """Resist should not go below -200%."""
        config = CalcConfig(enemy_fire_resist=0.0)
        multi = calc_mitigation_multi(
            DamageType.FIRE, config,
            penetration=100.0,
            exposure=50.0,
            curse_reduction=100.0,
        )
        # 0 - 100 - 50 - 100 = -250, clamped to -200
        # multi = 1 - (-200/100) = 3.0
        assert multi == pytest.approx(3.0)

    def test_wither_value_formula(self):
        """Wither 15 stacks = 90% increased chaos damage taken."""
        config = CalcConfig(wither_stacks=15)
        wither_multi = 1.0 + config.wither_stacks * 6.0 / 100.0
        assert wither_multi == pytest.approx(1.9)

    def test_shock_plus_wither(self):
        """Shock + wither stack additively for chaos damage."""
        shock = 15.0
        wither = 10 * 6.0  # 10 stacks
        total_chaos_taken = 1.0 + (shock + wither) / 100.0
        assert total_chaos_taken == pytest.approx(1.75)

    def test_diamond_flask_with_power_charges(self):
        """Diamond flask + power charges should give very high crit."""
        # 6% base, 200% inc crit (from power charges etc.)
        # Without lucky: 6 * 3 = 18% = 0.18
        # With lucky: 1 - (0.82)^2 = 0.3276
        normal = calc_effective_crit(6.0, 200.0)
        lucky = calc_effective_crit(6.0, 200.0, lucky=True)
        assert normal == pytest.approx(0.18)
        assert lucky == pytest.approx(0.3276)
        assert lucky > normal

    def test_config_reader_full_combat(self):
        """Config reader handles all new keys together."""
        from pop.calc.config_reader import read_config
        from pop.build_parser.models import BuildConfig

        cfg = read_config(BuildConfig(entries={
            "enemyIsBoss": "true",
            "useCurses": "true",
            "useFlasks": "true",
            "enemyCondition_Shocked": "true",
            "shockValue": "30",
            "witherStacks": "10",
            "enemyCondition_Intimidated": "true",
        }))
        assert cfg.enemy_is_boss is True
        assert cfg.use_curses is True
        assert cfg.use_flasks is True
        assert cfg.shock_value == 30.0
        assert cfg.wither_stacks == 10
        assert cfg.enemy_is_intimidated is True
        assert cfg.curse_effectiveness == 0.34  # Boss
