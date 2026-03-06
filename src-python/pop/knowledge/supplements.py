"""Manual supplement data for gems/items not yet in RePoE.

RePoE lags behind patch releases (it extracts from GGPK game files which
update on patch day). This module provides known-good data scraped from
official patch notes and community sources so the AI has accurate info
on launch day.

This file should be updated each league start, then cleared once RePoE
catches up (typically within 24-48 hours of patch release).
"""

from __future__ import annotations

from pop.knowledge.models import GemInfo, UniqueInfo

# =========================================================================
# 3.28 Mirage — New Active Skill Gems
# Source: https://www.poewiki.net/wiki/Version_3.28.0
#         https://www.poe-vault.com/guides/mirage-league-skill-gems
# =========================================================================

NEW_ACTIVE_GEMS_328: list[GemInfo] = [
    # New Holy Skill Gems (Strength/Intelligence)
    GemInfo(name="Divine Blast", required_level=28, tags=["Spell", "AoE", "Fire", "Lightning"]),
    GemInfo(name="Holy Hammers", required_level=28, tags=["Attack", "AoE", "Melee", "Slam"]),
    GemInfo(name="Holy Strike", required_level=28, tags=["Attack", "Melee"]),
    GemInfo(name="Shield of Light", required_level=28, tags=["Attack", "AoE", "Trigger"]),
    # New Transfigured Gems
    GemInfo(
        name="Shockwave Totem of Authority", required_level=28,
        tags=["Spell", "AoE", "Totem"],
    ),
    GemInfo(
        name="Static Strike of Gathering Lightning", required_level=28,
        tags=["Attack", "Melee", "Lightning", "AoE"],
    ),
    GemInfo(
        name="Charged Dash of Projection", required_level=28,
        tags=["Attack", "AoE", "Channelling", "Movement", "Lightning"],
    ),
    GemInfo(
        name="Flamethrower Trap of Stability", required_level=28,
        tags=["Spell", "Trap", "Fire", "AoE"],
    ),
    GemInfo(
        name="Kinetic Fusillade of Detonation", required_level=28,
        tags=["Attack", "Projectile"],
    ),
    GemInfo(
        name="Orb of Storms of Squalls", required_level=28,
        tags=["Spell", "AoE", "Lightning", "Chaining"],
    ),
    GemInfo(
        name="Shock Nova of Procession", required_level=28,
        tags=["Spell", "AoE", "Lightning"],
    ),
    GemInfo(
        name="Storm Burst of Repulsion", required_level=28,
        tags=["Spell", "AoE", "Lightning", "Channelling"],
    ),
    GemInfo(
        name="Siphoning Trap of Pain", required_level=28,
        tags=["Spell", "Trap", "AoE"],
    ),
    GemInfo(
        name="Searing Bond of Detonation", required_level=28,
        tags=["Spell", "Totem", "Fire"],
    ),
    GemInfo(
        name="Creeping Frost of Floes", required_level=28,
        tags=["Spell", "AoE", "Cold", "Projectile"],
    ),
]

# =========================================================================
# 3.28 Mirage — New Support Gems
# =========================================================================

NEW_SUPPORT_GEMS_328: list[GemInfo] = [
    # Regular new supports
    GemInfo(
        name="Blessed Call Support", required_level=31, is_support=True,
        tags=["Support", "Warcry"],
    ),
    GemInfo(
        name="Excommunicate Support", required_level=31, is_support=True,
        tags=["Support", "Melee", "Fire", "Lightning"],
    ),
    GemInfo(
        name="Exemplar Support", required_level=31, is_support=True,
        tags=["Support", "Minion", "Critical"],
    ),
    GemInfo(
        name="Hallow Support", required_level=31, is_support=True,
        tags=["Support", "Melee"],
    ),
    # Renamed gem
    GemInfo(
        name="Multiple Projectiles Support", required_level=8, is_support=True,
        tags=["Support", "Projectile"],
    ),
]

# =========================================================================
# 3.28 Mirage — New Exceptional Support Gems (replace Awakened gems)
# Source: https://www.u4n.com/news/list-of-poe-exceptional-gems-supports-328.html
# =========================================================================

