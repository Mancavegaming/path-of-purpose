"""Load skill-specific expert profiles for AI advisor context injection.

Profiles are JSON files in pop/ai/skill_profiles/ containing curated knowledge
from top build creators (Fubgun, Pohx, Kay, etc.) for each skill archetype.

Use "stale refresh" to trigger a review of all profiles against current patch notes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PROFILES_DIR = Path(__file__).parent / "skill_profiles"

# Cache: skill name (lowercase) -> profile dict
_cache: dict[str, dict] = {}
# Alias map: alias (lowercase) -> canonical skill name (lowercase)
_alias_map: dict[str, str] = {}


def _load_all() -> None:
    """Load all profile JSON files into the cache on first access."""
    if _cache:
        return

    if not _PROFILES_DIR.is_dir():
        logger.debug("No skill_profiles directory found at %s", _PROFILES_DIR)
        return

    for f in _PROFILES_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            skill_name = data.get("skill", "").lower()
            if not skill_name:
                continue
            _cache[skill_name] = data
            # Register aliases
            for alias in data.get("aliases", []):
                _alias_map[alias.lower()] = skill_name
        except Exception as e:
            logger.warning("Failed to load skill profile %s: %s", f.name, e)


def get_profile(skill_name: str) -> dict | None:
    """Look up a skill profile by name or alias.

    Returns the full profile dict or None if no match.
    """
    _load_all()
    key = skill_name.strip().lower()

    # Direct match
    if key in _cache:
        return _cache[key]

    # Alias match (full string)
    canonical = _alias_map.get(key)
    if canonical and canonical in _cache:
        return _cache[canonical]

    # Fuzzy: check if any profile skill name is contained in the query or vice versa
    for profile_key, profile in _cache.items():
        if profile_key in key or key in profile_key:
            return profile

    # Word-level alias/name matching — check each word in the query against aliases
    # and each multi-word alias against the query
    words = key.split()
    for word in words:
        if word in _alias_map and _alias_map[word] in _cache:
            return _cache[_alias_map[word]]
        if word in _cache:
            return _cache[word]
    # Check multi-word aliases as substrings of the query
    for alias, canonical_name in _alias_map.items():
        if alias in key and canonical_name in _cache:
            return _cache[canonical_name]

    return None


def format_profile_prompt(profile: dict) -> str:
    """Format a skill profile into a system prompt addendum for the AI."""
    lines: list[str] = []

    skill = profile.get("skill", "Unknown")
    expert = profile.get("expert_source", "Community")
    lines.append(f"\n\n--- EXPERT BUILD KNOWLEDGE: {skill} (source: {expert}) ---")

    # Ascendancy
    asc = profile.get("ascendancies", {})
    if asc:
        lines.append(f"\n## Ascendancy: {asc.get('top_pick', '?')}")
        if asc.get("alternatives"):
            lines.append(f"Alternatives: {', '.join(asc['alternatives'])}")
        if asc.get("notes"):
            lines.append(asc["notes"])

    # Gear priorities
    gear = profile.get("gear_priorities", {})
    if gear:
        lines.append("\n## Gear Priorities")
        for slot, advice in gear.items():
            lines.append(f"**{slot.replace('_', ' ').title()}**: {advice}")

    # Gem links
    gems = profile.get("gem_links", {})
    if gems:
        lines.append("\n## Gem Setup")
        if gems.get("main_6l"):
            lines.append(f"Main 6L: {' — '.join(gems['main_6l'])}")
        if gems.get("bossing_swap"):
            lines.append(f"Bossing swap: {gems['bossing_swap']}")
        if gems.get("auras"):
            aura_list = gems["auras"]
            lines.append(f"Auras: {', '.join(aura_list) if isinstance(aura_list, list) else aura_list}")
        for key in ("fire_trap_4l", "utility", "movement", "guard"):
            val = gems.get(key)
            if val:
                if isinstance(val, list):
                    lines.append(f"{key.replace('_', ' ').title()}: {' — '.join(val)}")
                else:
                    lines.append(f"{key.replace('_', ' ').title()}: {val}")

    # Tree priorities
    tree = profile.get("tree_priorities", [])
    if tree:
        lines.append("\n## Passive Tree Priorities")
        for item in tree:
            lines.append(f"- {item}")

    # Breakpoints
    bp = profile.get("breakpoints", [])
    if bp:
        lines.append("\n## Key Breakpoints")
        for item in bp:
            lines.append(f"- {item}")

    # Common mistakes
    mistakes = profile.get("common_mistakes", [])
    if mistakes:
        lines.append("\n## Common Mistakes to Watch For")
        for item in mistakes:
            lines.append(f"- {item}")

    # Scaling tips
    tips = profile.get("scaling_tips", "")
    if tips:
        lines.append(f"\n## Scaling Strategy\n{tips}")

    lines.append("\n--- END EXPERT BUILD KNOWLEDGE ---")
    lines.append(
        "Use this expert knowledge to evaluate the user's build. "
        "Reference specific gear, gem, and tree recommendations when advising. "
        "Flag any common mistakes you spot in their build."
    )

    return "\n".join(lines)


def get_skill_context(skill_name: str) -> str:
    """Get formatted AI context for a skill, or empty string if no profile exists."""
    profile = get_profile(skill_name)
    if not profile:
        return ""
    return format_profile_prompt(profile)
