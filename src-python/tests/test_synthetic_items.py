"""Tests for synthetic item generator (pop.calc.synthetic_items)."""

from __future__ import annotations

import pytest

from pop.build_parser.models import GuideItem, Item
from pop.calc.synthetic_items import (
    _ARMOUR_BASES,
    _STAT_MODS,
    _WEAPON_BASES,
    _pick_base_type,
    synthesize_build_items,
    synthesize_item,
)
from pop.calc.unique_db import is_known_unique, list_uniques


# ---------------------------------------------------------------------------
# Stat mod database integrity
# ---------------------------------------------------------------------------


class TestStatModDatabase:
    """Verify _STAT_MODS entries are well-formed."""

    def test_all_entries_are_list_of_tuples(self):
        """Every value must be a list of (template, basic, max) tuples."""
        for key, entries in _STAT_MODS.items():
            assert isinstance(entries, list), f"{key}: value is not a list"
            for i, entry in enumerate(entries):
                assert isinstance(entry, tuple), (
                    f"{key}[{i}]: expected tuple, got {type(entry).__name__}: {entry!r}"
                )
                assert len(entry) == 3, f"{key}[{i}]: expected 3 elements, got {len(entry)}"
                template, basic, maxi = entry
                assert isinstance(template, str), f"{key}[{i}]: template not str"
                assert isinstance(basic, (int, float)), f"{key}[{i}]: basic not numeric"
                assert isinstance(maxi, (int, float)), f"{key}[{i}]: max not numeric"

    def test_templates_contain_placeholder_or_literal(self):
        """Templates should contain {v} placeholder or be a fixed literal (gem levels)."""
        for key, entries in _STAT_MODS.items():
            for template, basic, maxi in entries:
                # Fixed-value mods (like +1 gem level) may not use {v}
                if basic == maxi and "{v}" not in template:
                    continue  # Literal template is fine when value is fixed
                assert "{v}" in template, f"{key}: template missing {{v}}: {template}"

    def test_max_ge_basic(self):
        """Max tier values should be >= basic tier values."""
        for key, entries in _STAT_MODS.items():
            for template, basic, maxi in entries:
                assert maxi >= basic, (
                    f"{key}: max ({maxi}) < basic ({basic}) for {template}"
                )

    def test_common_stats_present(self):
        """Key stat priorities that AI guides commonly produce should exist."""
        expected = [
            "life", "energy shield", "fire resistance", "cold resistance",
            "lightning resistance", "elemental resistances", "attack speed",
            "cast speed", "movement speed", "crit multi", "spell damage",
            "added physical damage", "accuracy", "minion damage",
            "dot multi", "life leech",
        ]
        for stat in expected:
            assert stat in _STAT_MODS, f"Missing common stat: {stat}"


# ---------------------------------------------------------------------------
# Weapon base database
# ---------------------------------------------------------------------------


class TestWeaponBases:
    """Verify _WEAPON_BASES entries are well-formed."""

    def test_all_entries_have_6_fields(self):
        for name, data in _WEAPON_BASES.items():
            assert len(data) == 6, f"{name}: expected 6 fields, got {len(data)}"

    def test_positive_damage(self):
        for name, (_, phys_min, phys_max, aps, crit, _) in _WEAPON_BASES.items():
            assert phys_min >= 0, f"{name}: negative phys_min"
            assert phys_max >= phys_min, f"{name}: phys_max < phys_min"
            # Shields in weapon bases may have APS=0
            assert aps >= 0, f"{name}: negative APS"
            assert crit >= 0, f"{name}: negative crit"

    def test_endgame_bases_present(self):
        endgame = [
            "Jewelled Foil", "Void Sceptre", "Thicket Bow", "Imperial Skean",
            "Gemini Claw", "Siege Axe", "Behemoth Mace",
        ]
        for base in endgame:
            assert base in _WEAPON_BASES, f"Missing endgame base: {base}"

    def test_leveling_bases_present(self):
        early = ["Rusted Sword", "Driftwood Wand", "Crude Bow"]
        for base in early:
            assert base in _WEAPON_BASES, f"Missing leveling base: {base}"


