"""
Phase D tests: DoT ailment damage (Ignite, Bleed, Poison).

Tests cover:
- Mod parser: DoT modifiers, ailment chance, duration
- dot_calc unit tests: each ailment formula, modifier filtering, enemy resist
- Full pipeline integration: combined_dps includes DoT
"""

import pytest

from pop.build_parser.models import (
    Build,
    BuildConfig,
    Gem,
    Item,
    ItemMod,
    SkillGroup,
)
from pop.calc.dot_calc import (
    calc_bleed_dps,
    calc_effective_ailment_chance,
    calc_ignite_dps,
    calc_poison_dps,
)
from pop.calc.engine import calculate_dps
from pop.calc.mod_parser import parse_mods
from pop.calc.models import (
    CalcConfig,
    DamageType,
    Modifier,
    StatPool,
)


# ===========================================================================
# Mod parser tests — DoT patterns
# ===========================================================================


class TestModParserDoT:
    def test_increased_burning_damage(self):
        result = parse_mods(["40% increased Burning Damage"])
        assert len(result.increased_dot) == 1
        m = result.increased_dot[0]
        assert m.value == 40.0
        assert DamageType.FIRE in m.damage_types

    def test_increased_dot_generic(self):
        result = parse_mods(["20% increased Damage over Time"])
        assert len(result.increased_dot) == 1
        assert result.increased_dot[0].value == 20.0
        assert result.increased_dot[0].damage_types == []

    def test_increased_dot_typed(self):
        result = parse_mods(["30% increased Fire Damage over Time"])
        assert len(result.increased_dot) == 1
        assert result.increased_dot[0].value == 30.0
        assert DamageType.FIRE in result.increased_dot[0].damage_types

    def test_more_dot(self):
        result = parse_mods(["25% more Damage over Time"])
        assert len(result.more_dot) == 1
        assert result.more_dot[0].value == 25.0

    def test_more_burning(self):
        result = parse_mods(["30% more Burning Damage"])
        assert len(result.more_dot) == 1
        assert result.more_dot[0].value == 30.0
        assert DamageType.FIRE in result.more_dot[0].damage_types

    def test_dot_multiplier_generic(self):
        result = parse_mods(["+15% to Damage over Time Multiplier"])
        assert result.dot_multi == 15.0

    def test_dot_multiplier_typed(self):
        result = parse_mods(["+20% to Fire Damage over Time Multiplier"])
        assert result.dot_multi_fire == 20.0

    def test_dot_multiplier_phys(self):
        result = parse_mods(["+10% to Physical Damage over Time Multiplier"])
        assert result.dot_multi_phys == 10.0

    def test_dot_multiplier_chaos(self):
        result = parse_mods(["+12% to Chaos Damage over Time Multiplier"])
        assert result.dot_multi_chaos == 12.0

    def test_chance_to_ignite(self):
        result = parse_mods(["20% chance to Ignite"])
        assert result.chance_to_ignite == 20.0

    def test_chance_to_bleed(self):
        result = parse_mods(["25% chance to cause Bleeding"])
        assert result.chance_to_bleed == 25.0

    def test_chance_to_poison(self):
        result = parse_mods(["60% chance to Poison on Hit"])
        assert result.chance_to_poison == 60.0

    def test_always_ignite(self):
        result = parse_mods(["Always Ignite"])
        assert result.chance_to_ignite == 100.0

    def test_poison_on_hit(self):
        result = parse_mods(["Poisons Enemies on Hit"])
        assert result.chance_to_poison == 100.0

    def test_ignite_duration(self):
        result = parse_mods(["30% increased Ignite Duration"])
        assert result.increased_ignite_duration == 30.0

    def test_bleed_duration(self):
        result = parse_mods(["20% increased Bleeding Duration"])
        assert result.increased_bleed_duration == 20.0

    def test_poison_duration(self):
        result = parse_mods(["50% increased Poison Duration"])
        assert result.increased_poison_duration == 50.0

    def test_ailment_duration_all(self):
        result = parse_mods(["20% increased Duration of Ailments"])
        assert result.increased_ignite_duration == 20.0
        assert result.increased_bleed_duration == 20.0
        assert result.increased_poison_duration == 20.0

    def test_increased_ailment_damage(self):
        result = parse_mods(["30% increased Damage with Ailments"])
        assert len(result.increased_dot) == 1
        assert result.increased_dot[0].value == 30.0

    def test_more_ailment_damage(self):
        result = parse_mods(["20% more Damage with Ailments"])
        assert len(result.more_dot) == 1
        assert result.more_dot[0].value == 20.0

    def test_increased_poison_damage(self):
        result = parse_mods(["40% increased Damage with Poison"])
        assert len(result.increased_dot) == 1
        assert result.increased_dot[0].value == 40.0
        assert DamageType.CHAOS in result.increased_dot[0].damage_types

    def test_dot_mods_dont_conflict_with_hit_mods(self):
        """Ensure 'increased Fire Damage' still goes to hit pool, not DoT."""
        result = parse_mods(["50% increased Fire Damage"])
        assert len(result.increased) == 1
        assert len(result.increased_dot) == 0


