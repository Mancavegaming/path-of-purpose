"""
Synthetic item generator for AI-built guides.

Converts GuideItem stat_priority lists into realistic Item objects with
actual mod text and numeric values, so the DPS calculator and item display
work on generated builds.

Two tiers:
- "basic" (budget / early mapping): ~T3-T4 mod rolls
- "max" (endgame / optimized): ~T1-T2 mod rolls
"""

from __future__ import annotations

from pop.build_parser.models import GuideItem, Item, ItemMod
from pop.calc.unique_db import get_unique


# ===================================================================
# Stat priority → mod text mapping
# ===================================================================
# Each entry: stat_keyword → (mod_text_template, basic_value, max_value)
# Template uses {v} for the numeric value.
# Some stats produce multiple mod lines (e.g., "elemental resistances").

_STAT_MODS: dict[str, list[tuple[str, float, float]]] = {
    # --- Life / ES / Mana ---
    "life": [("+{v} to maximum Life", 80, 130)],
    "maximum life": [("+{v} to maximum Life", 80, 130)],
    "flat life": [("+{v} to maximum Life", 80, 130)],
    "energy shield": [("+{v} to maximum Energy Shield", 55, 100)],
    "flat energy shield": [("+{v} to maximum Energy Shield", 55, 100)],
    "flat es": [("+{v} to maximum Energy Shield", 55, 100)],
    "% energy shield": [("{v}% increased maximum Energy Shield", 60, 110)],
    "mana": [("+{v} to maximum Mana", 60, 100)],

    # --- Resistances ---
    "fire resistance": [("+{v}% to Fire Resistance", 30, 46)],
    "fire res": [("+{v}% to Fire Resistance", 30, 46)],
    "cold resistance": [("+{v}% to Cold Resistance", 30, 46)],
    "cold res": [("+{v}% to Cold Resistance", 30, 46)],
    "lightning resistance": [("+{v}% to Lightning Resistance", 30, 46)],
    "lightning res": [("+{v}% to Lightning Resistance", 30, 46)],
    "chaos resistance": [("+{v}% to Chaos Resistance", 20, 35)],
    "chaos res": [("+{v}% to Chaos Resistance", 20, 35)],
    "elemental resistances": [
        ("+{v}% to Fire Resistance", 30, 46),
        ("+{v}% to Cold Resistance", 30, 46),
        ("+{v}% to Lightning Resistance", 30, 46),
    ],
    "all resistances": [("+{v}% to all Elemental Resistances", 12, 18)],
    "all res": [("+{v}% to all Elemental Resistances", 12, 18)],

    # --- Attributes ---
    "strength": [("+{v} to Strength", 30, 55)],
    "dexterity": [("+{v} to Dexterity", 30, 55)],
    "intelligence": [("+{v} to Intelligence", 30, 55)],
    "all attributes": [("+{v} to all Attributes", 12, 20)],
    "attributes": [("+{v} to all Attributes", 12, 20)],

    # --- Damage (generic) ---
    "increased damage": [("{v}% increased Damage", 20, 40)],
    "increased elemental damage": [("{v}% increased Elemental Damage", 25, 40)],
    "increased physical damage": [("{v}% increased Physical Damage", 40, 80)],
    "% physical damage": [("{v}% increased Physical Damage", 40, 80)],
    "increased fire damage": [("{v}% increased Fire Damage", 25, 40)],
    "increased cold damage": [("{v}% increased Cold Damage", 25, 40)],
    "increased lightning damage": [("{v}% increased Lightning Damage", 25, 40)],
    "increased chaos damage": [("{v}% increased Chaos Damage", 25, 40)],
    "increased spell damage": [("{v}% increased Spell Damage", 30, 65)],
    "spell damage": [("{v}% increased Spell Damage", 30, 65)],

    # --- Added damage ---
    "added physical damage": [("Adds {v} to {v2} Physical Damage", 8, 18)],
    "added fire damage": [("Adds {v} to {v2} Fire Damage", 15, 35)],
    "added fire damage to attacks": [("Adds {v} to {v2} Fire Damage to Attacks", 15, 35)],
    "added cold damage": [("Adds {v} to {v2} Cold Damage", 15, 35)],
    "added cold damage to attacks": [("Adds {v} to {v2} Cold Damage to Attacks", 15, 35)],
    "added lightning damage": [("Adds {v} to {v2} Lightning Damage", 5, 12)],
    "added lightning damage to attacks": [("Adds {v} to {v2} Lightning Damage to Attacks", 5, 12)],
    "added chaos damage": [("Adds {v} to {v2} Chaos Damage", 12, 28)],

    # --- Speed ---
    "attack speed": [("{v}% increased Attack Speed", 8, 16)],
    "increased attack speed": [("{v}% increased Attack Speed", 8, 16)],
    "cast speed": [("{v}% increased Cast Speed", 8, 16)],
    "increased cast speed": [("{v}% increased Cast Speed", 8, 16)],
    "movement speed": [("{v}% increased Movement Speed", 20, 30)],
    "move speed": [("{v}% increased Movement Speed", 20, 30)],

    # --- Crit ---
    "critical strike chance": [("{v}% increased Global Critical Strike Chance", 20, 35)],
    "crit chance": [("{v}% increased Global Critical Strike Chance", 20, 35)],
    "global crit": [("{v}% increased Global Critical Strike Chance", 20, 35)],
    "critical strike multiplier": [("+{v}% to Global Critical Strike Multiplier", 20, 38)],
    "crit multi": [("+{v}% to Global Critical Strike Multiplier", 20, 38)],
    "crit multiplier": [("+{v}% to Global Critical Strike Multiplier", 20, 38)],
    "spell crit": [("{v}% increased Critical Strike Chance for Spells", 40, 80)],

    # --- Gem levels ---
    "+1 gems": [("+1 to Level of all Skill Gems", 1, 1)],
    "+1 all gems": [("+1 to Level of all Skill Gems", 1, 1)],
    "+1 fire gems": [("+1 to Level of all Fire Skill Gems", 1, 1)],
    "+1 cold gems": [("+1 to Level of all Cold Skill Gems", 1, 1)],
    "+1 lightning gems": [("+1 to Level of all Lightning Skill Gems", 1, 1)],
    "+1 chaos gems": [("+1 to Level of all Chaos Skill Gems", 1, 1)],
    "+1 physical gems": [("+1 to Level of all Physical Skill Gems", 1, 1)],
    "+2 gems": [("+2 to Level of all Skill Gems", 2, 2)],
    "gem level": [("+1 to Level of all Skill Gems", 1, 1)],

    # --- Defences ---
    "armour": [("+{v} to Armour", 200, 500)],
    "flat armour": [("+{v} to Armour", 200, 500)],
    "% armour": [("{v}% increased Armour", 60, 120)],
    "evasion": [("+{v} to Evasion Rating", 200, 500)],
    "flat evasion": [("+{v} to Evasion Rating", 200, 500)],
    "% evasion": [("{v}% increased Evasion Rating", 60, 120)],
    "block": [("{v}% Chance to Block", 3, 5)],
    "spell block": [("{v}% Chance to Block Spell Damage", 3, 5)],
    "dodge": [("{v}% chance to Dodge Attack Hits", 3, 5)],

    # --- Leech / sustain ---
    "life leech": [("{v}% of Physical Attack Damage Leeched as Life", 0.4, 0.8)],
    "mana leech": [("{v}% of Physical Attack Damage Leeched as Mana", 0.2, 0.4)],
    "life on hit": [("+{v} Life gained for each Enemy hit by Attacks", 10, 20)],
    "life regen": [("{v} Life Regenerated per second", 50, 100)],
    "life regeneration": [("{v} Life Regenerated per second", 50, 100)],

    # --- Minion ---
    "minion damage": [("{v}% increased Minion Damage", 20, 40)],
    "minion life": [("{v}% increased Minion Life", 20, 40)],
    "minion speed": [("{v}% increased Minion Movement Speed", 15, 25)],

    # --- DoT ---
    "damage over time": [("{v}% increased Damage over Time", 20, 35)],
    "dot damage": [("{v}% increased Damage over Time", 20, 35)],
    "damage over time multiplier": [("+{v}% to Damage over Time Multiplier", 15, 30)],
    "dot multi": [("+{v}% to Damage over Time Multiplier", 15, 30)],
    "dot multiplier": [("+{v}% to Damage over Time Multiplier", 15, 30)],
    "fire dot multi": [("+{v}% to Fire Damage over Time Multiplier", 15, 30)],
    "chaos dot multi": [("+{v}% to Chaos Damage over Time Multiplier", 15, 30)],
    "cold dot multi": [("+{v}% to Cold Damage over Time Multiplier", 15, 30)],
    "physical dot multi": [("+{v}% to Physical Damage over Time Multiplier", 15, 30)],

    # --- Penetration ---
    "fire penetration": [("Damage Penetrates {v}% Fire Resistance", 5, 10)],
    "cold penetration": [("Damage Penetrates {v}% Cold Resistance", 5, 10)],
    "lightning penetration": [("Damage Penetrates {v}% Lightning Resistance", 5, 10)],
    "elemental penetration": [("Damage Penetrates {v}% Elemental Resistances", 3, 6)],

    # --- Accuracy ---
    "accuracy": [("+{v} to Accuracy Rating", 200, 400)],
    "accuracy rating": [("+{v} to Accuracy Rating", 200, 400)],

    # --- Aura / reservation ---
    "aura effect": [("{v}% increased effect of Non-Curse Auras from your Skills", 10, 20)],
    "reduced mana reservation": [("{v}% reduced Mana Reserved", 3, 6)],

    # --- Conversion ---
    "phys to lightning": [("{v}% of Physical Damage Converted to Lightning Damage", 25, 50)],
    "phys to fire": [("{v}% of Physical Damage Converted to Fire Damage", 25, 50)],
    "phys to cold": [("{v}% of Physical Damage Converted to Cold Damage", 25, 50)],

    # --- Misc ---
    "item quantity": [("{v}% increased Quantity of Items found", 5, 10)],
    "item rarity": [("{v}% increased Rarity of Items found", 15, 30)],
}


