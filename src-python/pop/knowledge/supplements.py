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


def get_boss_encounter_db() -> str:
    """Return boss encounter database for AI prompts."""
    return BOSS_ENCOUNTER_DB


def get_damage_mechanics_ref() -> str:
    """Return damage mechanics reference for AI prompts."""
    return DAMAGE_MECHANICS_REF


def get_atlas_strategy_ref() -> str:
    """Return atlas strategy and map mod reference for AI prompts."""
    return ATLAS_STRATEGY_REF


def get_map_mod_danger_ref() -> str:
    """Return map mod danger reference for AI prompts."""
    return MAP_MOD_DANGER_REF


# =========================================================================
# Boss & Endgame Encounter Database
# Used by AI to recommend defenses, DPS thresholds, and strategy per boss
# =========================================================================

BOSS_ENCOUNTER_DB: str = """\
## Boss & Endgame Encounter Reference

### Act Bosses (Leveling)
| Boss | Act | Key Mechanic | Damage Types | DPS Check | Tip |
|------|-----|-------------|-------------|-----------|-----|
| Merveil | 1 | Cold projectile nova | Cold, Phys | Low | Get cold res from coral ring |
| Vaal Oversoul | 2 | Slam + laser | Phys, Lightning | Low | Stay mobile, dodge slams |
| Dominus | 3 | Blood rain phase, touch of god | Phys, Lightning | ~5k DPS | Dodge touch, portal if needed |
| Malachai | 4 | Multi-phase, ground DoT | Phys, Chaos, Fire | ~8k DPS | Clear tentacles, avoid ground degens |
| Kitava (A5) | 5 | AoE slams, permanent -30% all res | Fire, Phys | ~15k DPS | Cap res AFTER the fight |
| Brine King | 6 | Cold cascades, adds | Cold, Phys | ~20k DPS | Keep moving, kill adds |
| Arakaali | 7 | Spinning laser, vaal rain | Chaos, Fire | ~25k DPS | Dodge laser, stay close |
| Solaris/Lunaris | 8 | Duo fight, alternating phases | Fire/Cold, Phys | ~30k DPS | Focus one at a time |
| Depraved Trinity | 9 | Multi-phase, each element | Phys, Ele | ~40k DPS | Bring all res capped |
| Kitava (A10) | 10 | Same as A5 but harder, -60% res total | Fire, Phys | ~60k DPS | Cap res to 75 AFTER kill |

### Map Bosses (Progression)
| Tier | Typical Boss DPS Needed | Life Target | Res Target | Notes |
|------|------------------------|-------------|------------|-------|
| T1-T5 | 100-300k | 4,000+ | 75/75/75 | Learn map layouts |
| T6-T10 | 300k-1M | 4,500+ | 75/75/75 | Map mods start mattering |
| T11-T13 | 1-2M | 5,000+ | 75/75/75 | Corrupted maps are dangerous |
| T14-T16 | 2-5M | 5,500+ | 75/75/75+ | Need layered defenses |

### Pinnacle Bosses
| Boss | Location | DPS Needed | EHP Needed | Key Mechanic | Counter |
|------|----------|-----------|------------|-------------|---------|
| Sirus, Awakener | Atlas | 2M+ | 5.5k+ life | Die beam (channeled), corridor, meteor maze | Flame Dash out, don't stand in storms |
| The Maven | Atlas | 3M+ | 5.5k+ life | Memory game, cascade of pain, brain phases | Practice memory, high DPS skips phases |
| Uber Elder | Shaper's Realm | 3M+ | 6k+ life | Shaper+Elder overlap, balls, slams | Stay close to Elder, dodge Shaper balls |
| The Shaper | Shaper's Realm | 2M+ | 5.5k+ life | Beam, slam, bullet hell, Zana phases | Dodge beam, hide in Zana bubble for bullet hell |
| The Elder | Elder's domain | 1.5M+ | 5k+ life | Ring phase, tentacle slam, adds | Kill adds fast, stay in ring |
| Uber Atziri | Alluring Abyss | 2M+ | 5.5k+ life | Split phase (reflect!), flameblast, storm calls | NO reflect builds, dodge flameblasts |
| Cortex (Venarius) | Synth map | 3M+ | 6k+ life | Phasing + clone phase, narrow arena | High mobility, burst during vulnerability |
| The Feared | Atlas | 5M+ | 6k+ life | All 5 bosses at once (Atziri, Elder, Shaper, Chayula, Cortex) | Single target DPS, avoid reflect from Atziri |
| The Formed | Atlas | 3M+ | 5.5k+ life | 3 Elder guardians simultaneously | AoE clear, dodge overlapping mechanics |
| The Twisted | Atlas | 3M+ | 5.5k+ life | 3 Shaper guardians simultaneously | AoE clear, high life/ES pool |
| The Hidden | Atlas | 3M+ | 5.5k+ life | 3 Breachlords simultaneously | Avoid Chayula darkness, AoE |
| The Forgotten | Atlas | 4M+ | 6k+ life | Synthesis bosses simultaneously | High burst, avoid ground effects |

### Uber Pinnacle Bosses (Hardest Content)
| Boss | DPS Needed | EHP Needed | Key Difference from Normal | Build Requirement |
|------|-----------|------------|---------------------------|-------------------|
| Uber Sirus | 10M+ | 7k+ life | Faster, more damage, smaller safe zones | Max spell suppression, high chaos res |
| Uber Maven | 10M+ | 7k+ life | Faster memory game, more cascades | Extremely high DPS to skip phases |
| Uber Shaper | 8M+ | 7k+ life | Bullet hell harder, beam wider | Capped spell suppression, high regen |
| Uber Elder | 10M+ | 7k+ life | Overlapping slams, faster phases | Need both high DPS AND tanky |
| Uber Atziri | 8M+ | 7k+ life | Split phase more deadly, tighter timing | Absolutely no reflect, max DPS |
| Uber Cortex | 10M+ | 7k+ life | Clone phase extremely dangerous | High burst windows, max mobility |

### Voidstone Progression (3.28 Map System)
1. **First Voidstone**: Kill any Tier 14+ map boss to unlock first shaped region
2. **Second Voidstone**: Defeat The Eater of Worlds or The Searing Exarch
3. **Third Voidstone**: Defeat the other Eldritch boss
4. **Fourth Voidstone**: Defeat Uber Elder
- Each Voidstone upgrades maps in a quadrant to T16
- Target: Get all 4 Voidstones before farming endgame content

### Boss Damage Type Summary (for defense planning)
- **Physical heavy**: Shaper slam, Elder tentacles, most map bosses
- **Cold heavy**: Merveil, Shaper beam, Elder Guardian (Purifier)
- **Fire heavy**: Kitava, Atziri, Searing Exarch
- **Lightning heavy**: Dominus, Eater of Worlds tentacles
- **Chaos heavy**: Arakaali, Al-Hezmin, Hunter influence
- **DoT/Degen heavy**: Shaper vortex balls, Maven cascade, Uber Elder ground
"""