# ===========================================================================
# Ailment chance tests
# ===========================================================================


class TestAilmentChance:
    def test_ignite_base_only(self):
        chance = calc_effective_ailment_chance(50.0, 0.0, "ignite")
        assert chance == pytest.approx(0.5)

    def test_ignite_crit_guarantees(self):
        # 0% base ignite but 100% crit → 100% ignite
        chance = calc_effective_ailment_chance(0.0, 1.0, "ignite")
        assert chance == pytest.approx(1.0)

    def test_ignite_crit_adds_to_base(self):
        # 50% base, 50% crit → 0.5 + 0.5*0.5 = 0.75
        chance = calc_effective_ailment_chance(50.0, 0.5, "ignite")
        assert chance == pytest.approx(0.75)

    def test_bleed_crit_no_effect(self):
        # Crit doesn't guarantee bleed
        chance = calc_effective_ailment_chance(25.0, 1.0, "bleed")
        assert chance == pytest.approx(0.25)

    def test_poison_crit_no_effect(self):
        chance = calc_effective_ailment_chance(60.0, 1.0, "poison")
        assert chance == pytest.approx(0.6)

    def test_zero_chance_zero_result(self):
        chance = calc_effective_ailment_chance(0.0, 0.0, "ignite")
        assert chance == pytest.approx(0.0)


# ===========================================================================
# Ignite unit tests
# ===========================================================================


class TestIgniteCalc:
    def _pool(self, **kwargs) -> StatPool:
        return StatPool(**kwargs)

    def test_base_formula(self):
        # 100 fire hit → 50 ignite DPS (50% per second)
        pool = self._pool()
        dps = calc_ignite_dps(100.0, pool, CalcConfig(), 1.0)
        assert dps == pytest.approx(50.0)

    def test_with_increased_fire(self):
        # 100% increased fire applies to ignite
        pool = self._pool(increased_mods=[
            Modifier(stat="inc_fire", value=100.0, damage_types=[DamageType.FIRE]),
        ])
        dps = calc_ignite_dps(100.0, pool, CalcConfig(), 1.0)
        # 50 * (1 + 1.0) = 100
        assert dps == pytest.approx(100.0)

    def test_with_burning_damage(self):
        # Burning damage is DoT-specific, applies to ignite
        pool = self._pool(increased_dot_mods=[
            Modifier(stat="inc_burning", value=50.0, damage_types=[DamageType.FIRE]),
        ])
        dps = calc_ignite_dps(100.0, pool, CalcConfig(), 1.0)
        # 50 * (1 + 0.5) = 75
        assert dps == pytest.approx(75.0)

    def test_attack_damage_excluded(self):
        # "increased Attack Damage" does NOT apply to ignite
        pool = self._pool(increased_mods=[
            Modifier(stat="increased_attack_damage", value=100.0),
        ])
        dps = calc_ignite_dps(100.0, pool, CalcConfig(), 1.0)
        assert dps == pytest.approx(50.0)  # no bonus

    def test_spell_damage_excluded(self):
        pool = self._pool(increased_mods=[
            Modifier(stat="increased_spell_damage", value=100.0),
        ])
        dps = calc_ignite_dps(100.0, pool, CalcConfig(), 1.0)
        assert dps == pytest.approx(50.0)

    def test_enemy_fire_resist(self):
        config = CalcConfig(enemy_fire_resist=40.0)
        pool = self._pool()
        dps = calc_ignite_dps(100.0, pool, config, 1.0)
        # 50 * 0.6 = 30
        assert dps == pytest.approx(30.0)

    def test_no_penetration_for_dot(self):
        # Penetration does NOT reduce resist for ignite
        config = CalcConfig(enemy_fire_resist=40.0)
        pool = self._pool(penetration={DamageType.FIRE: 20.0})
        dps = calc_ignite_dps(100.0, pool, config, 1.0)
        # Still 50 * 0.6 = 30 (pen ignored)
        assert dps == pytest.approx(30.0)

    def test_dot_multiplier(self):
        pool = self._pool(dot_multi=20.0, dot_multi_fire=30.0)
        dps = calc_ignite_dps(100.0, pool, CalcConfig(), 1.0)
        # 50 * (1 + (20+30)/100) = 50 * 1.5 = 75
        assert dps == pytest.approx(75.0)

    def test_zero_chance(self):
        dps = calc_ignite_dps(100.0, self._pool(), CalcConfig(), 0.0)
        assert dps == pytest.approx(0.0)

    def test_partial_chance(self):
        dps = calc_ignite_dps(100.0, self._pool(), CalcConfig(), 0.5)
        # 50 * 0.5 = 25
        assert dps == pytest.approx(25.0)

    def test_zero_fire_damage(self):
        dps = calc_ignite_dps(0.0, self._pool(), CalcConfig(), 1.0)
        assert dps == pytest.approx(0.0)

    def test_more_multiplier(self):
        pool = self._pool(more_mods=[
            Modifier(stat="more_fire", value=50.0, mod_type="more", damage_types=[DamageType.FIRE]),
        ])
        dps = calc_ignite_dps(100.0, pool, CalcConfig(), 1.0)
        # 50 * 1.5 = 75
        assert dps == pytest.approx(75.0)