EXCEPTIONAL_SUPPORT_GEMS_328: list[GemInfo] = [
    GemInfo(name="Cooldown Recovery Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Frostmage Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Cold"]),
    GemInfo(name="Greater Spell Cascade Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Spell", "AoE"]),
    GemInfo(name="Voidstorm Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Foulgrasp Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Greater Multistrike Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Attack", "Melee"]),
    GemInfo(name="Hiveborn Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Minion"]),
    GemInfo(name="Hextoad Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Curse"]),
    GemInfo(name="Eclipse Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Bloodsoaked Banner Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Invert the Rules Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Cast on Ward Break Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Trigger"]),
    GemInfo(name="Vaal Sacrifice Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Vaal"]),
    GemInfo(name="Greater Spell Echo Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Spell"]),
    GemInfo(name="Vaal Temptation Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Vaal"]),
    GemInfo(name="Machinations Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Trap", "Mine"]),
    GemInfo(name="Pyre Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Fire"]),
    GemInfo(name="Bonespire Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Scornful Herald Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Cull the Weak Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Greater Ancestral Call Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Attack", "Melee"]),
    GemInfo(name="Fissure Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "AoE"]),
    GemInfo(name="Hexpass Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Curse"]),
    GemInfo(name="Greater Fork Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Projectile"]),
    GemInfo(name="Greater Chain Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Chaining"]),
    GemInfo(name="Lethal Dose Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Chaos"]),
    GemInfo(name="Companionship Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Minion"]),
    GemInfo(name="Divine Sentinel Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Annihilation Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Invention Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Greater Kinetic Instability Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Void Shockwave Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Eldritch Blasphemy Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Curse"]),
    GemInfo(name="Gluttony Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Overheat Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Fire"]),
    GemInfo(name="Congregation Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Minion"]),
    GemInfo(name="Greater Devour Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Minion"]),
    GemInfo(name="Greater Unleash Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Spell"]),
    GemInfo(name="Pacifism Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Minion Pact Support", required_level=72, is_support=True, tags=["Support", "Exceptional", "Minion"]),
    GemInfo(name="Unholy Trinity Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Overloaded Intensity Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
    GemInfo(name="Transfusion Support", required_level=72, is_support=True, tags=["Support", "Exceptional"]),
]

# =========================================================================
# 3.28 Mirage — Removed/Replaced Gems
# Awakened support gems can no longer be obtained (except Empower/Enlighten/Enhance)
# Lesser Multiple Projectiles renamed to Multiple Projectiles Support
# =========================================================================

REMOVED_GEM_NAMES_328: set[str] = {
    # Awakened gems replaced by Exceptional versions
    "Awakened Added Cold Damage Support",
    "Awakened Added Fire Damage Support",
    "Awakened Added Lightning Damage Support",
    "Awakened Ancestral Call Support",
    "Awakened Arrow Nova Support",
    "Awakened Blasphemy Support",
    "Awakened Brutality Support",
    "Awakened Burning Damage Support",
    "Awakened Cast On Critical Strike Support",
    "Awakened Cast While Channelling Support",
    "Awakened Chain Support",
    "Awakened Cold Penetration Support",
    "Awakened Controlled Destruction Support",
    "Awakened Deadly Ailments Support",
    "Awakened Decay Support",
    "Awakened Elemental Damage with Attacks Support",
    "Awakened Elemental Focus Support",
    "Awakened Fire Penetration Support",
    "Awakened Fork Support",
    "Awakened Generosity Support",
    "Awakened Greater Multiple Projectiles Support",
    "Awakened Hextouch Support",
    "Awakened Increased Area of Effect Support",
    "Awakened Lightning Penetration Support",
    "Awakened Melee Physical Damage Support",
    "Awakened Melee Splash Support",
    "Awakened Minion Damage Support",
    "Awakened Multistrike Support",
    "Awakened Spell Cascade Support",
    "Awakened Spell Echo Support",
    "Awakened Swift Affliction Support",
    "Awakened Unleash Support",
    "Awakened Unbound Ailments Support",
    "Awakened Void Manipulation Support",
    "Awakened Vicious Projectiles Support",
    # Renamed
    "Lesser Multiple Projectiles Support",
}


# =========================================================================
# 3.28 Mirage — Unique Item Changes (nerfs/buffs affecting build planning)
# Source: https://www.poewiki.net/wiki/Version_3.28.0
# =========================================================================

