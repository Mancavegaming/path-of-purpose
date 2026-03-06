"""Tests for the PoB export code decoder."""

from __future__ import annotations

import base64
import zlib
from pathlib import Path

import pytest

from pop.build_parser.models import Build, Item, PassiveSpec, SkillGroup, Gem, BuildConfig
from pop.build_parser.pob_decode import (
    decode_pob_code,
    decode_pob_url,
    xml_to_string,
    _decompress_code,
    _parse_item_text,
)

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_CODE = (FIXTURES / "sample_build_code.txt").read_text().strip()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_code_from_xml(xml: str) -> str:
    """Create a PoB export code from raw XML string (for test isolation)."""
    compressed = zlib.compress(xml.encode("utf-8"))
    return base64.urlsafe_b64encode(compressed).decode("ascii")


MINIMAL_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding version="2.38.0">
    <Build className="Shadow" ascClassName="Assassin" level="95" mainSocketGroup="1" />
    <Tree />
    <Skills />
    <Items />
    <Config />
</PathOfBuilding>
"""


# ===========================================================================
# Decompression tests
# ===========================================================================


class TestDecompress:
    def test_valid_code_decompresses(self):
        xml_bytes = _decompress_code(SAMPLE_CODE)
        assert b"<PathOfBuilding" in xml_bytes

    def test_standard_base64_also_works(self):
        """PoB sometimes uses standard Base64 (+ and /) instead of URL-safe."""
        xml = b"<PathOfBuilding><Build/></PathOfBuilding>"
        compressed = zlib.compress(xml)
        # Encode with standard Base64, not URL-safe
        standard_b64 = base64.b64encode(compressed).decode("ascii")
        result = _decompress_code(standard_b64)
        assert b"<PathOfBuilding>" in result

    def test_invalid_base64_raises(self):
        with pytest.raises(ValueError, match="(Base64 decode failed|Zlib decompress failed)"):
            _decompress_code("!!!not-valid-base64!!!")

    def test_invalid_zlib_raises(self):
        # Valid Base64 but not zlib-compressed
        code = base64.urlsafe_b64encode(b"not compressed data").decode()
        with pytest.raises(ValueError, match="Zlib decompress failed"):
            _decompress_code(code)


# ===========================================================================
# Full decode tests (using sample fixture)
# ===========================================================================


class TestDecodeFullBuild:
    @pytest.fixture()
    def build(self) -> Build:
        return decode_pob_code(SAMPLE_CODE)

    def test_class_and_ascendancy(self, build: Build):
        assert build.class_name == "Witch"
        assert build.ascendancy_name == "Necromancer"

    def test_level(self, build: Build):
        assert build.level == 92

    def test_build_name(self, build: Build):
        assert build.build_name == "SRS Necromancer"

    def test_pob_version(self, build: Build):
        assert build.pob_version == "2.38.0"

    def test_main_socket_group(self, build: Build):
        assert build.main_socket_group == 1

    def test_summary_contains_key_info(self, build: Build):
        s = build.summary()
        assert "Necromancer" in s
        assert "92" in s


# ===========================================================================
# Skill / gem parsing
# ===========================================================================


class TestSkillParsing:
    @pytest.fixture()
    def build(self) -> Build:
        return decode_pob_code(SAMPLE_CODE)

    def test_skill_group_count(self, build: Build):
        assert len(build.skill_groups) == 3

    def test_main_skill_has_active_gem(self, build: Build):
        main = build.skill_groups[0]
        assert main.active_gem is not None
        assert main.active_gem.name == "Summon Raging Spirit"

    def test_main_skill_has_supports(self, build: Build):
        main = build.skill_groups[0]
        supports = main.support_gems
        assert len(supports) == 3
        support_names = {g.name for g in supports}
        assert "Minion Damage Support" in support_names
        assert "Unleash Support" in support_names
        assert "Melee Splash Support" in support_names

    def test_gem_levels_and_quality(self, build: Build):
        main = build.skill_groups[0]
        srs = main.active_gem
        assert srs.level == 21
        assert srs.quality == 20

    def test_disabled_skill_group(self, build: Build):
        movement = build.skill_groups[2]
        assert movement.is_enabled is False
        assert movement.label == "Movement"

    def test_aura_group(self, build: Build):
        auras = build.skill_groups[1]
        assert auras.active_gem.name == "Hatred"
        assert len(auras.support_gems) == 1
        assert auras.support_gems[0].name == "Generosity Support"

    def test_gem_display_name(self):
        gem = Gem(name="Summon Raging Spirit", level=21, quality=20)
        assert gem.display_name == "Summon Raging Spirit (Lv 21) (20%)"

    def test_gem_display_name_defaults(self):
        gem = Gem(name="Hatred", level=20, quality=0)
        assert gem.display_name == "Hatred"


# ===========================================================================
# Item parsing
# ===========================================================================


class TestItemParsing:
    @pytest.fixture()
    def build(self) -> Build:
        return decode_pob_code(SAMPLE_CODE)

    def test_item_count(self, build: Build):
        assert len(build.items) == 3

    def test_slot_assignment(self, build: Build):
        slots = build.items_by_slot()
        assert "Weapon 1" in slots
        assert "Boots" in slots
        assert "Helmet" in slots

    def test_rare_item_name_and_base(self, build: Build):
        slots = build.items_by_slot()
        shield = slots["Weapon 1"]
        assert shield.name == "Glyph Hold"
        assert shield.base_type == "Titanium Spirit Shield"
        assert shield.rarity == "RARE"

    def test_unique_item(self, build: Build):
        slots = build.items_by_slot()
        boots = slots["Boots"]
        assert boots.name == "Bones of Ullr"
        assert boots.base_type == "Silk Slippers"
        assert boots.rarity == "UNIQUE"

    def test_implicit_mods(self, build: Build):
        slots = build.items_by_slot()
        shield = slots["Weapon 1"]
        assert len(shield.implicits) == 1
        assert "Spell Damage" in shield.implicits[0].text

    def test_explicit_mods(self, build: Build):
        slots = build.items_by_slot()
        shield = slots["Weapon 1"]
        assert len(shield.explicits) >= 3
        mod_texts = [m.text for m in shield.explicits]
        assert any("maximum Life" in t for t in mod_texts)
        assert any("Fire Resistance" in t for t in mod_texts)

    def test_crafted_mod_detected(self, build: Build):
        slots = build.items_by_slot()
        helmet = slots["Helmet"]
        crafted = [m for m in helmet.explicits if m.is_crafted]
        assert len(crafted) == 1
        assert "Trigger" in crafted[0].text

    def test_all_mods_property(self, build: Build):
        slots = build.items_by_slot()
        shield = slots["Weapon 1"]
        assert len(shield.all_mods) == len(shield.implicits) + len(shield.explicits)

    def test_quality(self, build: Build):
        slots = build.items_by_slot()
        shield = slots["Weapon 1"]
        assert shield.quality == 20


# ===========================================================================
# Item text parser (unit-level)
# ===========================================================================


class TestParseItemText:
    def test_empty_text(self):
        item = _parse_item_text("")
        assert item.name == ""
        assert item.base_type == ""

    def test_minimal_item(self):
        text = "Rarity: NORMAL\nIron Ring\nImplicits: 0"
        item = _parse_item_text(text)
        assert item.rarity == "NORMAL"
        assert item.base_type == "Iron Ring"

    def test_item_with_name_and_base(self):
        text = "Rarity: RARE\nMy Cool Ring\nRuby Ring\nImplicits: 0\n+10 to Strength"
        item = _parse_item_text(text)
        assert item.name == "My Cool Ring"
        assert item.base_type == "Ruby Ring"
        assert len(item.explicits) == 1

    def test_crafted_mod_braces(self):
        text = "Rarity: RARE\nHelmet\nBone Helmet\nImplicits: 0\n{+1 to Minion Gems}"
        item = _parse_item_text(text)
        assert item.explicits[0].is_crafted is True
        assert item.explicits[0].text == "+1 to Minion Gems"


# ===========================================================================
# Config parsing
# ===========================================================================


class TestConfigParsing:
    @pytest.fixture()
    def build(self) -> Build:
        return decode_pob_code(SAMPLE_CODE)

    def test_config_entries_parsed(self, build: Build):
        cfg = build.config.entries
        assert cfg["enemyIsBoss"] == "Pinnacle"
        assert cfg["useFrenzyCharges"] == "true"
        assert cfg["minionsUsePowerCharges"] == "true"


# ===========================================================================
# Passive tree parsing
# ===========================================================================


class TestPassiveTree:
    @pytest.fixture()
    def build(self) -> Build:
        return decode_pob_code(SAMPLE_CODE)

    def test_has_passive_spec(self, build: Build):
        assert len(build.passive_specs) == 1

    def test_spec_title(self, build: Build):
        spec = build.passive_specs[0]
        assert spec.title == "Main"

    def test_tree_version(self, build: Build):
        spec = build.passive_specs[0]
        assert spec.tree_version == "3_25"

    def test_class_and_ascendancy_ids(self, build: Build):
        spec = build.passive_specs[0]
        assert spec.class_id == 5
        assert spec.ascendancy_id == 2


# ===========================================================================
# URL parsing
# ===========================================================================


class TestPobUrl:
    def test_pastebin_url(self):
        raw = decode_pob_url("https://pastebin.com/abc123")
        assert raw == "https://pastebin.com/raw/abc123"

    def test_pastebin_raw_url_passthrough(self):
        raw = decode_pob_url("https://pastebin.com/raw/abc123")
        assert raw == "https://pastebin.com/raw/abc123"

    def test_pobbin_url(self):
        raw = decode_pob_url("https://pobb.in/some-build-id")
        assert raw == "https://pobb.in/some-build-id/raw"

    def test_unknown_url_raises(self):
        with pytest.raises(ValueError, match="Unrecognized"):
            decode_pob_url("https://example.com/build")


# ===========================================================================
# Minimal XML (edge cases)
# ===========================================================================


class TestMinimalBuild:
    def test_minimal_xml_decodes(self):
        code = _make_code_from_xml(MINIMAL_XML)
        build = decode_pob_code(code)
        assert build.class_name == "Shadow"
        assert build.ascendancy_name == "Assassin"
        assert build.level == 95
        assert build.items == []
        assert build.skill_groups == []

    def test_missing_build_element_raises(self):
        xml = '<PathOfBuilding version="1"><NoBuild/></PathOfBuilding>'
        code = _make_code_from_xml(xml)
        with pytest.raises(ValueError, match="Missing <Build>"):
            decode_pob_code(code)


# ===========================================================================
# xml_to_string debug helper
# ===========================================================================


class TestXmlToString:
    def test_returns_formatted_xml(self):
        result = xml_to_string(SAMPLE_CODE)
        assert "<PathOfBuilding" in result
        assert "<Build" in result
        assert isinstance(result, str)