# ===========================================================================
# Bleed unit tests
# ===========================================================================


class TestBleedCalc:
    def _pool(self, **kwargs) -> StatPool:
        return StatPool(**kwargs)

    def test_base_formula_moving(self):
        # 100 phys → 70 base * 3 (moving) = 210 DPS
        config = CalcConfig(enemy_is_moving=True)
        dps = calc_bleed_dps(100.0, self._pool(), config, 1.0, is_attack=True)
        assert dps == pytest.approx(210.0)

    def test_base_formula_stationary(self):
        config = CalcConfig(enemy_is_moving=False)
        dps = calc_bleed_dps(100.0, self._pool(), config, 1.0, is_attack=True)
        assert dps == pytest.approx(70.0)

    def test_spell_returns_zero(self):
        dps = calc_bleed_dps(100.0, self._pool(), CalcConfig(), 1.0, is_attack=False)
        assert dps == pytest.approx(0.0)

    def test_no_phys_reduction_for_bleed(self):
        # Enemy phys reduction ignored for bleed
        config = CalcConfig(enemy_phys_reduction=50.0, enemy_is_moving=False)
        dps = calc_bleed_dps(100.0, self._pool(), config, 1.0, is_attack=True)
        assert dps == pytest.approx(70.0)  # not reduced

    def test_with_increased_phys(self):
        pool = self._pool(increased_mods=[
            Modifier(stat="inc_phys", value=100.0, damage_types=[DamageType.PHYSICAL]),
        ])
        config = CalcConfig(enemy_is_moving=False)
        dps = calc_bleed_dps(100.0, pool, config, 1.0, is_attack=True)
        # 70 * (1 + 1.0) = 140
        assert dps == pytest.approx(140.0)

    def test_dot_multiplier_phys(self):
        pool = self._pool(dot_multi_phys=50.0)
        config = CalcConfig(enemy_is_moving=False)
        dps = calc_bleed_dps(100.0, pool, config, 1.0, is_attack=True)
        # 70 * 1.5 = 105
        assert dps == pytest.approx(105.0)

    def test_zero_chance(self):
        dps = calc_bleed_dps(100.0, self._pool(), CalcConfig(), 0.0, is_attack=True)
        assert dps == pytest.approx(0.0)


# ===========================================================================
# Poison unit tests
# ===========================================================================


