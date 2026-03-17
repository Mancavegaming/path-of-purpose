"""Tests for PoE clipboard item parser."""

import pytest

from pop.price_check.clipboard_parser import parse_clipboard_item, ClipboardItem


# --- Sample clipboard texts ---

RARE_ARMOUR = """Item Class: Body Armours
Rarity: Rare
Doom Shell
Vaal Regalia
--------
Quality: +20% (augmented)
Energy Shield: 487 (augmented)
--------
Requirements:
Level: 68
Int: 194
--------
Sockets: B-B-B-B-B-B
--------
Item Level: 86
--------
+46 to maximum Energy Shield
+98 to maximum Life
+44% to Fire Resistance
+35% to Lightning Resistance
11% increased Stun and Block Recovery
--------
Shaper Item
"""

UNIQUE_WEAPON = """Item Class: Daggers
Rarity: Unique
Heartbreaker
Royal Skean
--------
Dagger
Physical Damage: 20-78
Critical Strike Chance: 6.50%
Attacks per Second: 1.30
Weapon Range: 10
--------
Requirements:
Level: 50
Dex: 71
Int: 102
--------
Sockets: B-G-G
--------
Item Level: 72
--------
40% increased Global Critical Strike Chance
--------
Adds 1 to 40 Lightning Damage to Spells
+50 to maximum Mana
10% increased Mana Regeneration Rate
Your Spells have Culling Strike
--------
"""

CORRUPTED_ITEM = """Item Class: Amulets
Rarity: Rare
Corruption Choker
Onyx Amulet
--------
Requirements:
Level: 60
--------
Item Level: 82
--------
+16 to all Attributes
--------
+37 to Dexterity
+79 to maximum Life
+41% to Fire Resistance
+31% to Cold Resistance
+15% to Lightning Resistance
--------
Corrupted
"""

INFLUENCED_ITEM = """Item Class: Gloves
Rarity: Rare
Mind Grip
Sorcerer Gloves
--------
Energy Shield: 96 (augmented)
--------
Requirements:
Level: 69
Int: 97
--------
Sockets: B-B-B-B
--------
Item Level: 85
--------
+67 to maximum Energy Shield
+89 to maximum Life
+46% to Cold Resistance
+43% to Lightning Resistance
--------
Shaper Item
Elder Item
"""

GEM_TEXT = """Item Class: Skill Gems
Rarity: Gem
Vaal Grace
--------
Level: 21 (Max)
Mana Cost: 50
Cast Time: 0.60 sec
Quality: +23%
--------
Requirements:
Level: 68
Dex: 117
--------
Grants the Grace skill
--------
"""

CURRENCY_TEXT = """Item Class: Currency
Rarity: Currency
Chaos Orb
--------
Stack Size: 14/20
--------
Reforges a rare item with new random modifiers
--------
"""

MAGIC_ITEM = """Item Class: Belts
Rarity: Magic
Stout Leather Belt of the Walrus
--------
Requirements:
Level: 8
--------
Item Level: 75
--------
+31 to maximum Life
--------
+47 to maximum Life
+16% to Cold Resistance
--------
"""

UNIDENTIFIED_ITEM = """Item Class: Body Armours
Rarity: Rare
Glorious Plate
--------
Armour: 776
--------
Requirements:
Level: 68
Str: 191
--------
Sockets: R-R-R-R-R-R
--------
Item Level: 84
--------
Unidentified
"""