# ---------------------------------------------------------------------------
# Armour base database
# ---------------------------------------------------------------------------


class TestArmourBases:
    """Verify _ARMOUR_BASES entries are well-formed."""

    def test_all_slots_present(self):
        expected_slots = [
            "Helmet", "Body Armour", "Gloves", "Boots",
            "Belt", "Amulet", "Ring 1", "Ring 2",
        ]
        for slot in expected_slots:
            assert slot in _ARMOUR_BASES, f"Missing slot: {slot}"

    def test_all_entries_have_5_fields(self):
        for slot, bases in _ARMOUR_BASES.items():
            for name, data in bases.items():
                assert len(data) == 5, f"{slot}/{name}: expected 5 fields, got {len(data)}"

    def test_ring_slots_have_same_bases(self):
        """Ring 1 and Ring 2 should have the same base entries."""
        assert _ARMOUR_BASES["Ring 1"] == _ARMOUR_BASES["Ring 2"]

    def test_endgame_armour_bases_present(self):
        assert "Eternal Burgonet" in _ARMOUR_BASES["Helmet"]
        assert "Hubris Circlet" in _ARMOUR_BASES["Helmet"]
        assert "Vaal Regalia" in _ARMOUR_BASES["Body Armour"]
        assert "Glorious Plate" in _ARMOUR_BASES["Body Armour"]
        assert "Titan Gauntlets" in _ARMOUR_BASES["Gloves"]
        assert "Slink Boots" in _ARMOUR_BASES["Boots"]


# ---------------------------------------------------------------------------
# Base type picking heuristic
# ---------------------------------------------------------------------------


class TestPickBaseType:
    """Test _pick_base_type heuristic."""

    def test_weapon_spell_picks_sceptre(self):
        assert _pick_base_type("Weapon 1", ["spell damage", "cast speed"]) == "Void Sceptre"

    def test_weapon_bow_picks_thicket(self):
        assert _pick_base_type("Weapon 1", ["bow", "physical damage"]) == "Thicket Bow"

    def test_weapon_crit_picks_foil(self):
        assert _pick_base_type("Weapon 1", ["crit", "attack speed"]) == "Jewelled Foil"

    def test_armour_body_picks_highest_armour(self):
        base = _pick_base_type("Body Armour", ["life", "% armour", "elemental resistances"])
        # Should pick high-armour endgame base
        data = _ARMOUR_BASES["Body Armour"][base]
        assert data[1] > 300, f"{base} armour too low: {data[1]}"

    def test_es_body_picks_pure_es(self):
        base = _pick_base_type("Body Armour", ["energy shield", "spell damage"])
        data = _ARMOUR_BASES["Body Armour"][base]
        _, ar, ev, es, _ = data
        assert es > 0 and es >= ar and es >= ev, f"{base} not ES-dominant: ar={ar} ev={ev} es={es}"

    def test_evasion_boots_picks_evasion(self):
        base = _pick_base_type("Boots", ["% evasion", "movement speed"])
        data = _ARMOUR_BASES["Boots"][base]
        _, ar, ev, es, _ = data
        assert ev > 0 and ev >= ar and ev >= es, f"{base} not evasion-dominant"

    def test_ring_crit_picks_diamond(self):
        assert _pick_base_type("Ring 1", ["crit", "life"]) == "Diamond Ring"

    def test_ring_life_picks_vermillion(self):
        assert _pick_base_type("Ring 1", ["life", "elemental resistances"]) == "Vermillion Ring"

    def test_amulet_default_onyx(self):
        assert _pick_base_type("Amulet", ["life", "crit multi"]) == "Onyx Amulet"

    def test_es_priority_no_false_match(self):
        """ES keyword should not falsely match on 'resistances'."""
        base = _pick_base_type("Body Armour", ["life", "elemental resistances", "% armour"])
        data = _ARMOUR_BASES["Body Armour"][base]
        _, ar, _, es, _ = data
        assert ar > es, f"{base}: should be armour-dominant, got ar={ar} es={es}"