class TestPoisonCalc:
    def _pool(self, **kwargs) -> StatPool:
        return StatPool(**kwargs)

    def test_base_formula(self):
        # (100 phys + 50 chaos) * 0.2 = 30 per stack
        # 2s duration * 2 hits/sec * 100% chance = 4 stacks
        # 30 * 4 = 120
        dps = calc_poison_dps(100.0, 50.0, self._pool(), CalcConfig(), 1.0, 2.0)
        assert dps == pytest.approx(120.0)

    def test_stacking_with_speed(self):
        # 1 hit/sec, 2s duration, 100% chance → 2 stacks
        dps = calc_poison_dps(100.0, 0.0, self._pool(), CalcConfig(), 1.0, 1.0)
        # 100 * 0.2 = 20 per stack, 2 stacks = 40
        assert dps == pytest.approx(40.0)

    def test_duration_increase(self):
        # +50% poison duration → 3s
        pool = self._pool(increased_poison_duration=50.0)
        dps = calc_poison_dps(100.0, 0.0, pool, CalcConfig(), 1.0, 1.0)
        # 20 per stack * 3 stacks = 60
        assert dps == pytest.approx(60.0)

    def test_enemy_chaos_resist(self):
        config = CalcConfig(enemy_chaos_resist=25.0)
        dps = calc_poison_dps(100.0, 0.0, self._pool(), config, 1.0, 1.0)
        # 20 * 0.75 * 2 stacks = 30
        assert dps == pytest.approx(30.0)

    def test_with_increased_chaos(self):
        pool = self._pool(increased_mods=[
            Modifier(stat="inc_chaos", value=100.0, damage_types=[DamageType.CHAOS]),
        ])
        dps = calc_poison_dps(100.0, 0.0, pool, CalcConfig(), 1.0, 1.0)
        # 20 * 2.0 * 2 stacks = 80
        assert dps == pytest.approx(80.0)

    def test_dot_multiplier_chaos(self):
        pool = self._pool(dot_multi=10.0, dot_multi_chaos=20.0)
        dps = calc_poison_dps(100.0, 0.0, pool, CalcConfig(), 1.0, 1.0)
        # 20 * 1.3 * 2 stacks = 52
        assert dps == pytest.approx(52.0)

    def test_zero_damage(self):
        dps = calc_poison_dps(0.0, 0.0, self._pool(), CalcConfig(), 1.0, 2.0)
        assert dps == pytest.approx(0.0)

    def test_zero_chance(self):
        dps = calc_poison_dps(100.0, 50.0, self._pool(), CalcConfig(), 0.0, 2.0)
        assert dps == pytest.approx(0.0)

    def test_partial_chance(self):
        # 50% chance → half the stacks
        dps = calc_poison_dps(100.0, 0.0, self._pool(), CalcConfig(), 0.5, 1.0)
        # 20 per stack * (2s * 1 hit/s * 0.5) = 20 * 1 = 20
        assert dps == pytest.approx(20.0)


# ===========================================================================
# Full pipeline integration tests
# ===========================================================================


