"""
Regex-based modifier parser for PoE item/gem/tree mod text.

Extracts structured Modifier objects from English mod strings found in
PoB exports, trade listings, and passive tree node descriptions.
"""

from __future__ import annotations

import re

from pop.calc.models import ConversionEntry, DamageType, ModCategory, Modifier

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DTYPE_MAP: dict[str, DamageType] = {
    "physical": DamageType.PHYSICAL,
    "fire": DamageType.FIRE,
    "cold": DamageType.COLD,
    "lightning": DamageType.LIGHTNING,
    "chaos": DamageType.CHAOS,
}

_ELE_TYPES = [DamageType.FIRE, DamageType.COLD, DamageType.LIGHTNING]
_ALL_TYPES = list(DamageType)


def _resolve_types(type_word: str) -> list[DamageType]:
    """Resolve a damage type keyword to a list of DamageType values."""
    word = type_word.lower().strip()
    if word in _DTYPE_MAP:
        return [_DTYPE_MAP[word]]
    if word == "elemental":
        return _ELE_TYPES[:]
    return []  # generic / all


# ---------------------------------------------------------------------------
# Flat added damage patterns
# ---------------------------------------------------------------------------

# "Adds X to Y <type> Damage" (weapon local)
_RE_FLAT_ADDED = re.compile(
    r"Adds (\d+) to (\d+) (Physical|Fire|Cold|Lightning|Chaos) Damage",
    re.IGNORECASE,
)

# "Adds X to Y <type> Damage to Attacks"
_RE_FLAT_ADDED_ATTACKS = re.compile(
    r"Adds (\d+) to (\d+) (Physical|Fire|Cold|Lightning|Chaos) Damage to Attacks",
    re.IGNORECASE,
)