# ===================================================================
# Weapon base type database — full leveling + endgame progression
# ===================================================================
# (base_name, phys_min, phys_max, aps, crit, implicit)
# Organized by type, sorted roughly by level requirement (low → high)

_WEAPON_BASES: dict[str, tuple[str, int, int, float, float, str]] = {
    # ---------------------------------------------------------------
    # ONE-HAND SWORDS — Thrusting (crit multi implicit)
    # ---------------------------------------------------------------
    # Early (lv 1-30)
    "Rusted Spike": ("Rusted Spike", 5, 20, 1.55, 5.5, "+15% to Global Critical Strike Multiplier"),
    "Whalebone Rapier": ("Whalebone Rapier", 6, 24, 1.6, 5.0, "+20% to Global Critical Strike Multiplier"),
    "Basket Rapier": ("Basket Rapier", 8, 32, 1.6, 5.0, "+20% to Global Critical Strike Multiplier"),
    "Thorn Rapier": ("Thorn Rapier", 10, 21, 1.6, 5.5, "+25% to Global Critical Strike Multiplier"),
    # Mid (lv 30-55)
    "Wyrmbone Rapier": ("Wyrmbone Rapier", 12, 48, 1.6, 5.0, "+25% to Global Critical Strike Multiplier"),
    "Estoc": ("Estoc", 15, 60, 1.5, 5.5, "+25% to Global Critical Strike Multiplier"),
    "Fancy Foil": ("Fancy Foil", 24, 45, 1.6, 5.5, "+25% to Global Critical Strike Multiplier"),
    "Harpy Rapier": ("Harpy Rapier", 20, 37, 1.6, 5.5, "+25% to Global Critical Strike Multiplier"),
    # Late (lv 55+)
    "Pecoraro": ("Pecoraro", 28, 52, 1.55, 5.5, "+25% to Global Critical Strike Multiplier"),
    "Elegant Foil": ("Elegant Foil", 30, 56, 1.6, 5.5, "+25% to Global Critical Strike Multiplier"),
    "Spiraled Foil": ("Spiraled Foil", 35, 66, 1.6, 5.5, "+25% to Global Critical Strike Multiplier"),
    "Tempered Foil": ("Tempered Foil", 40, 74, 1.55, 5.5, "+25% to Global Critical Strike Multiplier"),
    "Jewelled Foil": ("Jewelled Foil", 43, 80, 1.6, 5.5, "+25% to Global Critical Strike Multiplier"),
    "Apex Rapier": ("Apex Rapier", 38, 71, 1.5, 6.0, "+25% to Global Critical Strike Multiplier"),
    "Vaal Rapier": ("Vaal Rapier", 56, 104, 1.5, 6.5, "+25% to Global Critical Strike Multiplier"),

    # ---------------------------------------------------------------
    # ONE-HAND SWORDS — Non-thrusting
    # ---------------------------------------------------------------
    # Early
    "Rusted Sword": ("Rusted Sword", 4, 11, 1.55, 5.0, "40% increased Global Accuracy Rating"),
    "Copper Sword": ("Copper Sword", 5, 15, 1.5, 5.0, "40% increased Global Accuracy Rating"),
    "Sabre": ("Sabre", 6, 18, 1.5, 5.0, "40% increased Global Accuracy Rating"),
    "Cutlass": ("Cutlass", 9, 27, 1.5, 5.0, "+6% Chance to Block Attack Damage while Dual Wielding"),
    "Broad Sword": ("Broad Sword", 8, 24, 1.4, 5.0, "40% increased Global Accuracy Rating"),
    # Mid
    "Baselard": ("Baselard", 14, 42, 1.5, 5.0, "40% increased Global Accuracy Rating"),
    "Highland Blade": ("Highland Blade", 16, 48, 1.35, 5.0, "40% increased Global Accuracy Rating"),
    "Centurion Sword": ("Centurion Sword", 18, 54, 1.5, 5.0, "40% increased Global Accuracy Rating"),
    "Jade Sword": ("Jade Sword", 20, 60, 1.5, 5.0, "40% increased Global Accuracy Rating"),
    "Twilight Blade": ("Twilight Blade", 20, 45, 1.3, 5.0, "+6% Chance to Block Attack Damage while Dual Wielding"),
    # Late
    "Midnight Blade": ("Midnight Blade", 30, 80, 1.3, 5.0, "+6% Chance to Block Attack Damage while Dual Wielding"),
    "Tiger Hook": ("Tiger Hook", 26, 78, 1.5, 5.0, "+6% Chance to Block Attack Damage while Dual Wielding"),
    "Gladius": ("Gladius", 27, 82, 1.5, 5.0, "40% increased Global Accuracy Rating"),
    "Corsair Sword": ("Corsair Sword", 33, 99, 1.5, 5.0, "40% increased Global Accuracy Rating"),
    "Eternal Sword": ("Eternal Sword", 28, 84, 1.55, 5.0, "+475 to Accuracy Rating"),

    # ---------------------------------------------------------------
    # TWO-HAND SWORDS
    # ---------------------------------------------------------------
    # Early
    "Corroded Blade": ("Corroded Blade", 9, 14, 1.3, 5.0, ""),
    "Long Sword": ("Long Sword", 12, 20, 1.3, 5.0, ""),
    "Bastard Sword": ("Bastard Sword", 16, 26, 1.3, 5.0, ""),
    "Two-Handed Sword": ("Two-Handed Sword", 20, 33, 1.3, 5.0, ""),
    # Mid
    "Claymore": ("Claymore", 32, 53, 1.3, 5.0, ""),
    "Highland Blade": ("Highland Blade", 36, 60, 1.35, 5.0, ""),
    "Reaver Sword": ("Reaver Sword", 55, 115, 1.35, 5.0, ""),
    "Lion Sword": ("Lion Sword", 52, 108, 1.35, 5.0, ""),
    # Late
    "Ezomyte Blade": ("Ezomyte Blade", 80, 168, 1.3, 5.0, ""),
    "Vaal Greatsword": ("Vaal Greatsword", 100, 215, 1.25, 5.0, ""),
    "Exquisite Blade": ("Exquisite Blade", 105, 175, 1.3, 5.0, "60% increased Global Accuracy Rating"),
    "Infernal Sword": ("Infernal Sword", 100, 260, 1.3, 5.0, ""),
    "Karui Chopper": ("Karui Chopper", 72, 108, 1.15, 5.0, ""),

    # ---------------------------------------------------------------
    # ONE-HAND AXES
    # ---------------------------------------------------------------
    # Early
    "Rusted Hatchet": ("Rusted Hatchet", 4, 11, 1.5, 5.0, ""),
    "Jade Hatchet": ("Jade Hatchet", 6, 16, 1.5, 5.0, ""),
    "Boarding Axe": ("Boarding Axe", 8, 21, 1.5, 5.0, ""),
    "Cleaver": ("Cleaver", 10, 27, 1.3, 5.0, ""),
    "Tomahawk": ("Tomahawk", 12, 32, 1.5, 5.0, ""),
    # Mid
    "Wrist Chopper": ("Wrist Chopper", 18, 47, 1.5, 5.0, ""),
    "War Axe": ("War Axe", 22, 58, 1.5, 5.0, ""),
    "Karui Axe": ("Karui Axe", 32, 84, 1.5, 5.0, ""),
    "Jasper Chopper": ("Jasper Chopper", 26, 49, 1.45, 5.0, ""),
    # Late
    "Royal Axe": ("Royal Axe", 36, 67, 1.5, 5.0, ""),
    "Infernal Axe": ("Infernal Axe", 34, 90, 1.45, 5.0, ""),
    "Runic Hatchet": ("Runic Hatchet", 44, 82, 1.55, 5.0, ""),
    "Siege Axe": ("Siege Axe", 38, 100, 1.5, 5.0, ""),
    "Vaal Hatchet": ("Vaal Hatchet", 40, 95, 1.5, 5.0, ""),
    "Despot Axe": ("Despot Axe", 58, 107, 1.5, 5.0, ""),

    # ---------------------------------------------------------------
    # TWO-HAND AXES
    # ---------------------------------------------------------------
    # Early
    "Stone Axe": ("Stone Axe", 8, 12, 1.25, 5.0, ""),
    "Jade Chopper": ("Jade Chopper", 12, 18, 1.2, 5.0, ""),
    "Woodsplitter": ("Woodsplitter", 16, 24, 1.2, 5.0, ""),
    "Poleaxe": ("Poleaxe", 20, 30, 1.25, 5.0, ""),
    # Mid
    "Headsman Axe": ("Headsman Axe", 35, 58, 1.2, 5.0, ""),
    "Labrys": ("Labrys", 60, 100, 1.2, 5.0, ""),
    "Dagger Axe": ("Dagger Axe", 62, 93, 1.3, 5.0, ""),
    # Late
    "Sundering Axe": ("Sundering Axe", 95, 158, 1.2, 5.0, ""),
    "Ezomyte Axe": ("Ezomyte Axe", 80, 168, 1.25, 5.0, ""),
    "Vaal Axe": ("Vaal Axe", 90, 185, 1.25, 5.0, ""),
    "Fleshripper": ("Fleshripper", 100, 210, 1.2, 5.0, ""),

    # ---------------------------------------------------------------
    # ONE-HAND MACES
    # ---------------------------------------------------------------
    # Early
    "Driftwood Club": ("Driftwood Club", 3, 5, 1.2, 5.0, ""),
    "Wooden Mace": ("Wooden Mace", 5, 8, 1.2, 5.0, ""),
    "Stone Hammer": ("Stone Hammer", 8, 12, 1.2, 5.0, ""),
    "War Hammer": ("War Hammer", 11, 17, 1.45, 5.0, ""),
    "Rock Breaker": ("Rock Breaker", 13, 20, 1.2, 5.0, ""),
    # Mid
    "Fluted Mace": ("Fluted Mace", 20, 37, 1.25, 5.0, ""),
    "Legion Hammer": ("Legion Hammer", 28, 52, 1.2, 5.0, ""),
    "Tenderizer": ("Tenderizer", 26, 48, 1.3, 5.0, ""),
    # Late
    "Pernarch": ("Pernarch", 30, 56, 1.3, 5.0, ""),
    "Auric Mace": ("Auric Mace", 34, 64, 1.25, 5.0, ""),
    "Gavel": ("Gavel", 36, 67, 1.25, 5.0, ""),

    # ---------------------------------------------------------------
    # TWO-HAND MACES
    # ---------------------------------------------------------------
    # Early
    "Driftwood Maul": ("Driftwood Maul", 8, 12, 1.1, 5.0, ""),
    "Sledgehammer": ("Sledgehammer", 16, 24, 1.15, 5.0, ""),
    "Tribal Maul": ("Tribal Maul", 20, 30, 1.2, 5.0, ""),
    # Mid
    "Plated Maul": ("Plated Maul", 42, 64, 1.15, 5.0, ""),
    "Imperial Maul": ("Imperial Maul", 60, 112, 1.2, 5.0, ""),
    "Meatgrinder": ("Meatgrinder", 70, 130, 1.2, 5.0, ""),
    "Karui Maul": ("Karui Maul", 74, 138, 1.15, 5.0, ""),
    # Late
    "Terror Maul": ("Terror Maul", 78, 146, 1.15, 5.0, ""),
    "Coronal Maul": ("Coronal Maul", 82, 154, 1.2, 5.0, ""),
    "Colossus Mallet": ("Colossus Mallet", 100, 188, 1.1, 5.0, ""),
    "Piledriver": ("Piledriver", 85, 180, 1.25, 5.0, ""),
    "Behemoth Mace": ("Behemoth Mace", 105, 200, 1.15, 5.0, ""),

    # ---------------------------------------------------------------
    # DAGGERS (crit chance implicit)
    # ---------------------------------------------------------------
    # Early
    "Glass Shank": ("Glass Shank", 3, 12, 1.5, 6.0, "20% increased Global Critical Strike Chance"),
    "Skinning Knife": ("Skinning Knife", 4, 16, 1.5, 6.0, "20% increased Global Critical Strike Chance"),
    "Flaying Knife": ("Flaying Knife", 5, 20, 1.5, 6.0, "30% increased Global Critical Strike Chance"),
    "Stiletto": ("Stiletto", 11, 22, 1.6, 6.1, "30% increased Global Critical Strike Chance"),
    "Butcher Knife": ("Butcher Knife", 8, 33, 1.5, 6.0, "30% increased Global Critical Strike Chance"),
    # Mid
    "Gutting Knife": ("Gutting Knife", 8, 33, 1.5, 6.3, "30% increased Global Critical Strike Chance"),
    "Royal Skean": ("Royal Skean", 15, 60, 1.5, 6.0, "30% increased Global Critical Strike Chance"),
    "Demon Dagger": ("Demon Dagger", 15, 61, 1.5, 6.3, "30% increased Global Critical Strike Chance"),
    "Sai": ("Sai", 14, 28, 1.6, 6.5, "+6% Chance to Block Attack Damage while Dual Wielding"),
    # Late
    "Ezomyte Dagger": ("Ezomyte Dagger", 26, 52, 1.5, 6.3, "30% increased Global Critical Strike Chance"),
    "Platinum Kris": ("Platinum Kris", 24, 50, 1.5, 6.5, "+20% to Global Critical Strike Multiplier"),
    "Imperial Skean": ("Imperial Skean", 22, 87, 1.5, 6.3, "30% increased Global Critical Strike Chance"),
    "Ambusher": ("Ambusher", 27, 56, 1.6, 6.1, "30% increased Global Critical Strike Chance"),
    "Fiend Dagger": ("Fiend Dagger", 31, 121, 1.4, 6.3, "30% increased Global Critical Strike Chance"),

    # ---------------------------------------------------------------
    # RUNE DAGGERS (spell damage implicit)
    # ---------------------------------------------------------------
    "Copper Kris": ("Copper Kris", 6, 12, 1.5, 6.3, "20% increased Spell Damage"),
    "Boot Blade": ("Boot Blade", 10, 20, 1.5, 6.3, "24% increased Spell Damage"),
    "Golden Kris": ("Golden Kris", 14, 28, 1.5, 6.5, "28% increased Spell Damage"),
    "Primal Skull Dagger": ("Primal Skull Dagger", 20, 40, 1.5, 6.3, "30% increased Spell Damage"),

    # ---------------------------------------------------------------
    # CLAWS (life/mana on hit implicit)
    # ---------------------------------------------------------------
    # Early
    "Nailed Fist": ("Nailed Fist", 4, 10, 1.6, 6.0, "+3 Life gained for each Enemy hit by Attacks"),
    "Sharktooth Claw": ("Sharktooth Claw", 6, 16, 1.6, 6.0, "+6 Life gained for each Enemy hit by Attacks"),
    "Cat's Paw": ("Cat's Paw", 7, 18, 1.6, 6.0, "+9 Life gained for each Enemy hit by Attacks"),
    "Blinder": ("Blinder", 9, 24, 1.6, 6.0, "+12 Life gained for each Enemy hit by Attacks"),
    # Mid
    "Timeworn Claw": ("Timeworn Claw", 12, 32, 1.6, 6.0, "+18 Life gained for each Enemy hit by Attacks"),
    "Eagle Claw": ("Eagle Claw", 16, 42, 1.6, 6.0, "+25 Life gained for each Enemy hit by Attacks"),
    "Vaal Claw": ("Vaal Claw", 20, 52, 1.6, 6.0, "2% of Physical Attack Damage Leeched as Life"),
    "Hellion's Paw": ("Hellion's Paw", 26, 68, 1.6, 6.3, "+34 Life gained for each Enemy hit by Attacks"),
    # Late
    "Throat Stabber": ("Throat Stabber", 22, 56, 1.6, 6.3, "+40 Life gained for each Enemy hit by Attacks"),
    "Eye Gouger": ("Eye Gouger", 22, 58, 1.6, 6.3, "+44 Life gained for each Enemy hit by Attacks"),
    "Terror Claw": ("Terror Claw", 24, 64, 1.6, 6.3, "+46 Life gained for each Enemy hit by Attacks"),
    "Imperial Claw": ("Imperial Claw", 25, 100, 1.6, 6.0, "+46 Life gained for each Enemy hit by Attacks"),
    "Gemini Claw": ("Gemini Claw", 28, 75, 1.5, 6.3, "+38 Life gained for each Enemy hit by Attacks\n+14 Mana gained for each Enemy hit by Attacks"),

    # ---------------------------------------------------------------
    # WANDS (spell damage implicit)
    # ---------------------------------------------------------------
    # Early
    "Driftwood Wand": ("Driftwood Wand", 4, 8, 1.4, 7.0, "11% increased Spell Damage"),
    "Goat's Horn": ("Goat's Horn", 6, 11, 1.4, 7.0, "12% increased Spell Damage"),
    "Carved Wand": ("Carved Wand", 10, 19, 1.5, 7.0, "18% increased Spell Damage"),
    "Quartz Wand": ("Quartz Wand", 8, 15, 1.3, 7.0, "15% increased Spell Damage"),
    "Bone Spirit Wand": ("Bone Spirit Wand", 7, 13, 1.35, 7.0, "13% increased Spell Damage"),
    # Mid
    "Spiraled Wand": ("Spiraled Wand", 15, 28, 1.4, 7.0, "15% increased Spell Damage"),
    "Assembler Wand": ("Assembler Wand", 16, 30, 1.4, 7.0, "18% increased Spell Damage"),
    "Demon's Horn": ("Demon's Horn", 24, 44, 1.3, 7.0, "26% increased Spell Damage"),
    "Heathen Wand": ("Heathen Wand", 22, 41, 1.35, 7.0, "27% increased Spell Damage"),
    "Tornado Wand": ("Tornado Wand", 20, 37, 1.3, 7.0, "18% increased Spell Damage"),
    "Profane Wand": ("Profane Wand", 18, 33, 1.4, 7.0, "20% increased Spell Damage"),
    # Late
    "Opal Wand": ("Opal Wand", 26, 48, 1.4, 7.0, "38% increased Spell Damage"),
    "Imbued Wand": ("Imbued Wand", 29, 54, 1.5, 7.0, "33% increased Spell Damage"),
    "Prophecy Wand": ("Prophecy Wand", 26, 68, 1.2, 7.0, "39% increased Spell Damage"),

    # ---------------------------------------------------------------
    # SCEPTRES (elemental damage implicit)
    # ---------------------------------------------------------------
    # Early
    "Driftwood Sceptre": ("Driftwood Sceptre", 4, 7, 1.25, 6.0, "10% increased Elemental Damage"),
    "Darkwood Sceptre": ("Darkwood Sceptre", 6, 11, 1.25, 6.0, "14% increased Elemental Damage"),
    "Bronze Sceptre": ("Bronze Sceptre", 10, 19, 1.25, 6.0, "18% increased Elemental Damage"),
    "Ochre Sceptre": ("Ochre Sceptre", 8, 15, 1.4, 6.0, "16% increased Elemental Damage"),
    # Mid
    "Lead Sceptre": ("Lead Sceptre", 18, 33, 1.25, 6.0, "22% increased Elemental Damage"),
    "Crystal Sceptre": ("Crystal Sceptre", 22, 41, 1.4, 6.0, "30% increased Elemental Damage"),
    "Abyssal Sceptre": ("Abyssal Sceptre", 25, 46, 1.3, 6.0, "28% increased Elemental Damage"),
    "Karui Sceptre": ("Karui Sceptre", 20, 37, 1.3, 6.0, "26% increased Elemental Damage"),
    "Tyrant's Sekhem": ("Tyrant's Sekhem", 30, 56, 1.4, 6.0, "32% increased Elemental Damage"),
    "Carnal Sceptre": ("Carnal Sceptre", 26, 48, 1.4, 6.0, "36% increased Elemental Damage"),
    # Late
    "Vaal Sceptre": ("Vaal Sceptre", 32, 60, 1.4, 6.0, "40% increased Elemental Damage"),
    "Opal Sceptre": ("Opal Sceptre", 28, 52, 1.4, 6.2, "40% increased Elemental Damage"),
    "Void Sceptre": ("Void Sceptre", 34, 64, 1.4, 6.0, "40% increased Elemental Damage"),
    "Platinum Sceptre": ("Platinum Sceptre", 38, 70, 1.25, 6.0, "40% increased Elemental Damage"),
    "Sambar Sceptre": ("Sambar Sceptre", 24, 44, 1.4, 6.2, "6% increased Elemental Damage per 10 Devotion"),

    # ---------------------------------------------------------------
    # STAVES — Melee (block implicit)
    # ---------------------------------------------------------------
    # Early
    "Gnarled Branch": ("Gnarled Branch", 7, 14, 1.3, 6.2, "+12% Chance to Block Attack Damage while wielding a Staff"),
    "Primitive Staff": ("Primitive Staff", 10, 21, 1.3, 6.2, "+12% Chance to Block Attack Damage while wielding a Staff"),
    "Long Staff": ("Long Staff", 15, 31, 1.3, 6.2, "+15% Chance to Block Attack Damage while wielding a Staff"),
    # Mid
    "Iron Staff": ("Iron Staff", 25, 52, 1.3, 6.2, "+18% Chance to Block Attack Damage while wielding a Staff"),
    "Lathi": ("Lathi", 45, 94, 1.3, 6.2, "+18% Chance to Block Attack Damage while wielding a Staff"),
    "Coiled Staff": ("Coiled Staff", 48, 100, 1.3, 6.5, "+18% Chance to Block Attack Damage while wielding a Staff"),
    "Ezomyte Staff": ("Ezomyte Staff", 58, 122, 1.25, 6.2, "+18% Chance to Block Attack Damage while wielding a Staff"),
    # Late
    "Imperial Staff": ("Imperial Staff", 62, 130, 1.25, 6.2, "+18% Chance to Block Attack Damage while wielding a Staff"),
    "Moon Staff": ("Moon Staff", 55, 115, 1.3, 6.2, "+18% Chance to Block Attack Damage while wielding a Staff"),
    "Maelstrom Staff": ("Maelstrom Staff", 50, 105, 1.3, 6.5, "+18% Chance to Block Attack Damage while wielding a Staff"),
    "Judgement Staff": ("Judgement Staff", 70, 145, 1.3, 6.2, "+18% Chance to Block Attack Damage while wielding a Staff"),
    "Eclipse Staff": ("Eclipse Staff", 80, 168, 1.25, 6.5, "+18% Chance to Block Attack Damage while wielding a Staff"),

    # ---------------------------------------------------------------
    # WARSTAVES — Spell (spell block implicit)
    # ---------------------------------------------------------------
    "Vile Staff": ("Vile Staff", 15, 31, 1.3, 6.5, "12% Chance to Block Spell Damage while wielding a Staff"),
    "Serpentine Staff": ("Serpentine Staff", 30, 63, 1.3, 6.5, "15% Chance to Block Spell Damage while wielding a Staff"),
    "Battery Staff": ("Battery Staff", 46, 96, 1.3, 6.5, "18% Chance to Block Spell Damage while wielding a Staff"),
    "Eventuality Rod": ("Eventuality Rod", 42, 88, 1.3, 6.5, "18% Chance to Block Spell Damage while wielding a Staff"),
    "Reciprocation Staff": ("Reciprocation Staff", 52, 108, 1.25, 6.5, "18% Chance to Block Spell Damage while wielding a Staff"),

    # ---------------------------------------------------------------
    # BOWS
    # ---------------------------------------------------------------
    # Early
    "Crude Bow": ("Crude Bow", 3, 8, 1.4, 5.0, ""),
    "Short Bow": ("Short Bow", 5, 14, 1.55, 5.0, ""),
    "Long Bow": ("Long Bow", 7, 20, 1.3, 5.0, ""),
    "Grove Bow": ("Grove Bow", 10, 28, 1.5, 5.0, ""),
    "Bone Bow": ("Bone Bow", 10, 30, 1.35, 5.0, ""),
    # Mid
    "Composite Bow": ("Composite Bow", 14, 42, 1.45, 5.0, ""),
    "Reflex Bow": ("Reflex Bow", 16, 46, 1.5, 5.0, ""),
    "Recurve Bow": ("Recurve Bow", 18, 52, 1.45, 5.0, ""),
    "Sniper Bow": ("Sniper Bow", 15, 44, 1.35, 6.0, ""),
    "Steelwood Bow": ("Steelwood Bow", 22, 64, 1.35, 5.0, ""),
    "Citadel Bow": ("Citadel Bow", 20, 58, 1.1, 5.0, ""),
    # Late
    "Ranger Bow": ("Ranger Bow", 26, 76, 1.45, 5.0, ""),
    "Highborn Bow": ("Highborn Bow", 26, 76, 1.45, 5.0, ""),
    "Decimation Bow": ("Decimation Bow", 32, 94, 1.2, 5.0, ""),
    "Thicket Bow": ("Thicket Bow", 22, 65, 1.5, 5.0, ""),
    "Imperial Bow": ("Imperial Bow", 25, 103, 1.45, 5.0, ""),
    "Harbinger Bow": ("Harbinger Bow", 36, 108, 1.2, 5.0, ""),
    "Spine Bow": ("Spine Bow", 28, 82, 1.5, 6.0, ""),
    "Assassin Bow": ("Assassin Bow", 37, 78, 1.5, 6.5, ""),
    "Death Bow": ("Death Bow", 25, 82, 1.32, 6.5, ""),
    "Maraketh Bow": ("Maraketh Bow", 30, 88, 1.5, 5.0, "10% increased Movement Speed"),
    "Royal Bow": ("Royal Bow", 26, 78, 1.45, 5.0, ""),
    "Solarine Bow": ("Solarine Bow", 22, 66, 1.25, 5.0, ""),

    # ---------------------------------------------------------------
    # SHIELDS
    # ---------------------------------------------------------------
    # Bucklers (evasion, move speed implicit)
    "Pine Buckler": ("Pine Buckler", 0, 0, 0, 0, "3% increased Movement Speed"),
    "Lacquered Buckler": ("Lacquered Buckler", 0, 0, 0, 0, "6% increased Movement Speed"),
    "Imperial Buckler": ("Imperial Buckler", 0, 0, 0, 0, "6% increased Movement Speed"),
    "Crusader Buckler": ("Crusader Buckler", 0, 0, 0, 0, "6% increased Movement Speed"),
    # Kite Shields (armour/es, ele res implicit)
    "Branded Kite Shield": ("Branded Kite Shield", 0, 0, 0, 0, "+4% to all Elemental Resistances"),
    "Champion Kite Shield": ("Champion Kite Shield", 0, 0, 0, 0, "+8% to all Elemental Resistances"),
    "Mosaic Kite Shield": ("Mosaic Kite Shield", 0, 0, 0, 0, "+10% to all Elemental Resistances"),
    "Archon Kite Shield": ("Archon Kite Shield", 0, 0, 0, 0, "+12% to all Elemental Resistances"),
    # Tower Shields (pure armour)
    "Rawhide Tower Shield": ("Rawhide Tower Shield", 0, 0, 0, 0, ""),
    "Pinnacle Tower Shield": ("Pinnacle Tower Shield", 0, 0, 0, 0, ""),
    "Colossal Tower Shield": ("Colossal Tower Shield", 0, 0, 0, 0, ""),
    "Ezomyte Tower Shield": ("Ezomyte Tower Shield", 0, 0, 0, 0, ""),
    # Spirit Shields (pure ES)
    "Brass Spirit Shield": ("Brass Spirit Shield", 0, 0, 0, 0, "+25 to maximum Energy Shield"),
    "Ivory Spirit Shield": ("Ivory Spirit Shield", 0, 0, 0, 0, "+35 to maximum Energy Shield"),
    "Harmonic Spirit Shield": ("Harmonic Spirit Shield", 0, 0, 0, 0, "+50 to maximum Energy Shield"),
    "Fossilised Spirit Shield": ("Fossilised Spirit Shield", 0, 0, 0, 0, "+67 to maximum Energy Shield"),
    "Titanium Spirit Shield": ("Titanium Spirit Shield", 0, 0, 0, 0, "+78 to maximum Energy Shield"),
    # Special
    "Monarch": ("Monarch", 0, 0, 0, 0, ""),
    "Supreme Spiked Shield": ("Supreme Spiked Shield", 0, 0, 0, 0, "3% chance to deal Double Damage"),
    "Golden Buckler": ("Golden Buckler", 0, 0, 0, 0, "6% increased Movement Speed"),
}


