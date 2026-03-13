"""
Tests for the damage calculation engine (pop.calc).

Tests cover:
- Mod parser (regex extraction)
- Crit calculation
- Speed calculation
- Conversion chain
- Defense mitigation
- Full engine pipeline
"""

import pytest

from pop.build_parser.models import (
    Build,
    BuildConfig,
    Gem,
    Item,
    ItemMod,
    PassiveSpec,
    SkillGroup,
)
from pop.calc.config_reader import read_config
from pop.calc.conversion import apply_conversion
from pop.calc.crit_calc import calc_crit_dps_multi, calc_effective_crit
from pop.calc.defense_calc import calc_mitigation_multi
from pop.calc.engine import calculate_dps
from pop.calc.gem_data import get_active_gem_stats, get_support_effect
from pop.calc.mod_parser import ParsedMods, parse_mods
from pop.calc.models import (
    CalcConfig,
    CalcResult,
    ConversionEntry,
    DamageType,
    Modifier,
    StatPool,
)
from pop.calc.speed_calc import calc_hits_per_second


# ===========================================================================
# Mod parser tests
# ===========================================================================


class TestModParser:
    def test_flat_added_damage(self):
        mods = ["Adds 10 to 20 Physical Damage"]
        result = parse_mods(mods)
        assert DamageType.PHYSICAL in result.flat_added
        assert result.flat_added[DamageType.PHYSICAL] == 15.0

    def test_flat_added_to_attacks(self):
        mods = ["Adds 5 to 15 Fire Damage to Attacks"]
        result = parse_mods(mods)
        assert DamageType.FIRE in result.flat_added_attacks
        assert result.flat_added_attacks[DamageType.FIRE] == 10.0
        assert DamageType.FIRE not in result.flat_added

    def test_flat_added_to_spells(self):
        mods = ["Adds 8 to 12 Cold Damage to Spells"]
        result = parse_mods(mods)
        assert DamageType.COLD in result.flat_added_spells
        assert result.flat_added_spells[DamageType.COLD] == 10.0

    def test_increased_typed(self):
        mods = ["40% increased Fire Damage"]
        result = parse_mods(mods)
        assert len(result.increased) == 1
        assert result.increased[0].value == 40.0
        assert DamageType.FIRE in result.increased[0].damage_types

    def test_increased_elemental(self):
        mods = ["30% increased Elemental Damage"]
        result = parse_mods(mods)
        assert len(result.increased) == 1
        types = result.increased[0].damage_types
        assert DamageType.FIRE in types
        assert DamageType.COLD in types
        assert DamageType.LIGHTNING in types

    def test_increased_generic(self):
        mods = ["20% increased Damage"]
        result = parse_mods(mods)
        assert len(result.increased) == 1
        assert result.increased[0].damage_types == []  # applies to all

    def test_more_typed(self):
        mods = ["49% more Physical Damage"]
        result = parse_mods(mods)
        assert len(result.more) == 1
        assert result.more[0].value == 49.0
        assert result.more[0].mod_type == "more"

    def test_more_generic(self):
        mods = ["20% more Damage"]
        result = parse_mods(mods)
        assert len(result.more) == 1
        assert result.more[0].value == 20.0
        assert result.more[0].damage_types == []

    def test_less_damage(self):
        mods = ["26% less Damage"]
        result = parse_mods(mods)
        assert len(result.more) == 1
        assert result.more[0].value == -26.0

    def test_conversion(self):
        mods = ["50% of Physical Damage Converted to Fire Damage"]
        result = parse_mods(mods)
        assert len(result.conversions) == 1
        assert result.conversions[0].type_from == DamageType.PHYSICAL
        assert result.conversions[0].type_to == DamageType.FIRE
        assert result.conversions[0].percent == 50.0
        assert result.conversions[0].is_gained_as is False

    def test_gained_as_extra(self):
        mods = ["Gain 25% of Physical Damage as Extra Fire Damage"]
        result = parse_mods(mods)
        assert len(result.conversions) == 1
        assert result.conversions[0].is_gained_as is True
        assert result.conversions[0].percent == 25.0

    def test_penetration(self):
        mods = ["Penetrates 10% Fire Resistance"]
        result = parse_mods(mods)
        assert result.penetration[DamageType.FIRE] == 10.0

    def test_penetration_elemental(self):
        mods = ["Penetrates 5% Elemental Resistance"]
        result = parse_mods(mods)
        assert result.penetration[DamageType.FIRE] == 5.0
        assert result.penetration[DamageType.COLD] == 5.0
        assert result.penetration[DamageType.LIGHTNING] == 5.0

    def test_crit_chance(self):
        mods = ["80% increased Critical Strike Chance"]
        result = parse_mods(mods)
        assert result.increased_crit == 80.0

    def test_crit_multi(self):
        mods = ["+30% to Critical Strike Multiplier"]
        result = parse_mods(mods)
        assert result.crit_multi == 30.0

    def test_attack_speed(self):
        mods = ["15% increased Attack Speed"]
        result = parse_mods(mods)
        assert result.increased_attack_speed == 15.0

    def test_cast_speed(self):
        mods = ["20% increased Cast Speed"]
        result = parse_mods(mods)
        assert result.increased_cast_speed == 20.0

    def test_more_attack_speed(self):
        mods = ["10% more Attack Speed"]
        result = parse_mods(mods)
        assert 10.0 in result.more_attack_speed

    def test_less_attack_speed(self):
        mods = ["10% less Attack Speed"]
        result = parse_mods(mods)
        assert 10.0 in result.less_attack_speed

    def test_merge(self):
        a = parse_mods(["Adds 10 to 20 Physical Damage", "40% increased Fire Damage"])
        b = parse_mods(["Adds 5 to 15 Physical Damage", "20% increased Fire Damage"])
        a.merge(b)
        assert a.flat_added[DamageType.PHYSICAL] == 25.0  # 15 + 10
        assert len(a.increased) == 2

    def test_increased_spell_damage(self):
        mods = ["50% increased Spell Damage"]
        result = parse_mods(mods)
        assert len(result.increased) == 1
        assert result.increased[0].stat == "increased_spell_damage"

    def test_increased_weapon_type(self):
        mods = ["30% increased Damage with Swords"]
        result = parse_mods(mods)
        assert len(result.increased) == 1
        assert "sword" in result.increased[0].stat.lower()

    def test_multiple_mods(self):
        mods = [
            "Adds 10 to 20 Physical Damage",
            "40% increased Physical Damage",
            "10% more Damage",
            "+25% to Critical Strike Multiplier",
            "15% increased Attack Speed",
        ]
        result = parse_mods(mods)
        assert DamageType.PHYSICAL in result.flat_added
        assert len(result.increased) == 1
        assert len(result.more) == 1
        assert result.crit_multi == 25.0
        assert result.increased_attack_speed == 15.0


