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


def get_supplement_gems() -> list[GemInfo]:
    """Return all supplement gems for the current patch."""
    return NEW_ACTIVE_GEMS_328 + NEW_SUPPORT_GEMS_328 + EXCEPTIONAL_SUPPORT_GEMS_328


def get_removed_gem_names() -> set[str]:
    """Return names of gems removed/replaced in the current patch."""
    return REMOVED_GEM_NAMES_328
