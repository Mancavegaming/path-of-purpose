"""
Phase C tests: Conversion-modifier interaction, exposure, resist floor.

Tests cover:
- Source-aware modifier application (converted damage benefits from both source and final type mods)
- Chain conversion with modifier interaction
- "Gained as extra" with modifier interaction
- Exposure mechanics
- Resist floor (-200%)
- Conversion tracking correctness (contributions)
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
from pop.calc.conversion import apply_conversion_tracked, DamageContribution
from pop.calc.defense_calc import calc_mitigation_multi
from pop.calc.engine import calculate_dps
from pop.calc.models import (
    CalcConfig,
    ConversionEntry,
    DamageType,
    Modifier,
    StatPool,
)


# ===========================================================================
# Conversion tracking tests
# ===========================================================================


class TestConversionTracking:
    """Tests for the portions-based conversion with source tracking."""

    def test_no_conversion_single_contribution(self):
        base = {DamageType.PHYSICAL: 100.0}
        result = apply_conversion_tracked(base, [])
        assert len(result.contributions) == 1
        c = result.contributions[0]
        assert c.source_type == DamageType.PHYSICAL
        assert c.final_type == DamageType.PHYSICAL
        assert c.amount == pytest.approx(100.0)

    def test_partial_conversion_two_contributions(self):
        base = {DamageType.PHYSICAL: 100.0}
        convs = [ConversionEntry(
            type_from=DamageType.PHYSICAL, type_to=DamageType.FIRE, percent=50.0,
        )]
        result = apply_conversion_tracked(base, convs)
        # Should have two contributions: phys→phys (50) and phys→fire (50)
        by_final = {c.final_type: c for c in result.contributions}
        assert by_final[DamageType.PHYSICAL].source_type == DamageType.PHYSICAL
        assert by_final[DamageType.PHYSICAL].amount == pytest.approx(50.0)
        assert by_final[DamageType.FIRE].source_type == DamageType.PHYSICAL
        assert by_final[DamageType.FIRE].amount == pytest.approx(50.0)

    def test_chain_preserves_original_source(self):
        """Phys→Lightning→Cold: the cold portion should track back to Physical."""
        base = {DamageType.PHYSICAL: 100.0}
        convs = [
            ConversionEntry(type_from=DamageType.PHYSICAL, type_to=DamageType.LIGHTNING, percent=100.0),
            ConversionEntry(type_from=DamageType.LIGHTNING, type_to=DamageType.COLD, percent=100.0),
        ]
        result = apply_conversion_tracked(base, convs)
        assert len(result.contributions) == 1
        c = result.contributions[0]
        assert c.source_type == DamageType.PHYSICAL
        assert c.final_type == DamageType.COLD
        assert c.amount == pytest.approx(100.0)

    def test_gained_as_extra_contribution(self):
        base = {DamageType.PHYSICAL: 100.0}
        convs = [ConversionEntry(
            type_from=DamageType.PHYSICAL, type_to=DamageType.FIRE,
            percent=25.0, is_gained_as=True,
        )]
        result = apply_conversion_tracked(base, convs)
        # phys stays: phys→phys (100), gained: phys→fire (25)
        assert result.final_damage[DamageType.PHYSICAL] == pytest.approx(100.0)
        assert result.final_damage[DamageType.FIRE] == pytest.approx(25.0)
        phys_contrib = [c for c in result.contributions if c.final_type == DamageType.PHYSICAL]
        fire_contrib = [c for c in result.contributions if c.final_type == DamageType.FIRE]
        assert len(phys_contrib) == 1
        assert phys_contrib[0].source_type == DamageType.PHYSICAL
        assert len(fire_contrib) == 1
        assert fire_contrib[0].source_type == DamageType.PHYSICAL

    def test_multi_type_base_damage(self):
        """Base has both phys and lightning; only phys converts."""
        base = {DamageType.PHYSICAL: 100.0, DamageType.LIGHTNING: 50.0}
        convs = [ConversionEntry(
            type_from=DamageType.PHYSICAL, type_to=DamageType.FIRE, percent=100.0,
        )]
        result = apply_conversion_tracked(base, convs)
        assert result.final_damage[DamageType.PHYSICAL] == pytest.approx(0.0)
        assert result.final_damage[DamageType.FIRE] == pytest.approx(100.0)
        assert result.final_damage[DamageType.LIGHTNING] == pytest.approx(50.0)

    def test_chain_partial_preserves_mixed_sources(self):
        """50% phys→lightning, 50% lightning→cold. Lightning has own base + converted."""
        base = {DamageType.PHYSICAL: 100.0, DamageType.LIGHTNING: 40.0}
        convs = [
            ConversionEntry(type_from=DamageType.PHYSICAL, type_to=DamageType.LIGHTNING, percent=50.0),
            ConversionEntry(type_from=DamageType.LIGHTNING, type_to=DamageType.COLD, percent=50.0),
        ]
        result = apply_conversion_tracked(base, convs)
        # Phys: 50 stays as phys→phys
        # Lightning pool: 40 own + 50 from phys = 90
        # 50% of lightning converts to cold: 45 to cold, 45 stays
        # Cold: 45 (from mixed sources)
        assert result.final_damage[DamageType.PHYSICAL] == pytest.approx(50.0)
        assert result.final_damage[DamageType.LIGHTNING] == pytest.approx(45.0)
        assert result.final_damage[DamageType.COLD] == pytest.approx(45.0)

        # Check source attribution: cold should have portions from both phys and lightning
        cold_contribs = [c for c in result.contributions if c.final_type == DamageType.COLD]
        sources = {c.source_type: c.amount for c in cold_contribs}
        # 50 phys-origin lightning * 50% = 25 from phys
        # 40 own lightning * 50% = 20 from lightning
        assert sources[DamageType.PHYSICAL] == pytest.approx(25.0)
        assert sources[DamageType.LIGHTNING] == pytest.approx(20.0)


# ===========================================================================
# Source-aware modifier application tests
# ===========================================================================


class TestSourceAwareModifiers:
    """Test that converted damage benefits from both source and final type modifiers."""

    def test_phys_to_fire_gets_both_increased(self):
        """Phys→Fire conversion: 'increased Physical' AND 'increased Fire' both apply."""
        pool = StatPool()
        pool.increased_mods = [
            Modifier(stat="inc_phys", value=50.0, damage_types=[DamageType.PHYSICAL]),
            Modifier(stat="inc_fire", value=30.0, damage_types=[DamageType.FIRE]),
        ]
        # For a contribution with source=phys, final=fire: both should apply
        relevant = {DamageType.PHYSICAL, DamageType.FIRE}
        total_inc = pool.total_increased_for_types(relevant)
        assert total_inc == pytest.approx(80.0)

    def test_generic_increased_always_applies(self):
        """Generic 'increased Damage' applies regardless of types."""
        pool = StatPool()
        pool.increased_mods = [
            Modifier(stat="inc_generic", value=20.0, damage_types=[]),  # generic
            Modifier(stat="inc_fire", value=30.0, damage_types=[DamageType.FIRE]),
        ]
        relevant = {DamageType.PHYSICAL, DamageType.FIRE}
        total_inc = pool.total_increased_for_types(relevant)
        assert total_inc == pytest.approx(50.0)

    def test_unrelated_type_excluded(self):
        """'increased Cold' should NOT apply to phys→fire contribution."""
        pool = StatPool()
        pool.increased_mods = [
            Modifier(stat="inc_cold", value=40.0, damage_types=[DamageType.COLD]),
            Modifier(stat="inc_phys", value=20.0, damage_types=[DamageType.PHYSICAL]),
        ]
        relevant = {DamageType.PHYSICAL, DamageType.FIRE}
        total_inc = pool.total_increased_for_types(relevant)
        assert total_inc == pytest.approx(20.0)  # only phys

    def test_more_multiplier_source_aware(self):
        """More multipliers also apply based on source+final types."""
        pool = StatPool()
        pool.more_mods = [
            Modifier(stat="more_phys", value=50.0, mod_type="more", damage_types=[DamageType.PHYSICAL]),
            Modifier(stat="more_fire", value=30.0, mod_type="more", damage_types=[DamageType.FIRE]),
            Modifier(stat="more_cold", value=100.0, mod_type="more", damage_types=[DamageType.COLD]),
        ]
        relevant = {DamageType.PHYSICAL, DamageType.FIRE}
        total_more = pool.total_more_for_types(relevant)
        # 1.5 * 1.3 = 1.95 (cold excluded)
        assert total_more == pytest.approx(1.95)

    def test_elemental_increased_applies_to_converted(self):
        """'increased Elemental Damage' should apply to fire portion of phys→fire."""
        pool = StatPool()
        pool.increased_mods = [
            # Elemental damage applies to fire, cold, lightning
            Modifier(
                stat="inc_ele", value=40.0,
                damage_types=[DamageType.FIRE, DamageType.COLD, DamageType.LIGHTNING],
            ),
        ]
        relevant = {DamageType.PHYSICAL, DamageType.FIRE}
        total_inc = pool.total_increased_for_types(relevant)
        # Matches because fire is in the set
        assert total_inc == pytest.approx(40.0)


# ===========================================================================
# Exposure tests
# ===========================================================================


class TestExposure:
    def test_exposure_reduces_resist(self):
        config = CalcConfig(enemy_fire_resist=40.0)
        multi = calc_mitigation_multi(DamageType.FIRE, config, exposure=15.0)
        # 40 - 15 = 25% effective resist
        assert multi == pytest.approx(0.75)

    def test_exposure_plus_penetration(self):
        config = CalcConfig(enemy_fire_resist=40.0)
        multi = calc_mitigation_multi(DamageType.FIRE, config, penetration=10.0, exposure=15.0)
        # 40 - 15 (exposure) - 10 (pen) = 15% effective resist
        assert multi == pytest.approx(0.85)

    def test_exposure_into_negative(self):
        config = CalcConfig(enemy_fire_resist=10.0)
        multi = calc_mitigation_multi(DamageType.FIRE, config, exposure=25.0)
        # 10 - 25 = -15% → multiplier = 1.15
        assert multi == pytest.approx(1.15)

    def test_exposure_does_not_apply_to_physical(self):
        """Physical uses armour/reduction formula, not resist-based."""
        config = CalcConfig(enemy_phys_reduction=20.0)
        multi = calc_mitigation_multi(DamageType.PHYSICAL, config, exposure=50.0)
        # Exposure is ignored for physical — just flat reduction
        assert multi == pytest.approx(0.8)


# ===========================================================================
# Resist floor tests
# ===========================================================================


class TestResistFloor:
    def test_resist_floor_at_minus_200(self):
        config = CalcConfig(enemy_fire_resist=-100.0)
        # -100 - 120 pen = -220, floored to -200
        multi = calc_mitigation_multi(DamageType.FIRE, config, penetration=120.0)
        # Floor at -200% → multi = 1 - (-200/100) = 3.0
        assert multi == pytest.approx(3.0)

    def test_resist_floor_not_exceeded_when_above(self):
        config = CalcConfig(enemy_fire_resist=0.0)
        multi = calc_mitigation_multi(DamageType.FIRE, config, penetration=50.0)
        # -50% resist → multi = 1.5 (above floor, no clamping)
        assert multi == pytest.approx(1.5)


# ===========================================================================
# Full pipeline integration tests with Phase C mechanics
# ===========================================================================


class TestEnginePhaseCIntegration:
    """Full engine pipeline tests exercising conversion+modifier interaction."""

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
        support_names: list[str] | None = None,
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

        support_gems = [
            Gem(name=name, gem_id=f"Support/{name.replace(' ', '')}", is_support=True)
            for name in (support_names or [])
        ]
        main_skill = SkillGroup(
            slot="Weapon 1", label="Main", is_enabled=True,
            gems=[Gem(name="Cyclone", gem_id="ActiveSkill/Cyclone"), *support_gems],
        )
        return Build(
            class_name="Duelist", ascendancy_name="Slayer", level=90,
            main_socket_group=1, skill_groups=[main_skill], items=items,
            config=BuildConfig(entries=config_entries or {}),
        )

    def test_conversion_with_source_type_increased(self):
        """50% phys→fire + 'increased Physical' should boost BOTH the phys and fire portions."""
        build = self._make_attack_build(
            weapon_mods=["50% of Physical Damage Converted to Fire Damage"],
            gear_mods={
                "Helmet": ["100% increased Physical Damage"],
            },
        )
        result = calculate_dps(build)
        phys = next(t for t in result.type_breakdown if t.damage_type == DamageType.PHYSICAL)
        fire = next(t for t in result.type_breakdown if t.damage_type == DamageType.FIRE)
        # Base 150 phys → 75 phys + 75 fire
        # Both get 100% increased Physical (source type applies to converted portion)
        # Phys: 75 * 2.0 = 150
        # Fire: 75 * 2.0 = 150 (increased Phys applies because source is Phys)
        assert phys.after_mitigation == pytest.approx(150.0, rel=0.01)
        assert fire.after_mitigation == pytest.approx(150.0, rel=0.01)

    def test_conversion_with_final_type_increased(self):
        """50% phys→fire + 'increased Fire' should boost ONLY the fire portion."""
        build = self._make_attack_build(
            weapon_mods=["50% of Physical Damage Converted to Fire Damage"],
            gear_mods={
                "Helmet": ["100% increased Fire Damage"],
            },
        )
        result = calculate_dps(build)
        phys = next(t for t in result.type_breakdown if t.damage_type == DamageType.PHYSICAL)
        fire = next(t for t in result.type_breakdown if t.damage_type == DamageType.FIRE)
        # Phys: 75 * 1.0 = 75 (increased Fire doesn't apply to phys→phys)
        # Fire: 75 * 2.0 = 150 (increased Fire applies to phys→fire)
        assert phys.after_mitigation == pytest.approx(75.0, rel=0.01)
        assert fire.after_mitigation == pytest.approx(150.0, rel=0.01)

    def test_conversion_with_both_type_increased(self):
        """50% phys→fire + 'increased Phys' + 'increased Fire' on converted portion."""
        build = self._make_attack_build(
            weapon_mods=["50% of Physical Damage Converted to Fire Damage"],
            gear_mods={
                "Helmet": ["50% increased Physical Damage"],
                "Gloves": ["50% increased Fire Damage"],
            },
        )
        result = calculate_dps(build)
        phys = next(t for t in result.type_breakdown if t.damage_type == DamageType.PHYSICAL)
        fire = next(t for t in result.type_breakdown if t.damage_type == DamageType.FIRE)
        # Phys portion (phys→phys): 75 * (1 + 0.5) = 112.5 (only inc phys)
        # Fire portion (phys→fire): 75 * (1 + 0.5 + 0.5) = 150 (both inc phys and inc fire)
        assert phys.after_mitigation == pytest.approx(112.5, rel=0.01)
        assert fire.after_mitigation == pytest.approx(150.0, rel=0.01)

    def test_gained_as_extra_with_modifiers(self):
        """'Gained as extra fire' + 'increased Physical' applies to both portions."""
        build = self._make_attack_build(
            weapon_mods=["25% of Physical Damage as Extra Fire Damage"],
            gear_mods={
                "Helmet": ["100% increased Physical Damage"],
            },
        )
        result = calculate_dps(build)
        phys = next(t for t in result.type_breakdown if t.damage_type == DamageType.PHYSICAL)
        fire = next(t for t in result.type_breakdown if t.damage_type == DamageType.FIRE)
        # Base 150 phys, gained 25% as fire = 37.5 fire
        # inc Phys 100% applies to both (source is phys for both)
        # Phys: 150 * 2.0 = 300
        # Fire: 37.5 * 2.0 = 75
        assert phys.after_mitigation == pytest.approx(300.0, rel=0.01)
        assert fire.after_mitigation == pytest.approx(75.0, rel=0.01)

    def test_exposure_in_full_pipeline(self):
        """Exposure should reduce enemy resist in the full pipeline."""
        build = self._make_attack_build(
            weapon_mods=["100% of Physical Damage Converted to Fire Damage"],
            gear_mods={
                "Helmet": ["Fire Exposure on Hit, applying -10% to Fire Resistance"],
            },
        )
        config = CalcConfig(enemy_fire_resist=30.0)
        result = calculate_dps(build, config_overrides=config)
        fire = next(t for t in result.type_breakdown if t.damage_type == DamageType.FIRE)
        # 150 fire, resist 30% - 10% exposure = 20% effective
        # 150 * 0.8 = 120
        assert fire.after_mitigation == pytest.approx(120.0, rel=0.01)

    def test_full_conversion_chain_with_mods(self):
        """100% phys→lightning, 100% lightning→cold, with 'increased Physical'."""
        build = self._make_attack_build(
            weapon_mods=[
                "100% of Physical Damage Converted to Lightning Damage",
            ],
            gear_mods={
                "Helmet": ["100% of Lightning Damage Converted to Cold Damage"],
                "Gloves": ["100% increased Physical Damage"],
            },
        )
        result = calculate_dps(build)
        cold = next(t for t in result.type_breakdown if t.damage_type == DamageType.COLD)
        # 150 phys → 150 lightning → 150 cold
        # Source is still Physical, so 100% increased Physical applies
        # 150 * 2.0 = 300
        assert cold.after_mitigation == pytest.approx(300.0, rel=0.01)