# ---------------------------------------------------------------------------
# synthesize_item — rare items
# ---------------------------------------------------------------------------


class TestSynthesizeRare:
    """Test synthesize_item for rare items."""

    def _make_guide(self, slot: str, name: str = "", **kwargs) -> GuideItem:
        return GuideItem(slot=slot, name=name, **kwargs)

    def test_basic_body_armour(self):
        gi = self._make_guide(
            "Body Armour", name="Test Chest",
            stat_priority=["life", "elemental resistances", "% armour"],
        )
        item = synthesize_item(gi, tier="basic", item_id=42)

        assert item.id == 42
        assert item.slot == "Body Armour"
        assert item.rarity == "RARE"
        assert item.base_type != ""
        assert item.level == 68
        assert len(item.explicits) > 0

    def test_max_tier_higher_values(self):
        gi = self._make_guide(
            "Helmet", stat_priority=["life", "elemental resistances"],
        )
        basic = synthesize_item(gi, tier="basic")
        maxi = synthesize_item(gi, tier="max")

        # Max tier should have level 80
        assert basic.level == 68
        assert maxi.level == 80

        # Max should have higher life roll
        def _extract_life(item: Item) -> int:
            for mod in item.explicits:
                if "maximum Life" in mod.text:
                    num = "".join(c for c in mod.text if c.isdigit())
                    return int(num) if num else 0
            return 0

        assert _extract_life(maxi) > _extract_life(basic)

    def test_weapon_includes_phys_damage_in_raw_text(self):
        gi = self._make_guide(
            "Weapon 1", stat_priority=["physical damage", "attack speed", "crit"],
        )
        item = synthesize_item(gi, tier="basic")

        assert item.slot == "Weapon 1"
        assert "Physical Damage:" in item.raw_text
        assert "Attacks per Second:" in item.raw_text
        assert "Critical Strike Chance:" in item.raw_text

    def test_weapon_max_tier_scales_damage(self):
        gi = self._make_guide("Weapon 1", stat_priority=["physical damage"])
        basic = synthesize_item(gi, tier="basic")
        maxi = synthesize_item(gi, tier="max")

        # Extract phys damage from raw text
        import re
        pat = re.compile(r"Physical Damage: (\d+)-(\d+)")
        m_basic = pat.search(basic.raw_text)
        m_max = pat.search(maxi.raw_text)
        assert m_basic and m_max
        basic_avg = (int(m_basic.group(1)) + int(m_basic.group(2))) / 2
        max_avg = (int(m_max.group(1)) + int(m_max.group(2))) / 2
        assert max_avg > basic_avg

    def test_explicit_mods_from_priorities(self):
        gi = self._make_guide(
            "Gloves",
            stat_priority=["life", "attack speed", "accuracy"],
        )
        item = synthesize_item(gi, tier="basic")

        mod_texts = [m.text for m in item.explicits]
        assert any("Life" in t for t in mod_texts), f"No life mod in {mod_texts}"
        assert any("Attack Speed" in t for t in mod_texts), f"No AS mod in {mod_texts}"
        assert any("Accuracy" in t for t in mod_texts), f"No accuracy mod in {mod_texts}"

    def test_elemental_resistances_produces_three_mods(self):
        gi = self._make_guide("Boots", stat_priority=["elemental resistances"])
        item = synthesize_item(gi, tier="basic")

        res_mods = [m for m in item.explicits if "Resistance" in m.text]
        assert len(res_mods) == 3, f"Expected 3 res mods, got {len(res_mods)}: {res_mods}"

    def test_no_duplicate_mods(self):
        """Same template from different alias keys should not produce duplicates."""
        gi = self._make_guide(
            "Ring 1",
            stat_priority=["life", "maximum life"],  # Both map to same mod
        )
        item = synthesize_item(gi, tier="basic")

        life_mods = [m for m in item.explicits if "maximum Life" in m.text]
        assert len(life_mods) == 1, f"Duplicate life mods: {life_mods}"

    def test_raw_text_has_rarity_and_base(self):
        gi = self._make_guide("Belt", stat_priority=["life"])
        item = synthesize_item(gi, tier="basic")

        assert "Rarity: RARE" in item.raw_text
        assert item.base_type in item.raw_text

    def test_raw_text_has_separator(self):
        gi = self._make_guide("Amulet", stat_priority=["life", "crit multi"])
        item = synthesize_item(gi, tier="basic")
        assert "--------" in item.raw_text

    def test_base_type_override(self):
        """If GuideItem has base_type set, use it instead of heuristic."""
        gi = self._make_guide(
            "Body Armour",
            base_type="Astral Plate",
            stat_priority=["life"],
        )
        item = synthesize_item(gi, tier="basic")
        assert item.base_type == "Astral Plate"

    def test_empty_priorities_produces_item(self):
        """Even with no stat priorities, should still produce a valid item."""
        gi = self._make_guide("Helmet", stat_priority=[])
        item = synthesize_item(gi, tier="basic")
        assert item.slot == "Helmet"
        assert item.base_type != ""
        assert item.rarity == "RARE"

    def test_unknown_priority_ignored(self):
        """Unknown stat priority strings should be silently skipped."""
        gi = self._make_guide(
            "Boots",
            stat_priority=["life", "xyzzy_nonexistent", "movement speed"],
        )
        item = synthesize_item(gi, tier="basic")
        mod_texts = [m.text for m in item.explicits]
        assert any("Life" in t for t in mod_texts)
        assert any("Movement Speed" in t for t in mod_texts)

    def test_added_damage_range_format(self):
        """'Adds X to Y' mods should have two different numbers."""
        gi = self._make_guide("Ring 1", stat_priority=["added physical damage"])
        item = synthesize_item(gi, tier="basic")

        import re
        for mod in item.explicits:
            m = re.search(r"Adds (\d+) to (\d+)", mod.text)
            if m:
                low, high = int(m.group(1)), int(m.group(2))
                assert high > low, f"Range {low}-{high} invalid"
                return
        pytest.fail("No 'Adds X to Y' mod found")

    def test_float_value_formatting(self):
        """Float values like leech should format with one decimal."""
        gi = self._make_guide("Gloves", stat_priority=["life leech"])
        item = synthesize_item(gi, tier="basic")

        for mod in item.explicits:
            if "Leeched" in mod.text:
                assert "." in mod.text, f"Expected decimal in leech: {mod.text}"
                return
        pytest.fail("No leech mod found")

    def test_stat_priority_preserved(self):
        """stat_priority from GuideItem should flow through to synthesized Item."""
        gi = self._make_guide(
            "Helmet", stat_priority=["life", "fire resistance", "% armour"],
        )
        item = synthesize_item(gi, tier="basic")
        assert item.stat_priority == ["life", "fire resistance", "% armour"]

    def test_notes_preserved(self):
        """notes from GuideItem should flow through to synthesized Item."""
        gi = self._make_guide("Belt", stat_priority=["life"], notes="Get a Stygian Vise")
        item = synthesize_item(gi, tier="basic")
        assert item.notes == "Get a Stygian Vise"