# =========================================================================
# Damage Mechanics Reference
# Core PoE 1 damage math for the AI to reason about scaling
# =========================================================================

DAMAGE_MECHANICS_REF: str = """\
## PoE 1 Damage Mechanics Reference

### Damage Calculation Pipeline
```
Base Damage (weapon/gem)
  → + Flat Added Damage (gear, auras, supports)
  → × Damage Conversion (phys→ele chains)
  → × (1 + sum of all Increased%)
  → × product of all (1 + More%)
  → × Crit Multiplier (if crit)
  → × Enemy Resistance / Mitigation
  → × Hits per Second
  = DPS
```

### More vs Increased (CRITICAL DISTINCTION)
- **Increased** = additive with other "increased" sources. 100% increased + 50% increased = 150% total.
- **More** = multiplicative. Each "more" multiplier stacks multiplicatively. \
30% more × 40% more = 1.3 × 1.4 = 1.82x total.
- **Support gems give "more" multipliers** — this is why they are so powerful.
- **Passive tree and gear mostly give "increased"** — diminishing returns as you stack more.
- **Rule of thumb**: Prioritize "more" multipliers (supports, keystones) over stacking "increased" from passives.

### Damage Conversion Chains
- Conversion only goes in ONE direction: Physical → Lightning → Cold → Fire → Chaos
- You can skip steps (phys → fire via Avatar of Fire)
- 100% conversion = all damage benefits from BOTH the original and converted type's modifiers
- Common chains:
  - **Phys → Lightning**: Phys to Lightning Support (50%), Wrath aura
  - **Phys → Cold**: Hatred aura (25% of phys as extra cold), Hrimsorrow gloves (50% convert)
  - **Phys → Fire**: Avatar of Fire (50%), Chieftain ascendancy, Anger
  - **Full ele convert**: 100% phys → ele lets you ignore phys reflect, scale with penetration
  - **Eternity Shroud chaos**: Convert all to ele → extra chaos per Shaper item

### Critical Strike Scaling
- **Crit Chance** = Base × (1 + sum of Increased Crit%). Capped at 100%.
- **Crit Multiplier** = 150% base + sum of all crit multi sources
- **Effective Crit Multi** = (Crit Chance × Crit Multi) + ((1 - Crit Chance) × 100%)
- **When to invest in crit**: Only after you have 40%+ base crit chance. Below that, \
Elemental Overload or Resolute Technique is better.
- **Crit breakpoints**: At 50% crit, each 10% multi ≈ 5% more DPS. At 80% crit, \
each 10% multi ≈ 8% more DPS.
- **Power charges**: Each gives +40% increased crit chance. Assassin gets +2 max.
- **Brittle** (ground effect): Adds up to +15% BASE crit chance — extremely powerful.

### Attack Speed & Cast Speed
- **Attacks per second** = Base APS × (1 + sum of Increased Attack Speed%)
- More attacks = more DPS AND more life leech instances
- **Attack speed breakpoints**: For Cyclone, APS directly = DPS. For Multistrike, \
each attack fires 3 times at 75% more speed.
- **Cast speed** works identically for spells but doesn't affect trap/mine throwing speed.
- **Cooldown recovery** matters for triggered skills (CWDT, CoC) — 14% CDR is the first breakpoint \
for Cast on Crit builds.

### Ailment Mechanics
- **Ignite**: 50% of base fire hit over 4 seconds. Scales with fire/burning/DoT multi/damage over time.
- **Bleed**: 70% of base phys hit over 5 seconds (moving targets: 210%). Scales with phys/DoT multi.
- **Poison**: (8% phys + 0% chaos) of base hit per second for 2 seconds. Stacks infinitely. \
Scales with chaos/poison/DoT multi. Duration matters — longer poison = more stacks.
- **Shock**: Up to 50% increased damage taken. Threshold based on hit vs enemy max life.
- **Chill**: Up to 30% reduced action speed. Based on cold damage vs enemy max life.
- **Freeze**: Threshold = 5% of enemy max life in a single cold hit. Duration based on damage.
- **For ailment builds**: Stack flat damage + ailment multi + duration. \
Skill-specific: Deadly Ailments, Swift Affliction, Unbound Ailments.

### Penetration & Exposure
- **Penetration** (attacks/spells): Ignores % of enemy resistance. Only applies to hits, NOT DoT.
  - Fire Pen Support (37%), Lightning Pen Support (37%), Cold Pen Support (37%)
  - Inquisitor ascendancy: Inevitable Judgement ignores ALL ele res on crit
- **Exposure**: Reduces enemy resistance by flat amount (typically -10% to -25%)
  - Wave of Conviction: -25% to the highest element hit
  - Frost Bomb: -25% cold res
  - Hydrosphere: -10% cold/lightning
  - Scorching Ray: Up to -25% fire res
- **Curses**: Flammability/Frostbite/Conductivity reduce enemy res by 29-44%
  - Most bosses have 33% less curse effect
  - Multiple curses require Whispers of Doom anoint or curse limit sources
- **Against bosses**: Typical boss has 40% elemental resistance, 25% chaos resistance. \
Pinnacle bosses may have higher.

### Defensive Mechanics
- **Armour**: Reduces physical hit damage. Formula: DR = Armour / (Armour + 5 × Damage). \
More armour needed vs bigger hits. 30k armour reduces 5k hit by ~50%, but only 23% of a 30k hit.
- **Evasion**: Entropy-based dodge. 50% evasion = dodge every other attack (not random). \
Does NOT work against spells.
- **Block**: Chance to block attacks (and spells with Glancing Blows or Gladiator). \
75% cap. Blocked hit does 0 damage (or 65% with Glancing Blows).
- **Spell Suppression**: 50% reduced spell damage taken when suppressed. 100% suppress chance = \
permanent 50% less spell damage. Dex-based gear and tree.
- **Endurance Charges**: +4% phys DR and +4% ele res per charge. 3 base max.
- **Fortify**: 20% reduced hit damage taken. Melee attacks generate fortification stacks.
- **Guard Skills**: Steelskin (flat absorb), Molten Shell (armour-scaled absorb), \
Immortal Call (brief phys immunity, consumes endurance charges). Use with CWDT for automation.
- **Max Resistance**: Default 75%. Each +1% max res = 4% less ele damage taken. \
Extremely valuable: +5% max res ≈ 20% less ele damage.
- **Chaos Resistance**: Often neglected. -60% default. Target: 0% for maps, +30% for endgame.

### Aura Efficiency
| Aura | Mana Reserved | Best For | Notes |
|------|-------------|----------|-------|
| Hatred | 50% | Phys→Cold, melee/bow | 25% phys as extra cold + 18% more cold |
| Anger | 50% | Fire attacks, flat fire | Flat added fire to attacks |
| Wrath | 50% | Lightning attacks/spells | Flat added lightning + 13% more spell lightning |
| Determination | 50% | Armour stacking | +2k flat armour + 56% more armour |
| Grace | 50% | Evasion stacking | +3k flat evasion + 30% more evasion |
| Discipline | 35% | ES builds | Flat ES + ES recharge |
| Defiance Banner | 10% | Universal defense | +21% armour/evasion, less crit damage taken |
| Precision | 22-100 flat | Attack crit | Flat accuracy + crit chance. Keep low level. |
| Herald of Ash | 25% | Fire/phys | Overkill fire burn, 15% phys as extra fire |
| Herald of Ice | 25% | Cold/crit mapper | Shatter explosions for clear |
| Herald of Purity | 25% | Phys melee | Flat phys + sentinels |
| Zealotry | 50% | Spell crit | 15% more spell damage + crit |
| Haste | 50% | Speed builds | 16% attack/cast/move speed |
| Purity of Elements | 50% | Res fix | +34% all res + ailment immunity |
| Vitality | 35% | Regen builds | Life regen/second |
| Malevolence | 50% | DoT builds | 20% more DoT + skill duration |
| Pride | 50% | Phys melee | Nearby enemies take more phys (ramps to 39%) |

### Clear Speed Scaling
- **AoE**: Area of Effect increases — Increased AoE Support (mapping), Concentrated Effect (bossing swap)
- **Chain/Pierce/Fork**: Projectile skills need one of these for clear
  - Chain: hits additional enemies (good with Herald of Ice)
  - Pierce: passes through enemies (good for linear skills like Tornado Shot)
  - Fork: splits into 2 — less reliable but higher potential spread
- **Explosions**: Profane Bloom (Occultist), Gratuitous Violence (Gladiator), Inpulsa's, \
Herald of Ice shatter chains — best clear mechanic in the game
- **Movement speed**: 30%+ move speed from boots + Quicksilver Flask + Onslaught. \
Faster movement = faster map clear.
- **Skill range**: Cyclone range = AoE investment. Bow range = proj speed. Spell range = AoE/proj.

### Cluster Jewels (Endgame Optimization)
- **Large cluster** (outer socket): 8-12 passives, 2 jewel sockets, weapon/spell/elemental/physical notables
- **Medium cluster** (middle socket): 4-6 passives, 1 jewel socket, specific mechanic notables
- **Small cluster** (inner socket): 2-3 passives, life/ES/resistance focused
- **Key notables by build type**:
  - Melee: Feed the Fury (attack leech), Fuel the Fight (mana leech), Martial Prowess
  - Spells: Scintillating Idea (mana), Conjured Wall (ES), Arcane Adept
  - Minions: Renewal (minion life), Feasting Fiends (minion leech), Rotten Claws (minion crit)
  - DoT: Wasting Affliction, Brush with Death, Flow of Life
  - Crit: Pressure Points, Quick Getaway, Magnifier
  - Defense: Enduring Composure (endurance charges), Fettle (life), Surging Vitality (life regen)
"""