# ===================================================================
# Armour base type database — full leveling + endgame progression
# ===================================================================
# Slot → base_types → (name, armour, evasion, es, implicit)
# Includes early/mid/late bases per slot.

_ARMOUR_BASES: dict[str, dict[str, tuple[str, int, int, int, str]]] = {
    "Helmet": {
        # Pure armour — early
        "Iron Hat": ("Iron Hat", 20, 0, 0, ""),
        "Cone Helmet": ("Cone Helmet", 50, 0, 0, ""),
        "Barbute Helmet": ("Barbute Helmet", 80, 0, 0, ""),
        "Soldier Helmet": ("Soldier Helmet", 150, 0, 0, ""),
        "Great Helmet": ("Great Helmet", 175, 0, 0, ""),
        # Pure armour — mid/late
        "Samite Helmet": ("Samite Helmet", 220, 0, 0, ""),
        "Pig-Faced Bascinet": ("Pig-Faced Bascinet", 260, 0, 0, ""),
        "Ezomyte Burgonet": ("Ezomyte Burgonet", 280, 0, 0, ""),
        "Royal Burgonet": ("Royal Burgonet", 310, 0, 0, ""),
        "Eternal Burgonet": ("Eternal Burgonet", 350, 0, 0, ""),
        # Pure evasion — early
        "Leather Cap": ("Leather Cap", 0, 15, 0, ""),
        "Tricorne": ("Tricorne", 0, 50, 0, ""),
        "Leather Hood": ("Leather Hood", 0, 80, 0, ""),
        "Hunter Hood": ("Hunter Hood", 0, 120, 0, ""),
        # Pure evasion — mid/late
        "Noble Tricorne": ("Noble Tricorne", 0, 200, 0, ""),
        "Sinner Tricorne": ("Sinner Tricorne", 0, 250, 0, ""),
        "Silken Hood": ("Silken Hood", 0, 370, 0, ""),
        "Ursine Pelt": ("Ursine Pelt", 0, 400, 0, ""),
        "Lion Pelt": ("Lion Pelt", 0, 470, 0, ""),
        # Pure ES — early
        "Vine Circlet": ("Vine Circlet", 0, 0, 10, ""),
        "Iron Circlet": ("Iron Circlet", 0, 0, 15, ""),
        "Torture Cage": ("Torture Cage", 0, 0, 30, ""),
        # Pure ES — mid/late
        "Bone Circlet": ("Bone Circlet", 0, 0, 80, ""),
        "Prophet Crown": ("Prophet Crown", 0, 0, 90, ""),
        "Necromancer Circlet": ("Necromancer Circlet", 0, 0, 100, ""),
        "Mind Cage": ("Mind Cage", 0, 0, 130, ""),
        "Hubris Circlet": ("Hubris Circlet", 0, 0, 155, ""),
        # Hybrid
        "Nightmare Bascinet": ("Nightmare Bascinet", 275, 0, 55, ""),
        "Praetor Crown": ("Praetor Crown", 200, 0, 70, ""),
        "Magistrate Crown": ("Magistrate Crown", 200, 0, 50, ""),
        "Vaal Mask": ("Vaal Mask", 0, 200, 60, ""),
        "Deicide Mask": ("Deicide Mask", 0, 230, 50, ""),
        "Harlequin Mask": ("Harlequin Mask", 0, 200, 65, ""),
        "Blizzard Crown": ("Blizzard Crown", 0, 0, 100, "Adds 14 to 18 Cold Damage to Spells"),
    },
    "Body Armour": {
        # Pure armour — early
        "Plate Vest": ("Plate Vest", 40, 0, 0, ""),
        "Scale Vest": ("Scale Vest", 70, 0, 0, ""),
        "Chainmail": ("Chainmail", 100, 0, 0, ""),
        "Ring Mail": ("Ring Mail", 140, 0, 0, ""),
        "Full Scale Armour": ("Full Scale Armour", 200, 0, 0, ""),
        # Pure armour — mid
        "Full Plate": ("Full Plate", 530, 0, 0, ""),
        "Holy Chainmail": ("Holy Chainmail", 330, 0, 0, ""),
        "Elegant Ringmail": ("Elegant Ringmail", 400, 0, 0, ""),
        "Crusader Plate": ("Crusader Plate", 500, 0, 0, ""),
        # Pure armour — late
        "Gladiator Plate": ("Gladiator Plate", 600, 0, 0, ""),
        "Astral Plate": ("Astral Plate", 711, 0, 0, "+12% to all Elemental Resistances"),
        "Glorious Plate": ("Glorious Plate", 776, 0, 0, ""),
        "Simple Robe": ("Simple Robe", 0, 0, 0, ""),
        # Pure evasion — early
        "Shabby Jerkin": ("Shabby Jerkin", 0, 30, 0, ""),
        "Strapped Leather": ("Strapped Leather", 0, 60, 0, ""),
        "Buckskin Tunic": ("Buckskin Tunic", 0, 100, 0, ""),
        "Wild Leather": ("Wild Leather", 0, 150, 0, ""),
        # Pure evasion — mid/late
        "Full Wyrmscale": ("Full Wyrmscale", 0, 350, 0, ""),
        "Sharkskin Tunic": ("Sharkskin Tunic", 0, 400, 0, ""),
        "Destiny Leather": ("Destiny Leather", 0, 500, 0, ""),
        "Assassin's Garb": ("Assassin's Garb", 0, 596, 0, "3% increased Movement Speed"),
        "Zodiac Leather": ("Zodiac Leather", 0, 630, 0, ""),
        # Pure ES — early
        "Simple Robe": ("Simple Robe", 0, 0, 0, ""),
        "Silk Robe": ("Silk Robe", 0, 0, 40, ""),
        "Scholar's Robe": ("Scholar's Robe", 0, 0, 60, ""),
        # Pure ES — mid/late
        "Spidersilk Robe": ("Spidersilk Robe", 0, 0, 100, ""),
        "Widowsilk Robe": ("Widowsilk Robe", 0, 0, 155, ""),
        "Occultist's Vestment": ("Occultist's Vestment", 0, 0, 175, ""),
        "Vaal Regalia": ("Vaal Regalia", 0, 0, 200, ""),
        # Hybrid
        "Triumphant Lamellar": ("Triumphant Lamellar", 320, 320, 0, ""),
        "Sadist Garb": ("Sadist Garb", 225, 225, 75, ""),
        "Carnal Armour": ("Carnal Armour", 0, 320, 100, ""),
        "Sacrificial Garb": ("Sacrificial Garb", 200, 200, 60, ""),
        "Lacquered Garb": ("Lacquered Garb", 0, 340, 90, ""),
        "Sentinel Jacket": ("Sentinel Jacket", 0, 380, 70, ""),
        "General's Brigandine": ("General's Brigandine", 310, 210, 0, ""),
        "Majestic Plate": ("Majestic Plate", 500, 0, 60, ""),
    },
    "Gloves": {
        # Pure armour — early/mid
        "Iron Gauntlets": ("Iron Gauntlets", 15, 0, 0, ""),
        "Plated Gauntlets": ("Plated Gauntlets", 40, 0, 0, ""),
        "Bronze Gauntlets": ("Bronze Gauntlets", 60, 0, 0, ""),
        "Steel Gauntlets": ("Steel Gauntlets", 100, 0, 0, ""),
        "Riveted Gloves": ("Riveted Gloves", 160, 0, 0, ""),
        "Legion Gloves": ("Legion Gloves", 170, 0, 0, ""),
        # Pure armour — late
        "Goliath Gauntlets": ("Goliath Gauntlets", 180, 0, 0, ""),
        "Crusader Gloves": ("Crusader Gloves", 200, 0, 0, ""),
        "Vaal Gauntlets": ("Vaal Gauntlets", 220, 0, 0, ""),
        "Titan Gauntlets": ("Titan Gauntlets", 250, 0, 0, ""),
        "Spiked Gloves": ("Spiked Gloves", 225, 0, 0, "18% increased Melee Damage"),
        # Pure evasion — early/mid
        "Rawhide Gloves": ("Rawhide Gloves", 0, 20, 0, ""),
        "Goathide Gloves": ("Goathide Gloves", 0, 40, 0, ""),
        "Deerskin Gloves": ("Deerskin Gloves", 0, 80, 0, ""),
        "Nubuck Gloves": ("Nubuck Gloves", 0, 120, 0, ""),
        "Shagreen Gloves": ("Shagreen Gloves", 0, 220, 0, ""),
        # Pure evasion — late
        "Steelscale Gauntlets": ("Steelscale Gauntlets", 0, 240, 0, ""),
        "Slink Gloves": ("Slink Gloves", 0, 295, 0, ""),
        "Gripped Gloves": ("Gripped Gloves", 0, 220, 0, "14% increased Projectile Attack Damage"),
        # Pure ES — early/mid
        "Wool Gloves": ("Wool Gloves", 0, 0, 15, ""),
        "Velvet Gloves": ("Velvet Gloves", 0, 0, 25, ""),
        "Silk Gloves": ("Silk Gloves", 0, 0, 50, ""),
        "Arcanist Gloves": ("Arcanist Gloves", 0, 0, 70, ""),
        # Pure ES — late
        "Sorcerer Gloves": ("Sorcerer Gloves", 0, 0, 97, ""),
        "Fingerless Silk Gloves": ("Fingerless Silk Gloves", 0, 0, 80, "16% increased Spell Damage"),
        # Hybrid
        "Dragonscale Gauntlets": ("Dragonscale Gauntlets", 175, 0, 40, ""),
        "Strapped Mitts": ("Strapped Mitts", 50, 0, 0, ""),
        "Apothecary's Gloves": ("Apothecary's Gloves", 0, 120, 40, ""),
    },
    "Boots": {
        # Pure armour — early/mid
        "Iron Greaves": ("Iron Greaves", 20, 0, 0, ""),
        "Steel Greaves": ("Steel Greaves", 50, 0, 0, ""),
        "Plated Greaves": ("Plated Greaves", 120, 0, 0, ""),
        "Riveted Boots": ("Riveted Boots", 160, 0, 0, ""),
        # Pure armour — late
        "Goliath Greaves": ("Goliath Greaves", 180, 0, 0, ""),
        "Vaal Greaves": ("Vaal Greaves", 220, 0, 0, ""),
        "Titan Greaves": ("Titan Greaves", 250, 0, 0, ""),
        # Pure evasion — early/mid
        "Rawhide Boots": ("Rawhide Boots", 0, 40, 0, ""),
        "Goathide Boots": ("Goathide Boots", 0, 30, 0, ""),
        "Deerskin Boots": ("Deerskin Boots", 0, 80, 0, ""),
        "Mesh Boots": ("Mesh Boots", 0, 100, 0, ""),
        "Sharkskin Boots": ("Sharkskin Boots", 0, 180, 0, ""),
        # Pure evasion — late
        "Stealth Boots": ("Stealth Boots", 0, 200, 0, ""),
        "Murder Boots": ("Murder Boots", 0, 260, 0, ""),
        "Slink Boots": ("Slink Boots", 0, 295, 0, ""),
        # Pure ES — early/mid
        "Wool Shoes": ("Wool Shoes", 0, 0, 15, ""),
        "Velvet Slippers": ("Velvet Slippers", 0, 0, 25, ""),
        "Silk Slippers": ("Silk Slippers", 0, 0, 40, ""),
        "Conjurer Boots": ("Conjurer Boots", 0, 0, 55, ""),
        # Pure ES — late
        "Arcanist Slippers": ("Arcanist Slippers", 0, 0, 70, ""),
        "Sorcerer Boots": ("Sorcerer Boots", 0, 0, 97, ""),
        # Hybrid
        "Dragonscale Boots": ("Dragonscale Boots", 175, 0, 40, ""),
        "Two-Toned Boots (Fire/Cold)": ("Two-Toned Boots", 185, 0, 0, "+12% to Fire and Cold Resistances"),
        "Two-Toned Boots (Fire/Lightning)": ("Two-Toned Boots", 0, 185, 0, "+12% to Fire and Lightning Resistances"),
        "Two-Toned Boots (Cold/Lightning)": ("Two-Toned Boots", 0, 0, 62, "+12% to Cold and Lightning Resistances"),
        "Fugitive Boots": ("Fugitive Boots", 0, 200, 0, "8% increased Movement Speed"),
    },
    "Belt": {
        # All belts (available at various levels, mostly by type not tier)
        "Rustic Sash": ("Rustic Sash", 0, 0, 0, "20% increased Physical Damage"),
        "Chain Belt": ("Chain Belt", 0, 0, 0, "+20 to maximum Energy Shield"),
        "Cloth Belt": ("Cloth Belt", 0, 0, 0, "15% increased Stun and Block Recovery"),
        "Leather Belt": ("Leather Belt", 0, 0, 0, "+40 to maximum Life"),
        "Heavy Belt": ("Heavy Belt", 0, 0, 0, "+25 to Strength"),
        "Studded Belt": ("Studded Belt", 0, 0, 0, "20% increased Stun Duration on Enemies"),
        "Crystal Belt": ("Crystal Belt", 0, 0, 0, "+75 to maximum Energy Shield"),
        "Vanguard Belt": ("Vanguard Belt", 0, 0, 0, "+260 to Armour and Evasion Rating"),
        "Stygian Vise": ("Stygian Vise", 0, 0, 0, "Has 1 Abyssal Socket"),
        "Micro-Distillery Belt": ("Micro-Distillery Belt", 0, 0, 0, "Has 1 Flask Slot"),
        "Mechalarm Belt": ("Mechalarm Belt", 0, 0, 0, "Has 1 Flask Slot"),
    },
    "Amulet": {
        # Attribute amulets (available from early game)
        "Coral Amulet": ("Coral Amulet", 0, 0, 0, "Regenerate 2 Life per second"),
        "Paua Amulet": ("Paua Amulet", 0, 0, 0, "+25 to maximum Mana"),
        "Amber Amulet": ("Amber Amulet", 0, 0, 0, "+30 to Strength"),
        "Jade Amulet": ("Jade Amulet", 0, 0, 0, "+26 to Dexterity"),
        "Lapis Amulet": ("Lapis Amulet", 0, 0, 0, "+26 to Intelligence"),
        "Gold Amulet": ("Gold Amulet", 0, 0, 0, "12% increased Rarity of Items found"),
        # Dual-attribute amulets (mid game)
        "Agate Amulet": ("Agate Amulet", 0, 0, 0, "+16 to Strength and Intelligence"),
        "Citrine Amulet": ("Citrine Amulet", 0, 0, 0, "+16 to Strength and Dexterity"),
        "Turquoise Amulet": ("Turquoise Amulet", 0, 0, 0, "+16 to Dexterity and Intelligence"),
        "Onyx Amulet": ("Onyx Amulet", 0, 0, 0, "+16 to all Attributes"),
        # Endgame bases
        "Marble Amulet": ("Marble Amulet", 0, 0, 0, "1.6% of Life Regenerated per second"),
        "Blue Pearl Amulet": ("Blue Pearl Amulet", 0, 0, 0, "24% increased Mana Regeneration Rate"),
        "Astrolabe Amulet": ("Astrolabe Amulet", 0, 0, 0, "+8% to all Elemental Resistances"),
        "Seaglass Amulet": ("Seaglass Amulet", 0, 0, 0, "4% increased Cast Speed"),
        "Simplex Amulet": ("Simplex Amulet", 0, 0, 0, ""),
        # Talismans
        "Ashscale Talisman": ("Ashscale Talisman", 0, 0, 0, "14% increased Fire Damage"),
        "Wereclaw Talisman": ("Wereclaw Talisman", 0, 0, 0, "14% increased Physical Damage"),
        "Spinefuse Talisman": ("Spinefuse Talisman", 0, 0, 0, "14% increased Spell Damage"),
    },
    "Ring 1": {
        # Basic rings (early game)
        "Iron Ring": ("Iron Ring", 0, 0, 0, "Adds 1 to 4 Physical Damage to Attacks"),
        "Coral Ring": ("Coral Ring", 0, 0, 0, "Regenerate 2 Life per second"),
        "Paua Ring": ("Paua Ring", 0, 0, 0, "+25 to maximum Mana"),
        "Gold Ring": ("Gold Ring", 0, 0, 0, "12% increased Rarity of Items found"),
        "Moonstone Ring": ("Moonstone Ring", 0, 0, 0, "+25 to maximum Energy Shield"),
        # Elemental resistance rings (early-mid)
        "Ruby Ring": ("Ruby Ring", 0, 0, 0, "+30% to Fire Resistance"),
        "Sapphire Ring": ("Sapphire Ring", 0, 0, 0, "+30% to Cold Resistance"),
        "Topaz Ring": ("Topaz Ring", 0, 0, 0, "+30% to Lightning Resistance"),
        "Amethyst Ring": ("Amethyst Ring", 0, 0, 0, "+17% to Chaos Resistance"),
        # Dual resistance rings (mid game)
        "Two-Stone Ring (Fire/Cold)": ("Two-Stone Ring", 0, 0, 0, "+16% to Fire and Cold Resistances"),
        "Two-Stone Ring (Fire/Lightning)": ("Two-Stone Ring", 0, 0, 0, "+16% to Fire and Lightning Resistances"),
        "Two-Stone Ring (Cold/Lightning)": ("Two-Stone Ring", 0, 0, 0, "+16% to Cold and Lightning Resistances"),
        "Prismatic Ring": ("Prismatic Ring", 0, 0, 0, "+8% to all Elemental Resistances"),
        "Unset Ring": ("Unset Ring", 0, 0, 0, "Has 1 Socket"),
        # Endgame bases
        "Diamond Ring": ("Diamond Ring", 0, 0, 0, "20% increased Global Critical Strike Chance"),
        "Steel Ring": ("Steel Ring", 0, 0, 0, "Adds 3 to 11 Physical Damage to Attacks"),
        "Opal Ring": ("Opal Ring", 0, 0, 0, "25% increased Elemental Damage"),
        "Vermillion Ring": ("Vermillion Ring", 0, 0, 0, "5% increased maximum Life"),
        "Cerulean Ring": ("Cerulean Ring", 0, 0, 0, "+50 to maximum Mana"),
        "Bone Ring": ("Bone Ring", 0, 0, 0, "+16% to Chaos Resistance"),
        "Iolite Ring": ("Iolite Ring", 0, 0, 0, "+15% to all Elemental Resistances"),
        "Cogwork Ring": ("Cogwork Ring", 0, 0, 0, "Has 1 Socket"),
    },
    "Ring 2": {},  # Populated from Ring 1 below
}