# ---------------------------------------------------------------------------
# synthesize_item — unique items
# ---------------------------------------------------------------------------


class TestSynthesizeUnique:
    """Test synthesize_item with known unique names."""

    def test_tabula_rasa(self):
        gi = GuideItem(slot="Body Armour", name="Tabula Rasa")
        item = synthesize_item(gi, tier="basic", item_id=10)

        assert item.rarity == "UNIQUE"
        assert item.name == "Tabula Rasa"
        assert item.base_type == "Simple Robe"
        assert "Rarity: UNIQUE" in item.raw_text
        assert any("Socket" in m.text or "White" in m.text for m in item.explicits)

    def test_headhunter(self):
        gi = GuideItem(slot="Belt", name="Headhunter")
        item = synthesize_item(gi)

        assert item.rarity == "UNIQUE"
        assert item.name == "Headhunter"

    def test_unique_tier_ignored(self):
        """Tier should not affect unique item stats — they're fixed."""
        gi = GuideItem(slot="Body Armour", name="Tabula Rasa")
        basic = synthesize_item(gi, tier="basic")
        maxi = synthesize_item(gi, tier="max")

        assert basic.explicits == maxi.explicits

    def test_unknown_name_falls_through_to_rare(self):
        """Name that isn't a known unique should produce a rare."""
        gi = GuideItem(
            slot="Helmet", name="My Custom Helm",
            stat_priority=["life", "fire resistance"],
        )
        item = synthesize_item(gi)
        assert item.rarity == "RARE"

    def test_unique_weapon_has_weapon_header(self):
        """Unique weapons with APS should have weapon stats in raw_text."""
        # Find a unique weapon with APS > 0
        from pop.calc.unique_db import get_unique
        wep_data = get_unique("Lioneye's Glare")
        if wep_data and wep_data.aps > 0:
            gi = GuideItem(slot="Weapon 1", name="Lioneye's Glare")
            item = synthesize_item(gi)
            assert "Attacks per Second:" in item.raw_text


