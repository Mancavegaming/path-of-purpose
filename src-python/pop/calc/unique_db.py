"""
Comprehensive PoE 1 unique item database.

Every commonly used unique item with real mod text, so the synthetic item
generator can produce accurate Items when the AI builder recommends uniques.

Each entry stores the full explicit mod list as it appears in-game at the
item's typical roll range (mid-high rolls for numeric values).

Data sourced from PoE 1 (3.25+ era, pre-3.28 nerfs noted where relevant).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UniqueItemData:
    """Full data for a unique item."""
    name: str
    base_type: str
    item_class: str  # "helmet", "body", "gloves", "boots", "weapon", "shield", "amulet", "ring", "belt", "flask", "jewel"
    implicits: list[str] = field(default_factory=list)
    explicits: list[str] = field(default_factory=list)
    # Weapon-specific fields (only for weapons)
    phys_min: int = 0
    phys_max: int = 0
    aps: float = 0.0
    crit: float = 0.0
    # Extra elemental damage on weapon
    ele_damage: str = ""  # e.g. "Adds 10 to 20 Fire Damage"


_UNIQUES: dict[str, UniqueItemData] = {}


def _u(name: str, base_type: str, item_class: str, *,
       implicits: list[str] | None = None,
       explicits: list[str] | None = None,
       phys_min: int = 0, phys_max: int = 0,
       aps: float = 0.0, crit: float = 0.0,
       ele_damage: str = "") -> None:
    _UNIQUES[name] = UniqueItemData(
        name=name, base_type=base_type, item_class=item_class,
        implicits=implicits or [], explicits=explicits or [],
        phys_min=phys_min, phys_max=phys_max, aps=aps, crit=crit,
        ele_damage=ele_damage,
    )


# ===================================================================
# HELMETS
# ===================================================================

_u("Goldrim", "Leather Cap", "helmet", explicits=[
    "+36 to Evasion Rating",
    "10% increased Rarity of Items found",
    "+35% to all Elemental Resistances",
    "Reflects 4 Physical Damage to Melee Attackers",
])

_u("Abyssus", "Ezomyte Burgonet", "helmet", explicits=[
    "Adds 40 to 60 Physical Damage to Attacks",
    "+100 to Armour",
    "+2 to Melee Weapon and Unarmed Attack range",
    "100% increased Armour",
    "+50% to Critical Strike Multiplier for Attacks",
    "40% increased Physical Damage taken",
])

_u("Starkonja's Head", "Silken Hood", "helmet", explicits=[
    "+60 to Dexterity",
    "50% reduced Damage when on Low Life",
    "10% increased Attack Speed",
    "25% increased Global Critical Strike Chance",
    "+100 to maximum Life",
    "150% increased Evasion Rating",
])

_u("Devoto's Devotion", "Nightmare Bascinet", "helmet", explicits=[
    "10% reduced Global Physical Damage",
    "+50 to Dexterity",
    "16% increased Attack Speed",
    "180% increased Armour and Energy Shield",
    "20% increased Movement Speed",
    "Mercury Footprints",
])

_u("Hrimnor's Resolve", "Samite Helmet", "helmet", explicits=[
    "+2 to Level of all Fire Skill Gems",
    "30% increased Fire Damage",
    "100% increased Armour",
    "+100 to maximum Life",
    "Cannot be Frozen or Chilled",
])

_u("Crown of the Inward Eye", "Prophet Crown", "helmet", explicits=[
    "333% increased Armour and Energy Shield",
    "Transfiguration of Soul",
    "Transfiguration of Body",
    "Transfiguration of Mind",
])

_u("The Devouring Diadem", "Necromancer Circlet", "helmet", explicits=[
    "+1 to Level of Socketed Gems",
    "Socketed Gems have 25% reduced Mana Reservation Efficiency",
    "Trigger Level 15 Feast of Flesh every 5 seconds",
    "20% increased Energy Shield",
    "+150 to maximum Energy Shield",
    "10% chance for Energy Shield Recharge to start when you use a Skill",
    "Eldritch Battery",
])

_u("Fractal Thoughts", "Vaal Mask", "helmet", explicits=[
    "+1 to Maximum Power Charges",
    "25% increased Critical Strike Chance per Power Charge",
    "1% increased Lightning Damage per 1% Lightning Resistance above 75%",
    "+100 to maximum Life",
    "25% increased Dexterity",
])

_u("Lightpoacher", "Great Crown", "helmet", explicits=[
    "Has 2 Abyssal Sockets",
    "Trigger Level 20 Spirit Burst when you use a Skill while you have a Spirit Charge",
    "+1 to Maximum Spirit Charges per Abyss Jewel affecting you",
    "5% increased Movement Speed per Spirit Charge",
])

_u("Rat's Nest", "Ursine Pelt", "helmet", explicits=[
    "15% increased Attack Speed",
    "75% increased Global Critical Strike Chance",
    "150% increased Evasion Rating",
    "10% increased Movement Speed",
    "10% reduced maximum Life",
])

_u("Eber's Unification", "Hubris Circlet", "helmet", explicits=[
    "Trigger Level 10 Void Gaze when you use a Skill",
    "+200 to maximum Energy Shield",
    "1% increased Spell Damage per 16 Intelligence",
    "Gain 10% of Physical Damage as Extra Chaos Damage",
])

_u("Hale Negator", "Mind Cage", "helmet", explicits=[
    "Has 2 Abyssal Sockets",
    "+2 to Level of Socketed Minion Gems",
    "200% increased Energy Shield",
    "+2 to Maximum number of Sentinels of Purity",
])

_u("Alpha's Howl", "Sinner Tricorne", "helmet", explicits=[
    "+2 to Level of Socketed Aura Gems",
    "8% reduced Mana Reserved",
    "+55 to Evasion Rating",
    "Cannot be Frozen",
])

_u("Geofri's Crest", "Great Helmet", "helmet", explicits=[
    "+1 to Level of Socketed Gems",
    "+55 to maximum Life",
    "+55 to maximum Mana",
    "+20% to Fire Resistance",
    "+20% to Cold Resistance",
    "+20% to Lightning Resistance",
])

_u("Honourhome", "Soldier Helmet", "helmet", explicits=[
    "+2 to Level of Socketed Gems",
    "100% increased Armour",
    "+10% to all Elemental Resistances",
    "30% reduced Mana Cost of Skills during any Flask Effect",
])

_u("Asenath's Mark", "Iron Circlet", "helmet", explicits=[
    "+30 to maximum Energy Shield",
    "5% increased Attack Speed",
    "5% increased Cast Speed",
    "+30 to Accuracy Rating",
    "Trigger a Socketed Spell when you Attack with a Bow",
])

_u("Mask of the Tribunal", "Magistrate Crown", "helmet", explicits=[
    "+25 to all Attributes",
    "150% increased Armour and Energy Shield",
    "Nearby Allies have 5% increased Attack Speed",
    "Nearby Allies have 5% increased Cast Speed",
    "1% increased Mana Reservation Efficiency of Skills per 250 total Attributes",
])

# ===================================================================
# BODY ARMOUR
# ===================================================================

_u("Tabula Rasa", "Simple Robe", "body", explicits=[
    "Has 6 White Sockets",
])

_u("Belly of the Beast", "Full Wyrmscale", "body", explicits=[
    "200% increased Armour",
    "40% increased maximum Life",
    "+15% to all Elemental Resistances",
    "50% increased Flask Life Recovery rate",
    "Extra Gore",
])

_u("Loreweave", "Elegant Ringmail", "body", explicits=[
    "Has 6 Sockets",
    "+20 to all Attributes",
    "Adds 12 to 30 Physical Damage to Attacks",
    "60% increased Global Critical Strike Chance",
    "+20 to maximum Energy Shield",
    "+100 to maximum Life",
    "+80 to maximum Mana",
    "Your Maximum Resistances are 78%",
])

_u("Carcass Jack", "Varnished Coat", "body", explicits=[
    "120% increased Evasion and Energy Shield",
    "+55 to maximum Life",
    "+12% to all Elemental Resistances",
    "40% increased Area of Effect",
    "40% increased Area Damage",
    "Extra Gore",
])

_u("Cloak of Defiance", "Lacquered Garb", "body", explicits=[
    "+100 to maximum Mana",
    "160% increased Evasion and Energy Shield",
    "10% of Damage is taken from Mana before Life",
    "2% of Mana Regenerated per second",
    "Mind Over Matter",
])

_u("Shav's Wrappings", "Occultist's Vestment", "body",
   explicits=[
    "+1 to Level of Socketed Spell Gems",
    "150% increased Energy Shield",
    "10% faster start of Energy Shield Recharge",
    "+30% to Lightning Resistance",
    "Reflects 1 to 250 Lightning Damage to Melee Attackers",
    "Chaos Damage does not bypass Energy Shield",
])

_u("Shavronne's Wrappings", "Occultist's Vestment", "body",
   explicits=[
    "+1 to Level of Socketed Spell Gems",
    "150% increased Energy Shield",
    "10% faster start of Energy Shield Recharge",
    "+30% to Lightning Resistance",
    "Reflects 1 to 250 Lightning Damage to Melee Attackers",
    "Chaos Damage does not bypass Energy Shield",
])

_u("The Brass Dome", "Gladiator Plate", "body", explicits=[
    "30% increased Armour",
    "+5% to maximum Cold Resistance",
    "+5% to maximum Fire Resistance",
    "+5% to maximum Lightning Resistance",
    "50% increased Shock Duration on you",
    "Take no Extra Damage from Critical Strikes",
])

_u("Skin of the Loyal", "Simple Robe", "body", explicits=[
    "Sockets cannot be modified",
    "+1 to Level of Socketed Gems",
    "100% increased Global Defences",
])

_u("Skin of the Lords", "Simple Robe", "body", explicits=[
    "Sockets cannot be modified",
    "+2 to Level of Socketed Gems",
    "100% increased Global Defences",
    "Has a random Keystone",
])

_u("Atziri's Splendour", "Sacrificial Garb", "body", explicits=[
    "+100 to Armour",
    "+100 to maximum Energy Shield",
    "+100 to maximum Life",
    "+20% to all Elemental Resistances",
])

_u("Queen of the Forest", "Destiny Leather", "body", explicits=[
    "+200 to Evasion Rating",
    "200% increased Evasion Rating",
    "+70 to maximum Life",
    "+15% to Fire Resistance",
    "+15% to Cold Resistance",
    "25% reduced Movement Speed",
    "1% increased Movement Speed per 600 Evasion Rating, up to 75%",
])

_u("Inpulsa's Broken Heart", "Sadist Garb", "body", explicits=[
    "+70 to maximum Life",
    "50% increased Damage if you have Shocked an Enemy Recently",
    "25% increased Effect of Shock",
    "Shocked Enemies you Kill Explode, dealing 5% of their Life as Lightning Damage",
    "Unaffected by Shock",
])

_u("Farrul's Fur", "Triumphant Lamellar", "body", explicits=[
    "+100 to maximum Life",
    "150% increased Armour and Evasion",
    "+2 to Level of Socketed Cat Skill Gems",
    "Aspect of the Cat has no Reservation",
    "Gain up to your maximum number of Frenzy and Power Charges when you gain Cat's Stealth",
    "You have Phasing while you have Cat's Stealth",
])

_u("Kaom's Heart", "Glorious Plate", "body", explicits=[
    "Has no Sockets",
    "+500 to maximum Life",
    "20% increased Fire Damage",
])

_u("Lioneye's Vision", "Crusader Plate", "body", explicits=[
    "+160 to Armour",
    "+100 to maximum Life",
    "Socketed Gems are Supported by Level 15 Pierce",
    "15% reduced Mana Cost of Skills",
])

_u("Voll's Protector", "Holy Chainmail", "body", explicits=[
    "+100 to maximum Life",
    "Gain a Power Charge on Critical Strike",
    "Inner Conviction",
])

_u("Hyrri's Ire", "Zodiac Leather", "body", explicits=[
    "+60 to Dexterity",
    "Adds 13 to 23 Cold Damage to Attacks",
    "2500 to 3000 Evasion Rating",
    "10% chance to Dodge Attack Hits",
    "10% chance to Dodge Spell Hits",
])

_u("Dendrobate", "Sentari's Answer", "body", explicits=[
    "+40 to Dexterity",
    "+40 to Intelligence",
    "10% increased Poison Duration",
    "Socketed Gems are Supported by Level 10 Lesser Poison",
    "150% increased Evasion and Energy Shield",
    "10% increased Damage with Poison per Power Charge",
])

_u("Shroud of the Lightless", "Carnal Armour", "body", explicits=[
    "Has 2 Abyssal Sockets",
    "Socketed Gems are Supported by Level 20 Elemental Penetration",
    "20% increased maximum Life",
    "20% increased maximum Energy Shield",
    "+55 to maximum Life",
])

# ===================================================================
# GLOVES
# ===================================================================

_u("Lochtonial Caress", "Iron Gauntlets", "gloves", explicits=[
    "10% increased Attack Speed",
    "10% increased Cast Speed",
    "+20 to maximum Life",
    "10% chance to gain a Power, Frenzy, or Endurance Charge on Kill",
    "Conduit",
])

_u("Sadima's Touch", "Wool Gloves", "gloves", explicits=[
    "Adds 4 to 8 Fire Damage to Attacks",
    "Adds 1 to 13 Lightning Damage to Attacks",
    "+18 to maximum Energy Shield",
    "6% increased Quantity of Items found",
])

_u("Maligaro's Virtuosity", "Deerskin Gloves", "gloves", explicits=[
    "+25 to Dexterity",
    "5% increased Attack Speed",
    "50% increased Global Critical Strike Chance",
    "+28% to Global Critical Strike Multiplier",
    "150% increased Evasion Rating",
])

_u("Facebreaker", "Strapped Mitts", "gloves", explicits=[
    "+45 to Strength",
    "10% increased Attack Speed",
    "800% more Physical Damage with Unarmed Melee Attacks",
    "Extra Gore",
])

_u("Shaper's Touch", "Crusader Gloves", "gloves", explicits=[
    "+4 to maximum Life per 10 Intelligence",
    "+2 to Accuracy Rating per 2 Intelligence",
    "+2 to maximum Mana per 4 Strength",
    "+2 to maximum Energy Shield per 5 Strength",
    "2% increased Melee Physical Damage per 10 Dexterity",
    "2% increased Evasion Rating per 10 Strength",
])

_u("Hrimburn", "Goathide Gloves", "gloves", explicits=[
    "Adds 5 to 12 Cold Damage to Spells and Attacks",
    "+30 to Evasion Rating",
    "+30% to Cold Resistance",
    "Your Cold Damage can Ignite",
    "50% increased Freeze Duration on Enemies",
])

_u("Atziri's Acuity", "Vaal Gauntlets", "gloves", explicits=[
    "+60 to Intelligence",
    "200% increased Armour",
    "8% increased maximum Life",
    "+30% to Lightning Resistance",
    "Leech applies instantly on Critical Strike",
])

_u("Hands of the High Templar", "Crusader Gloves", "gloves", explicits=[
    "Can be modified while Corrupted",
    "Can have up to 5 Implicit Modifiers",
    "+100 to maximum Life",
    "130% increased Armour and Energy Shield",
    "Critical Strike Chance is increased by Overcapped Fire Resistance",
])

_u("Asenath's Gentle Touch", "Silk Gloves", "gloves", explicits=[
    "+50 to maximum Life",
    "+50 to maximum Mana",
    "+100 to maximum Energy Shield",
    "Curse Enemies with Temporal Chains on Hit",
    "Non-Aura Curses you inflict are not removed from Dying Enemies",
    "Enemies near corpses affected by your Curses are Blinded",
    "Enemies Killed near corpses affected by your Curses explode, dealing 3% of their Life as Physical Damage",
])

_u("Oskarm", "Nubuck Gloves", "gloves", explicits=[
    "+100 to Accuracy Rating",
    "+80 to Evasion Rating",
    "+60 to maximum Life",
    "2% increased Attack Critical Strike Chance per 200 Accuracy Rating",
    "Curse Enemies with Assassin's Mark on Hit",
])

_u("Command of the Pit", "Riveted Gloves", "gloves", explicits=[
    "Has 2 Abyssal Sockets",
    "+4 to Level of Socketed Minion Gems",
    "Minions have 3000 to 5000 added Accuracy Rating",
])

_u("Null and Void", "Legion Gloves", "gloves", explicits=[
    "+20 to Strength",
    "25% increased Attack Speed during any Flask Effect",
    "200% increased Armour and Evasion",
    "Trigger Level 20 Rampage on Kill",
])

_u("Tombfist", "Steelscale Gauntlets", "gloves", explicits=[
    "Has 2 Abyssal Sockets",
    "6% increased Attack Speed",
    "With a Murderous Eye Jewel Socketed, Intimidate Enemies for 4 seconds on Hit",
    "With a Searching Eye Jewel Socketed, Maim Enemies for 4 seconds on Hit",
])

# ===================================================================
# BOOTS
# ===================================================================

_u("Wanderlust", "Wool Shoes", "boots", explicits=[
    "+5 to Dexterity",
    "+10 to maximum Energy Shield",
    "20% increased Movement Speed",
    "Cannot be Frozen",
])

_u("Seven-League Step", "Rawhide Boots", "boots", explicits=[
    "50% increased Movement Speed",
])

_u("Atziri's Step", "Slink Boots", "boots", explicits=[
    "180% increased Evasion Rating",
    "+70 to maximum Life",
    "30% increased Movement Speed",
    "16% chance to Dodge Spell Hits",
])

_u("Darkray Vectors", "Dragonscale Boots", "boots", explicits=[
    "+1 to Maximum Frenzy Charges",
    "+25 to Dexterity",
    "2% increased Movement Speed per Frenzy Charge",
    "140% increased Armour and Evasion",
    "+40% to Lightning Resistance",
    "10% increased Dodge Rating per Frenzy Charge",
    "40% reduced Frenzy Charge Duration",
])

_u("Sin Trek", "Stealth Boots", "boots", explicits=[
    "+25 to Dexterity",
    "+25 to Intelligence",
    "+100 to maximum Energy Shield",
    "30% increased Movement Speed",
    "30% increased Evasion Rating",
])

_u("Bubonic Trail", "Murder Boots", "boots", explicits=[
    "Has 2 Abyssal Sockets",
    "4% increased maximum Life",
    "30% increased Movement Speed",
    "Enemies you Kill have a 10% chance to Explode, dealing a quarter of their Maximum Life as Chaos Damage",
])

_u("Kaom's Roots", "Titan Greaves", "boots", explicits=[
    "Has no Sockets",
    "+200 to maximum Life",
    "Cannot be Knocked Back",
    "Unwavering Stance",
])

_u("The Blood Dance", "Sharkskin Boots", "boots", explicits=[
    "+30 to Dexterity",
    "15% increased Attack Speed while you have at least one Frenzy Charge",
    "2% increased Movement Speed per Frenzy Charge",
    "3% of Life Regenerated per second per Frenzy Charge",
    "2% reduced Attack and Cast Speed per Frenzy Charge",
    "+50 to maximum Life",
    "25% chance to gain a Frenzy Charge on Kill",
])

_u("Rainbowstride", "Conjurer Boots", "boots", explicits=[
    "+1 to Level of Socketed Gems",
    "+150 to maximum Mana",
    "+20% to all Elemental Resistances",
    "25% increased Movement Speed",
    "+6% Chance to Block Spell Damage",
])

_u("Stormcharger", "Plated Greaves", "boots", explicits=[
    "Adds 1 to 50 Lightning Damage to Attacks",
    "+100 to Armour",
    "25% increased Movement Speed",
    "50% increased Effect of Lightning Ailments",
    "50% of Physical Damage Converted to Lightning Damage",
])

_u("Wake of Destruction", "Mesh Boots", "boots", explicits=[
    "Adds 1 to 120 Lightning Damage to Attacks",
    "+25 to Strength",
    "+25 to Intelligence",
    "15% increased Movement Speed",
])

_u("Ralakesh's Impatience", "Riveted Boots", "boots", explicits=[
    "+15% to all Elemental Resistances",
    "+25 to maximum Life",
    "25% increased Movement Speed",
    "Count as having maximum number of Endurance Charges",
    "Count as having maximum number of Frenzy Charges",
    "Count as having maximum number of Power Charges",
])

_u("Garukhan's Flight", "Stealth Boots", "boots", explicits=[
    "+3 to Level of all Dexterity Skill Gems",
    "30% increased Movement Speed",
    "Immune to Burning Ground, Shocked Ground, Chilled Ground",
    "+100 to maximum Energy Shield",
    "Regenerate 100 Life per second while moving",
])

# ===================================================================
# AMULETS
# ===================================================================

_u("Karui Ward", "Jade Amulet", "amulet",
   implicits=["+26 to Dexterity"],
   explicits=[
    "+30 to Strength",
    "+30 to Dexterity",
    "30% increased Projectile Speed",
    "10% increased Movement Speed",
    "30% increased Projectile Damage",
])

_u("Astramentis", "Onyx Amulet", "amulet",
   implicits=["+16 to all Attributes"],
   explicits=[
    "+116 to all Attributes",
])

_u("Atziri's Foible", "Paua Amulet", "amulet",
   implicits=["+25 to maximum Mana"],
   explicits=[
    "+80 to maximum Mana",
    "80% increased Mana Regeneration Rate",
    "Items and Gems have 25% reduced Attribute Requirements",
    "-4 to Level of all Skills",
    "+4 to Level of all Skills when on Low Life",
])

_u("Impresence (Physical)", "Onyx Amulet", "amulet",
   implicits=["+16 to all Attributes"],
   explicits=[
    "+60 to maximum Life",
    "20% increased Physical Damage",
    "Adds 12 to 16 Physical Damage",
    "Vulnerability has no Reservation if Cast as an Aura",
    "Gain Maddening Presence for 10 seconds when you Kill a Rare or Unique Enemy",
])

_u("Impresence (Fire)", "Onyx Amulet", "amulet",
   implicits=["+16 to all Attributes"],
   explicits=[
    "+60 to maximum Life",
    "30% increased Fire Damage",
    "Adds 12 to 16 Fire Damage",
    "Flammability has no Reservation if Cast as an Aura",
    "Gain Maddening Presence for 10 seconds when you Kill a Rare or Unique Enemy",
])

_u("Impresence (Cold)", "Onyx Amulet", "amulet",
   implicits=["+16 to all Attributes"],
   explicits=[
    "+60 to maximum Life",
    "30% increased Cold Damage",
    "Adds 12 to 16 Cold Damage",
    "Frostbite has no Reservation if Cast as an Aura",
    "Gain Maddening Presence for 10 seconds when you Kill a Rare or Unique Enemy",
])

_u("Impresence (Lightning)", "Onyx Amulet", "amulet",
   implicits=["+16 to all Attributes"],
   explicits=[
    "+60 to maximum Life",
    "30% increased Lightning Damage",
    "Adds 1 to 32 Lightning Damage",
    "Conductivity has no Reservation if Cast as an Aura",
    "Gain Maddening Presence for 10 seconds when you Kill a Rare or Unique Enemy",
])

_u("Impresence (Chaos)", "Onyx Amulet", "amulet",
   implicits=["+16 to all Attributes"],
   explicits=[
    "+60 to maximum Life",
    "20% increased Chaos Damage",
    "Adds 12 to 16 Chaos Damage",
    "Despair has no Reservation if Cast as an Aura",
    "Gain Maddening Presence for 10 seconds when you Kill a Rare or Unique Enemy",
])

_u("Xoph's Blood", "Amber Amulet", "amulet",
   implicits=["+30 to Strength"],
   explicits=[
    "+10% to Fire Resistance",
    "10% increased Strength",
    "Damage Penetrates 10% Fire Resistance",
    "Cover Enemies in Ash when they Hit you",
    "Avatar of Fire",
])

_u("Pandemonius", "Jade Amulet", "amulet",
   implicits=["+26 to Dexterity"],
   explicits=[
    "+25 to Dexterity",
    "20% increased Cold Damage",
    "+35% to Cold Resistance",
    "Chill Enemy for 1 second when Hit, reducing their Action Speed by 30%",
    "Blind Chilled Enemies on Hit",
    "Damage Penetrates 20% Cold Resistance against Chilled Enemies",
])

_u("Badge of the Brotherhood", "Turquoise Amulet", "amulet",
   implicits=["+16 to Dexterity and Intelligence"],
   explicits=[
    "10% increased Movement Speed",
    "Your Maximum Frenzy Charges is equal to your Maximum Power Charges",
])

_u("Marylene's Fallacy", "Lapis Amulet", "amulet",
   implicits=["+26 to Intelligence"],
   explicits=[
    "+80% to Global Critical Strike Multiplier",
    "Adds 3 to 4 Cold Damage to Attacks",
    "40% reduced Global Critical Strike Chance",
    "Non-critical Strikes deal 40% less Damage",
])

_u("Presence of Chayula", "Onyx Amulet", "amulet",
   implicits=["+16 to all Attributes"],
   explicits=[
    "+60% to Chaos Resistance",
    "20% of Maximum Life as Extra Maximum Energy Shield",
    "Cannot be Stunned",
])

_u("Eye of Chayula", "Onyx Amulet", "amulet",
   implicits=["+16 to all Attributes"],
   explicits=[
    "20% reduced maximum Life",
    "30% increased Rarity of Items found",
    "Cannot be Stunned",
])

_u("Carnage Heart", "Onyx Amulet", "amulet",
   implicits=["+16 to all Attributes"],
   explicits=[
    "+30 to all Attributes",
    "25% increased Damage while Leeching",
    "50% increased Life Leeched per second",
    "+20% to all Elemental Resistances",
    "Extra Gore",
])

_u("Bisco's Collar", "Gold Amulet", "amulet",
   implicits=["12% increased Rarity of Items found"],
   explicits=[
    "100% increased Rarity of Items Dropped by Slain Magic Enemies",
    "50% increased Quantity of Items Dropped by Slain Normal Enemies",
])

_u("Shaper's Seed", "Agate Amulet", "amulet",
   implicits=["+16 to Strength and Intelligence"],
   explicits=[
    "+30 to maximum Life",
    "+20 to maximum Mana",
    "Regenerate 2% of Life per second",
    "Nearby Allies gain 2% of Life Regenerated per second",
    "Nearby Allies gain 40% increased Mana Regeneration Rate",
])

_u("Ngamahu Tiki", "Coral Amulet", "amulet",
   implicits=["Regenerate 2 Life per second"],
   explicits=[
    "+70 to maximum Life",
    "+36% to Fire Resistance",
    "1% of Life Regenerated per second per Endurance Charge",
    "50% increased Fire Damage while Ignited",
    "Ignited when Hit",
])

_u("Replica Dragonfang's Flight", "Onyx Amulet", "amulet",
   implicits=["+16 to all Attributes"],
   explicits=[
    "+3 to Level of all Skill Gems",
    "+5% to all maximum Resistances",
    "-20% to all Resistances",
])

_u("Leadership's Price", "Onyx Amulet", "amulet",
   implicits=["+16 to all Attributes"],
   explicits=[
    "You have Consecrated Ground around you while stationary",
    "Nearby Enemies have 50% reduced Life Regeneration Rate",
    "Nearby Allies have Culling Strike",
    "You and Nearby Allies deal 30% increased Damage",
    "You and Nearby Allies have +10% to all maximum Resistances",
])

_u("Ungil's Harmony", "Turquoise Amulet", "amulet",
   implicits=["+16 to Dexterity and Intelligence"],
   explicits=[
    "100% increased Global Critical Strike Chance",
    "Your Critical Strike Multiplier is 300%",
])

# ===================================================================
# RINGS
# ===================================================================

_u("Praxis", "Paua Ring", "ring",
   implicits=["+25 to maximum Mana"],
   explicits=[
    "+30 to maximum Mana",
    "30% increased Mana Regeneration Rate",
    "-8 to Total Mana Cost of Skills",
    "8% of Damage taken Recouped as Mana",
])

_u("Le Heup of All", "Iron Ring", "ring",
   implicits=["Adds 1 to 4 Physical Damage to Attacks"],
   explicits=[
    "+24 to all Attributes",
    "24% increased Damage",
    "24% increased Rarity of Items found",
    "+24% to all Elemental Resistances",
])

_u("Mark of the Shaper", "Opal Ring", "ring",
   implicits=["25% increased Elemental Damage"],
   explicits=[
    "Adds 12 to 30 Lightning Damage to Spells",
    "20% increased Spell Damage",
    "80% increased maximum Energy Shield",
    "If your other Ring is an Elder Item, 80% more Spell Damage",
])

_u("Circle of Guilt", "Iron Ring", "ring",
   implicits=["Adds 1 to 4 Physical Damage to Attacks"],
   explicits=[
    "+20 to Strength",
    "Adds 7 to 12 Physical Damage",
    "Herald of Purity has 40% increased Buff Effect",
    "Herald of Purity has 40% reduced Mana Reservation",
])

_u("Thief's Torment", "Prismatic Ring", "ring",
   implicits=["+8% to all Elemental Resistances"],
   explicits=[
    "Can't use other Rings",
    "+30 Life gained for each Enemy Hit by Attacks",
    "+20 Mana gained for each Enemy Hit by Attacks",
    "+16% to all Elemental Resistances",
    "50% increased Quantity of Items Found",
])

_u("Pyre", "Sapphire Ring", "ring",
   implicits=["+30% to Cold Resistance"],
   explicits=[
    "+25 to Strength",
    "40% increased Burning Damage",
    "100% of Cold Damage Converted to Fire Damage",
    "Ignited Enemies are destroyed on Kill",
])

_u("Call of the Brotherhood", "Two-Stone Ring", "ring",
   implicits=["+16% to Cold and Lightning Resistances"],
   explicits=[
    "+15 to Intelligence",
    "15% increased Lightning Damage",
    "40% of Lightning Damage Converted to Cold Damage",
    "Your spells have 100% chance to Shock against Frozen enemies",
])

_u("Berek's Grip", "Two-Stone Ring", "ring",
   implicits=["+16% to Cold and Lightning Resistances"],
   explicits=[
    "+25 to maximum Life",
    "Adds 1 to 50 Lightning Damage to Spells and Attacks",
    "+30% to Lightning Resistance",
    "1% of Damage Leeched as Life against Shocked Enemies",
    "1% of Damage Leeched as Energy Shield against Frozen Enemies",
])

_u("Malachai's Artifice", "Unset Ring", "ring",
   implicits=["Has 1 Socket"],
   explicits=[
    "-20% to all Elemental Resistances",
    "Socketed Gems have Elemental Equilibrium",
])

_u("Essence Worm", "Unset Ring", "ring",
   implicits=["Has 1 Socket"],
   explicits=[
    "Socketed Gem has 80% reduced Reservation Efficiency",
    "+2 to Level of Socketed Aura Gems",
    "40% increased Mana Reserved",
])

_u("Sibyl's Lament", "Coral Ring", "ring",
   implicits=["Regenerate 2 Life per second"],
   explicits=[
    "+40 to maximum Energy Shield",
    "+30% to Fire Resistance",
    "+30% to Lightning Resistance",
    "80% reduced Reflected Elemental Damage taken",
])

_u("Ventor's Gamble", "Gold Ring", "ring",
   implicits=["12% increased Rarity of Items found"],
   explicits=[
    "+50 to maximum Life",
    "+10% to Fire Resistance",
    "+10% to Cold Resistance",
    "+10% to Lightning Resistance",
    "10% increased Rarity of Items found",
    "5% increased Quantity of Items found",
])

_u("Nimis", "Topaz Ring", "ring",
   implicits=["+30% to Lightning Resistance"],
   explicits=[
    "Projectiles Return to you",
    "+30% to Lightning Resistance",
    "50% increased Projectile Damage",
])

_u("Ashes of the Stars", "Onyx Amulet", "amulet",
   implicits=["+16 to all Attributes"],
   explicits=[
    "+30% to Quality of all Skill Gems",
    "+1 to Level of all Skill Gems",
    "10% increased Mana Reservation Efficiency of Skills",
    "15% increased Experience Gain of Gems",
])

_u("Crystallised Omniscience", "Onyx Amulet", "amulet",
   implicits=["+16 to all Attributes"],
   explicits=[
    "Modifiers to Attributes instead apply to Omniscience",
    "+1% to all Elemental Resistances per 10 Omniscience",
    "Penetrate 1% Elemental Resistances per 10 Omniscience",
    "Attribute Requirements can be satisfied by Omniscience",
])

# ===================================================================
# BELTS
# ===================================================================

_u("Headhunter", "Leather Belt", "belt",
   implicits=["+40 to maximum Life"],
   explicits=[
    "+55 to Strength",
    "+55 to Dexterity",
    "+50 to maximum Life",
    "+25% to Cold Resistance",
    "When you Kill a Rare Monster, you gain its Modifiers for 20 seconds",
])

_u("Mageblood", "Heavy Belt", "belt",
   implicits=["+25 to Strength"],
   explicits=[
    "+50 to Dexterity",
    "+50 to Intelligence",
    "+60 to maximum Life",
    "Magic Utility Flasks applied to you have 80% increased Effect",
    "Magic Utility Flasks applied to you never expire during Flask Effect",
])

_u("Wurm's Molt", "Leather Belt", "belt",
   implicits=["+40 to maximum Life"],
   explicits=[
    "+25 to Strength",
    "+25 to Intelligence",
    "+60 to maximum Life",
    "+15% to Cold Resistance",
    "0.4% of Physical Attack Damage Leeched as Life",
    "0.4% of Physical Attack Damage Leeched as Mana",
])

_u("Prismweave", "Rustic Sash", "belt",
   implicits=["20% increased Physical Damage"],
   explicits=[
    "Adds 15 to 25 Fire Damage to Attacks",
    "Adds 15 to 25 Cold Damage to Attacks",
    "Adds 1 to 40 Lightning Damage to Attacks",
    "30% increased Elemental Damage with Attack Skills",
    "+15% to all Elemental Resistances",
])

_u("Perandus Blazon", "Cloth Belt", "belt",
   implicits=["15% increased Stun and Block Recovery"],
   explicits=[
    "+20 to all Attributes",
    "8% increased Quantity of Items found",
    "+20% to Fire Resistance",
    "20% increased Flask Effect Duration",
])

_u("String of Servitude", "Heavy Belt", "belt",
   implicits=["Implicit Modifier magnitudes are tripled"],
   explicits=[
    "Has 1 Implicit Modifier",
])

_u("Perseverance", "Vanguard Belt", "belt",
   implicits=["+260 to Armour and Evasion Rating"],
   explicits=[
    "+200 to Armour",
    "+200 to Evasion Rating",
    "+30 to maximum Energy Shield",
    "+40 to maximum Life",
    "You have Onslaught while you have Fortify",
    "Melee Hits Fortify",
    "1% increased Attack Damage per 200 of the lowest of Armour and Evasion Rating",
])

_u("Ryslatha's Coil", "Studded Belt", "belt",
   implicits=["20% increased Stun Duration on Enemies"],
   explicits=[
    "+80 to maximum Life",
    "+30 to Strength",
    "30% more Maximum Physical Attack Damage",
    "30% less Minimum Physical Attack Damage",
    "Adds 1 to 3 Physical Damage to Attacks",
    "20% increased Stun Duration on Enemies",
])

_u("Darkness Enthroned", "Stygian Vise", "belt",
   implicits=["Has 1 Abyssal Socket"],
   explicits=[
    "Has 1 Abyssal Socket",
    "75% increased Effect of Socketed Abyss Jewels",
])

_u("Soul Tether", "Cloth Belt", "belt",
   implicits=["15% increased Stun and Block Recovery"],
   explicits=[
    "+30 to Intelligence",
    "+100 to maximum Energy Shield",
    "Gain 6% of Maximum Life as Extra Maximum Energy Shield",
    "Life Leech effects are not removed at Full Life",
    "Life Leech effects Recover Energy Shield instead while on Full Life",
])

_u("The Magnate", "Studded Belt", "belt",
   implicits=["20% increased Stun Duration on Enemies"],
   explicits=[
    "+25 to Strength",
    "+40 to maximum Life",
    "50% increased Flask Charges gained",
    "25% increased Physical Damage",
    "20% increased Area of Effect while you have at least 25 Rage",
])

# ===================================================================
# WEAPONS — SWORDS
# ===================================================================

_u("Oni-Goroshi", "Charan's Sword", "weapon",
   phys_min=6, phys_max=13, aps=1.45, crit=5.0,
   explicits=[
    "Uses both hand slots",
    "Has 6 Sockets",
    "40% increased Physical Damage",
    "Adds 3 to 5 Physical Damage to Attacks per Level",
    "Gain Her Embrace for 3 seconds when you Ignite an Enemy",
    "While in Her Embrace, take 0.5% of your total Maximum Life and Energy Shield as Fire Damage per second per Level",
])

_u("The Saviour", "Vaal Rapier", "weapon",
   phys_min=56, phys_max=104, aps=1.5, crit=6.5,
   implicits=["+25% to Global Critical Strike Multiplier"],
   explicits=[
    "Triggers Level 20 Reflection when Equipped",
    "350% increased Physical Damage",
    "Adds 20 to 30 Physical Damage",
    "6% increased Attack Speed",
])

_u("Paradoxica", "Vaal Rapier", "weapon",
   phys_min=56, phys_max=104, aps=1.5, crit=6.5,
   implicits=["+25% to Global Critical Strike Multiplier"],
   explicits=[
    "Attacks with this Weapon deal Double Damage",
    "Veiled Prefix",
    "Veiled Suffix",
])

_u("Starforge", "Infernal Sword", "weapon",
   phys_min=100, phys_max=260, aps=1.3, crit=5.0,
   explicits=[
    "500% increased Physical Damage",
    "8% increased Area of Effect",
    "+100 to maximum Life",
    "Your Physical Damage can Shock",
    "Deal no Elemental Damage",
])

_u("Ahn's Might", "Midnight Blade", "weapon",
   phys_min=30, phys_max=80, aps=1.3, crit=5.0,
   explicits=[
    "240% increased Physical Damage",
    "+25 to Strength",
    "20% increased Attack Speed while you have no Endurance Charges",
    "+60% to Global Critical Strike Multiplier while you have no Endurance Charges",
    "-1 to Maximum Endurance Charges",
])

# ===================================================================
# WEAPONS — DAGGERS
# ===================================================================

_u("Arakaali's Fang", "Fiend Dagger", "weapon",
   phys_min=31, phys_max=121, aps=1.4, crit=6.3,
   implicits=["30% increased Global Critical Strike Chance"],
   explicits=[
    "170% increased Physical Damage",
    "1% increased Attack Speed per 8 Dexterity",
    "+46 to maximum Life",
    "10% chance to Poison on Hit",
    "Rampage",
    "15% chance on Kill to Trigger Level 20 Raise Spiders",
])

_u("Heartbreaker", "Royal Skean", "weapon",
   phys_min=15, phys_max=60, aps=1.5, crit=6.0,
   implicits=["30% increased Global Critical Strike Chance"],
   explicits=[
    "+35 to Spell Damage",
    "50% increased Spell Damage",
    "+50 to maximum Energy Shield",
    "10% increased Movement Speed",
    "Minions have 30% increased Movement Speed",
    "Spell Damage Modifiers apply to Minion Damage",
])

# ===================================================================
# WEAPONS — AXES
# ===================================================================

_u("Atziri's Disfavour", "Vaal Axe", "weapon",
   phys_min=180, phys_max=300, aps=1.25, crit=5.0,
   explicits=[
    "+2 to Level of Socketed Support Gems",
    "Adds 25 to 45 Physical Damage",
    "25% chance to cause Bleeding on Hit",
    "100% increased Bleed Duration",
])

_u("Dreadarc", "Cleaver", "weapon",
   phys_min=23, phys_max=64, aps=1.3, crit=5.0,
   explicits=[
    "Adds 5 to 15 Physical Damage",
    "Adds 10 to 20 Fire Damage",
    "+20% to Fire Resistance",
    "1% of Fire Damage Leeched as Life",
    "Gain an Endurance Charge when you are Hit",
])

_u("Hezmana's Bloodlust", "Vaal Hatchet", "weapon",
   phys_min=48, phys_max=113, aps=1.5, crit=5.0,
   explicits=[
    "200% increased Physical Damage",
    "Adds 12 to 24 Physical Damage",
    "+25% to Cold Resistance",
    "Skills Cost Life instead of Mana",
])

# ===================================================================
# WEAPONS — MACES / SCEPTRES
# ===================================================================

_u("Brightbeak", "War Hammer", "weapon",
   phys_min=11, phys_max=17, aps=1.45, crit=5.0,
   explicits=[
    "50% increased Attack Speed",
    "30% increased Critical Strike Chance",
    "+20% to Fire Resistance",
    "+20% to Lightning Resistance",
])

_u("Doon Cuebiyari", "Vaal Sceptre", "weapon",
   phys_min=32, phys_max=60, aps=1.4, crit=6.0,
   implicits=["40% increased Elemental Damage"],
   explicits=[
    "+1 to Level of Socketed Strength Gems",
    "1% increased Damage per 8 Strength",
    "1% increased Armour per 16 Strength",
    "+50 to Strength",
])

# ===================================================================
# WEAPONS — WANDS
# ===================================================================

_u("Lifesprig", "Driftwood Wand", "weapon",
   phys_min=4, phys_max=8, aps=1.4, crit=7.0,
   implicits=["11% increased Spell Damage"],
   explicits=[
    "+1 to Level of Socketed Spell Gems",
    "+20 to maximum Life",
    "+20 to maximum Mana",
    "Regenerate 6 Life per second",
    "+8% to Chaos Resistance",
])

_u("Storm Prison", "Carved Wand", "weapon",
   phys_min=10, phys_max=19, aps=1.5, crit=7.0,
   implicits=["18% increased Spell Damage"],
   explicits=[
    "+1 to Level of Socketed Lightning Gems",
    "+30 to maximum Mana",
    "Adds 1 to 30 Lightning Damage to Spells",
    "25% chance to gain a Power Charge on Kill",
    "+1 to Maximum Power Charges",
])

_u("Axiom Perpetuum", "Bronzescale Wand", "weapon",
   phys_min=8, phys_max=14, aps=1.35, crit=7.0,
   implicits=["12% increased Spell Damage"],
   explicits=[
    "Adds 2 to 3 Fire Damage to Spells",
    "Adds 2 to 3 Cold Damage to Spells",
    "Adds 1 to 5 Lightning Damage to Spells",
    "10% increased Cast Speed",
    "100% increased Critical Strike Chance for Spells",
])

_u("Piscator's Vigil", "Tornado Wand", "weapon",
   phys_min=20, phys_max=37, aps=1.3, crit=7.0,
   implicits=["18% increased Spell Damage"],
   explicits=[
    "No Physical Damage",
    "10% increased Attack Speed",
    "200% increased Elemental Damage with Attack Skills",
    "+25% to Critical Strike Multiplier",
    "+100 to Accuracy Rating",
])

_u("Void Battery", "Prophecy Wand", "weapon",
   phys_min=26, phys_max=68, aps=1.2, crit=7.0,
   implicits=["39% increased Spell Damage"],
   explicits=[
    "+1 to Maximum Power Charges",
    "80% increased Spell Damage",
    "25% increased Spell Damage per Power Charge",
    "+50 to maximum Mana",
    "+4% Chance to Block Attack Damage while wielding a Staff",
])

_u("Tulborn", "Spiraled Wand", "weapon",
   phys_min=15, phys_max=28, aps=1.4, crit=7.0,
   implicits=["15% increased Spell Damage"],
   explicits=[
    "+2 to Level of all Cold Spell Skill Gems",
    "Adds 4 to 50 Cold Damage to Spells",
    "+40 to maximum Mana",
    "10% increased Cast Speed",
])

# ===================================================================
# WEAPONS — BOWS
# ===================================================================

_u("Quill Rain", "Short Bow", "weapon",
   phys_min=5, phys_max=14, aps=3.0, crit=5.0,
   explicits=[
    "100% increased Attack Speed",
    "+2 Mana gained for each Enemy hit by Attacks",
    "50% less Weapon Damage",
    "100% increased Projectile Speed",
])

_u("Lioneye's Glare", "Imperial Bow", "weapon",
   phys_min=53, phys_max=220, aps=1.45, crit=5.0,
   explicits=[
    "340% increased Physical Damage",
    "Adds 8 to 14 Physical Damage",
    "+200 to Accuracy Rating",
    "Hits can't be Evaded",
    "Far Shot",
])

_u("Windripper", "Imperial Bow", "weapon",
   phys_min=25, phys_max=103, aps=1.5, crit=5.0,
   explicits=[
    "Adds 22 to 42 Cold Damage",
    "Adds 1 to 60 Lightning Damage",
    "15% increased Quantity of Items Dropped by Slain Frozen Enemies",
    "30% increased Rarity of Items Dropped by Slain Shocked Enemies",
    "+100 to Evasion Rating",
])

_u("Death's Opus", "Death Bow", "weapon",
   phys_min=25, phys_max=82, aps=1.32, crit=6.5,
   explicits=[
    "300% increased Physical Damage",
    "10% increased Attack Speed",
    "+50% to Critical Strike Multiplier",
    "Bow Attacks fire 2 additional Arrows",
    "+100 to maximum Life",
])

_u("Voltaxic Rift", "Spine Bow", "weapon",
   phys_min=28, phys_max=82, aps=1.5, crit=6.0,
   explicits=[
    "Adds 1 to 150 Lightning Damage",
    "200% increased Physical Damage",
    "10% increased Attack Speed",
    "60% of Lightning Damage Converted to Chaos Damage",
    "10% chance to Shock",
    "Your Chaos Damage can Shock",
])

_u("Chin Sol", "Assassin Bow", "weapon",
   phys_min=37, phys_max=78, aps=1.5, crit=6.5,
   explicits=[
    "200% increased Physical Damage",
    "10% increased Attack Speed",
    "100% more Bow Damage at Close Range",
    "Knocks Back Enemies if they are Close",
    "Bow Knockback distance is doubled",
])

_u("Tempest", "Citadel Bow", "weapon",
   phys_min=20, phys_max=58, aps=1.1, crit=5.0,
   explicits=[
    "Adds 10 to 26 Physical Damage",
    "Adds 9 to 85 Lightning Damage",
    "6% increased Attack Speed",
    "Arrows always Pierce",
])

_u("Reach of the Council", "Spine Bow", "weapon",
   phys_min=28, phys_max=82, aps=1.5, crit=6.0,
   explicits=[
    "250% increased Physical Damage",
    "10% increased Attack Speed",
    "Bow Attacks fire 4 additional Arrows",
    "20% less Weapon Damage",
])

# ===================================================================
# WEAPONS — CLAWS
# ===================================================================

_u("Wasp Nest", "Throat Stabber", "weapon",
   phys_min=22, phys_max=56, aps=1.6, crit=6.3,
   implicits=["+40 Life gained for each Enemy hit by Attacks"],
   explicits=[
    "40% increased Physical Damage",
    "20% increased Attack Speed",
    "25% increased Critical Strike Chance",
    "+300 to Accuracy Rating",
    "20% chance to Poison on Hit",
    "Adds 2 to 6 Chaos Damage per Poison on the Enemy",
])

_u("The Scourge", "Terror Claw", "weapon",
   phys_min=24, phys_max=64, aps=1.6, crit=6.3,
   implicits=["+46 Life gained for each Enemy hit by Attacks"],
   explicits=[
    "180% increased Physical Damage",
    "20% increased Attack Speed",
    "Adds 2 to 6 Physical Damage for each Zombie you own",
    "Minions deal 70% increased Damage",
    "Increases and Reductions to Minion Damage also affect you",
])

_u("Touch of Anguish", "Imperial Claw", "weapon",
   phys_min=25, phys_max=100, aps=1.6, crit=6.0,
   implicits=["+46 Life gained for each Enemy hit by Attacks"],
   explicits=[
    "Adds 26 to 46 Cold Damage",
    "20% increased Cold Damage",
    "25% chance to gain a Frenzy Charge on Killing a Frozen Enemy",
    "Skills Chain +1 times",
    "30% more Damage with Hits and Ailments against Enemies that are on Full Life",
])

# ===================================================================
# WEAPONS — STAVES
# ===================================================================

_u("Cane of Kulemak", "Judgement Staff", "weapon",
   phys_min=70, phys_max=145, aps=1.3, crit=6.2,
   implicits=["+18% Chance to Block Attack Damage while wielding a Staff"],
   explicits=[
    "+2 to Level of all Spell Skill Gems",
    "100% increased Spell Damage",
    "10% increased Cast Speed",
    "+80 to maximum Mana",
    "Veiled Suffix",
])

_u("The Covenant", "Spidersilk Robe", "body", explicits=[
    "+1 to Level of Socketed Skill Gems",
    "Socketed Gems are Supported by Level 29 Added Chaos Damage",
    "+100 to maximum Life",
    "+200 to maximum Energy Shield",
    "Skills Cost +100 Life",
])

# ===================================================================
# SHIELDS
# ===================================================================

_u("Lycosidae", "Rawhide Tower Shield", "shield", explicits=[
    "+200 to Armour",
    "+120 to maximum Life",
    "Hits can't be Evaded",
    "+5% Chance to Block",
])

_u("The Princess", "Golden Buckler", "shield", explicits=[
    "+40 to Evasion Rating",
    "+10% to all Elemental Resistances",
    "Gain 10% of Physical Damage as Extra Cold Damage",
    "+1 to Maximum Endurance Charges",
])

_u("Prismatic Eclipse", "Twilight Blade", "weapon",
   phys_min=20, phys_max=45, aps=1.3, crit=5.0,
   explicits=[
    "+8% Chance to Block Attack Damage while Dual Wielding",
    "Adds 1 to 100 Lightning Damage",
    "25% increased Global Attack Speed per Green Socket",
    "12% increased Physical Damage per Red Socket",
    "+100 to Accuracy Rating per Green Socket",
])

_u("Aegis Aurora", "Champion Kite Shield", "shield",
   implicits=["+8% to all Elemental Resistances"],
   explicits=[
    "+200 to Armour",
    "+20 to maximum Energy Shield",
    "+50% to Cold Resistance",
    "Replenishes Energy Shield by 2% of Armour when you Block",
    "+5% Chance to Block",
])

_u("Magna Eclipsis", "Pinnacle Tower Shield", "shield", explicits=[
    "+28 to maximum Life",
    "250% increased Armour",
    "Socketed Gems are Supported by Level 30 Greater Spell Echo",
    "+2 to Level of Socketed Gems",
])

_u("Ahn's Heritage", "Colossal Tower Shield", "shield", explicits=[
    "+2 to Level of Socketed Gems",
    "+3% to maximum Fire Resistance while you have no Endurance Charges",
    "+3% to maximum Cold Resistance while you have no Endurance Charges",
    "+3% to maximum Lightning Resistance while you have no Endurance Charges",
    "+3000 to Armour while you have no Endurance Charges",
    "-1 to Maximum Endurance Charges",
])

_u("Saffell's Frame", "Branded Kite Shield", "shield",
   implicits=["+4% to all Elemental Resistances"],
   explicits=[
    "+20% to all Elemental Resistances",
    "+4% to maximum Fire Resistance",
    "+4% to maximum Cold Resistance",
    "+4% to maximum Lightning Resistance",
    "Cannot Block Attack Damage",
    "20% increased Chance to Block Spell Damage",
])

_u("Lioneye's Remorse", "Pinnacle Tower Shield", "shield", explicits=[
    "+1000 to Armour",
    "+160 to maximum Life",
    "5% reduced Movement Speed",
    "20% increased Stun and Block Recovery",
])

# ===================================================================
# FLASKS
# ===================================================================

_u("Dying Sun", "Ruby Flask", "flask", explicits=[
    "+50% to Fire Resistance",
    "20% less Fire Damage taken",
    "Skills fire 2 additional Projectiles during Flask Effect",
    "25% increased Area of Effect during Flask Effect",
])

_u("Bottled Faith", "Sulphur Flask", "flask", explicits=[
    "40% increased Damage",
    "Creates Consecrated Ground on Use",
    "2% increased Critical Strike Chance against Enemies on Consecrated Ground during Flask effect",
    "Consecrated Ground created during Effect applies 7% increased Damage taken to Enemies",
])

_u("Atziri's Promise", "Amethyst Flask", "flask", explicits=[
    "+35% to Chaos Resistance",
    "2% of Chaos Damage Leeched as Life during Flask effect",
    "Gain 15% of Physical Damage as Extra Chaos Damage during effect",
    "Gain 15% of Elemental Damage as Extra Chaos Damage during effect",
])

_u("Taste of Hate", "Sapphire Flask", "flask", explicits=[
    "+50% to Cold Resistance",
    "20% less Cold Damage taken",
    "Gain 15% of Physical Damage as Extra Cold Damage during effect",
    "30% chance to Avoid being Frozen during Flask effect",
])

_u("Lion's Roar", "Granite Flask", "flask", explicits=[
    "+3000 to Armour",
    "Adds Knockback to Melee Attacks during Flask effect",
    "Knocks Back Enemies in an Area when you use a Flask",
    "25% more Melee Physical Damage during effect",
])

_u("Wise Oak", "Bismuth Flask", "flask", explicits=[
    "+35% to all Elemental Resistances",
    "During Flask Effect, 10% reduced Damage taken of each Element for which your Uncapped Elemental Resistance is lowest",
    "During Flask Effect, Damage Penetrates 10% Resistance of each Element for which your Uncapped Elemental Resistance is highest",
])

_u("Cinderswallow Urn", "Silver Flask", "flask", explicits=[
    "20% increased Onslaught Effect",
    "Recharges 1 Charge when you Consume an Ignited Corpse",
    "Enemies Ignited by you during Flask Effect take 10% increased Damage",
    "Recover 3% of Life when you Kill an Enemy during Flask Effect",
])

_u("Sin's Rebirth", "Stibnite Flask", "flask", explicits=[
    "Creates a Smoke Cloud on Use",
    "Gain Unholy Might during Flask Effect",
])

_u("The Overflowing Chalice", "Sulphur Flask", "flask", explicits=[
    "40% increased Damage",
    "100% increased Charge Recovery",
    "Enemies in your Consecrated Ground take 10% increased Damage",
    "50% of Charges gained also apply to your other Flasks",
])

_u("Progenesis", "Amethyst Flask", "flask", explicits=[
    "+35% to Chaos Resistance",
    "25% of Life Loss from Hit is Recovered over 4 seconds",
    "Poisons you inflict deal Damage 25% faster during Flask Effect",
])

_u("Divination Distillate", "Large Hybrid Flask", "flask", explicits=[
    "50% increased Charges used",
    "Adds 6 to 12 Fire Damage to Attacks during Flask Effect",
    "4% increased Quantity of Items found during Flask Effect",
    "40% increased Rarity of Items found during Flask Effect",
    "+6% to maximum Fire Resistance during Flask Effect",
    "+6% to maximum Cold Resistance during Flask Effect",
    "+6% to maximum Lightning Resistance during Flask Effect",
])

_u("Rumi's Concoction", "Granite Flask", "flask", explicits=[
    "+3000 to Armour",
    "+10% Chance to Block Attack Damage during Flask effect",
    "+6% Chance to Block Spell Damage during Flask effect",
])

_u("Coruscating Elixir", "Ruby Flask", "flask", explicits=[
    "+50% to Fire Resistance",
    "Removes all but 1 Life on use",
    "Removes Burning on use",
    "Chaos Damage does not bypass Energy Shield during Effect",
    "100% of Fire Damage from Hits taken as Chaos Damage during Flask Effect",
])

_u("Lavianga's Spirit", "Sanctified Mana Flask", "flask", explicits=[
    "50% increased Amount Recovered",
    "33% reduced Recovery Rate",
    "Skills have no Mana Cost during Effect",
])

_u("Quicksilver Flask of Adrenaline", "Quicksilver Flask", "flask", explicits=[
    "40% increased Movement Speed",
    "25% increased Movement Speed during Flask Effect",
])

# ===================================================================
# JEWELS (Abyssal, regular, cluster)
# ===================================================================

_u("Watcher's Eye", "Prismatic Jewel", "jewel", explicits=[
    "+5% to maximum Energy Shield",
    "+5% to maximum Life",
    "+5% to maximum Mana",
    "Modifier while affected by Aura 1",
    "Modifier while affected by Aura 2",
])

_u("Militant Faith", "Timeless Jewel", "jewel", explicits=[
    "Carved to glorify a Templar general",
    "Passives in radius are Conquered by the Templars",
])

_u("Lethal Pride", "Timeless Jewel", "jewel", explicits=[
    "Carved to glorify a Karui general",
    "Passives in radius are Conquered by the Karui",
])

_u("Glorious Vanity", "Timeless Jewel", "jewel", explicits=[
    "Carved to glorify a Vaal general",
    "Passives in radius are Conquered by the Vaal",
])

_u("Brutal Restraint", "Timeless Jewel", "jewel", explicits=[
    "Carved to glorify a Maraketh general",
    "Passives in radius are Conquered by the Maraketh",
])

_u("Elegant Hubris", "Timeless Jewel", "jewel", explicits=[
    "Carved to glorify an Eternal general",
    "Passives in radius are Conquered by the Eternal Empire",
])

_u("Thread of Hope", "Crimson Jewel", "jewel", explicits=[
    "Only affects Passives in Medium Ring",
    "Passives in Radius can be Allocated without being connected to your tree",
    "-20% to all Elemental Resistances",
])

_u("Unnatural Instinct", "Viridian Jewel", "jewel", explicits=[
    "Allocated Small Passive Skills in Radius grant nothing",
    "Grants all bonuses of Unallocated Small Passive Skills in Radius",
])

_u("Forbidden Flame", "Crimson Jewel", "jewel", explicits=[
    "Allocates a specific Ascendancy Notable (must pair with Forbidden Flesh)",
])

_u("Forbidden Flesh", "Cobalt Jewel", "jewel", explicits=[
    "Allocates a specific Ascendancy Notable (must pair with Forbidden Flame)",
])

_u("The Green Nightmare", "Viridian Jewel", "jewel", explicits=[
    "Passives granting Cold Resistance or all Elemental Resistances in Radius also grant Chance to Dodge Attack Hits at 35% of its value",
])

_u("The Red Nightmare", "Crimson Jewel", "jewel", explicits=[
    "Passives granting Fire Resistance or all Elemental Resistances in Radius also grant Chance to Block Attack Damage at 35% of its value",
])

_u("The Blue Nightmare", "Cobalt Jewel", "jewel", explicits=[
    "Passives granting Lightning Resistance or all Elemental Resistances in Radius also grant Chance to Block Spell Damage at 35% of its value",
])

_u("Inspired Learning", "Crimson Jewel", "jewel", explicits=[
    "With 4 Notables Allocated in Radius, When you Kill a Rare Monster, you gain 1 of its Modifiers for 20 seconds",
])

_u("Split Personality", "Crimson Jewel", "jewel", explicits=[
    "This Jewel's Socket has 25% increased effect per Allocated Notable Passive Skill between it and your Class' starting location",
    "+5 to Strength",
    "+5 to Intelligence",
])

_u("Voices", "Large Cluster Jewel", "jewel", explicits=[
    "Adds 3 Jewel Socket Passive Skills",
    "Added Small Passive Skills grant Nothing",
])

_u("Megalomaniac", "Medium Cluster Jewel", "jewel", explicits=[
    "Adds 4 Passive Skills",
    "Added Small Passive Skills grant Nothing",
    "Has 3 random Notable Passive Skills",
])

# Clean up helper
del _u


# ===================================================================
# Public API
# ===================================================================


def get_unique(name: str) -> UniqueItemData | None:
    """Look up a unique item by name. Returns None if not found."""
    return _UNIQUES.get(name)


def is_known_unique(name: str) -> bool:
    """Check if a unique name is in our database."""
    return name in _UNIQUES


def list_uniques() -> list[str]:
    """Return all known unique item names."""
    return sorted(_UNIQUES.keys())


def list_uniques_by_class(item_class: str) -> list[str]:
    """Return unique names filtered by item class (e.g. 'helmet', 'weapon')."""
    return sorted(
        name for name, data in _UNIQUES.items()
        if data.item_class == item_class
    )