# Ring 2 shares Ring 1 bases
_ARMOUR_BASES["Ring 2"] = dict(_ARMOUR_BASES["Ring 1"])


# ===================================================================
# Slot → default base type heuristic
# ===================================================================

def _pick_base_type(slot: str, stat_priorities: list[str]) -> str:
    """Pick a sensible base type for a slot given stat priorities."""
    prio_lower = [s.lower() for s in stat_priorities]
    prio_text = " ".join(prio_lower)

    if slot in ("Weapon 1", "Weapon 2"):
        # Guess weapon type from stats
        if any(kw in prio_text for kw in ["spell", "cast speed", "gem level", "spell damage"]):
            return "Void Sceptre"
        if any(kw in prio_text for kw in ["bow", "projectile"]):
            return "Thicket Bow"
        if "crit" in prio_text:
            return "Jewelled Foil"
        if "dagger" in prio_text:
            return "Imperial Skean"
        if "claw" in prio_text:
            return "Gemini Claw"
        if "axe" in prio_text:
            return "Siege Axe"
        if "mace" in prio_text:
            return "Behemoth Mace"
        return "Jewelled Foil"  # Default: sword

    bases = _ARMOUR_BASES.get(slot, {})
    if not bases:
        return ""

    # Pick based on defence priorities — prefer the base with highest value for the target stat
    # Check individual priorities (not joined text) to avoid false substring matches
    def _best_base(key_fn):
        """Return the base name with the highest value for the given defence extractor."""
        best_name, best_val = "", 0
        for name in bases:
            _, ar, ev, es, _ = bases[name]
            val = key_fn(ar, ev, es)
            if val > best_val:
                best_name, best_val = name, val
        return best_name

    if any(p in ("energy shield", "flat es", "flat energy shield", "% energy shield", "es")
           for p in prio_lower):
        pick = _best_base(lambda ar, ev, es: es if es >= ar and es >= ev else 0)
        if pick:
            return pick
    if any(p in ("evasion", "flat evasion", "% evasion", "dodge") for p in prio_lower):
        pick = _best_base(lambda ar, ev, es: ev if ev >= ar and ev >= es else 0)
        if pick:
            return pick
    if any(p in ("armour", "flat armour", "% armour", "block") for p in prio_lower):
        pick = _best_base(lambda ar, ev, es: ar if ar >= ev and ar >= es else 0)
        if pick:
            return pick

    # For jewelry with specific implicit needs
    if slot in ("Ring 1", "Ring 2"):
        if "crit" in prio_text:
            return "Diamond Ring"
        if "life" in prio_text:
            return "Vermillion Ring"
        if "physical" in prio_text or "phys" in prio_text:
            return "Steel Ring"
        if "elemental" in prio_text:
            return "Opal Ring"
        return "Diamond Ring"

    if slot == "Amulet":
        return "Onyx Amulet"

    if slot == "Belt":
        if "life" in prio_text:
            return "Leather Belt"
        if "physical" in prio_text or "phys" in prio_text:
            return "Rustic Sash"
        if "energy shield" in prio_text or "es" in prio_text:
            return "Crystal Belt"
        return "Stygian Vise"

    # Default: first base in the slot
    return next(iter(bases), "")