class TestEnginePhaseDIntegration:
    _WEAPON_RAW = (
        "Rarity: RARE\nTest Sword\nCorsair Sword\n"
        "Physical Damage: 100-200\n"
        "Attacks per Second: 1.5\n"
        "Critical Strike Chance: 5.0%\n"
        "Implicits: 0\n"
    )

    def _make_attack_build(
        self,
        weapon_mods: list[str] | None = None,
        gear_mods: dict[str, list[str]] | None = None,
        config_entries: dict[str, str] | None = None,
    ) -> Build:
        weapon = Item(
            id=1, slot="Weapon 1", name="Test Sword", base_type="Corsair Sword",
            raw_text=self._WEAPON_RAW,
            explicits=[ItemMod(text=t) for t in (weapon_mods or [])],
        )
        items = [weapon]
        for slot, mods in (gear_mods or {}).items():
            items.append(Item(
                id=len(items) + 1, slot=slot, name=f"Test {slot}", base_type=f"Test {slot}",
                explicits=[ItemMod(text=t) for t in mods],
            ))
        main_skill = SkillGroup(
            slot="Weapon 1", label="Main", is_enabled=True,
            gems=[Gem(name="Cyclone", gem_id="ActiveSkill/Cyclone")],
        )
        return Build(
            class_name="Duelist", ascendancy_name="Slayer", level=90,
            main_socket_group=1, skill_groups=[main_skill], items=items,
            config=BuildConfig(entries=config_entries or {}),
        )

    def test_no_ailment_chance_no_dot(self):
        """Without ignite/bleed/poison chance, all DoT DPS should be 0."""
        build = self._make_attack_build()
        result = calculate_dps(build)
        assert result.ignite_dps == 0.0
        assert result.bleed_dps == 0.0
        assert result.poison_dps == 0.0
        assert result.total_dot_dps == 0.0
        assert result.combined_dps == result.total_dps

    def test_ignite_in_pipeline(self):
        """100% phys→fire + 100% ignite chance → ignite DPS > 0."""
        build = self._make_attack_build(
            weapon_mods=[
                "100% of Physical Damage Converted to Fire Damage",
            ],
            gear_mods={
                "Helmet": ["100% chance to Ignite"],
            },
        )
        result = calculate_dps(build)
        # 150 fire hit → 75 ignite DPS base, 100% chance
        assert result.ignite_dps == pytest.approx(75.0, rel=0.01)
        assert result.total_dot_dps > 0
        assert result.combined_dps > result.total_dps

    def test_bleed_in_pipeline(self):
        """25% bleed chance → bleed DPS > 0 (attacks only, moving enemy)."""
        build = self._make_attack_build(
            gear_mods={
                "Gloves": ["25% chance to cause Bleeding"],
            },
        )
        result = calculate_dps(build)
        # 150 phys * 0.7 * 3 (moving) * 0.25 chance = 78.75
        assert result.bleed_dps == pytest.approx(78.75, rel=0.01)

    def test_poison_in_pipeline(self):
        """100% poison chance with phys damage → stacking poison."""
        build = self._make_attack_build(
            gear_mods={
                "Gloves": ["Poisons Enemies on Hit"],
            },
        )
        result = calculate_dps(build)
        # 150 phys * 0.2 = 30 per stack
        # Stacks = 2s * hits_per_second * 1.0 chance
        # hits_per_second = 1.5 * 3.0 (cyclone) = 4.5
        # Stacks = 2 * 4.5 = 9, DPS = 30 * 9 = 270
        assert result.poison_dps == pytest.approx(270.0, rel=0.01)

    def test_combined_dps_includes_dot(self):
        """combined_dps = hit DPS + total DoT DPS."""
        build = self._make_attack_build(
            gear_mods={
                "Gloves": ["100% chance to Ignite"],
            },
            weapon_mods=["100% of Physical Damage Converted to Fire Damage"],
        )
        result = calculate_dps(build)
        expected_combined = result.total_dps + result.total_dot_dps
        assert result.combined_dps == pytest.approx(expected_combined, rel=0.01)

    def test_ignite_with_burning_damage_mod(self):
        """Burning damage mod should boost ignite DPS."""
        build_base = self._make_attack_build(
            weapon_mods=["100% of Physical Damage Converted to Fire Damage"],
            gear_mods={"Helmet": ["100% chance to Ignite"]},
        )
        build_with_burning = self._make_attack_build(
            weapon_mods=["100% of Physical Damage Converted to Fire Damage"],
            gear_mods={
                "Helmet": ["100% chance to Ignite"],
                "Gloves": ["100% increased Burning Damage"],
            },
        )
        result_base = calculate_dps(build_base)
        result_burning = calculate_dps(build_with_burning)
        # 100% increased burning should double ignite DPS
        assert result_burning.ignite_dps == pytest.approx(
            result_base.ignite_dps * 2.0, rel=0.01,
        )

    def test_ignite_crit_grants_chance(self):
        """High crit with no explicit ignite chance should still ignite via crits."""
        build = self._make_attack_build(
            weapon_mods=["100% of Physical Damage Converted to Fire Damage"],
            gear_mods={
                # High crit but no ignite chance mod
                "Amulet": ["500% increased Critical Strike Chance"],
            },
        )
        result = calculate_dps(build)
        # 5% base crit * (1 + 5.0) = 30% crit → ~30% effective ignite
        assert result.ignite_dps > 0

    def test_dot_multiplier_in_pipeline(self):
        """DoT multiplier should boost ignite."""
        build = self._make_attack_build(
            weapon_mods=["100% of Physical Damage Converted to Fire Damage"],
            gear_mods={
                "Helmet": ["100% chance to Ignite"],
                "Gloves": ["+50% to Fire Damage over Time Multiplier"],
            },
        )
        result = calculate_dps(build)
        # Base ignite: 75. With 50% fire DoT multi: 75 * 1.5 = 112.5
        assert result.ignite_dps == pytest.approx(112.5, rel=0.01)