# ===========================================================================
# Crit calculation tests
# ===========================================================================


class TestCritCalc:
    def test_base_crit(self):
        chance = calc_effective_crit(5.0, 0.0)
        assert chance == pytest.approx(0.05)

    def test_increased_crit(self):
        chance = calc_effective_crit(5.0, 200.0)
        assert chance == pytest.approx(0.15)

    def test_crit_cap_poe1(self):
        chance = calc_effective_crit(5.0, 10000.0)
        assert chance == pytest.approx(1.0)

    def test_crit_cap_poe2(self):
        chance = calc_effective_crit(5.0, 10000.0, is_poe2=True)
        assert chance == pytest.approx(0.8)

    def test_crit_dps_multi_no_crit(self):
        multi = calc_crit_dps_multi(0.0, 150.0)
        assert multi == pytest.approx(1.0)

    def test_crit_dps_multi_50pct(self):
        multi = calc_crit_dps_multi(0.5, 200.0)
        assert multi == pytest.approx(1.5)

    def test_crit_dps_multi_100pct(self):
        multi = calc_crit_dps_multi(1.0, 150.0)
        assert multi == pytest.approx(1.5)


# ===========================================================================
# Speed calculation tests
# ===========================================================================


class TestSpeedCalc:
    def test_base_speed(self):
        speed = calc_hits_per_second(1.5, 0.0, [])
        assert speed == pytest.approx(1.5)

    def test_increased_speed(self):
        speed = calc_hits_per_second(1.5, 100.0, [])
        assert speed == pytest.approx(3.0)

    def test_more_speed(self):
        speed = calc_hits_per_second(1.5, 0.0, [50.0])
        assert speed == pytest.approx(2.25)

    def test_less_speed(self):
        speed = calc_hits_per_second(1.5, 0.0, [], [50.0])
        assert speed == pytest.approx(0.75)

    def test_combined(self):
        # 1.5 * (1 + 0.5) * (1 + 0.2) * (1 - 0.1) = 1.5 * 1.5 * 1.2 * 0.9
        speed = calc_hits_per_second(1.5, 50.0, [20.0], [10.0])
        assert speed == pytest.approx(1.5 * 1.5 * 1.2 * 0.9)