# ---------------------------------------------------------------------------
# synthesize_build_items — batch synthesis
# ---------------------------------------------------------------------------


class TestSynthesizeBuildItems:
    """Test batch item synthesis."""

    def test_batch_assigns_sequential_ids(self):
        guide_items = [
            GuideItem(slot="Helmet", name="", stat_priority=["life"]),
            GuideItem(slot="Body Armour", name="", stat_priority=["life"]),
            GuideItem(slot="Boots", name="", stat_priority=["movement speed"]),
        ]
        items = synthesize_build_items(guide_items, tier="basic", start_id=100)

        assert len(items) == 3
        assert items[0].id == 100
        assert items[1].id == 101
        assert items[2].id == 102

    def test_batch_mixed_unique_and_rare(self):
        guide_items = [
            GuideItem(slot="Body Armour", name="Tabula Rasa"),
            GuideItem(slot="Helmet", name="", stat_priority=["life", "elemental resistances"]),
            GuideItem(slot="Belt", name="Headhunter"),
        ]
        items = synthesize_build_items(guide_items, tier="basic")

        assert items[0].rarity == "UNIQUE"
        assert items[1].rarity == "RARE"
        assert items[2].rarity == "UNIQUE"

    def test_batch_empty_list(self):
        items = synthesize_build_items([], tier="basic")
        assert items == []

    def test_batch_respects_tier(self):
        guide_items = [
            GuideItem(slot="Helmet", name="", stat_priority=["life"]),
        ]
        basic = synthesize_build_items(guide_items, tier="basic")
        maxi = synthesize_build_items(guide_items, tier="max")

        assert basic[0].level == 68
        assert maxi[0].level == 80


# ---------------------------------------------------------------------------
# Unique database integrity
# ---------------------------------------------------------------------------


class TestUniqueDatabase:
    """Verify unique item database is consistent."""

    def test_all_uniques_have_explicits(self):
        for name in list_uniques():
            from pop.calc.unique_db import get_unique
            data = get_unique(name)
            assert data is not None
            assert len(data.explicits) > 0, f"{name}: no explicits"

    def test_all_uniques_have_base_type(self):
        for name in list_uniques():
            from pop.calc.unique_db import get_unique
            data = get_unique(name)
            assert data.base_type, f"{name}: empty base_type"

    def test_all_uniques_have_item_class(self):
        for name in list_uniques():
            from pop.calc.unique_db import get_unique
            data = get_unique(name)
            assert data.item_class, f"{name}: empty item_class"

    def test_known_unique_lookup(self):
        assert is_known_unique("Tabula Rasa")
        assert is_known_unique("Headhunter")
        assert not is_known_unique("Random Rare Item")

    def test_unique_count_reasonable(self):
        """We should have a substantial unique database."""
        assert len(list_uniques()) >= 150


