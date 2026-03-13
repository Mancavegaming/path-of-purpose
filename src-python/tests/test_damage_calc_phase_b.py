"""
Phase B tests for the damage calculation engine.

Tests cover:
- Passive tree stat extraction (tree_stats.py)
- RePoE gem data loading (repoe_loader.py)
- Stat aggregator orchestration (stat_aggregator.py)
- Full engine integration with tree + RePoE data
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from pop.build_parser.models import (
    Build,
    BuildConfig,
    Gem,
    Item,
    ItemMod,
    PassiveSpec,
    SkillGroup,
)
from pop.calc.engine import calculate_dps
from pop.calc.gem_data import ActiveGemStats, SupportGemEffect
from pop.calc.mod_parser import ParsedMods, parse_mods
from pop.calc.models import CalcConfig, DamageType, Modifier
from pop.calc.repoe_loader import RePoEGemDB, clear_repoe_cache
from pop.calc.stat_aggregator import collect_all_mods
from pop.calc.tree_stats import clear_cache as clear_tree_cache, get_node_stats


# ===========================================================================
# Tree stats tests
# ===========================================================================


class TestTreeStats:
    """Tests for passive tree stat extraction."""

    @pytest.fixture(autouse=True)
    def _reset_cache(self):
        """Clear the tree cache before each test."""
        clear_tree_cache()
        yield
        clear_tree_cache()

    def test_get_node_stats_with_real_cache(self):
        """Test against the real passive tree cache if available."""
        cache_path = (
            Path(__file__).parent.parent / "pop" / "knowledge" / "cache" / "passive_tree.json"
        )
        if not cache_path.exists():
            pytest.skip("No passive tree cache available")

        # Node 5865 = "Physical Damage, Armour" with stats:
        #   "15% increased Armour", "10% increased Physical Damage"
        result = get_node_stats([5865])
        # Should have extracted increased physical damage
        phys_mods = [
            m for m in result.increased
            if DamageType.PHYSICAL in m.damage_types
        ]
        assert len(phys_mods) > 0
        assert any(m.value == 10.0 for m in phys_mods)

    def test_get_node_stats_attack_speed_node(self):
        """Test node with attack speed stat."""
        cache_path = (
            Path(__file__).parent.parent / "pop" / "knowledge" / "cache" / "passive_tree.json"
        )
        if not cache_path.exists():
            pytest.skip("No passive tree cache available")

        # Node 63673 = "Physical Damage, Attack Speed" with:
        #   "5% increased Attack Speed", "10% increased Physical Damage"
        result = get_node_stats([63673])
        assert result.increased_attack_speed == 5.0
        phys_mods = [
            m for m in result.increased
            if DamageType.PHYSICAL in m.damage_types
        ]
        assert any(m.value == 10.0 for m in phys_mods)

    def test_get_node_stats_multiple_nodes(self):
        """Test collecting stats from multiple nodes."""
        cache_path = (
            Path(__file__).parent.parent / "pop" / "knowledge" / "cache" / "passive_tree.json"
        )
        if not cache_path.exists():
            pytest.skip("No passive tree cache available")

        # Two physical damage nodes
        result = get_node_stats([5865, 63673])
        phys_mods = [
            m for m in result.increased
            if DamageType.PHYSICAL in m.damage_types
        ]
        # Both nodes have 10% increased phys damage
        total_phys = sum(m.value for m in phys_mods)
        assert total_phys == pytest.approx(20.0)

    def test_get_node_stats_unknown_ids(self):
        """Unknown node IDs should be silently skipped."""
        result = get_node_stats([9999999, 8888888])
        assert len(result.increased) == 0
        assert len(result.more) == 0

    def test_get_node_stats_empty_list(self):
        """Empty node list should return empty ParsedMods."""
        result = get_node_stats([])
        assert len(result.increased) == 0

    def test_get_node_stats_with_mock(self):
        """Test with mocked tree data to verify parsing logic."""
        mock_nodes = {
            100: {"stats": ["20% increased Fire Damage", "10% increased Attack Speed"]},
            200: {"stats": ["+30% to Critical Strike Multiplier"]},
            300: {"stats": ["Adds 5 to 10 Physical Damage to Attacks"]},
        }

        with patch("pop.calc.tree_stats._get_nodes", return_value=mock_nodes):
            result = get_node_stats([100, 200, 300])

        # Fire damage from node 100
        fire_mods = [m for m in result.increased if DamageType.FIRE in m.damage_types]
        assert any(m.value == 20.0 for m in fire_mods)

        # Attack speed from node 100
        assert result.increased_attack_speed == 10.0

        # Crit multi from node 200
        assert result.crit_multi == 30.0

        # Flat phys to attacks from node 300
        assert result.flat_added_attacks.get(DamageType.PHYSICAL) == pytest.approx(7.5)

    def test_more_damage_node(self):
        """Test node with 'more' damage stat."""
        mock_nodes = {
            999: {"stats": ["40% more Damage"]},
        }

        with patch("pop.calc.tree_stats._get_nodes", return_value=mock_nodes):
            result = get_node_stats([999])

        assert len(result.more) == 1
        assert result.more[0].value == 40.0


# ===========================================================================
# RePoE loader tests
# ===========================================================================


class TestRePoELoader:
    """Tests for the RePoE dynamic gem data loader."""

    @pytest.fixture(autouse=True)
    def _reset_repoe(self):
        clear_repoe_cache()
        yield
        clear_repoe_cache()

    def _make_repoe_data(self) -> dict:
        """Create minimal RePoE-style gem data for testing."""
        return {
            "Metadata/Gems/Arc": {
                "base_item": {
                    "display_name": "Arc",
                    "release_state": "released",
                },
                "display_name": "Arc",
                "is_support": False,
                "cast_time": 700,
                "tags": ["lightning", "intelligence", "spell"],
                "active_skill": {
                    "types": ["Spell", "Damage", "Lightning", "Chaining"],
                    "is_skill_totem": False,
                },
                "static": {
                    "crit_chance": 500,
                    "damage_effectiveness": 80,
                    "stats": [
                        {"id": "spell_minimum_base_lightning_damage", "type": "float"},
                        {"id": "spell_maximum_base_lightning_damage", "type": "float"},
                    ],
                },
                "per_level": {
                    "20": {
                        "required_level": 70,
                        "stat_text": {
                            "spell_minimum_base_lightning_damage\n"
                            "spell_maximum_base_lightning_damage":
                                "Deals 198 to 1122 Lightning Damage",
                        },
                        "stats": [{"value": 198}, {"value": 1122}],
                    },
                },
            },
            "Metadata/Gems/BrutalitySupport": {
                "base_item": {
                    "display_name": "Brutality Support",
                    "release_state": "released",
                },
                "display_name": "Brutality Support",
                "is_support": True,
                "tags": ["physical", "strength", "support"],
                "static": {
                    "stats": [
                        {"id": "support_brutality_physical_damage_+%_final", "type": "additional"},
                    ],
                    "stat_text": {
                        "deal_no_elemental_damage": "Supported Skills deal no Elemental Damage",
                    },
                },
                "per_level": {
                    "20": {
                        "required_level": 70,
                        "stat_text": {
                            "support_brutality_physical_damage_+%_final":
                                "Supported Skills deal 39% more Physical Damage",
                        },
                        "stats": [{"value": 39}],
                    },
                },
            },
            "Metadata/Gems/Cyclone": {
                "base_item": {
                    "display_name": "Cyclone",
                    "release_state": "released",
                },
                "display_name": "Cyclone",
                "is_support": False,
                "tags": ["attack", "strength"],
                "active_skill": {
                    "types": ["Attack", "Area", "Melee", "Movement", "Channel"],
                    "is_skill_totem": False,
                },
                "static": {},
                "per_level": {
                    "20": {
                        "required_level": 70,
                        "stat_text": {},
                        "stats": [],
                    },
                },
            },
        }

    def test_load_from_dict(self):
        db = RePoEGemDB()
        db.load_from_dict(self._make_repoe_data())
        assert db.is_loaded
        assert len(db.get_gem_names()) == 3

    def test_get_active_stats_spell(self):
        db = RePoEGemDB()
        db.load_from_dict(self._make_repoe_data())

        stats = db.get_active_stats("Arc", level=20)
        assert stats is not None
        assert stats.is_spell is True
        assert stats.is_attack is False
        assert DamageType.LIGHTNING in stats.base_damage
        # avg of 198 and 1122 = 660
        assert stats.base_damage[DamageType.LIGHTNING] == pytest.approx(660.0)
        assert stats.base_crit == pytest.approx(5.0)  # 500 / 100
        assert stats.base_cast_time == pytest.approx(0.7)  # 700ms
        assert stats.damage_effectiveness == pytest.approx(0.8)  # 80 / 100

    def test_get_active_stats_attack(self):
        db = RePoEGemDB()
        db.load_from_dict(self._make_repoe_data())

        stats = db.get_active_stats("Cyclone", level=20)
        assert stats is not None
        assert stats.is_attack is True
        assert stats.is_spell is False
        assert "melee" in stats.tags

    def test_get_support_stats(self):
        db = RePoEGemDB()
        db.load_from_dict(self._make_repoe_data())

        effect = db.get_support_stats("Brutality Support", level=20)
        assert effect is not None
        assert len(effect.modifiers) > 0
        # Should find "39% more Physical Damage"
        more_phys = [
            m for m in effect.modifiers
            if m.mod_type == "more" and m.value == 39.0
        ]
        assert len(more_phys) == 1

    def test_fallback_to_hardcoded(self):
        db = RePoEGemDB()
        # Don't load any data — should fall back to hardcoded

        stats = db.get_active_stats("Cyclone")
        # Falls back to hardcoded gem_data
        assert stats is not None
        assert stats.is_attack is True

    def test_unknown_gem_returns_none(self):
        db = RePoEGemDB()
        db.load_from_dict(self._make_repoe_data())

        stats = db.get_active_stats("NonExistentGem123")
        assert stats is None

    def test_unknown_support_returns_none(self):
        db = RePoEGemDB()
        db.load_from_dict(self._make_repoe_data())

        effect = db.get_support_stats("NonExistentSupport123")
        assert effect is None


# ===========================================================================
# Stat aggregator tests
# ===========================================================================


class TestStatAggregator:
    """Tests for the stat aggregator module."""

    def _make_build_with_tree(
        self,
        node_stats: dict[int, dict] | None = None,
        gear_mods: dict[str, list[str]] | None = None,
        support_names: list[str] | None = None,
    ) -> Build:
        """Create a build with passive tree nodes."""
        items = [
            Item(
                id=1, slot="Weapon 1", name="Sword", base_type="Corsair Sword",
                raw_text=(
                    "Rarity: RARE\nSword\nCorsair Sword\n"
                    "Physical Damage: 100-200\n"
                    "Attacks per Second: 1.5\n"
                    "Critical Strike Chance: 5.0%\n"
                    "Implicits: 0\n"
                ),
            ),
        ]

        for slot, mods in (gear_mods or {}).items():
            items.append(Item(
                id=len(items) + 1,
                slot=slot,
                name=f"Test {slot}",
                base_type=f"Test {slot}",
                explicits=[ItemMod(text=t) for t in mods],
            ))

        support_gems = [
            Gem(name=n, gem_id=f"Support/{n.replace(' ', '')}", is_support=True)
            for n in (support_names or [])
        ]

        main_skill = SkillGroup(
            slot="Weapon 1",
            is_enabled=True,
            gems=[
                Gem(name="Cyclone", gem_id="ActiveSkill/Cyclone"),
                *support_gems,
            ],
        )

        return Build(
            class_name="Duelist",
            level=90,
            main_socket_group=1,
            skill_groups=[main_skill],
            items=items,
            passive_specs=[PassiveSpec(
                nodes=list((node_stats or {}).keys()),
                tree_version="3_25",
            )],
            config=BuildConfig(),
        )

    def test_collect_items_only(self):
        build = self._make_build_with_tree(
            gear_mods={"Helmet": ["40% increased Physical Damage"]},
        )
        parsed, warnings = collect_all_mods(
            build, build.main_skill, is_attack=True,
            use_tree=False, use_repoe=False,
        )
        phys_mods = [m for m in parsed.increased if DamageType.PHYSICAL in m.damage_types]
        assert any(m.value == 40.0 for m in phys_mods)

    def test_collect_with_tree_mocked(self):
        mock_nodes = {
            100: {"stats": ["30% increased Physical Damage"]},
            200: {"stats": ["15% increased Attack Speed"]},
        }

        build = self._make_build_with_tree(
            node_stats=mock_nodes,
            gear_mods={"Helmet": ["20% increased Physical Damage"]},
        )

        with patch("pop.calc.tree_stats._get_nodes", return_value=mock_nodes):
            parsed, warnings = collect_all_mods(
                build, build.main_skill, is_attack=True,
                use_tree=True, use_repoe=False,
            )

        # 30% from tree + 20% from helmet
        phys_mods = [m for m in parsed.increased if DamageType.PHYSICAL in m.damage_types]
        total_phys = sum(m.value for m in phys_mods)
        assert total_phys == pytest.approx(50.0)

        # 15% attack speed from tree
        assert parsed.increased_attack_speed == 15.0

    def test_collect_with_supports(self):
        build = self._make_build_with_tree(
            support_names=["Brutality Support"],
        )
        parsed, warnings = collect_all_mods(
            build, build.main_skill, is_attack=True,
            use_tree=False, use_repoe=False,
        )
        # Brutality should add a more multiplier
        assert len(parsed.more) > 0
        assert any(m.value == 59.0 for m in parsed.more)  # hardcoded Brutality = 59%


# ===========================================================================
# Full engine integration with tree + RePoE
# ===========================================================================


class TestEnginePhaseB:
    """Integration tests for the engine with tree stats and RePoE data."""

    def _make_build(
        self,
        weapon_raw: str = "",
        weapon_mods: list[str] | None = None,
        gear_mods: dict[str, list[str]] | None = None,
        support_names: list[str] | None = None,
        node_ids: list[int] | None = None,
        skill_name: str = "Cyclone",
        is_spell: bool = False,
    ) -> Build:
        items = []
        if not is_spell:
            items.append(Item(
                id=1, slot="Weapon 1", name="Sword", base_type="Corsair Sword",
                raw_text=weapon_raw or (
                    "Rarity: RARE\nSword\nCorsair Sword\n"
                    "Physical Damage: 100-200\n"
                    "Attacks per Second: 1.5\n"
                    "Critical Strike Chance: 5.0%\n"
                    "Implicits: 0\n"
                ),
                explicits=[ItemMod(text=t) for t in (weapon_mods or [])],
            ))

        for slot, mods in (gear_mods or {}).items():
            items.append(Item(
                id=len(items) + 1,
                slot=slot, name=f"Test {slot}", base_type=f"Test {slot}",
                explicits=[ItemMod(text=t) for t in mods],
            ))

        supports = [
            Gem(name=n, gem_id=f"Support/{n}", is_support=True)
            for n in (support_names or [])
        ]

        main = SkillGroup(
            slot="" if is_spell else "Weapon 1",
            is_enabled=True,
            gems=[Gem(name=skill_name, gem_id=f"ActiveSkill/{skill_name}"), *supports],
        )

        return Build(
            class_name="Duelist" if not is_spell else "Witch",
            level=90,
            main_socket_group=1,
            skill_groups=[main],
            items=items,
            passive_specs=[PassiveSpec(
                nodes=node_ids or [],
                tree_version="3_25",
            )],
            config=BuildConfig(),
        )

    def test_engine_with_tree_stats(self):
        """Test full DPS calc including passive tree nodes."""
        mock_nodes = {
            100: {"stats": ["50% increased Physical Damage"]},
            200: {"stats": ["20% increased Attack Speed"]},
            300: {"stats": ["+20% to Critical Strike Multiplier"]},
        }

        build = self._make_build(node_ids=[100, 200, 300])

        with patch("pop.calc.tree_stats._get_nodes", return_value=mock_nodes):
            result = calculate_dps(build, use_tree=True, use_repoe=False)

        # Base: 150 phys
        # increased: 50% from tree → 150 * 1.5 = 225
        # speed: 1.5 * 3.0 (cyclone) * (1 + 0.2) = 5.4
        # crit: 5% base, multi 150+20=170% → ecm = 1 + 0.05*(1.7-1) = 1.035
        # avgHit = 225 * 1.035 = 232.875
        assert result.hit_damage == pytest.approx(225.0 * 1.035, rel=0.02)
        assert result.hits_per_second == pytest.approx(5.4, rel=0.01)

    def test_engine_tree_plus_gear(self):
        """Tree stats and gear stats should combine."""
        mock_nodes = {
            100: {"stats": ["30% increased Physical Damage"]},
        }

        build = self._make_build(
            node_ids=[100],
            gear_mods={"Helmet": ["20% increased Physical Damage"]},
        )

        with patch("pop.calc.tree_stats._get_nodes", return_value=mock_nodes):
            result = calculate_dps(build, use_tree=True, use_repoe=False)

        # 30% tree + 20% gear = 50% increased
        # 5% crit, 150% multi → ecm = 1.025
        # avgHit = 150 * 1.5 * 1.025 = 230.625
        assert result.hit_damage == pytest.approx(225.0 * 1.025, rel=0.02)

    def test_engine_tree_plus_supports(self):
        """Tree increased + support more should multiply correctly."""
        mock_nodes = {
            100: {"stats": ["100% increased Physical Damage"]},
        }

        build = self._make_build(
            node_ids=[100],
            support_names=["Brutality Support"],
        )

        with patch("pop.calc.tree_stats._get_nodes", return_value=mock_nodes):
            result = calculate_dps(build, use_tree=True, use_repoe=False)

        # 100% increased from tree → 150 * 2.0 = 300
        # 59% more from Brutality → 300 * 1.59 = 477
        # 5% crit, 150% multi → ecm = 1.025
        # avgHit = 477 * 1.025 = 488.925
        assert result.hit_damage == pytest.approx(300.0 * 1.59 * 1.025, rel=0.02)

    def test_engine_with_repoe_spell(self):
        """Test spell DPS with RePoE-loaded gem data."""
        repoe_data = {
            "Metadata/Gems/Arc": {
                "base_item": {"display_name": "Arc", "release_state": "released"},
                "is_support": False,
                "cast_time": 700,
                "active_skill": {"types": ["Spell", "Lightning"]},
                "static": {"crit_chance": 600, "damage_effectiveness": 80},
                "per_level": {
                    "20": {
                        "stat_text": {
                            "dmg": "Deals 200 to 1000 Lightning Damage",
                        },
                    },
                },
            },
        }

        db = RePoEGemDB()
        db.load_from_dict(repoe_data)

        build = self._make_build(skill_name="Arc", is_spell=True)

        with patch("pop.calc.engine.get_repoe_db", return_value=db), \
             patch("pop.calc.stat_aggregator.get_repoe_db", return_value=db):
            result = calculate_dps(build, use_tree=False, use_repoe=True)

        assert result.skill_name == "Arc"
        assert result.is_attack is False
        # Base: avg(200, 1000) = 600
        lightning = next(t for t in result.type_breakdown if t.damage_type == DamageType.LIGHTNING)
        assert lightning.after_mitigation == pytest.approx(600.0)

    def test_engine_no_tree_no_repoe_still_works(self):
        """Engine should work fine with both tree and RePoE disabled."""
        build = self._make_build()
        result = calculate_dps(build, use_tree=False, use_repoe=False)
        assert result.total_dps > 0
        assert result.skill_name == "Cyclone"

    def test_engine_tree_crit_and_speed(self):
        """Tree nodes providing crit and speed should affect the result."""
        mock_nodes = {
            100: {"stats": ["200% increased Critical Strike Chance"]},
            200: {"stats": ["+50% to Critical Strike Multiplier"]},
            300: {"stats": ["30% increased Attack Speed"]},
        }

        build = self._make_build(node_ids=[100, 200, 300])

        with patch("pop.calc.tree_stats._get_nodes", return_value=mock_nodes):
            result = calculate_dps(build, use_tree=True, use_repoe=False)

        # Crit: 5% base * (1 + 200/100) = 15%
        assert result.crit_chance == pytest.approx(15.0, rel=0.01)
        # Crit multi: 150 + 50 = 200%
        # effective: 1 + 0.15 * (2.0 - 1.0) = 1.15
        assert result.effective_crit_multi == pytest.approx(1.15, rel=0.01)
        # Speed: 1.5 * 3.0 (cyclone) * (1 + 0.3) = 5.85
        assert result.hits_per_second == pytest.approx(5.85, rel=0.01)

    def test_engine_tree_conversion(self):
        """Tree conversion nodes should work in the pipeline."""
        mock_nodes = {
            100: {"stats": ["40% of Physical Damage Converted to Fire Damage"]},
        }

        build = self._make_build(node_ids=[100])

        with patch("pop.calc.tree_stats._get_nodes", return_value=mock_nodes):
            result = calculate_dps(build, use_tree=True, use_repoe=False)

        phys = next(t for t in result.type_breakdown if t.damage_type == DamageType.PHYSICAL)
        fire = next(t for t in result.type_breakdown if t.damage_type == DamageType.FIRE)
        # 150 phys → 60% stays (90), 40% converts to fire (60)
        assert phys.after_mitigation == pytest.approx(90.0, rel=0.01)
        assert fire.after_mitigation == pytest.approx(60.0, rel=0.01)

    def test_engine_tree_penetration(self):
        """Tree penetration nodes should reduce enemy resistance."""
        mock_nodes = {
            100: {"stats": ["Penetrates 15% Fire Resistance"]},
        }

        build = self._make_build(
            node_ids=[100],
            weapon_mods=["100% of Physical Damage Converted to Fire Damage"],
        )
        config = CalcConfig(enemy_fire_resist=40.0)

        with patch("pop.calc.tree_stats._get_nodes", return_value=mock_nodes):
            result = calculate_dps(build, config_overrides=config, use_tree=True, use_repoe=False)

        fire = next(t for t in result.type_breakdown if t.damage_type == DamageType.FIRE)
        # 150 phys → 150 fire (100% conversion)
        # fire resist 40% - 15% pen = 25% effective resist
        # 150 * 0.75 = 112.5
        assert fire.after_mitigation == pytest.approx(112.5, rel=0.01)

    def test_engine_real_tree_if_cached(self):
        """Integration test using real passive tree cache (skipped if no cache)."""
        cache_path = (
            Path(__file__).parent.parent / "pop" / "knowledge" / "cache" / "passive_tree.json"
        )
        if not cache_path.exists():
            pytest.skip("No passive tree cache")

        # Use real tree nodes: 5865 (10% phys + 15% armour) and 63673 (10% phys + 5% aps)
        build = self._make_build(node_ids=[5865, 63673])
        result = calculate_dps(build, use_tree=True, use_repoe=False)

        # Should have 20% increased phys from tree + 5% attack speed
        # hit = 150 * 1.2 = 180
        # speed = 1.5 * 3.0 (cyclone) * 1.05 = 4.725
        assert result.hit_damage == pytest.approx(180.0, rel=0.05)
        assert result.hits_per_second == pytest.approx(4.725, rel=0.05)
        assert result.total_dps > 0