# ===========================================================================
# Conversion tests
# ===========================================================================


class TestConversion:
    def test_no_conversion(self):
        base = {DamageType.PHYSICAL: 100.0}
        result = apply_conversion(base, [])
        assert result[DamageType.PHYSICAL] == pytest.approx(100.0)

    def test_full_conversion(self):
        base = {DamageType.PHYSICAL: 100.0}
        convs = [ConversionEntry(
            type_from=DamageType.PHYSICAL,
            type_to=DamageType.FIRE,
            percent=100.0,
        )]
        result = apply_conversion(base, convs)
        assert result[DamageType.PHYSICAL] == pytest.approx(0.0)
        assert result[DamageType.FIRE] == pytest.approx(100.0)

    def test_partial_conversion(self):
        base = {DamageType.PHYSICAL: 100.0}
        convs = [ConversionEntry(
            type_from=DamageType.PHYSICAL,
            type_to=DamageType.FIRE,
            percent=50.0,
        )]
        result = apply_conversion(base, convs)
        assert result[DamageType.PHYSICAL] == pytest.approx(50.0)
        assert result[DamageType.FIRE] == pytest.approx(50.0)

    def test_gained_as_extra(self):
        base = {DamageType.PHYSICAL: 100.0}
        convs = [ConversionEntry(
            type_from=DamageType.PHYSICAL,
            type_to=DamageType.FIRE,
            percent=25.0,
            is_gained_as=True,
        )]
        result = apply_conversion(base, convs)
        assert result[DamageType.PHYSICAL] == pytest.approx(100.0)  # unchanged
        assert result[DamageType.FIRE] == pytest.approx(25.0)

    def test_over_100_percent_scaled(self):
        base = {DamageType.PHYSICAL: 100.0}
        convs = [
            ConversionEntry(type_from=DamageType.PHYSICAL, type_to=DamageType.FIRE, percent=60.0),
            ConversionEntry(type_from=DamageType.PHYSICAL, type_to=DamageType.COLD, percent=60.0),
        ]
        result = apply_conversion(base, convs)
        # Total conversion = 120%, scaled to 100%
        # Each gets 60/120 * 100 = 50%
        assert result[DamageType.PHYSICAL] == pytest.approx(0.0)
        assert result[DamageType.FIRE] == pytest.approx(50.0)
        assert result[DamageType.COLD] == pytest.approx(50.0)

    def test_chain_conversion(self):
        base = {DamageType.PHYSICAL: 100.0}
        convs = [
            ConversionEntry(type_from=DamageType.PHYSICAL, type_to=DamageType.LIGHTNING, percent=50.0),
            ConversionEntry(type_from=DamageType.LIGHTNING, type_to=DamageType.COLD, percent=100.0),
        ]
        result = apply_conversion(base, convs)
        assert result[DamageType.PHYSICAL] == pytest.approx(50.0)
        assert result[DamageType.LIGHTNING] == pytest.approx(0.0)
        assert result[DamageType.COLD] == pytest.approx(50.0)


# ===========================================================================
# Defense mitigation tests
# ===========================================================================