UNIQUE_CHANGES_328: list[str] = [
    "Ghostwrithe: ES cap reduced to 40% of max life (was 50%)",
    "The Red Dream: Max life scaling reduced to 50% (was 75%)",
    "The Green Dream: Max mana scaling reduced to 75% (was 100%)",
    "The Blue Dream: Max ES scaling reduced to 75% (was 100%)",
    "Hand of Thought and Motion: Int accuracy scaling reduced to 3% per 25 Int (was 5%)",
    "Choir of the Storm: Mana scaling now 1% per 4% overcapped lightning res (was 1% per 2%)",
    "Deidbell: Warcry buff effect reduced to 20-35% (was 25-50%)",
    "Doon Cuebiyari: Strength scaling ratios adjusted (nerfed)",
    "Berek's Respite: Ignite explosion on kill removed",
    "Reverberation Rod: Now uses Greater Spell Cascade (was Awakened Spell Cascade)",
    "Tulborn: Cold spell gem levels reduced to +2-3 (was +2-4)",
]

# =========================================================================
# 3.28 Mirage — Meta Build Tier List
# Source: https://maxroll.gg/poe/category/build-guides (scraped 2026-03-06)
# Used by the AI to recommend proven builds when users ask for suggestions
# =========================================================================

META_BUILDS_328: list[dict[str, str]] = [
    {
        "skill": "Penance Brand of Dissipation",
        "class": "Templar", "ascendancy": "Inquisitor",
        "tier": "S", "playstyle": "all-rounder",
        "notes": "Top bosser with strong map clear. Scales with cast speed and crit.",
    },
    {
        "skill": "Cyclone Shockwave",
        "class": "Duelist", "ascendancy": "Slayer",
        "tier": "S", "playstyle": "mapper, league starter",
        "notes": "Melee mapping powerhouse. Overleech sustain. Scales phys + impale.",
    },
    {
        "skill": "Kinetic Blast of Clustering",
        "class": "Witch", "ascendancy": "Necromancer",
        "tier": "S", "playstyle": "mapper, clearspeed",
        "notes": "Screen-wide explosions. Clearspeed king. Needs investment for bossing.",
    },
    {
        "skill": "Kinetic Fusillade Ballista",
        "class": "Templar", "ascendancy": "Hierophant",
        "tier": "S", "playstyle": "all-rounder, league starter",
        "notes": "New 3.28 gem. High boss DPS + solid clear via totems. Budget friendly.",
    },
    {
        "skill": "Holy Flame Totem",
        "class": "Templar", "ascendancy": "Hierophant",
        "tier": "A", "playstyle": "league starter, budget",
        "notes": "Reliable starter. Balance of damage, clear, and defence on a budget.",
    },
    {
        "skill": "Carrion Golems + Zombies",
        "class": "Witch", "ascendancy": "Necromancer",
        "tier": "A", "playstyle": "minion, all-rounder",
        "notes": "Classic minion build. Strong bossing, relaxed playstyle.",
    },
    {
        "skill": "Arakaali's Raise Spider",
        "class": "Witch", "ascendancy": "Occultist",
        "tier": "A", "playstyle": "minion, bosser",
        "notes": "Minion bosser. Requires Arakaali's Fang dagger (budget ~50c+).",
    },
    {
        "skill": "Elemental Hit of the Spectrum",
        "class": "Ranger", "ascendancy": "Deadeye",
        "tier": "A", "playstyle": "ranged, mapper",
        "notes": "Ranged ele scaling. Great clear with chain/fork. Deadeye proj scaling.",
    },
    {
        "skill": "Cyclone",
        "class": "Witch", "ascendancy": "Elementalist",
        "tier": "A", "playstyle": "melee, all-rounder",
        "notes": "Elemental Cyclone variant. Golems + Elementalist ele scaling.",
    },
    {
        "skill": "Poisonous Concoction of Bouncing",
        "class": "Ranger", "ascendancy": "Pathfinder",
        "tier": "A", "playstyle": "league starter, budget",
        "notes": "No weapon needed. Flask sustain via Pathfinder. Great starter.",
    },
    {
        "skill": "Lightning Arrow",
        "class": "Ranger", "ascendancy": "Deadeye",
        "tier": "A", "playstyle": "mapper, ranged",
        "notes": "Classic bow mapper. Scales with flat lightning + crit. Fast clear.",
    },
    {
        "skill": "Righteous Fire",
        "class": "Templar", "ascendancy": "Inquisitor",
        "tier": "A", "playstyle": "mapper, tanky, league starter",
        "notes": "Walk and burn. Extremely tanky. RF + Fire Trap for bossing.",
    },
    {
        "skill": "Toxic Rain",
        "class": "Ranger", "ascendancy": "Pathfinder",
        "tier": "B", "playstyle": "league starter, DoT",
        "notes": "Reliable DoT starter. Scales with gem levels + attack speed.",
    },
    {
        "skill": "Spark",
        "class": "Templar", "ascendancy": "Inquisitor",
        "tier": "A", "playstyle": "mapper, bosser",
        "notes": "Projectile spam. Scales with proj speed, duration, crit. Great in indoor maps.",
    },
    {
        "skill": "Summon Raging Spirits",
        "class": "Witch", "ascendancy": "Necromancer",
        "tier": "B", "playstyle": "minion, league starter",
        "notes": "Budget minion starter. Scales with gem levels + minion damage.",
    },
    {
        "skill": "Ice Shot",
        "class": "Ranger", "ascendancy": "Deadeye",
        "tier": "B", "playstyle": "mapper, ranged",
        "notes": "Cold bow build. Beautiful clear with herald of ice chains.",
    },
    {
        "skill": "Blade Vortex",
        "class": "Shadow", "ascendancy": "Assassin",
        "tier": "B", "playstyle": "mapper, poison",
        "notes": "Poison BV. Scales with poison duration + stack count. Plague Bearer combo.",
    },
]