# ===================================================================
# Core synthesis function
# ===================================================================


def synthesize_item(
    guide_item: GuideItem,
    tier: str = "basic",
    item_id: int = 0,
) -> Item:
    """Convert a GuideItem with stat priorities into a real Item with mods.

    Args:
        guide_item: The guide item with name, slot, stat_priority.
        tier: "basic" for budget rolls, "max" for top-tier rolls.
        item_id: Unique item ID to assign.

    Returns:
        A fully populated Item with explicits, raw_text, base_type.
    """
    # Check if this is a known unique item
    unique_data = get_unique(guide_item.name) if guide_item.name else None
    if unique_data:
        return _synthesize_unique(unique_data, guide_item.slot, item_id)

    slot = guide_item.slot
    priorities = guide_item.stat_priority or []

    # Determine base type — validate weapon bases against our DB
    is_weapon = slot in ("Weapon 1", "Weapon 2")
    base_type = guide_item.base_type or ""
    if is_weapon and base_type and base_type not in _WEAPON_BASES:
        # AI gave an invalid/hallucinated base type — fall back to our picker
        base_type = ""
    base_type = base_type or _pick_base_type(slot, priorities)

    # Build implicit from base type database
    implicits: list[ItemMod] = []
    if is_weapon and base_type in _WEAPON_BASES:
        _, _, _, _, _, implicit = _WEAPON_BASES[base_type]
        if implicit:
            implicits.append(ItemMod(text=implicit, is_implicit=True))
    else:
        for slot_key in (slot, ):
            bases = _ARMOUR_BASES.get(slot_key, {})
            for bname, (_, _, _, _, implicit) in bases.items():
                if bname == base_type and implicit:
                    implicits.append(ItemMod(text=implicit, is_implicit=True))
                    break

    # Build explicit mods from stat priorities
    explicits: list[ItemMod] = []
    use_max = tier == "max"

    # For weapons: compute final damage including local mods (flat phys + % phys)
    # The raw_text "Physical Damage: X-Y" line must show FINAL values (like PoB does),
    # because the engine reads this line and treats weapon mods as LOCAL (excluded from
    # the global modifier pool).
    #
    # Real weapon local mods:
    #   basic (T3-T4): +13-24 flat phys, ~80% increased phys, ~10% local AS
    #   max   (T1-T2): +26-51 flat phys, ~150% increased phys, ~24% local AS
    if is_weapon and base_type in _WEAPON_BASES:
        wb = _WEAPON_BASES[base_type]
        _, phys_min, phys_max, aps, crit, _ = wb
        if use_max:
            flat_min, flat_max = 26, 51
            local_inc_phys = 150
            local_inc_as = 24
            local_inc_crit = 30
        else:
            flat_min, flat_max = 13, 24
            local_inc_phys = 80
            local_inc_as = 10
            local_inc_crit = 20
        scaled_min = int((phys_min + flat_min) * (1 + local_inc_phys / 100))
        scaled_max = int((phys_max + flat_max) * (1 + local_inc_phys / 100))
        aps = round(aps * (1 + local_inc_as / 100), 2)
        crit = round(crit * (1 + local_inc_crit / 100), 1)
        # Raw text will include weapon stats
        # Don't add as explicit — goes in raw_text header

    # Convert stat priorities to mod lines
    seen_stats: set[str] = set()
    for prio in priorities:
        prio_lower = prio.lower().strip()

        # Find matching stat entries
        mod_entries = _STAT_MODS.get(prio_lower)
        if not mod_entries:
            # Try partial matching
            for key, entries in _STAT_MODS.items():
                if prio_lower in key or key in prio_lower:
                    mod_entries = entries
                    break

        if not mod_entries:
            continue

        for entry in mod_entries:
            if isinstance(entry, str):
                # Flat text without value (shouldn't happen with current data)
                continue

            template, basic_val, max_val = entry
            val = max_val if use_max else basic_val

            # Skip duplicate stats — use full template as dedup key
            if template in seen_stats:
                continue
            seen_stats.add(template)

            # Format the mod text
            if "{v2}" in template:
                # "Adds X to Y" range format
                low = int(val)
                high = int(val * 2.2)
                mod_text = template.replace("{v}", str(low)).replace("{v2}", str(high))
            elif isinstance(val, float) and val != int(val):
                mod_text = template.replace("{v}", f"{val:.1f}")
            else:
                mod_text = template.replace("{v}", str(int(val)))

            explicits.append(ItemMod(text=mod_text))

    # Build raw_text (PoB-compatible format)
    raw_lines: list[str] = []
    raw_lines.append(f"Rarity: RARE")
    raw_lines.append(guide_item.name or f"Synthetic {base_type}")
    raw_lines.append(base_type)

    # Weapon stats in raw_text header (reuse scaled values from above)
    if is_weapon and base_type in _WEAPON_BASES:
        raw_lines.append(f"Physical Damage: {scaled_min}-{scaled_max}")
        raw_lines.append(f"Critical Strike Chance: {crit}%")
        raw_lines.append(f"Attacks per Second: {aps}")

    # Implicits
    for imp in implicits:
        raw_lines.append(imp.text)

    # Separator
    raw_lines.append("--------")

    # Explicits
    for exp in explicits:
        raw_lines.append(exp.text)

    raw_text = "\n".join(raw_lines)

    return Item(
        id=item_id,
        slot=slot,
        name=guide_item.name or f"Synthetic {base_type}",
        base_type=base_type,
        rarity="RARE",
        level=80 if tier == "max" else 68,
        implicits=implicits,
        explicits=explicits,
        raw_text=raw_text,
        stat_priority=priorities,
        notes=guide_item.notes,
    )