class TestDefenseCalc:
    def test_no_resist(self):
        config = CalcConfig()
        multi = calc_mitigation_multi(DamageType.FIRE, config)
        assert multi == pytest.approx(1.0)

    def test_positive_resist(self):
        config = CalcConfig(enemy_fire_resist=40.0)
        multi = calc_mitigation_multi(DamageType.FIRE, config)
        assert multi == pytest.approx(0.6)

    def test_resist_with_penetration(self):
        config = CalcConfig(enemy_fire_resist=40.0)
        multi = calc_mitigation_multi(DamageType.FIRE, config, penetration=20.0)
        assert multi == pytest.approx(0.8)

    def test_negative_resist(self):
        config = CalcConfig(enemy_fire_resist=-50.0)
        multi = calc_mitigation_multi(DamageType.FIRE, config)
        assert multi == pytest.approx(1.5)

    def test_phys_reduction(self):
        config = CalcConfig(enemy_phys_reduction=20.0)
        multi = calc_mitigation_multi(DamageType.PHYSICAL, config)
        assert multi == pytest.approx(0.8)


# ===========================================================================
# Config reader tests
# ===========================================================================


class TestConfigReader:
    def test_empty_config(self):
        cfg = read_config(BuildConfig())
        assert cfg.enemy_is_boss is False
        assert cfg.enemy_fire_resist == 0.0

    def test_boss_preset(self):
        cfg = read_config(BuildConfig(entries={"enemyIsBoss": "true"}))
        assert cfg.enemy_is_boss is True
        assert cfg.enemy_fire_resist == 40.0  # Shaper preset

    def test_custom_resist(self):
        cfg = read_config(BuildConfig(entries={
            "enemyIsBoss": "true",
            "enemyFireResist": "30",
        }))
        # Custom resist set, boss preset should NOT override
        assert cfg.enemy_fire_resist == 30.0

    def test_poe2_detection(self):
        cfg = read_config(BuildConfig(), tree_version="poe2_1.0")
        assert cfg.is_poe2 is True

    def test_charges(self):
        cfg = read_config(BuildConfig(entries={
            "useFrenzyCharges": "true",
            "frenzyCharges": "3",
        }))
        assert cfg.use_frenzy_charges is True
        assert cfg.frenzy_charges == 3


# ===========================================================================
# Gem data tests
# ===========================================================================


class TestGemData:
    def test_known_active_gem(self):
        stats = get_active_gem_stats("Cyclone")
        assert stats is not None
        assert stats.is_attack is True
        assert "melee" in stats.tags

    def test_known_spell_gem(self):
        stats = get_active_gem_stats("Arc")
        assert stats is not None
        assert stats.is_spell is True
        assert DamageType.LIGHTNING in stats.base_damage

    def test_unknown_gem(self):
        stats = get_active_gem_stats("NonExistentSkill")
        assert stats is None

    def test_known_support(self):
        effect = get_support_effect("Brutality Support")
        assert effect is not None
        assert len(effect.modifiers) > 0
        assert effect.modifiers[0].value == 59

    def test_unknown_support(self):
        effect = get_support_effect("NonExistentSupport")
        assert effect is None


# ===========================================================================
# Full engine integration tests
# ===========================================================================


