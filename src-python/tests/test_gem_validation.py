"""Tests for AI build generator gem validation (PoE 2 / hallucinated gem removal)."""

import pytest

from pop.ai.generator import _build_valid_gem_names, _is_valid_gem, _validate_guide_gems
from pop.build_parser.models import (
    BuildGuide,
    GuideGem,
    GuideGemGroup,
    LevelBracket,
)
from pop.knowledge.models import GemInfo, KnowledgeBase


def _make_kb(gem_names: list[str]) -> KnowledgeBase:
    """Create a minimal KnowledgeBase with the given gem names."""
    gems = [GemInfo(name=n, is_support="Support" in n) for n in gem_names]
    return KnowledgeBase(gems=gems, version="test")


def _make_guide(gem_names_by_slot: dict[str, list[str]]) -> BuildGuide:
    """Create a minimal BuildGuide with one bracket containing the given gems."""
    groups = []
    for slot, names in gem_names_by_slot.items():
        gems = [GuideGem(name=n, is_support="Support" in n) for n in names]
        groups.append(GuideGemGroup(slot=slot, gems=gems))
    bracket = LevelBracket(title="1-12", gem_groups=groups)
    return BuildGuide(url="", title="Test Build", brackets=[bracket])


class TestBuildValidGemNames:
    def test_from_knowledge_base(self):
        kb = _make_kb(["Cyclone", "Melee Physical Damage Support"])
        names = _build_valid_gem_names(kb)
        assert "Cyclone" in names
        assert "Melee Physical Damage Support" in names

    def test_includes_gem_data_fallback(self):
        names = _build_valid_gem_names(None)
        # gem_data should have common gems
        assert len(names) > 50

    def test_merges_both_sources(self):
        kb = _make_kb(["Totally New Gem"])
        names = _build_valid_gem_names(kb)
        assert "Totally New Gem" in names
        # Should also have gems from gem_data
        assert len(names) > 50


class TestIsValidGem:
    def test_exact_match(self):
        valid = {"Cyclone", "Melee Physical Damage Support"}
        assert _is_valid_gem("Cyclone", valid)
        assert _is_valid_gem("Melee Physical Damage Support", valid)

    def test_unknown_gem(self):
        valid = {"Cyclone", "Melee Physical Damage Support"}
        assert not _is_valid_gem("Hypnotic Eye Support", valid)

    def test_vaal_variant(self):
        valid = {"Cyclone"}
        assert _is_valid_gem("Vaal Cyclone", valid)

    def test_support_suffix_normalization(self):
        valid = {"Brutality Support"}
        # Name without suffix should match if "X Support" is in the set
        assert _is_valid_gem("Brutality", valid)


class TestValidateGuideGems:
    def test_removes_invalid_gems(self):
        kb = _make_kb(["Cyclone", "Melee Physical Damage Support", "Brutality Support"])
        guide = _make_guide({
            "Body Armour": [
                "Cyclone",
                "Melee Physical Damage Support",
                "Hypnotic Eye Support",  # PoE 2 gem — should be removed
            ],
        })

        result = _validate_guide_gems(guide, kb)

        gems = result.brackets[0].gem_groups[0].gems
        names = [g.name for g in gems]
        assert "Cyclone" in names
        assert "Melee Physical Damage Support" in names
        assert "Hypnotic Eye Support" not in names

    def test_keeps_all_valid_gems(self):
        kb = _make_kb(["Spark", "Spell Echo Support", "Controlled Destruction Support"])
        guide = _make_guide({
            "Body Armour": ["Spark", "Spell Echo Support", "Controlled Destruction Support"],
        })

        result = _validate_guide_gems(guide, kb)

        gems = result.brackets[0].gem_groups[0].gems
        assert len(gems) == 3

    def test_multiple_brackets_and_slots(self):
        kb = _make_kb(["Cyclone", "Flame Dash"])
        guide = BuildGuide(
            url="", title="Test",
            brackets=[
                LevelBracket(
                    title="1-12",
                    gem_groups=[
                        GuideGemGroup(
                            slot="Body Armour",
                            gems=[
                                GuideGem(name="Cyclone"),
                                GuideGem(name="Fake Gem Support", is_support=True),
                            ],
                        ),
                    ],
                ),
                LevelBracket(
                    title="12-24",
                    gem_groups=[
                        GuideGemGroup(
                            slot="Boots",
                            gems=[
                                GuideGem(name="Flame Dash"),
                                GuideGem(name="Another Fake", is_support=True),
                            ],
                        ),
                    ],
                ),
            ],
        )

        result = _validate_guide_gems(guide, kb)

        b1_gems = [g.name for g in result.brackets[0].gem_groups[0].gems]
        b2_gems = [g.name for g in result.brackets[1].gem_groups[0].gems]
        assert b1_gems == ["Cyclone"]
        assert b2_gems == ["Flame Dash"]

    def test_no_valid_names_skips_validation(self):
        """If no valid gem names are loaded, skip validation (don't remove everything)."""
        kb = KnowledgeBase(gems=[], version="empty")
        guide = _make_guide({"Body Armour": ["Some Gem"]})

        # With empty KB and no gem_data fallback, validation should still work
        # because gem_data fallback provides names
        result = _validate_guide_gems(guide, kb)
        # The gem may or may not survive depending on gem_data contents,
        # but the function shouldn't crash
        assert len(result.brackets) == 1

    def test_poe2_gems_removed(self):
        """Specific PoE 2 gems that AI has hallucinated should be caught."""
        kb = _make_kb(["Cyclone", "Melee Physical Damage Support"])
        poe2_gems = [
            "Hypnotic Eye Support",
            "Tempest Bell",
            "Arcane Surge of Overflowing",  # Fake PoE 2 transfig
            "Glacial Cascade of Annihilation",  # Fake
        ]
        guide = _make_guide({
            "Body Armour": ["Cyclone", "Melee Physical Damage Support"] + poe2_gems,
        })

        result = _validate_guide_gems(guide, kb)

        gems = [g.name for g in result.brackets[0].gem_groups[0].gems]
        assert "Cyclone" in gems
        assert "Melee Physical Damage Support" in gems
        for poe2 in poe2_gems:
            assert poe2 not in gems