class TestParseRareArmour:
    def test_rarity(self):
        item = parse_clipboard_item(RARE_ARMOUR)
        assert item.rarity == "Rare"

    def test_name(self):
        item = parse_clipboard_item(RARE_ARMOUR)
        assert item.name == "Doom Shell"

    def test_base_type(self):
        item = parse_clipboard_item(RARE_ARMOUR)
        assert item.base_type == "Vaal Regalia"

    def test_item_class(self):
        item = parse_clipboard_item(RARE_ARMOUR)
        assert item.item_class == "Body Armours"

    def test_quality(self):
        item = parse_clipboard_item(RARE_ARMOUR)
        assert item.quality == 20

    def test_ilvl(self):
        item = parse_clipboard_item(RARE_ARMOUR)
        assert item.ilvl == 86

    def test_sockets(self):
        item = parse_clipboard_item(RARE_ARMOUR)
        assert item.sockets == "B-B-B-B-B-B"

    def test_explicits(self):
        item = parse_clipboard_item(RARE_ARMOUR)
        assert len(item.explicits) >= 4
        assert any("maximum Life" in m for m in item.explicits)
        assert any("Fire Resistance" in m for m in item.explicits)

    def test_influences(self):
        item = parse_clipboard_item(RARE_ARMOUR)
        assert "Shaper" in item.influences

    def test_not_corrupted(self):
        item = parse_clipboard_item(RARE_ARMOUR)
        assert not item.corrupted


class TestParseUniqueWeapon:
    def test_rarity(self):
        item = parse_clipboard_item(UNIQUE_WEAPON)
        assert item.rarity == "Unique"

    def test_name(self):
        item = parse_clipboard_item(UNIQUE_WEAPON)
        assert item.name == "Heartbreaker"

    def test_base_type(self):
        item = parse_clipboard_item(UNIQUE_WEAPON)
        assert item.base_type == "Royal Skean"

    def test_item_class(self):
        item = parse_clipboard_item(UNIQUE_WEAPON)
        assert item.item_class == "Daggers"

    def test_has_implicits(self):
        item = parse_clipboard_item(UNIQUE_WEAPON)
        assert len(item.implicits) >= 1
        assert any("Critical Strike Chance" in m for m in item.implicits)

    def test_has_explicits(self):
        item = parse_clipboard_item(UNIQUE_WEAPON)
        assert len(item.explicits) >= 3


class TestParseCorruptedItem:
    def test_corrupted(self):
        item = parse_clipboard_item(CORRUPTED_ITEM)
        assert item.corrupted

    def test_has_implicit(self):
        item = parse_clipboard_item(CORRUPTED_ITEM)
        assert len(item.implicits) >= 1
        assert any("all Attributes" in m for m in item.implicits)

    def test_has_explicits(self):
        item = parse_clipboard_item(CORRUPTED_ITEM)
        assert len(item.explicits) >= 4


class TestParseInfluencedItem:
    def test_double_influence(self):
        item = parse_clipboard_item(INFLUENCED_ITEM)
        assert "Shaper" in item.influences
        assert "Elder" in item.influences


class TestParseGem:
    def test_is_gem(self):
        item = parse_clipboard_item(GEM_TEXT)
        assert item.is_gem

    def test_gem_level(self):
        item = parse_clipboard_item(GEM_TEXT)
        assert item.gem_level == 21

    def test_gem_quality(self):
        item = parse_clipboard_item(GEM_TEXT)
        assert item.gem_quality == 23

    def test_base_type(self):
        item = parse_clipboard_item(GEM_TEXT)
        assert item.base_type == "Vaal Grace"


class TestParseCurrency:
    def test_is_currency(self):
        item = parse_clipboard_item(CURRENCY_TEXT)
        assert item.is_currency

    def test_base_type(self):
        item = parse_clipboard_item(CURRENCY_TEXT)
        assert item.base_type == "Chaos Orb"


class TestParseMagicItem:
    def test_rarity(self):
        item = parse_clipboard_item(MAGIC_ITEM)
        assert item.rarity == "Magic"

    def test_base_type(self):
        item = parse_clipboard_item(MAGIC_ITEM)
        assert "Leather Belt" in item.base_type


class TestParseUnidentifiedItem:
    def test_unidentified(self):
        item = parse_clipboard_item(UNIDENTIFIED_ITEM)
        assert item.unidentified

    def test_no_explicits(self):
        item = parse_clipboard_item(UNIDENTIFIED_ITEM)
        assert len(item.explicits) == 0


class TestEdgeCases:
    def test_empty_text_raises(self):
        with pytest.raises(ValueError):
            parse_clipboard_item("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            parse_clipboard_item("   \n\n  ")