def _synthesize_unique(
    unique_data: "UniqueItemData",
    slot: str,
    item_id: int,
) -> Item:
    """Build an Item from a known unique's database entry."""
    from pop.calc.unique_db import UniqueItemData  # noqa: F811

    implicits = [ItemMod(text=t, is_implicit=True) for t in unique_data.implicits]
    explicits = [ItemMod(text=t) for t in unique_data.explicits]

    # Build raw_text
    raw_lines: list[str] = [
        "Rarity: UNIQUE",
        unique_data.name,
        unique_data.base_type,
    ]

    # Weapon header
    if unique_data.aps > 0:
        if unique_data.phys_min > 0 or unique_data.phys_max > 0:
            raw_lines.append(f"Physical Damage: {unique_data.phys_min}-{unique_data.phys_max}")
        if unique_data.ele_damage:
            raw_lines.append(unique_data.ele_damage)
        raw_lines.append(f"Critical Strike Chance: {unique_data.crit}%")
        raw_lines.append(f"Attacks per Second: {unique_data.aps}")

    # Implicits
    for imp in unique_data.implicits:
        raw_lines.append(imp)

    raw_lines.append("--------")

    # Explicits
    for exp in unique_data.explicits:
        raw_lines.append(exp)

    return Item(
        id=item_id,
        slot=slot,
        name=unique_data.name,
        base_type=unique_data.base_type,
        rarity="UNIQUE",
        level=1,
        implicits=implicits,
        explicits=explicits,
        raw_text="\n".join(raw_lines),
    )


def synthesize_build_items(
    guide_items: list[GuideItem],
    tier: str = "basic",
    start_id: int = 1,
) -> list[Item]:
    """Synthesize all items in a guide bracket.

    Args:
        guide_items: List of GuideItems from a build guide bracket.
        tier: "basic" or "max".
        start_id: Starting item ID for sequential assignment.

    Returns:
        List of Item objects with real mods.
    """
    items: list[Item] = []
    for i, gi in enumerate(guide_items):
        items.append(synthesize_item(gi, tier=tier, item_id=start_id + i))
    return items