# ---------------------------------------------------------------------------
# Integration: synthesized build → DPS calculation
# ---------------------------------------------------------------------------


class TestSyntheticBuildDps:
    """End-to-end: synthesize items → build a Build → run calculate_dps."""

    def _make_build_with_synth_items(self, tier: str = "basic") -> "Build":
        from pop.build_parser.models import Build, Gem, SkillGroup

        guide_items = [
            GuideItem(slot="Weapon 1", name="", stat_priority=["physical damage", "attack speed"]),
            GuideItem(slot="Body Armour", name="", stat_priority=["life", "elemental resistances"]),
            GuideItem(slot="Helmet", name="", stat_priority=["life", "fire resistance"]),
            GuideItem(slot="Gloves", name="", stat_priority=["life", "attack speed"]),
            GuideItem(slot="Boots", name="", stat_priority=["life", "movement speed"]),
            GuideItem(slot="Belt", name="", stat_priority=["life"]),
            GuideItem(slot="Ring 1", name="", stat_priority=["life", "cold resistance"]),
            GuideItem(slot="Amulet", name="", stat_priority=["life", "critical strike"]),
        ]
        items = synthesize_build_items(guide_items, tier=tier, start_id=1)

        skill_groups = [
            SkillGroup(
                slot="Weapon 1",
                gems=[
                    Gem(name="Cyclone", is_support=False, level=20),
                    Gem(name="Melee Physical Damage Support", is_support=True, level=20),
                    Gem(name="Increased Area of Effect Support", is_support=True, level=20),
                ],
            )
        ]

        return Build(
            class_name="Marauder",
            ascendancy_name="Berserker",
            level=80,
            main_socket_group=1,
            items=items,
            skill_groups=skill_groups,
        )

    def test_synth_build_calculates_without_crash(self):
        """DPS engine should handle synthesized builds without errors."""
        from pop.calc.engine import calculate_dps

        build = self._make_build_with_synth_items("basic")
        result = calculate_dps(build, use_tree=False, use_repoe=False)

        # Should produce a result (may have warnings, that's fine)
        assert result is not None

    def test_synth_build_max_tier_higher_dps(self):
        """Max-tier synth build should generally produce >= basic-tier DPS."""
        from pop.calc.engine import calculate_dps

        basic_build = self._make_build_with_synth_items("basic")
        max_build = self._make_build_with_synth_items("max")

        basic_result = calculate_dps(basic_build, use_tree=False, use_repoe=False)
        max_result = calculate_dps(max_build, use_tree=False, use_repoe=False)

        # Max tier should be >= basic (or both 0 if gem not recognized)
        assert max_result.combined_dps >= basic_result.combined_dps

    def test_synth_weapon_has_damage_mods(self):
        """Synthesized weapon should have recognizable damage mods."""
        guide = GuideItem(slot="Weapon 1", name="", stat_priority=["physical damage", "attack speed"])
        weapon = synthesize_item(guide, tier="max")

        # Should have explicits containing damage-related text
        mod_texts = [m.text.lower() for m in weapon.explicits]
        has_damage = any("damage" in t or "attack" in t for t in mod_texts)
        assert has_damage, f"Weapon mods lack damage/attack text: {mod_texts}"

    def test_synth_build_items_have_stat_priority(self):
        """All synthesized rare items should preserve stat_priority."""
        build = self._make_build_with_synth_items("basic")
        rares = [i for i in build.items if i.rarity == "RARE"]
        for item in rares:
            assert len(item.stat_priority) > 0, f"{item.slot}: missing stat_priority"
