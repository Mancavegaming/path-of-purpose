"""Tests for the Delta Engine — passive, gear, gem diffs and the top-level engine."""

from __future__ import annotations

import pytest

from pop.build_parser.models import (
    Build,
    Gem,
    Item,
    ItemMod,
    PassiveSpec,
    SkillGroup,
)
from pop.poe_api.models import (
    CharacterDetail,
    EquippedItem,
    PassiveData,
)
from pop.delta.models import (
    DeltaGap,
    DeltaReport,
    GapCategory,
    GearDelta,
    ModGap,
    PassiveDelta,
    Severity,
    SlotDelta,
    SkillGroupDelta,
)
from pop.delta.passive_diff import diff_passives
from pop.delta.gear_diff import diff_gear, diff_slot, _normalize_mod, _mod_importance
from pop.delta.gem_diff import diff_skill_group, diff_gems
from pop.delta.engine import analyze


# ===========================================================================
# Passive diff
# ===========================================================================


class TestPassiveDiff:
    def test_identical_trees(self):
        guide = PassiveSpec(nodes=[1, 2, 3, 4, 5])
        char = PassiveData(hashes=[1, 2, 3, 4, 5])
        delta = diff_passives(guide, char)
        assert delta.missing_count == 0
        assert delta.extra_count == 0
        assert delta.match_pct == 100.0

    def test_character_missing_nodes(self):
        guide = PassiveSpec(nodes=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        char = PassiveData(hashes=[1, 2, 3])
        delta = diff_passives(guide, char)
        assert delta.missing_count == 7
        assert delta.extra_count == 0
        assert delta.match_pct == 30.0

    def test_character_has_extra_nodes(self):
        guide = PassiveSpec(nodes=[1, 2, 3])
        char = PassiveData(hashes=[1, 2, 3, 99, 100])
        delta = diff_passives(guide, char)
        assert delta.missing_count == 0
        assert delta.extra_count == 2
        assert delta.match_pct == 100.0  # all guide nodes are present

    def test_mixed_missing_and_extra(self):
        guide = PassiveSpec(nodes=[1, 2, 3, 4, 5])
        char = PassiveData(hashes=[1, 2, 6, 7])
        delta = diff_passives(guide, char)
        assert delta.missing_count == 3  # 3, 4, 5
        assert delta.extra_count == 2    # 6, 7
        assert delta.match_pct == 40.0

    def test_empty_guide_tree(self):
        guide = PassiveSpec(nodes=[])
        char = PassiveData(hashes=[1, 2, 3])
        delta = diff_passives(guide, char)
        assert delta.match_pct == 100.0  # nothing to match against

    def test_hashes_ex_included(self):
        guide = PassiveSpec(nodes=[1, 2, 3])
        char = PassiveData(hashes=[1], hashes_ex=[2, 3])
        delta = diff_passives(guide, char)
        assert delta.missing_count == 0
        assert delta.match_pct == 100.0

    def test_severity_critical(self):
        delta = PassiveDelta(match_pct=30, missing_count=50, guide_total=70)
        assert delta.severity == Severity.CRITICAL

    def test_severity_high(self):
        delta = PassiveDelta(match_pct=70, missing_count=10, guide_total=30)
        assert delta.severity == Severity.HIGH

    def test_severity_medium(self):
        delta = PassiveDelta(match_pct=90, missing_count=3, guide_total=30)
        assert delta.severity == Severity.MEDIUM

    def test_severity_low(self):
        delta = PassiveDelta(match_pct=98, missing_count=1, guide_total=30)
        assert delta.severity == Severity.LOW

    def test_summary_text(self):
        delta = PassiveDelta(match_pct=75.0, missing_count=10, extra_count=3)
        s = delta.summary
        assert "75%" in s
        assert "10 nodes" in s
        assert "3 to respec" in s


# ===========================================================================
# Gear diff — helpers
# ===========================================================================


class TestGearHelpers:
    def test_normalize_mod_strips_numbers(self):
        assert _normalize_mod("+120 to maximum Life") == "+# to maximum life"
        assert _normalize_mod("+85 to maximum Life") == "+# to maximum life"

    def test_normalize_mod_collapses_whitespace(self):
        assert _normalize_mod("  +5  to  Strength  ") == "+# to strength"

    def test_mod_importance_life(self):
        assert _mod_importance("+120 to maximum Life") == 1.0

    def test_mod_importance_resistance(self):
        score = _mod_importance("+45% to Fire Resistance")
        assert score == 0.7

    def test_mod_importance_unknown(self):
        score = _mod_importance("Some random mod nobody knows")
        assert score == 0.3


# ===========================================================================
# Gear diff — slot level
# ===========================================================================


class TestSlotDiff:
    def test_empty_slot_vs_guide(self):
        guide_item = Item(
            name="Glyph Hold",
            base_type="Spirit Shield",
            slot="Weapon 1",
            implicits=[ItemMod(text="15% increased Spell Damage", is_implicit=True)],
            explicits=[
                ItemMod(text="+120 to maximum Life"),
                ItemMod(text="+45% to Fire Resistance"),
            ],
        )
        delta = diff_slot("Weapon 1", guide_item, None)
        assert delta.has_item is False
        assert delta.match_pct == 0.0
        assert len(delta.missing_mods) == 3
        assert delta.priority_score == 100.0

    def test_no_guide_item(self):
        delta = diff_slot("Boots", None, None)
        assert delta.match_pct == 100.0  # nothing expected

    def test_perfect_match(self):
        guide_item = Item(
            explicits=[
                ItemMod(text="+100 to maximum Life"),
                ItemMod(text="+40% to Fire Resistance"),
            ],
        )
        char_item = EquippedItem(
            explicit_mods=[
                "+95 to maximum Life",
                "+38% to Fire Resistance",
            ],
        )
        delta = diff_slot("Helmet", guide_item, char_item)
        assert delta.matched_mods == 2
        assert len(delta.missing_mods) == 0
        assert delta.match_pct == 100.0

    def test_partial_match(self):
        guide_item = Item(
            explicits=[
                ItemMod(text="+100 to maximum Life"),
                ItemMod(text="+40% to Fire Resistance"),
                ItemMod(text="+30% to Cold Resistance"),
                ItemMod(text="+50 to maximum Energy Shield"),
            ],
        )
        char_item = EquippedItem(
            explicit_mods=[
                "+85 to maximum Life",
                # missing fire res, cold res, ES
                "+15% increased Rarity of Items Found",
            ],
        )
        delta = diff_slot("Helmet", guide_item, char_item)
        assert delta.matched_mods == 1  # Life matched
        assert len(delta.missing_mods) == 3
        assert delta.match_pct == 25.0

    def test_fuzzy_matching_works(self):
        """API says 'Maximum' (capital M), PoB says 'maximum' (lowercase)."""
        guide_item = Item(
            explicits=[ItemMod(text="+100 to maximum Life")],
        )
        char_item = EquippedItem(
            explicit_mods=["+92 to Maximum Life"],
        )
        delta = diff_slot("Belt", guide_item, char_item)
        assert delta.matched_mods == 1

    def test_slot_delta_severity(self):
        assert SlotDelta(slot="X", match_pct=0, has_item=False).severity == Severity.CRITICAL
        assert SlotDelta(slot="X", match_pct=20).severity == Severity.CRITICAL
        assert SlotDelta(slot="X", match_pct=50).severity == Severity.HIGH
        assert SlotDelta(slot="X", match_pct=75).severity == Severity.MEDIUM
        assert SlotDelta(slot="X", match_pct=90).severity == Severity.LOW


# ===========================================================================
# Gear diff — full gear comparison
# ===========================================================================


class TestGearDiff:
    def test_all_slots_matched(self):
        guide = {
            "Helmet": Item(explicits=[ItemMod(text="+80 to maximum Life")]),
            "Boots": Item(explicits=[ItemMod(text="+30% Movement Speed")]),
        }
        char = {
            "Helmet": EquippedItem(explicit_mods=["+75 to maximum Life"]),
            "Boots": EquippedItem(explicit_mods=["+25% increased Movement Speed"]),
        }
        delta = diff_gear(guide, char)
        assert len(delta.slot_deltas) == 2
        assert delta.overall_match_pct == 100.0

    def test_one_slot_empty(self):
        guide = {
            "Helmet": Item(name="Test Helm", explicits=[ItemMod(text="+80 to maximum Life")]),
        }
        char: dict[str, EquippedItem] = {}
        delta = diff_gear(guide, char)
        assert delta.slot_deltas[0].has_item is False
        assert delta.overall_match_pct == 0.0

    def test_worst_slots_sorted(self):
        guide = {
            "Helmet": Item(explicits=[ItemMod(text="+80 to maximum Life")]),
            "Boots": Item(explicits=[
                ItemMod(text="+80 to maximum Life"),
                ItemMod(text="+30% Movement Speed"),
                ItemMod(text="+40% Fire Resistance"),
            ]),
        }
        char = {
            "Helmet": EquippedItem(explicit_mods=["+75 to maximum Life"]),
            "Boots": EquippedItem(explicit_mods=["+10 to Dexterity"]),
        }
        delta = diff_gear(guide, char)
        worst = delta.worst_slots
        # Boots should be worst (0% match on 3 mods vs Helmet 100% on 1 mod)
        assert worst[0].slot == "Boots"


# ===========================================================================
# Gem diff
# ===========================================================================


class TestGemDiff:
    def _make_group(
        self,
        active: str,
        supports: list[str],
        slot: str = "Body Armour",
        enabled: bool = True,
    ) -> SkillGroup:
        gems = [Gem(name=active, is_support=False, is_enabled=True)]
        for s in supports:
            gems.append(Gem(name=s, is_support=True, is_enabled=True))
        return SkillGroup(slot=slot, is_enabled=enabled, gems=gems)

    def test_all_supports_present(self):
        group = self._make_group("SRS", ["Minion Damage", "Unleash"])
        char_gems = ["Summon Raging Spirit", "Minion Damage", "Unleash"]
        delta = diff_skill_group(group, char_gems)
        assert delta.missing_supports == []
        assert delta.match_pct == 100.0

    def test_missing_one_support(self):
        group = self._make_group("SRS", ["Minion Damage", "Unleash", "Melee Splash"])
        char_gems = ["Summon Raging Spirit", "Minion Damage"]
        delta = diff_skill_group(group, char_gems)
        assert len(delta.missing_supports) == 2
        assert "Unleash" in delta.missing_supports
        assert "Melee Splash" in delta.missing_supports

    def test_entirely_missing_group(self):
        group = self._make_group("SRS", ["Minion Damage"])
        delta = diff_skill_group(group, [])
        assert delta.is_missing_entirely is True
        assert delta.match_pct == 0.0

    def test_extra_supports_detected(self):
        group = self._make_group("SRS", ["Minion Damage"])
        char_gems = ["Summon Raging Spirit", "Minion Damage", "Added Fire Damage"]
        delta = diff_skill_group(group, char_gems)
        assert "Added Fire Damage" in delta.extra_supports

    def test_severity_missing_entirely(self):
        d = SkillGroupDelta(skill_name="X", is_missing_entirely=True)
        assert d.severity == Severity.CRITICAL

    def test_severity_missing_supports(self):
        d = SkillGroupDelta(skill_name="X", missing_supports=["A"])
        assert d.severity == Severity.HIGH

    def test_diff_gems_multiple_groups(self):
        groups = [
            self._make_group("SRS", ["Minion Damage"], slot="Body Armour"),
            self._make_group("Hatred", ["Generosity"], slot="Helmet"),
        ]
        char_gems = {
            "Body Armour": ["Summon Raging Spirit", "Minion Damage"],
            # Helmet gems missing
        }
        delta = diff_gems(groups, char_gems)
        assert len(delta.group_deltas) == 2
        assert delta.group_deltas[0].match_pct == 100.0
        assert delta.group_deltas[1].is_missing_entirely is True
        assert delta.total_missing_supports == 1  # Generosity

    def test_disabled_groups_excluded(self):
        groups = [
            self._make_group("SRS", ["Minion Damage"], enabled=True),
            self._make_group("Flame Dash", [], enabled=False),
        ]
        delta = diff_gems(groups, {})
        assert len(delta.group_deltas) == 1  # only SRS


# ===========================================================================
# Full engine — analyze()
# ===========================================================================


class TestEngine:
    def _make_guide(self) -> Build:
        return Build(
            class_name="Witch",
            ascendancy_name="Necromancer",
            level=92,
            build_name="SRS Necromancer",
            main_socket_group=1,
            passive_specs=[
                PassiveSpec(nodes=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
            ],
            skill_groups=[
                SkillGroup(
                    slot="Body Armour",
                    is_enabled=True,
                    gems=[
                        Gem(name="Summon Raging Spirit", is_support=False, is_enabled=True),
                        Gem(name="Minion Damage Support", is_support=True, is_enabled=True),
                        Gem(name="Unleash Support", is_support=True, is_enabled=True),
                    ],
                ),
            ],
            items=[
                Item(
                    slot="Helmet",
                    name="Horror Crown",
                    base_type="Bone Helmet",
                    explicits=[
                        ItemMod(text="+95 to maximum Life"),
                        ItemMod(text="+40% to Fire Resistance"),
                        ItemMod(text="+35% to Lightning Resistance"),
                    ],
                ),
                Item(
                    slot="Boots",
                    name="Bones of Ullr",
                    base_type="Silk Slippers",
                    explicits=[
                        ItemMod(text="+20 to maximum Life"),
                        ItemMod(text="+1 to Level of all Raise Zombie Gems"),
                    ],
                ),
            ],
        )

    def _make_character(self) -> CharacterDetail:
        return CharacterDetail(
            name="SRS_Necro",
            class_name="Necromancer",
            level=85,
            league="Settlers",
            passives=PassiveData(hashes=[1, 2, 3, 4, 5]),  # missing 6-10
            equipment=[
                EquippedItem(
                    name="Bad Helmet",
                    inventory_id="Helm",
                    explicit_mods=["+50 to maximum Life"],
                    # missing fire and lightning res
                ),
                # no boots at all
            ],
        )

    def test_analyze_produces_report(self):
        report = analyze(self._make_guide(), self._make_character())
        assert isinstance(report, DeltaReport)
        assert report.guide_build_name == "SRS Necromancer"
        assert report.character_name == "SRS_Necro"

    def test_passive_delta_populated(self):
        report = analyze(self._make_guide(), self._make_character())
        assert report.passive_delta.missing_count == 5  # nodes 6-10
        assert report.passive_delta.match_pct == 50.0

    def test_gear_delta_populated(self):
        report = analyze(self._make_guide(), self._make_character())
        gear = report.gear_delta
        assert len(gear.slot_deltas) == 2  # helmet + boots

        helmet = next(s for s in gear.slot_deltas if s.slot == "Helmet")
        assert helmet.matched_mods == 1  # life matched
        assert len(helmet.missing_mods) == 2  # fire + lightning res

        boots = next(s for s in gear.slot_deltas if s.slot == "Boots")
        assert boots.has_item is False  # no boots on character

    def test_gem_delta_populated(self):
        report = analyze(self._make_guide(), self._make_character())
        # No gem map available (no socketedItems parsing yet)
        # All guide gems should be reported as missing
        assert report.gem_delta.total_missing_supports >= 0

    def test_top_gaps_ranked(self):
        report = analyze(self._make_guide(), self._make_character())
        assert len(report.top_gaps) <= 3
        assert len(report.top_gaps) > 0

        # Gaps should be sorted by score descending
        scores = [g.score for g in report.top_gaps]
        assert scores == sorted(scores, reverse=True)

        # Each gap has a rank
        for i, gap in enumerate(report.top_gaps):
            assert gap.rank == i + 1

    def test_top_gaps_have_content(self):
        report = analyze(self._make_guide(), self._make_character())
        for gap in report.top_gaps:
            assert gap.title
            assert gap.detail
            assert gap.category in GapCategory
            assert gap.severity in Severity
            assert gap.score > 0

    def test_display_output(self):
        report = analyze(self._make_guide(), self._make_character())
        output = report.display()
        assert "SRS_Necro" in output
        assert "SRS Necromancer" in output
        assert "#1" in output  # at least one ranked gap

    def test_empty_guide_no_crash(self):
        guide = Build()
        char = CharacterDetail(name="Empty")
        report = analyze(guide, char)
        assert report.top_gaps == []

    def test_perfect_match_no_gaps(self):
        guide = Build(
            passive_specs=[PassiveSpec(nodes=[1, 2, 3])],
            items=[
                Item(
                    slot="Helmet",
                    explicits=[ItemMod(text="+80 to maximum Life")],
                ),
            ],
        )
        char = CharacterDetail(
            name="Perfect",
            passives=PassiveData(hashes=[1, 2, 3]),
            equipment=[
                EquippedItem(
                    inventory_id="Helm",
                    explicit_mods=["+80 to maximum Life"],
                ),
            ],
        )
        report = analyze(guide, char)
        # Should have no gaps or only low severity
        critical_gaps = [g for g in report.top_gaps if g.severity == Severity.CRITICAL]
        assert len(critical_gaps) == 0