# =========================================================================
# Atlas Strategy Reference (3.28 Map System)
# Used by AI to recommend atlas passive strategies and progression plans
# =========================================================================

ATLAS_STRATEGY_REF: str = """\
## Atlas Strategy Reference (3.28 Mirage)

### Atlas Passive Tree — Strategy Archetypes
Choose ONE primary strategy and support it with atlas passives. Don't spread points thin.

| Strategy | Best For | Key Atlas Passives | Currency/Hour |
|----------|---------|-------------------|---------------|
| **Essence Farming** | League start, SSF | Essence nodes (top-left) | Medium |
| **Strongbox** | Easy mapping, passive income | Strongbox nodes, Ambush | Medium |
| **Harvest** | Crafting-focused | Harvest nodes (center-left) | High (craft value) |
| **Legion** | Fast clear builds | Legion nodes (bottom-right), monolith duration | High |
| **Breach** | High-DPS builds | Breach nodes, Breachstone upgrades | Medium-High |
| **Delirium** | Tanky + high DPS | Delirium nodes, reward type focus | Very High |
| **Expedition** | Any build | Expedition nodes, logbook drops | High |
| **Ritual** | Tanky builds | Ritual nodes, tribute bonuses | Medium |
| **Blight** | Builds with good AoE | Blight nodes, anointed maps | Medium |
| **Heist** | Any build (separate content) | Not atlas — run blueprints/contracts | Very High |
| **Boss Rush** | High DPS, boss killers | Map boss nodes, guardian/conqueror drops | High |
| **Scarab Farming** | Fast mappers | Scarab-related nodes, monster pack size | High |

### Atlas Progression Path
1. **T1-T5 (Just entered maps)**: Run any maps. Complete bonus objectives. \
Allocate atlas passives into your chosen strategy. Unlock Kirac missions.
2. **T6-T10 (Building atlas)**: Focus on map completion for bonus objectives. \
Start using scarabs and map device crafts. Build toward first Voidstone.
3. **T11-T13 (Approaching red maps)**: Use alchemy + vaal on maps. \
Run Kirac missions for completion. Target conqueror/elder guardian maps.
4. **T14-T16 (Red maps)**: Farm your chosen strategy hard. \
Acquire first 2 Voidstones (Eater of Worlds + Searing Exarch). \
Shaped Regions bonus active.
5. **T16 (All Voidstones)**: All maps are T16. Focus purely on your \
chosen atlas strategy with fully juiced maps. Run Uber bosses for profit.

### Shaped Regions (3.28 NEW)
- Astrolabes create shaped regions that apply modifiers to map clusters
- Place astrolabes strategically to boost your farming strategy
- Example: Place astrolabe on Essence cluster for +1 essence tier in those maps

### Map Juicing (Endgame Profit)
| Method | Effect | Cost | Best With |
|--------|--------|------|-----------|
| Alchemy + Vaal | Corruption for +1 map tier, 8-mod rare | Low | Everything |
| Scarabs | Targeted league mechanic spawns | Medium | Your atlas strategy |
| Sextants | Modifiers to Voidstones (area bonuses) | Medium | Specific strategies |
| Map Device Craft | Ambush, Fortune, Domination, etc. | Low-Medium | Depends |
| Delirium Orbs | Fog + rewards in any map | High | Tanky fast builds |
| Beyond | Extra monsters → more drops | Medium | Fast clear builds |

### Kirac Missions
- Free map sustain — always run Kirac missions
- Can complete atlas bonus objectives via Kirac
- Kirac's shop resets after each mission
- Some missions guarantee unique maps (good for completion)

### Atlas Keystone Considerations
| Keystone | Effect | Good For | Bad For |
|----------|--------|----------|---------|
| **Singular Focus** | Non-favoured maps drop as currency | Target farming | Map completion |
| **Wandering Path** | 50% more atlas passive effect, no notables | Generic strategies | Specific strategies |
| **Shadow of the Vaal** | Vaal side areas more common/rewarding | Vaal fragment farming | Nothing specific |
"""