# =========================================================================
# 3.28 Mirage — Key Balance & System Changes
# Injected into AI prompts so it understands the current meta context
# =========================================================================

PATCH_328_BALANCE_SUMMARY: str = """\
## 3.28 Mirage — Key Balance Changes

### New Ascendancy
- **Scion Reliquarian**: New ascendancy borrowing powers from unique items. Changes per league. \
Incompatible with Forbidden Flame/Flesh jewels.

### Awakened → Exceptional Gems
- ALL Awakened support gems replaced by Exceptional support gems (drop from endgame bosses, Lv 72+).
- Awakened Empower/Enlighten/Enhance still exist.
- Exceptional gems have different mechanics than their Awakened predecessors.

### Map System Overhaul
- Maps decoupled from specific areas — select map area via Atlas before activation.
- Astrolabes create "Shaped Regions" applying modifiers to map clusters.
- Voidstones upgrade minimum map tier to 16 within quadrants.
- Tier 17 maps become Nightmare Maps.
- Favoured Map system removed.
- Cartographer's Chisels removed; 20% map quality now gives +10% IIQ (was +20%).

### Unique Item Nerfs
- Ghostwrithe: ES cap 40% (was 50%)
- The Red Dream: Life scaling 50% (was 75%)
- Hand of Thought and Motion: Accuracy per Int halved
- Choir of the Storm: Mana scaling halved
- Deidbell: Warcry buff effect reduced
- Berek's Respite: Ignite explosion removed

### New Currency
- Coin of Knowledge, Coin of Power, Coin of Skill: Corrupt gems with support effects.
- Flesh of Xesht: Transforms Breach uniques to alternate forms.

### Meta Builds (3.28 Mirage League)
Top tier: Penance Brand Inquisitor, Cyclone Shockwave Slayer, Kinetic Blast Necromancer, \
Kinetic Fusillade Ballista Hierophant.
Strong: Holy Flame Totem Hierophant, Carrion Golems Necromancer, Elemental Hit Deadeye, \
RF Inquisitor, Spark Inquisitor, Poisonous Concoction Pathfinder.
Solid: Toxic Rain Pathfinder, SRS Necromancer, Blade Vortex Assassin, Lightning Arrow Deadeye.
"""


def get_supplement_gems() -> list[GemInfo]:
    """Return all supplement gems for the current patch."""
    return NEW_ACTIVE_GEMS_328 + NEW_SUPPORT_GEMS_328 + EXCEPTIONAL_SUPPORT_GEMS_328


def get_removed_gem_names() -> set[str]:
    """Return names of gems removed/replaced in the current patch."""
    return REMOVED_GEM_NAMES_328


def get_meta_builds() -> list[dict[str, str]]:
    """Return current meta build tier list."""
    return META_BUILDS_328


def get_balance_summary() -> str:
    """Return formatted balance summary for the current patch."""
    return PATCH_328_BALANCE_SUMMARY