class TestEngine:
    def _make_attack_build(
        self,
        weapon_raw: str = "",
        weapon_mods: list[str] | None = None,
        support_names: list[str] | None = None,
        gear_mods: dict[str, list[str]] | None = None,
        config_entries: dict[str, str] | None = None,
    ) -> Build:
        """Create a minimal attack build for testing."""
        # Weapon item
        weapon = Item(
            id=1,
            slot="Weapon 1",
            name="Test Sword",
            base_type="Corsair Sword",
            raw_text=weapon_raw,
            implicits=[],
            explicits=[ItemMod(text=t) for t in (weapon_mods or [])],
        )
        items = [weapon]

        # Additional gear
        for slot, mods in (gear_mods or {}).items():
            items.append(Item(
                id=len(items) + 1,
                slot=slot,
                name=f"Test {slot}",
                base_type=f"Test {slot}",
                explicits=[ItemMod(text=t) for t in mods],
            ))

        # Supports
        support_gems = [
            Gem(name=name, gem_id=f"Support/{name.replace(' ', '')}", is_support=True)
            for name in (support_names or [])
        ]

        # Main skill
        main_skill = SkillGroup(
            slot="Weapon 1",
            label="Main",
            is_enabled=True,
            gems=[
                Gem(name="Cyclone", gem_id="ActiveSkill/Cyclone", is_support=False),
                *support_gems,
            ],
        )

        return Build(
            class_name="Duelist",
            ascendancy_name="Slayer",
            level=90,
            main_socket_group=1,
            skill_groups=[main_skill],
            items=items,
            config=BuildConfig(entries=config_entries or {}),
        )

    def _make_spell_build(
        self,
        spell_name: str = "Arc",
        support_names: list[str] | None = None,
        gear_mods: dict[str, list[str]] | None = None,
    ) -> Build:
        """Create a minimal spell build for testing."""
        items = []
        for slot, mods in (gear_mods or {}).items():
            items.append(Item(
                id=len(items) + 1,
                slot=slot,
                name=f"Test {slot}",
                base_type=f"Test {slot}",
                explicits=[ItemMod(text=t) for t in mods],
            ))

        support_gems = [
            Gem(name=name, gem_id=f"Support/{name.replace(' ', '')}", is_support=True)
            for name in (support_names or [])
        ]

        main_skill = SkillGroup(
            slot="Body Armour",
            label="Main",
            is_enabled=True,
            gems=[
                Gem(name=spell_name, gem_id=f"ActiveSkill/{spell_name.replace(' ', '')}"),
                *support_gems,
            ],
        )

        return Build(
            class_name="Witch",
            ascendancy_name="Elementalist",
            level=90,
            main_socket_group=1,
            skill_groups=[main_skill],
            items=items,
            config=BuildConfig(),
        )

    def test_no_main_skill(self):
        build = Build()
        result = calculate_dps(build)
        assert "No main skill" in result.warnings[0]
        assert result.total_dps == 0.0

    def test_basic_attack_weapon_only(self):
        build = self._make_attack_build(
            weapon_raw=(
                "Rarity: RARE\nTest Sword\nCorsair Sword\n"
                "Physical Damage: 100-200\n"
                "Attacks per Second: 1.5\n"
                "Critical Strike Chance: 6.0%\n"
                "Implicits: 0\n"
            ),
        )
        result = calculate_dps(build)
        assert result.total_dps > 0
        assert result.skill_name == "Cyclone"
        assert result.is_attack is True
        # Base: avg 150 phys * 0.56 (cyclone effectiveness applied to flat, not base)
        # Actually base weapon damage is 150, no flat added from elsewhere
        # Speed: 1.5 * 3.0 (cyclone 300% attack speed multi) = 4.5
        # Crit: 6% base, no increased = 6% chance, 150% multi → 1.03 effective
        # DPS ≈ 150 * 1.03 * 4.5 ≈ 695.25
        assert result.hits_per_second == pytest.approx(4.5)
        # PoB-aligned: hit_damage = avgHit (after crit averaging)
        # 6% base crit, 150% multi → effective_crit_multi = 1.03
        # avgHit = 150 * 1.03 = 154.5
        assert result.hit_damage == pytest.approx(150.0 * 1.03, rel=0.01)

    def test_attack_with_increased(self):
        build = self._make_attack_build(
            weapon_raw=(
                "Rarity: RARE\nTest Sword\nCorsair Sword\n"
                "Physical Damage: 100-200\n"
                "Attacks per Second: 1.5\n"
                "Critical Strike Chance: 5.0%\n"
                "Implicits: 0\n"
            ),
            weapon_mods=["40% increased Physical Damage"],
            gear_mods={
                "Helmet": ["60% increased Physical Damage"],
            },
        )
        result = calculate_dps(build)
        # Weapon "40% increased Physical Damage" is local (baked into weapon
        # damage line already), so only helmet 60% counts globally.
        # 5% crit, 150% multi → ecm = 1.025
        # avgHit = 150 * 1.6 * 1.025 = 246.0
        assert result.hit_damage == pytest.approx(150.0 * 1.6 * 1.025, rel=0.02)

    def test_attack_with_more(self):
        build = self._make_attack_build(
            weapon_raw=(
                "Rarity: RARE\nTest Sword\nCorsair Sword\n"
                "Physical Damage: 100-200\n"
                "Attacks per Second: 1.5\n"
                "Critical Strike Chance: 5.0%\n"
                "Implicits: 0\n"
            ),
            support_names=["Brutality Support"],
        )
        result = calculate_dps(build)
        # Brutality: 59% more physical
        # 5% crit, 150% multi → ecm = 1.025
        # avgHit = 150 * 1.59 * 1.025 = 244.4625
        assert result.hit_damage == pytest.approx(150.0 * 1.59 * 1.025, rel=0.02)

    def test_attack_with_flat_added(self):
        build = self._make_attack_build(
            weapon_raw=(
                "Rarity: RARE\nTest Sword\nCorsair Sword\n"
                "Physical Damage: 100-200\n"
                "Attacks per Second: 1.5\n"
                "Critical Strike Chance: 5.0%\n"
                "Implicits: 0\n"
            ),
            gear_mods={
                "Ring 1": ["Adds 10 to 20 Fire Damage to Attacks"],
            },
        )
        result = calculate_dps(build)
        # Cyclone damage effectiveness = 0.56
        # Flat fire from ring: avg 15 * 0.56 = 8.4
        # Phys: 150, Fire: 8.4
        phys_breakdown = next(
            t for t in result.type_breakdown if t.damage_type == DamageType.PHYSICAL
        )
        fire_breakdown = next(
            t for t in result.type_breakdown if t.damage_type == DamageType.FIRE
        )
        assert phys_breakdown.after_mitigation == pytest.approx(150.0)
        assert fire_breakdown.after_mitigation == pytest.approx(8.4, rel=0.01)

    def test_spell_basic(self):
        build = self._make_spell_build("Arc")
        result = calculate_dps(build)
        assert result.total_dps > 0
        assert result.skill_name == "Arc"
        assert result.is_attack is False
        # Arc: base ~560.5 lightning, cast time 0.7s → 1/0.7 ≈ 1.43 casts/s
        assert result.hits_per_second == pytest.approx(1.0 / 0.7, rel=0.01)
        lightning = next(
            t for t in result.type_breakdown if t.damage_type == DamageType.LIGHTNING
        )
        assert lightning.after_mitigation == pytest.approx(560.5)

    def test_spell_with_supports(self):
        build = self._make_spell_build(
            "Arc",
            support_names=["Controlled Destruction Support"],
        )
        result = calculate_dps(build)
        # CD Support: 44% more spell damage
        lightning = next(
            t for t in result.type_breakdown if t.damage_type == DamageType.LIGHTNING
        )
        assert lightning.after_more == pytest.approx(560.5 * 1.44, rel=0.01)

    def test_conversion_in_full_pipeline(self):
        build = self._make_attack_build(
            weapon_raw=(
                "Rarity: RARE\nTest Sword\nCorsair Sword\n"
                "Physical Damage: 100-200\n"
                "Attacks per Second: 1.5\n"
                "Critical Strike Chance: 5.0%\n"
                "Implicits: 0\n"
            ),
            weapon_mods=[
                "50% of Physical Damage Converted to Fire Damage",
            ],
        )
        result = calculate_dps(build)
        phys = next(t for t in result.type_breakdown if t.damage_type == DamageType.PHYSICAL)
        fire = next(t for t in result.type_breakdown if t.damage_type == DamageType.FIRE)
        # 150 phys → 75 phys + 75 fire
        assert phys.after_mitigation == pytest.approx(75.0, rel=0.01)
        assert fire.after_mitigation == pytest.approx(75.0, rel=0.01)

    def test_enemy_resist(self):
        build = self._make_spell_build("Arc")
        config = CalcConfig(enemy_lightning_resist=40.0)
        result = calculate_dps(build, config_overrides=config)
        lightning = next(
            t for t in result.type_breakdown if t.damage_type == DamageType.LIGHTNING
        )
        # 560.5 * 0.6 (40% resist)
        assert lightning.after_mitigation == pytest.approx(560.5 * 0.6, rel=0.01)

    def test_penetration_in_pipeline(self):
        build = self._make_spell_build(
            "Arc",
            gear_mods={
                "Ring 1": ["Penetrates 10% Lightning Resistance"],
            },
        )
        config = CalcConfig(enemy_lightning_resist=40.0)
        result = calculate_dps(build, config_overrides=config)
        lightning = next(
            t for t in result.type_breakdown if t.damage_type == DamageType.LIGHTNING
        )
        # 560.5 * (1 - (40-10)/100) = 560.5 * 0.7
        assert lightning.after_mitigation == pytest.approx(560.5 * 0.7, rel=0.01)

    def test_crit_in_pipeline(self):
        build = self._make_attack_build(
            weapon_raw=(
                "Rarity: RARE\nTest Sword\nCorsair Sword\n"
                "Physical Damage: 100-200\n"
                "Attacks per Second: 1.5\n"
                "Critical Strike Chance: 10.0%\n"
                "Implicits: 0\n"
            ),
            gear_mods={
                "Amulet": [
                    "100% increased Critical Strike Chance",
                    "+50% to Critical Strike Multiplier",
                ],
            },
        )
        result = calculate_dps(build)
        # Crit: 10% base * (1 + 100/100) = 20% effective
        # Multi: 150 + 50 = 200%
        # Effective crit multi: 1 + 0.2 * (2.0 - 1) = 1.2
        assert result.crit_chance == pytest.approx(20.0, rel=0.01)
        assert result.effective_crit_multi == pytest.approx(1.2, rel=0.01)

    def test_frenzy_charges(self):
        build = self._make_attack_build(
            weapon_raw=(
                "Rarity: RARE\nTest Sword\nCorsair Sword\n"
                "Physical Damage: 100-200\n"
                "Attacks per Second: 1.5\n"
                "Critical Strike Chance: 5.0%\n"
                "Implicits: 0\n"
            ),
            config_entries={
                "useFrenzyCharges": "true",
                "frenzyCharges": "3",
            },
        )
        result = calculate_dps(build)
        # 3 frenzy charges: 12% more damage, 12% increased speed
        # 5% crit, 150% multi → ecm = 1.025
        # avgHit = 150 * 1.12 * 1.025 = 172.2
        # speed = 1.5 * 3.0 (cyclone) * (1 + 0.12) = 5.04
        assert result.hit_damage == pytest.approx(150.0 * 1.12 * 1.025, rel=0.02)
        assert result.hits_per_second == pytest.approx(1.5 * 3.0 * 1.12, rel=0.01)

    def test_unknown_gem_warning(self):
        build = Build(
            class_name="Duelist",
            level=90,
            main_socket_group=1,
            skill_groups=[SkillGroup(
                slot="Weapon 1",
                is_enabled=True,
                gems=[Gem(name="InventedSkill123", gem_id="ActiveSkill/Invented")],
            )],
            items=[Item(
                id=1, slot="Weapon 1", name="Sword", base_type="Corsair Sword",
                raw_text="Physical Damage: 100-200\nAttacks per Second: 1.5\n"
                         "Critical Strike Chance: 5.0%\nImplicits: 0\n",
            )],
        )
        result = calculate_dps(build)
        assert any("Unknown gem" in w for w in result.warnings)
        # Should still produce a result using heuristics
        assert result.total_dps > 0

    def test_result_type_breakdown_has_all_types(self):
        build = self._make_attack_build(
            weapon_raw=(
                "Rarity: RARE\nTest Sword\nCorsair Sword\n"
                "Physical Damage: 100-200\n"
                "Attacks per Second: 1.5\n"
                "Critical Strike Chance: 5.0%\n"
                "Implicits: 0\n"
            ),
        )
        result = calculate_dps(build)
        types_in_breakdown = {t.damage_type for t in result.type_breakdown}
        assert types_in_breakdown == set(DamageType)