# =========================================================================
# Map Mod Danger Reference
# Which map mods are dangerous or impossible for specific build types
# =========================================================================

MAP_MOD_DANGER_REF: str = """\
## Map Mod Danger Reference

### CANNOT RUN (reroll these mods for your build)
| Map Mod | Dangerous For | Why |
|---------|---------------|-----|
| **Elemental Reflect** | ALL elemental damage builds | Reflects % of ele damage back — instant death |
| **Physical Reflect** | ALL physical damage builds | Reflects % of phys damage back — instant death |
| **No Leech** | Leech-dependent builds (Slayer, Vaal Pact) | Completely disables life/mana leech |
| **No Regen** | RF, regen-dependent, MoM builds | Disables all life/mana/ES regeneration |
| **Cannot inflict Ailments** | Ignite, Poison, Bleed builds | Your main damage source does nothing |
| **Monsters are Hexproof** | Curse-dependent builds (Occultist) | Curses have no effect on monsters |

### DANGEROUS (run with caution)
| Map Mod | Dangerous For | Mitigation |
|---------|---------------|-----------|
| **-max res** | All builds | Each -1% max res = ~4% more ele damage taken. -12% = very dangerous. |
| **Extra damage as [element]** | Low-res builds | Stack res above 75%, or avoid |
| **Extra crit / crit multi** | Low EHP builds | Monsters can one-shot. Need high life + crit reduction |
| **Reduced flask charges** | Flask-dependent builds (Pathfinder) | Less recovery, less utility uptime |
| **Monsters have % phys as extra [ele]** | Low res builds | Combined with -max res = rippy |
| **Increased monster speed** | Slow builds | Harder to dodge, faster attacks |
| **Reduced block chance** | Block-based builds (Gladiator) | Major defense layer gutted |
| **Less armour/evasion** | Armour/evasion stackers | Major defense layer reduced |
| **Temporal Chains** | All builds | Slower clear, less DPS (less attack/cast speed) |
| **Monsters steal charges** | Charge-dependent builds | Power/frenzy charges stolen on hit |

### PROFITABLE / SAFE TO RUN
| Map Mod | Effect | Notes |
|---------|--------|-------|
| **Increased monster pack size** | More monsters = more drops | ALWAYS run if possible — best quantity mod |
| **Extra magic/rare monsters** | More drops, more XP | Slightly harder but very profitable |
| **Area has increased monster variety** | Cosmetic mostly | Free quantity |
| **Increased item quantity/rarity** | Direct profit boost | Always run |
| **Monsters have % chance to avoid ailments** | Minor annoyance | Usually fine for non-ailment builds |

### Build-Specific Mod Interactions
| Build Archetype | Must Avoid | Careful With | Safe to Run |
|----------------|-----------|-------------|-------------|
| **Physical melee** (Cyclone, Blade Flurry) | Phys reflect | No leech, -max res | Ele reflect, hexproof |
| **Elemental attack** (Ele Hit, LA) | Ele reflect | No leech, -max res, extra crit | Phys reflect |
| **Spell caster** (Spark, Arc) | Ele reflect | No regen (if MoM), -max res | Phys reflect |
| **DoT/Ailment** (RF, Poison, Ignite) | No ailments (if ailment), no regen (if RF) | -max res | Reflect (DoT doesn't reflect) |
| **Minion** (SRS, Golems, Spectres) | - | Reduced minion speed/life | Reflect, hexproof, most mods |
| **Totem** (HFT, Ballista) | - | Reduced totem life | Reflect (totems take it, not you) |
| **Trapper/Miner** | - | Reduced flask charges | Reflect, most mods |
| **CI/Low-life** | No regen (if ES regen), no leech | Chaos damage mods | Phys/ele reflect (if ES) |

### Map Rolling Strategy
1. **Alch and go** (budget): Alchemy orb → check for "cannot run" mods → run
2. **Chisel + alch + vaal** (standard): 20% quality first → alch → vaal for chance at 8-mod
3. **Reroll bad mods**: Use chaos orbs or scour+alch if you hit "cannot run" mods
4. **8-mod corrupted maps**: Very dangerous but high rewards. Only run if build handles all mods.
5. **Quantity threshold**: Aim for 80%+ IIQ on red maps for good returns

### Sextant Strategy
- Apply sextants to Voidstones for area modifiers
- Stack with scarabs for multiplicative effect
- Popular combos: Beyond + pack size, Breach + Breach scarabs, Legion + monolith duration
"""
