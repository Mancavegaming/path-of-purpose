"""
Dynamic gem stat loader from RePoE data.

Fetches and caches the full RePoE gems.min.json, then extracts
per-level stats for active and support gems. Falls back to the
hardcoded gem_data.py database when data is unavailable.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from pop.calc.gem_data import ActiveGemStats, SupportGemEffect, get_active_gem_stats, get_support_effect
from pop.calc.mod_parser import ParsedMods, parse_mods
from pop.calc.models import DamageType, Modifier

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "knowledge" / "cache"
REPOE_GEMS_CACHE = CACHE_DIR / "repoe_gems.json"

# Regex to extract base damage from stat_text values
# "Deals X to Y <type> Damage"
_RE_DEALS_DAMAGE = re.compile(
    r"Deals (\d+) to (\d+) (Physical|Fire|Cold|Lightning|Chaos) Damage",
    re.IGNORECASE,
)

_DTYPE_MAP: dict[str, DamageType] = {
    "physical": DamageType.PHYSICAL,
    "fire": DamageType.FIRE,
    "cold": DamageType.COLD,
    "lightning": DamageType.LIGHTNING,
    "chaos": DamageType.CHAOS,
}

# Tag-based attack/spell detection
_ATTACK_TAGS = {"Attack", "Melee", "RangedAttack"}
_SPELL_TAGS = {"Spell"}


class RePoEGemDB:
    """Dynamic gem database loaded from RePoE gems.min.json."""

    def __init__(self) -> None:
        self._raw: dict | None = None
        self._gem_index: dict[str, dict] = {}  # display_name -> gem entry
        self._loaded = False

    def load_from_cache(self) -> bool:
        """Load from local cache. Returns True if successful."""
        if not REPOE_GEMS_CACHE.exists():
            return False
        try:
            self._raw = json.loads(REPOE_GEMS_CACHE.read_text(encoding="utf-8"))
            self._build_index()
            self._loaded = True
            logger.info("Loaded %d gems from RePoE cache", len(self._gem_index))
            return True
        except Exception as e:
            logger.warning("Failed to load RePoE gem cache: %s", e)
            return False

    def load_from_dict(self, data: dict) -> None:
        """Load from an already-fetched dict (for use after async fetch)."""
        self._raw = data
        self._build_index()
        self._loaded = True

    def save_to_cache(self) -> None:
        """Save the raw data to local cache."""
        if self._raw is None:
            return
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        REPOE_GEMS_CACHE.write_text(
            json.dumps(self._raw, separators=(",", ":")),
            encoding="utf-8",
        )

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def _lookup_gem(self, name: str) -> dict | None:
        """Look up gem by name with Support suffix fallback."""
        if not self._loaded:
            return None
        entry = self._gem_index.get(name)
        if entry is not None:
            return entry
        # PoB often strips "Support" suffix from support gem names
        if not name.endswith(" Support"):
            entry = self._gem_index.get(name + " Support")
            if entry is not None:
                return entry
        return None

    def _build_index(self) -> None:
        """Build display_name -> gem entry index."""
        if not self._raw:
            return
        self._gem_index.clear()
        for _key, entry in self._raw.items():
            if not isinstance(entry, dict):
                continue
            bi = entry.get("base_item", {})
            if not isinstance(bi, dict):
                continue
            if bi.get("release_state") != "released":
                continue
            name = bi.get("display_name", "") or entry.get("display_name", "")
            if name and name not in self._gem_index:
                self._gem_index[name] = entry

    def get_active_stats(self, name: str, level: int = 20) -> ActiveGemStats | None:
        """Get active gem stats from RePoE data.

        Falls back to hardcoded gem_data if not found in RePoE.
        """
        entry = self._lookup_gem(name)
        if entry is None or entry.get("is_support"):
            return get_active_gem_stats(name)

        # Determine attack vs spell from tags
        types = []
        active_skill = entry.get("active_skill", {})
        if isinstance(active_skill, dict):
            types = active_skill.get("types", [])
        tags_list = entry.get("tags", [])

        is_attack = bool(_ATTACK_TAGS & set(types))
        is_spell = bool(_SPELL_TAGS & set(types)) and not is_attack

        # Base damage from per_level stat_text
        base_damage: dict[DamageType, float] = {}
        per_level = entry.get("per_level", {})
        level_data = per_level.get(str(level), per_level.get("20", {}))
        stat_text = level_data.get("stat_text", {}) if isinstance(level_data, dict) else {}

        if isinstance(stat_text, dict):
            for _stat_ids, text in stat_text.items():
                if not isinstance(text, str):
                    continue
                for m in _RE_DEALS_DAMAGE.finditer(text):
                    dtype = _DTYPE_MAP.get(m.group(3).lower())
                    if dtype:
                        avg = (float(m.group(1)) + float(m.group(2))) / 2.0
                        base_damage[dtype] = base_damage.get(dtype, 0.0) + avg

        # Crit chance (static, in hundredths: 600 = 6.00%)
        static = entry.get("static", {})
        raw_crit = static.get("crit_chance") if isinstance(static, dict) else None
        base_crit = raw_crit / 100.0 if isinstance(raw_crit, (int, float)) and raw_crit > 0 else 5.0

        # Damage effectiveness (static, percent points: 80 = 0.80)
        raw_eff = static.get("damage_effectiveness") if isinstance(static, dict) else None
        damage_effectiveness = (raw_eff / 100.0 if isinstance(raw_eff, (int, float)) and raw_eff > 0
                                else 1.0)

        # Cast time (root level, in milliseconds: 700 = 0.7s)
        raw_cast = entry.get("cast_time")
        base_cast_time = raw_cast / 1000.0 if isinstance(raw_cast, (int, float)) and raw_cast > 0 else 1.0

        # Attack speed multiplier — not directly in RePoE for most attacks
        # Fall back to hardcoded if available
        hardcoded = get_active_gem_stats(name)
        attack_speed_multiplier = hardcoded.attack_speed_multiplier if hardcoded else 1.0

        # Lowercase tags for consistency
        tag_strings = [t.lower() for t in types] if types else [t.lower() for t in tags_list]

        return ActiveGemStats(
            name=name,
            tags=tag_strings,
            is_attack=is_attack,
            is_spell=is_spell,
            base_damage=base_damage,
            base_crit=base_crit,
            base_cast_time=base_cast_time,
            damage_effectiveness=damage_effectiveness,
            attack_speed_multiplier=attack_speed_multiplier,
        )

    def get_support_stats(self, name: str, level: int = 20) -> SupportGemEffect | None:
        """Get support gem effects from RePoE data.

        Parses the stat_text at the given level through mod_parser,
        then falls back to hardcoded data for values we can't parse.
        """
        entry = self._lookup_gem(name)
        if entry is None or not entry.get("is_support"):
            return get_support_effect(name)

        per_level = entry.get("per_level", {})
        level_data = per_level.get(str(level), per_level.get("20", {}))
        stat_text = level_data.get("stat_text", {}) if isinstance(level_data, dict) else {}

        # Also collect static stat_text (constant effects)
        static = entry.get("static", {})
        static_text = static.get("stat_text", {}) if isinstance(static, dict) else {}

        # Combine all stat texts
        all_texts: list[str] = []
        for text_dict in (stat_text, static_text):
            if isinstance(text_dict, dict):
                for _ids, text in text_dict.items():
                    if isinstance(text, str):
                        all_texts.append(text)

        # Parse through mod_parser
        parsed = parse_mods(all_texts, source=f"gem:{name}")

        # Build SupportGemEffect
        modifiers: list[Modifier] = []
        modifiers.extend(parsed.more)
        modifiers.extend(parsed.increased)

        added_damage: dict[DamageType, float] = {}
        for dtype, val in parsed.flat_added.items():
            added_damage[dtype] = val
        for dtype, val in parsed.flat_added_attacks.items():
            added_damage[dtype] = added_damage.get(dtype, 0.0) + val
        for dtype, val in parsed.flat_added_spells.items():
            added_damage[dtype] = added_damage.get(dtype, 0.0) + val

        attack_speed_mod = parsed.increased_attack_speed
        less_attack_speed = parsed.less_attack_speed[0] if parsed.less_attack_speed else 0.0

        effect = SupportGemEffect(
            name=name,
            modifiers=modifiers,
            added_damage=added_damage,
            attack_speed_mod=attack_speed_mod,
            less_attack_speed=less_attack_speed,
        )

        # If we got nothing useful from RePoE, fall back to hardcoded
        if not modifiers and not added_damage and not attack_speed_mod:
            hardcoded = get_support_effect(name)
            if hardcoded:
                return hardcoded

        return effect

    def get_gem_names(self) -> list[str]:
        """Return all known gem names."""
        return list(self._gem_index.keys())


# Module-level singleton
_db: RePoEGemDB | None = None


def get_repoe_db() -> RePoEGemDB:
    """Get the module-level RePoE gem database, loading from cache if needed."""
    global _db
    if _db is None:
        _db = RePoEGemDB()
        _db.load_from_cache()
    return _db


def set_repoe_db(db: RePoEGemDB) -> None:
    """Set the module-level RePoE gem database (for testing or after async fetch)."""
    global _db
    _db = db


def clear_repoe_cache() -> None:
    """Clear the module-level DB (for testing)."""
    global _db
    _db = None