# "Adds X to Y <type> Damage to Spells"
_RE_FLAT_ADDED_SPELLS = re.compile(
    r"Adds (\d+) to (\d+) (Physical|Fire|Cold|Lightning|Chaos) Damage to Spells",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Increased damage patterns
# ---------------------------------------------------------------------------

# "X% increased <type> Damage"
_RE_INCREASED_TYPED = re.compile(
    r"(\d+)% increased (Physical|Fire|Cold|Lightning|Chaos|Elemental) Damage",
    re.IGNORECASE,
)

# "X% increased Damage" (generic)
_RE_INCREASED_GENERIC = re.compile(
    r"(\d+)% increased Damage(?!\s+(?:with|over|taken))",
    re.IGNORECASE,
)

# "X% increased Attack Damage"
_RE_INCREASED_ATTACK = re.compile(
    r"(\d+)% increased Attack Damage",
    re.IGNORECASE,
)

# "X% increased Spell Damage"
_RE_INCREASED_SPELL = re.compile(
    r"(\d+)% increased Spell Damage",
    re.IGNORECASE,
)

# "X% increased Melee Damage"
_RE_INCREASED_MELEE = re.compile(
    r"(\d+)% increased Melee Damage",
    re.IGNORECASE,
)

# "X% increased Projectile Damage"
_RE_INCREASED_PROJECTILE = re.compile(
    r"(\d+)% increased Projectile Damage",
    re.IGNORECASE,
)

# "X% increased Area Damage"
_RE_INCREASED_AREA = re.compile(
    r"(\d+)% increased Area Damage",
    re.IGNORECASE,
)

# Weapon-type specific: "X% increased Damage with <weapon>"
_RE_INCREASED_WEAPON_TYPE = re.compile(
    r"(\d+)% increased (?:Physical )?Damage with "
    r"(Swords?|Axes?|Maces?|Staves?|Daggers?|Claws?|Wands?|Bows?|Two Handed Weapons?)",
    re.IGNORECASE,
)

# "X% increased Damage with Hits"
_RE_INCREASED_HITS = re.compile(
    r"(\d+)% increased Damage with Hits",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# More damage patterns
# ---------------------------------------------------------------------------

# "X% more <type> Damage"
_RE_MORE_TYPED = re.compile(
    r"(\d+)% more (Physical|Fire|Cold|Lightning|Chaos|Elemental) Damage",
    re.IGNORECASE,
)

# "X% more Damage"
_RE_MORE_GENERIC = re.compile(
    r"(\d+)% more Damage(?!\s+(?:with|over|taken))",
    re.IGNORECASE,
)

# "X% more Attack Damage"
_RE_MORE_ATTACK = re.compile(
    r"(\d+)% more Attack Damage",
    re.IGNORECASE,
)

# "X% more Spell Damage"
_RE_MORE_SPELL = re.compile(
    r"(\d+)% more Spell Damage",
    re.IGNORECASE,
)

# "X% more Melee Damage" / "X% more Melee Physical Damage"
_RE_MORE_MELEE = re.compile(
    r"(\d+)% more Melee(?: Physical)? Damage",
    re.IGNORECASE,
)

# "X% more Projectile Damage"
_RE_MORE_PROJECTILE = re.compile(
    r"(\d+)% more Projectile Damage",
    re.IGNORECASE,
)

# "X% more Area Damage"
_RE_MORE_AREA = re.compile(
    r"(\d+)% more Area Damage",
    re.IGNORECASE,
)

# "Deals X% more Damage with Hits" (some support wording)
_RE_MORE_HITS = re.compile(
    r"(?:Deals )?(\d+)% more Damage with Hits",
    re.IGNORECASE,
)

# "X% less <type> Damage" / "X% less Damage" — treated as negative more
_RE_LESS_TYPED = re.compile(
    r"(\d+)% less (Physical|Fire|Cold|Lightning|Chaos|Elemental) Damage",
    re.IGNORECASE,
)

_RE_LESS_GENERIC = re.compile(
    r"(\d+)% less Damage(?!\s+(?:with|over|taken))",
    re.IGNORECASE,
)

# "X% less Attack Speed" — negative more speed
_RE_LESS_ATTACK_SPEED = re.compile(
    r"(\d+)% less Attack Speed",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Conversion patterns
# ---------------------------------------------------------------------------

# "X% of Physical Damage Converted to <type> Damage"
_RE_CONVERSION = re.compile(
    r"(\d+)% of (Physical|Fire|Cold|Lightning) Damage Converted to "
    r"(Fire|Cold|Lightning|Chaos) Damage",
    re.IGNORECASE,
)

# "Gain X% of <type> Damage as Extra <type> Damage"
# Also matches "X% of <type> Damage as Extra <type> Damage" (no Gain prefix)
_RE_GAINED_AS = re.compile(
    r"(?:Gain )?(\d+)% of (Physical|Fire|Cold|Lightning) Damage as Extra "
    r"(Fire|Cold|Lightning|Chaos) Damage",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Penetration patterns
# ---------------------------------------------------------------------------

# "Penetrates X% <type> Resistance"
_RE_PENETRATION = re.compile(
    r"Penetrates (\d+)% (Fire|Cold|Lightning|Elemental|Chaos) Resistance",
    re.IGNORECASE,
)

# "Damage Penetrates X% <type> Resistance"
_RE_PENETRATION2 = re.compile(
    r"Damage Penetrates (\d+)% (Fire|Cold|Lightning|Elemental|Chaos) Resistance",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Exposure patterns
# ---------------------------------------------------------------------------

# "Exposure applies -X% to <type> Resistance" or
# "apply <type> Exposure" (typically -10% default in PoE)
_RE_EXPOSURE_VALUE = re.compile(
    r"Exposure applies an additional (-?\d+)% to (Fire|Cold|Lightning|Elemental) Resistance",
    re.IGNORECASE,
)

# "<type> Exposure on Hit, applying -X% to <type> Resistance"
_RE_EXPOSURE_ON_HIT = re.compile(
    r"(Fire|Cold|Lightning) Exposure on Hit,? applying (-?\d+)% to "
    r"(?:Fire|Cold|Lightning) Resistance",
    re.IGNORECASE,
)

# "-X% to <type> Resistance" (from curses, debuffs — treated as exposure-like)
_RE_RESIST_REDUCTION = re.compile(
    r"Nearby Enemies have (-?\d+)% to (Fire|Cold|Lightning|Elemental|All Elemental) Resistance",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Damage over Time patterns
# ---------------------------------------------------------------------------

# "X% increased Damage over Time"
_RE_INCREASED_DOT = re.compile(
    r"(\d+)% increased Damage over Time",
    re.IGNORECASE,
)

# "X% increased Burning Damage"
_RE_INCREASED_BURNING = re.compile(
    r"(\d+)% increased Burning Damage",
    re.IGNORECASE,
)

# "X% increased <type> Damage over Time"
_RE_INCREASED_DOT_TYPED = re.compile(
    r"(\d+)% increased (Physical|Fire|Cold|Lightning|Chaos) Damage over Time",
    re.IGNORECASE,
)

# "X% more Damage over Time"
_RE_MORE_DOT = re.compile(
    r"(\d+)% more Damage over Time",
    re.IGNORECASE,
)

# "X% more Burning Damage"
_RE_MORE_BURNING = re.compile(
    r"(\d+)% more Burning Damage",
    re.IGNORECASE,
)

# "+X% to Damage over Time Multiplier"
_RE_DOT_MULTI = re.compile(
    r"\+(\d+)% to Damage over Time Multiplier",
    re.IGNORECASE,
)

# "+X% to <type> Damage over Time Multiplier"
_RE_DOT_MULTI_TYPED = re.compile(
    r"\+(\d+)% to (Fire|Physical|Chaos) Damage over Time Multiplier",
    re.IGNORECASE,
)

# "X% increased Damage with Ailments"
_RE_INCREASED_AILMENT = re.compile(
    r"(\d+)% increased Damage with Ailments",
    re.IGNORECASE,
)

# "X% more Damage with Ailments"
_RE_MORE_AILMENT = re.compile(
    r"(\d+)% more Damage with Ailments",
    re.IGNORECASE,
)

# "X% increased Damage with Poison"
_RE_INCREASED_POISON_DMG = re.compile(
    r"(\d+)% increased Damage with Poison",
    re.IGNORECASE,
)

# "X% more Damage with Poison"
_RE_MORE_POISON_DMG = re.compile(
    r"(\d+)% more Damage with Poison",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Ailment chance patterns
# ---------------------------------------------------------------------------

# "X% chance to Ignite"
_RE_CHANCE_IGNITE = re.compile(
    r"(\d+)% chance to Ignite",
    re.IGNORECASE,
)

# "X% chance to cause Bleeding" / "X% chance to Bleed"
_RE_CHANCE_BLEED = re.compile(
    r"(\d+)% chance to (?:cause )?Bleed(?:ing)?",
    re.IGNORECASE,
)

# "X% chance to Poison" / "X% chance to Poison on Hit"
_RE_CHANCE_POISON = re.compile(
    r"(\d+)% chance to Poison",
    re.IGNORECASE,
)

# "Always Ignites"
_RE_ALWAYS_IGNITE = re.compile(
    r"Always Ignite",
    re.IGNORECASE,
)

# "Poison on Hit" (100% chance)
_RE_POISON_ON_HIT = re.compile(
    r"Poisons? (?:Enemies )?on Hit",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Ailment duration patterns
# ---------------------------------------------------------------------------

# "X% increased Ignite Duration"
_RE_IGNITE_DURATION = re.compile(
    r"(\d+)% increased Ignite Duration",
    re.IGNORECASE,
)

# "X% increased Bleeding Duration" / "X% increased Bleed Duration"
_RE_BLEED_DURATION = re.compile(
    r"(\d+)% increased Bleed(?:ing)? Duration",
    re.IGNORECASE,
)

# "X% increased Poison Duration"
_RE_POISON_DURATION = re.compile(
    r"(\d+)% increased Poison Duration",
    re.IGNORECASE,
)

# "X% increased Duration of Ailments"
_RE_AILMENT_DURATION = re.compile(
    r"(\d+)% increased Duration of (?:Elemental )?Ailments",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Critical strike patterns
# ---------------------------------------------------------------------------

# "X% increased Critical Strike Chance"
_RE_INCREASED_CRIT = re.compile(
    r"(\d+)% increased (?:Global )?Critical Strike Chance",
    re.IGNORECASE,
)

# "+X% to Critical Strike Multiplier"
_RE_CRIT_MULTI = re.compile(
    r"\+(\d+)% to (?:Global )?Critical Strike Multiplier",
    re.IGNORECASE,
)

# "X% increased Critical Strike Chance for Spells"
_RE_INCREASED_CRIT_SPELLS = re.compile(
    r"(\d+)% increased Critical Strike Chance for Spells",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Speed patterns
# ---------------------------------------------------------------------------

# "X% increased Attack Speed"
_RE_INCREASED_ATTACK_SPEED = re.compile(
    r"(\d+)% increased Attack Speed",
    re.IGNORECASE,
)

# "X% increased Cast Speed"
_RE_INCREASED_CAST_SPEED = re.compile(
    r"(\d+)% increased Cast Speed",
    re.IGNORECASE,
)

# "X% more Attack Speed"
_RE_MORE_ATTACK_SPEED = re.compile(
    r"(\d+)% more Attack Speed",
    re.IGNORECASE,
)

# "X% more Cast Speed"
_RE_MORE_CAST_SPEED = re.compile(
    r"(\d+)% more Cast Speed",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Accuracy patterns
# ---------------------------------------------------------------------------

# "+X to Accuracy Rating"
_RE_FLAT_ACCURACY = re.compile(
    r"\+(\d+) to Accuracy Rating",
    re.IGNORECASE,
)

# "X% increased Accuracy Rating"
_RE_INCREASED_ACCURACY = re.compile(
    r"(\d+)% increased Accuracy Rating",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Aura effect patterns
# ---------------------------------------------------------------------------

# "X% increased effect of Non-Curse Auras from your Skills"
_RE_INCREASED_AURA_EFFECT = re.compile(
    r"(\d+)% increased (?:effect of )?(?:Non-Curse )?Aura(?:s|) (?:Effect|from)",
    re.IGNORECASE,
)

# "X% increased Aura Effect"
_RE_INCREASED_AURA_EFFECT2 = re.compile(
    r"(\d+)% increased Aura Effect",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Impale patterns
# ---------------------------------------------------------------------------

# "X% chance to Impale on Hit"
_RE_IMPALE_CHANCE = re.compile(
    r"(\d+)% chance to Impale (?:Enemies )?on Hit",
    re.IGNORECASE,
)

# "Impales you inflict last X additional Hits"
_RE_IMPALE_EXTRA_STACKS = re.compile(
    r"Impales? you inflict last (\d+) additional Hits?",
    re.IGNORECASE,
)

# "X% increased Impale Effect"
_RE_IMPALE_EFFECT = re.compile(
    r"(\d+)% increased Impale Effect",
    re.IGNORECASE,
)

# "Attacks Impale on Hit" (100% chance)
_RE_IMPALE_ON_HIT = re.compile(
    r"Attacks Impale on Hit",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Projectile patterns
# ---------------------------------------------------------------------------

# "Fires X additional Projectiles" / "Skills fire X additional Projectiles"
_RE_ADDITIONAL_PROJECTILES = re.compile(
    r"(?:Fires?|Skills? fire) (\d+) additional Projectiles?",
    re.IGNORECASE,
)

# "+X to number of Projectiles" (from tree/items)
_RE_PLUS_PROJECTILES = re.compile(
    r"\+(\d+) (?:to (?:the )?number of )?Projectiles?",
    re.IGNORECASE,
)

# "Projectiles Pierce X additional Targets"
_RE_PIERCE_TARGETS = re.compile(
    r"Projectiles Pierce (\d+) additional Targets?",
    re.IGNORECASE,
)

# "Projectiles Pierce all Targets" / "Arrows Pierce all Targets"
_RE_PIERCE_ALL = re.compile(
    r"(?:Projectiles|Arrows) Pierce (?:all|All) Targets?",
    re.IGNORECASE,
)

# "Projectiles Chain +X times"
_RE_CHAIN = re.compile(
    r"Projectiles Chain \+(\d+) times?",
    re.IGNORECASE,
)

# "Projectiles Fork"
_RE_FORK = re.compile(
    r"Projectiles Fork",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Totem patterns
# ---------------------------------------------------------------------------

# "+X to maximum number of Summoned Totems"
_RE_MAX_TOTEMS = re.compile(
    r"\+(\d+) to (?:maximum number of )?(?:Summoned )?Totems?",
    re.IGNORECASE,
)

# "X% more Damage per Totem"
_RE_MORE_PER_TOTEM = re.compile(
    r"(\d+)% more Damage per Totem",
    re.IGNORECASE,
)

# "Place an additional Totem"
_RE_ADDITIONAL_TOTEM = re.compile(
    r"Place (?:an )?additional Totem",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ParsedMods:
    """Container for all modifiers parsed from a set of mod strings."""

    def __init__(self) -> None:
        self.flat_added: dict[DamageType, float] = {}
        self.flat_added_attacks: dict[DamageType, float] = {}
        self.flat_added_spells: dict[DamageType, float] = {}
        self.increased: list[Modifier] = []
        self.more: list[Modifier] = []
        self.conversions: list[ConversionEntry] = []
        self.penetration: dict[DamageType, float] = {}
        self.exposure: dict[DamageType, float] = {}
        self.increased_crit: float = 0.0
        self.increased_crit_spells: float = 0.0
        self.crit_multi: float = 0.0
        self.increased_attack_speed: float = 0.0
        self.increased_cast_speed: float = 0.0
        self.more_attack_speed: list[float] = []
        self.more_cast_speed: list[float] = []
        self.less_attack_speed: list[float] = []

        # DoT / ailment
        self.increased_dot: list[Modifier] = []
        self.more_dot: list[Modifier] = []
        self.dot_multi: float = 0.0
        self.dot_multi_fire: float = 0.0
        self.dot_multi_phys: float = 0.0
        self.dot_multi_chaos: float = 0.0
        self.chance_to_ignite: float = 0.0
        self.chance_to_bleed: float = 0.0
        self.chance_to_poison: float = 0.0
        self.increased_ignite_duration: float = 0.0
        self.increased_bleed_duration: float = 0.0
        self.increased_poison_duration: float = 0.0

        # Curse resist reduction (from active curses, after effectiveness)
        self.curse_resist_reduction: dict[DamageType, float] = {}
        # Enemy "increased damage taken" (Vulnerability, Punishment, etc.)
        self.enemy_increased_damage_taken: dict[DamageType, float] = {}
        # Generic enemy increased damage taken (applies to all types)
        self.enemy_increased_damage_taken_generic: float = 0.0

        # Impale
        self.impale_chance: float = 0.0  # 0-100%
        self.increased_impale_effect: float = 0.0
        self.extra_impale_stacks: int = 0

        # Projectile mechanics
        self.additional_projectiles: int = 0
        self.pierce_targets: int = 0
        self.pierce_all: bool = False
        self.chain_plus: int = 0
        self.fork: bool = False

        # Totem/trap/mine
        self.max_totem_bonus: int = 0  # +X to max totems

        # Accuracy
        self.flat_accuracy: float = 0.0
        self.increased_accuracy: float = 0.0

        # Aura effect
        self.increased_aura_effect: float = 0.0

        # Defence stats
        self.flat_life: float = 0.0
        self.increased_life: float = 0.0
        self.flat_energy_shield: float = 0.0
        self.increased_energy_shield: float = 0.0
        self.flat_armour: float = 0.0
        self.increased_armour: float = 0.0
        self.flat_evasion: float = 0.0
        self.increased_evasion: float = 0.0
        self.flat_mana: float = 0.0
        self.fire_resistance: float = 0.0
        self.cold_resistance: float = 0.0
        self.lightning_resistance: float = 0.0
        self.chaos_resistance: float = 0.0
        self.all_elemental_resistance: float = 0.0
        self.spell_suppression: float = 0.0

        # Special flags for non-standard mechanics
        # e.g. {"crits_ignore_resist": True, "lucky_crit": True, "base_crit_bonus": 2.0}
        self.special_flags: dict[str, object] = {}

    def merge(self, other: ParsedMods) -> None:
        """Merge another ParsedMods into this one."""
        for dtype, val in other.flat_added.items():
            self.flat_added[dtype] = self.flat_added.get(dtype, 0.0) + val
        for dtype, val in other.flat_added_attacks.items():
            self.flat_added_attacks[dtype] = (
                self.flat_added_attacks.get(dtype, 0.0) + val
            )
        for dtype, val in other.flat_added_spells.items():
            self.flat_added_spells[dtype] = (
                self.flat_added_spells.get(dtype, 0.0) + val
            )
        self.increased.extend(other.increased)
        self.more.extend(other.more)
        self.conversions.extend(other.conversions)
        for dtype, val in other.penetration.items():
            self.penetration[dtype] = self.penetration.get(dtype, 0.0) + val
        for dtype, val in other.exposure.items():
            self.exposure[dtype] = self.exposure.get(dtype, 0.0) + val
        self.increased_crit += other.increased_crit
        self.increased_crit_spells += other.increased_crit_spells
        self.crit_multi += other.crit_multi
        self.increased_attack_speed += other.increased_attack_speed
        self.increased_cast_speed += other.increased_cast_speed
        self.more_attack_speed.extend(other.more_attack_speed)
        self.more_cast_speed.extend(other.more_cast_speed)
        self.less_attack_speed.extend(other.less_attack_speed)
        self.increased_dot.extend(other.increased_dot)
        self.more_dot.extend(other.more_dot)
        self.dot_multi += other.dot_multi
        self.dot_multi_fire += other.dot_multi_fire
        self.dot_multi_phys += other.dot_multi_phys
        self.dot_multi_chaos += other.dot_multi_chaos
        self.chance_to_ignite += other.chance_to_ignite
        self.chance_to_bleed += other.chance_to_bleed
        self.chance_to_poison += other.chance_to_poison
        self.increased_ignite_duration += other.increased_ignite_duration
        self.increased_bleed_duration += other.increased_bleed_duration
        self.increased_poison_duration += other.increased_poison_duration
        for dtype, val in other.curse_resist_reduction.items():
            self.curse_resist_reduction[dtype] = (
                self.curse_resist_reduction.get(dtype, 0.0) + val
            )
        for dtype, val in other.enemy_increased_damage_taken.items():
            self.enemy_increased_damage_taken[dtype] = (
                self.enemy_increased_damage_taken.get(dtype, 0.0) + val
            )
        self.enemy_increased_damage_taken_generic += other.enemy_increased_damage_taken_generic
        self.impale_chance += other.impale_chance
        self.increased_impale_effect += other.increased_impale_effect
        self.extra_impale_stacks += other.extra_impale_stacks
        self.additional_projectiles += other.additional_projectiles
        self.pierce_targets += other.pierce_targets
        if other.pierce_all:
            self.pierce_all = True
        self.chain_plus += other.chain_plus
        if other.fork:
            self.fork = True
        self.max_totem_bonus += other.max_totem_bonus
        self.flat_accuracy += other.flat_accuracy
        self.increased_accuracy += other.increased_accuracy
        self.increased_aura_effect += other.increased_aura_effect
        # Defence stats
        self.flat_life += other.flat_life
        self.increased_life += other.increased_life
        self.flat_energy_shield += other.flat_energy_shield
        self.increased_energy_shield += other.increased_energy_shield
        self.flat_armour += other.flat_armour
        self.increased_armour += other.increased_armour
        self.flat_evasion += other.flat_evasion
        self.increased_evasion += other.increased_evasion
        self.flat_mana += other.flat_mana
        self.fire_resistance += other.fire_resistance
        self.cold_resistance += other.cold_resistance
        self.lightning_resistance += other.lightning_resistance
        self.chaos_resistance += other.chaos_resistance
        self.all_elemental_resistance += other.all_elemental_resistance
        self.spell_suppression += other.spell_suppression
        for key, val in other.special_flags.items():
            self.special_flags[key] = val


def parse_mods(mods: list[str], source: str = "") -> ParsedMods:
    """Parse a list of mod text strings into structured modifiers.

    Args:
        mods: List of modifier text strings (from items, gems, tree nodes).
        source: Label for attribution (e.g. "item:Helmet").

    Returns:
        ParsedMods containing all extracted modifiers.
    """
    result = ParsedMods()

    for mod_text in mods:
        _parse_single_mod(mod_text, source, result)

    return result


def _add_flat(store: dict[DamageType, float], dtype: DamageType, lo: str, hi: str) -> None:
    avg = (float(lo) + float(hi)) / 2.0
    store[dtype] = store.get(dtype, 0.0) + avg


def _parse_single_mod(text: str, source: str, out: ParsedMods) -> None:
    """Parse a single mod string and add results to `out`."""

    # --- Flat added damage (to attacks) ---
    m = _RE_FLAT_ADDED_ATTACKS.search(text)
    if m:
        dtype = _DTYPE_MAP[m.group(3).lower()]
        _add_flat(out.flat_added_attacks, dtype, m.group(1), m.group(2))
        return

    # --- Flat added damage (to spells) ---
    m = _RE_FLAT_ADDED_SPELLS.search(text)
    if m:
        dtype = _DTYPE_MAP[m.group(3).lower()]
        _add_flat(out.flat_added_spells, dtype, m.group(1), m.group(2))
        return

    # --- Flat added damage (generic / weapon local) ---
    m = _RE_FLAT_ADDED.search(text)
    if m:
        dtype = _DTYPE_MAP[m.group(3).lower()]
        _add_flat(out.flat_added, dtype, m.group(1), m.group(2))
        return

    # --- Conversion ---
    m = _RE_CONVERSION.search(text)
    if m:
        out.conversions.append(ConversionEntry(
            type_from=_DTYPE_MAP[m.group(2).lower()],
            type_to=_DTYPE_MAP[m.group(3).lower()],
            percent=float(m.group(1)),
            source=source,
        ))
        return

    # --- Gained as extra ---
    m = _RE_GAINED_AS.search(text)
    if m:
        out.conversions.append(ConversionEntry(
            type_from=_DTYPE_MAP[m.group(2).lower()],
            type_to=_DTYPE_MAP[m.group(3).lower()],
            percent=float(m.group(1)),
            is_gained_as=True,
            source=source,
        ))
        return

    # --- Penetration ---
    for pattern in (_RE_PENETRATION, _RE_PENETRATION2):
        m = pattern.search(text)
        if m:
            types = _resolve_types(m.group(2))
            val = float(m.group(1))
            for dtype in types:
                out.penetration[dtype] = out.penetration.get(dtype, 0.0) + val
            return

    # --- Exposure ---
    m = _RE_EXPOSURE_VALUE.search(text)
    if m:
        val = abs(float(m.group(1)))  # Exposure is stored as positive reduction
        types = _resolve_types(m.group(2))
        for dtype in types:
            out.exposure[dtype] = out.exposure.get(dtype, 0.0) + val
        return

    m = _RE_EXPOSURE_ON_HIT.search(text)
    if m:
        val = abs(float(m.group(2)))
        types = _resolve_types(m.group(1))
        for dtype in types:
            out.exposure[dtype] = out.exposure.get(dtype, 0.0) + val
        return

    m = _RE_RESIST_REDUCTION.search(text)
    if m:
        val = abs(float(m.group(1)))  # Convert negative to positive reduction
        type_word = m.group(2).lower()
        if "all elemental" in type_word or "elemental" == type_word:
            types = _ELE_TYPES[:]
        else:
            types = _resolve_types(type_word)
        for dtype in types:
            out.exposure[dtype] = out.exposure.get(dtype, 0.0) + val
        return

    # --- DoT multiplier (must be before generic increased/more) ---
    m = _RE_DOT_MULTI_TYPED.search(text)
    if m:
        dtype_word = m.group(2).lower()
        val = float(m.group(1))
        if dtype_word == "fire":
            out.dot_multi_fire += val
        elif dtype_word == "physical":
            out.dot_multi_phys += val
        elif dtype_word == "chaos":
            out.dot_multi_chaos += val
        return

    m = _RE_DOT_MULTI.search(text)
    if m:
        out.dot_multi += float(m.group(1))
        return

    # --- DoT increased/more (must be before generic increased/more) ---
    m = _RE_INCREASED_DOT_TYPED.search(text)
    if m:
        types = _resolve_types(m.group(2))
        out.increased_dot.append(Modifier(
            stat=f"increased_{m.group(2).lower()}_dot",
            value=float(m.group(1)),
            mod_type="increased",
            damage_types=types,
            source=source,
        ))
        return

    m = _RE_INCREASED_DOT.search(text)
    if m:
        out.increased_dot.append(Modifier(
            stat="increased_dot",
            value=float(m.group(1)),
            mod_type="increased",
            source=source,
        ))
        return

    m = _RE_INCREASED_BURNING.search(text)
    if m:
        out.increased_dot.append(Modifier(
            stat="increased_burning_damage",
            value=float(m.group(1)),
            mod_type="increased",
            damage_types=[DamageType.FIRE],
            source=source,
        ))
        return

    m = _RE_MORE_DOT.search(text)
    if m:
        out.more_dot.append(Modifier(
            stat="more_dot",
            value=float(m.group(1)),
            mod_type="more",
            source=source,
        ))
        return

    m = _RE_MORE_BURNING.search(text)
    if m:
        out.more_dot.append(Modifier(
            stat="more_burning_damage",
            value=float(m.group(1)),
            mod_type="more",
            damage_types=[DamageType.FIRE],
            source=source,
        ))
        return

    m = _RE_INCREASED_AILMENT.search(text)
    if m:
        out.increased_dot.append(Modifier(
            stat="increased_ailment_damage",
            value=float(m.group(1)),
            mod_type="increased",
            source=source,
        ))
        return

    m = _RE_MORE_AILMENT.search(text)
    if m:
        out.more_dot.append(Modifier(
            stat="more_ailment_damage",
            value=float(m.group(1)),
            mod_type="more",
            source=source,
        ))
        return

    m = _RE_INCREASED_POISON_DMG.search(text)
    if m:
        out.increased_dot.append(Modifier(
            stat="increased_poison_damage",
            value=float(m.group(1)),
            mod_type="increased",
            damage_types=[DamageType.CHAOS],
            source=source,
        ))
        return

    m = _RE_MORE_POISON_DMG.search(text)
    if m:
        out.more_dot.append(Modifier(
            stat="more_poison_damage",
            value=float(m.group(1)),
            mod_type="more",
            damage_types=[DamageType.CHAOS],
            source=source,
        ))
        return

    # --- Ailment chance ---
    m = _RE_ALWAYS_IGNITE.search(text)
    if m:
        out.chance_to_ignite = 100.0
        return

    m = _RE_CHANCE_IGNITE.search(text)
    if m:
        out.chance_to_ignite += float(m.group(1))
        return

    m = _RE_CHANCE_BLEED.search(text)
    if m:
        out.chance_to_bleed += float(m.group(1))
        return

    # Check percentage poison before "Poison on Hit" (100%)
    m = _RE_CHANCE_POISON.search(text)
    if m:
        out.chance_to_poison += float(m.group(1))
        return

    m = _RE_POISON_ON_HIT.search(text)
    if m:
        out.chance_to_poison = 100.0
        return

    # --- Ailment duration ---
    m = _RE_IGNITE_DURATION.search(text)
    if m:
        out.increased_ignite_duration += float(m.group(1))
        return

    m = _RE_BLEED_DURATION.search(text)
    if m:
        out.increased_bleed_duration += float(m.group(1))
        return

    m = _RE_POISON_DURATION.search(text)
    if m:
        out.increased_poison_duration += float(m.group(1))
        return

    m = _RE_AILMENT_DURATION.search(text)
    if m:
        val = float(m.group(1))
        out.increased_ignite_duration += val
        out.increased_bleed_duration += val
        out.increased_poison_duration += val
        return

    # --- Less damage (negative more) ---
    m = _RE_LESS_TYPED.search(text)
    if m:
        types = _resolve_types(m.group(2))
        out.more.append(Modifier(
            stat=f"less_{m.group(2).lower()}_damage",
            value=-float(m.group(1)),
            mod_type="more",
            damage_types=types,
            source=source,
        ))
        return

    m = _RE_LESS_GENERIC.search(text)
    if m:
        out.more.append(Modifier(
            stat="less_damage",
            value=-float(m.group(1)),
            mod_type="more",
            source=source,
        ))
        return

    # --- Less attack speed ---
    m = _RE_LESS_ATTACK_SPEED.search(text)
    if m:
        out.less_attack_speed.append(float(m.group(1)))
        return

    # --- More damage (typed) ---
    m = _RE_MORE_TYPED.search(text)
    if m:
        types = _resolve_types(m.group(2))
        out.more.append(Modifier(
            stat=f"more_{m.group(2).lower()}_damage",
            value=float(m.group(1)),
            mod_type="more",
            damage_types=types,
            source=source,
        ))
        return

    # --- More damage (generic) ---
    m = _RE_MORE_GENERIC.search(text)
    if m:
        out.more.append(Modifier(
            stat="more_damage",
            value=float(m.group(1)),
            mod_type="more",
            source=source,
        ))
        return

    # --- More attack/spell damage ---
    m = _RE_MORE_ATTACK.search(text)
    if m:
        out.more.append(Modifier(
            stat="more_attack_damage",
            value=float(m.group(1)),
            mod_type="more",
            category=ModCategory.SKILL_SPECIFIC,
            source=source,
        ))
        return

    m = _RE_MORE_SPELL.search(text)
    if m:
        out.more.append(Modifier(
            stat="more_spell_damage",
            value=float(m.group(1)),
            mod_type="more",
            category=ModCategory.SKILL_SPECIFIC,
            source=source,
        ))
        return

    m = _RE_MORE_MELEE.search(text)
    if m:
        out.more.append(Modifier(
            stat="more_melee_damage",
            value=float(m.group(1)),
            mod_type="more",
            category=ModCategory.SKILL_SPECIFIC,
            source=source,
        ))
        return

    m = _RE_MORE_PROJECTILE.search(text)
    if m:
        out.more.append(Modifier(
            stat="more_projectile_damage",
            value=float(m.group(1)),
            mod_type="more",
            source=source,
        ))
        return

    m = _RE_MORE_AREA.search(text)
    if m:
        out.more.append(Modifier(
            stat="more_area_damage",
            value=float(m.group(1)),
            mod_type="more",
            source=source,
        ))
        return

    m = _RE_MORE_HITS.search(text)
    if m:
        out.more.append(Modifier(
            stat="more_damage_with_hits",
            value=float(m.group(1)),
            mod_type="more",
            source=source,
        ))
        return

    # --- Increased damage (typed) ---
    m = _RE_INCREASED_TYPED.search(text)
    if m:
        types = _resolve_types(m.group(2))
        out.increased.append(Modifier(
            stat=f"increased_{m.group(2).lower()}_damage",
            value=float(m.group(1)),
            mod_type="increased",
            damage_types=types,
            category=ModCategory.TYPE_SPECIFIC,
            source=source,
        ))
        return

    # --- Increased damage (generic) ---
    m = _RE_INCREASED_GENERIC.search(text)
    if m:
        out.increased.append(Modifier(
            stat="increased_damage",
            value=float(m.group(1)),
            mod_type="increased",
            source=source,
        ))
        return

    # --- Increased attack/spell/melee/projectile/area damage ---
    m = _RE_INCREASED_ATTACK.search(text)
    if m:
        out.increased.append(Modifier(
            stat="increased_attack_damage",
            value=float(m.group(1)),
            mod_type="increased",
            category=ModCategory.SKILL_SPECIFIC,
            source=source,
        ))
        return

    m = _RE_INCREASED_SPELL.search(text)
    if m:
        out.increased.append(Modifier(
            stat="increased_spell_damage",
            value=float(m.group(1)),
            mod_type="increased",
            category=ModCategory.SKILL_SPECIFIC,
            source=source,
        ))
        return

    m = _RE_INCREASED_MELEE.search(text)
    if m:
        out.increased.append(Modifier(
            stat="increased_melee_damage",
            value=float(m.group(1)),
            mod_type="increased",
            category=ModCategory.SKILL_SPECIFIC,
            source=source,
        ))
        return

    m = _RE_INCREASED_PROJECTILE.search(text)
    if m:
        out.increased.append(Modifier(
            stat="increased_projectile_damage",
            value=float(m.group(1)),
            mod_type="increased",
            source=source,
        ))
        return

    m = _RE_INCREASED_AREA.search(text)
    if m:
        out.increased.append(Modifier(
            stat="increased_area_damage",
            value=float(m.group(1)),
            mod_type="increased",
            source=source,
        ))
        return

    m = _RE_INCREASED_WEAPON_TYPE.search(text)
    if m:
        out.increased.append(Modifier(
            stat=f"increased_{m.group(2).lower()}_damage",
            value=float(m.group(1)),
            mod_type="increased",
            category=ModCategory.WEAPON_TYPE,
            source=source,
        ))
        return

    m = _RE_INCREASED_HITS.search(text)
    if m:
        out.increased.append(Modifier(
            stat="increased_damage_with_hits",
            value=float(m.group(1)),
            mod_type="increased",
            source=source,
        ))
        return

    # --- Crit ---
    m = _RE_INCREASED_CRIT_SPELLS.search(text)
    if m:
        out.increased_crit_spells += float(m.group(1))
        return

    m = _RE_INCREASED_CRIT.search(text)
    if m:
        out.increased_crit += float(m.group(1))
        return

    m = _RE_CRIT_MULTI.search(text)
    if m:
        out.crit_multi += float(m.group(1))
        return

    # --- Speed ---
    m = _RE_MORE_ATTACK_SPEED.search(text)
    if m:
        out.more_attack_speed.append(float(m.group(1)))
        return

    m = _RE_MORE_CAST_SPEED.search(text)
    if m:
        out.more_cast_speed.append(float(m.group(1)))
        return

    m = _RE_INCREASED_ATTACK_SPEED.search(text)
    if m:
        out.increased_attack_speed += float(m.group(1))
        return

    m = _RE_INCREASED_CAST_SPEED.search(text)
    if m:
        out.increased_cast_speed += float(m.group(1))
        return

    # --- Impale ---
    m = _RE_IMPALE_ON_HIT.search(text)
    if m:
        out.impale_chance = 100.0
        return

    m = _RE_IMPALE_CHANCE.search(text)
    if m:
        out.impale_chance += float(m.group(1))
        return

    m = _RE_IMPALE_EXTRA_STACKS.search(text)
    if m:
        out.extra_impale_stacks += int(m.group(1))
        return

    m = _RE_IMPALE_EFFECT.search(text)
    if m:
        out.increased_impale_effect += float(m.group(1))
        return

    # --- Projectile mechanics ---
    m = _RE_ADDITIONAL_PROJECTILES.search(text)
    if m:
        out.additional_projectiles += int(m.group(1))
        return

    m = _RE_PLUS_PROJECTILES.search(text)
    if m:
        out.additional_projectiles += int(m.group(1))
        return

    m = _RE_PIERCE_ALL.search(text)
    if m:
        out.pierce_all = True
        return

    m = _RE_PIERCE_TARGETS.search(text)
    if m:
        out.pierce_targets += int(m.group(1))
        return

    m = _RE_CHAIN.search(text)
    if m:
        out.chain_plus += int(m.group(1))
        return

    m = _RE_FORK.search(text)
    if m:
        out.fork = True
        return

    # --- Totem ---
    m = _RE_ADDITIONAL_TOTEM.search(text)
    if m:
        out.max_totem_bonus += 1
        return

    m = _RE_MAX_TOTEMS.search(text)
    if m:
        out.max_totem_bonus += int(m.group(1))
        return

    # --- Accuracy ---
    m = _RE_FLAT_ACCURACY.search(text)
    if m:
        out.flat_accuracy += float(m.group(1))
        return

    m = _RE_INCREASED_ACCURACY.search(text)
    if m:
        out.increased_accuracy += float(m.group(1))
        return

    # --- Aura effect ---
    m = _RE_INCREASED_AURA_EFFECT.search(text)
    if m:
        out.increased_aura_effect += float(m.group(1))
        return

    m = _RE_INCREASED_AURA_EFFECT2.search(text)
    if m:
        out.increased_aura_effect += float(m.group(1))
        return

    # --- Defence stats ---
    _parse_defence_mod(text, out)


# ===================================================================
# Defence mod patterns
# ===================================================================

_RE_FLAT_LIFE = re.compile(r"\+(\d+) to maximum Life", re.IGNORECASE)
_RE_INC_LIFE = re.compile(r"(\d+)% increased maximum Life", re.IGNORECASE)
_RE_FLAT_ES = re.compile(r"\+(\d+) to maximum Energy Shield", re.IGNORECASE)
_RE_INC_ES = re.compile(r"(\d+)% increased maximum Energy Shield", re.IGNORECASE)
_RE_FLAT_MANA = re.compile(r"\+(\d+) to maximum Mana", re.IGNORECASE)
_RE_FLAT_ARMOUR = re.compile(r"\+(\d+) to Armour", re.IGNORECASE)
_RE_INC_ARMOUR = re.compile(r"(\d+)% increased Armour", re.IGNORECASE)
_RE_FLAT_EVASION = re.compile(r"\+(\d+) to Evasion(?! Rating)", re.IGNORECASE)
_RE_FLAT_EVASION_RATING = re.compile(r"\+(\d+) to Evasion Rating", re.IGNORECASE)
_RE_INC_EVASION = re.compile(r"(\d+)% increased Evasion Rating", re.IGNORECASE)
_RE_FIRE_RES = re.compile(r"\+(\d+)% to Fire Resistance", re.IGNORECASE)
_RE_COLD_RES = re.compile(r"\+(\d+)% to Cold Resistance", re.IGNORECASE)
_RE_LIGHT_RES = re.compile(r"\+(\d+)% to Lightning Resistance", re.IGNORECASE)
_RE_CHAOS_RES = re.compile(r"\+(\d+)% to Chaos Resistance", re.IGNORECASE)
_RE_ALL_ELE_RES = re.compile(r"\+(\d+)% to all Elemental Resistances", re.IGNORECASE)
_RE_SPELL_SUPP = re.compile(r"\+(\d+)% chance to Suppress Spell Damage", re.IGNORECASE)
_RE_BLOCK = re.compile(r"\+?(\d+)% (?:Chance to )?Block(?: Attack Damage)?", re.IGNORECASE)
_RE_SPELL_BLOCK = re.compile(r"\+?(\d+)% (?:Chance to )?Block Spell Damage", re.IGNORECASE)


def _parse_defence_mod(text: str, out: ParsedMods) -> None:
    """Parse defensive mods (life, ES, armour, evasion, resistances)."""
    m = _RE_FLAT_LIFE.search(text)
    if m:
        out.flat_life += float(m.group(1))
        return

    m = _RE_INC_LIFE.search(text)
    if m:
        out.increased_life += float(m.group(1))
        return

    m = _RE_FLAT_ES.search(text)
    if m:
        out.flat_energy_shield += float(m.group(1))
        return

    m = _RE_INC_ES.search(text)
    if m:
        out.increased_energy_shield += float(m.group(1))
        return

    m = _RE_FLAT_MANA.search(text)
    if m:
        out.flat_mana += float(m.group(1))
        return

    m = _RE_FLAT_ARMOUR.search(text)
    if m:
        out.flat_armour += float(m.group(1))
        return

    m = _RE_INC_ARMOUR.search(text)
    if m:
        out.increased_armour += float(m.group(1))
        return

    m = _RE_FLAT_EVASION_RATING.search(text)
    if m:
        out.flat_evasion += float(m.group(1))
        return

    m = _RE_FLAT_EVASION.search(text)
    if m:
        out.flat_evasion += float(m.group(1))
        return

    m = _RE_INC_EVASION.search(text)
    if m:
        out.increased_evasion += float(m.group(1))
        return

    m = _RE_ALL_ELE_RES.search(text)
    if m:
        out.all_elemental_resistance += float(m.group(1))
        return

    m = _RE_FIRE_RES.search(text)
    if m:
        out.fire_resistance += float(m.group(1))
        return

    m = _RE_COLD_RES.search(text)
    if m:
        out.cold_resistance += float(m.group(1))
        return

    m = _RE_LIGHT_RES.search(text)
    if m:
        out.lightning_resistance += float(m.group(1))
        return

    m = _RE_CHAOS_RES.search(text)
    if m:
        out.chaos_resistance += float(m.group(1))
        return

    m = _RE_SPELL_SUPP.search(text)
    if m:
        out.spell_suppression += float(m.group(1))
        return

    m = _RE_SPELL_BLOCK.search(text)
    if m:
        out.special_flags["spell_block_chance"] = (
            float(out.special_flags.get("spell_block_chance", 0.0)) + float(m.group(1))
        )
        return

    m = _RE_BLOCK.search(text)
    if m:
        out.special_flags["block_chance"] = (
            float(out.special_flags.get("block_chance", 0.0)) + float(m.group(1))
        )
