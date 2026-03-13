"""
Ascendancy node effect database for the DPS calculator.

Each ascendancy class has build-defining notable passives. This module
provides the DPS-relevant effects for the most impactful nodes.

Effects are stored as modifiers + special_mechanics flags for non-standard
behaviors (e.g. Inquisitor "crits ignore resistance").
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pop.calc.models import ConversionEntry, DamageType, Modifier


@dataclass
class AscendancyNode:
    """A single ascendancy notable passive."""

    name: str
    class_name: str  # e.g. "Elementalist", "Assassin"
    modifiers: list[Modifier] = field(default_factory=list)
    conversions: list[ConversionEntry] = field(default_factory=list)
    penetration: dict[DamageType, float] = field(default_factory=dict)
    increased_crit: float = 0.0
    crit_multi: float = 0.0
    base_crit_bonus: float = 0.0  # added to base crit before scaling
    increased_speed: float = 0.0  # attack or cast speed
    # Special mechanics that can't be expressed as modifiers
    special: dict[str, object] = field(default_factory=dict)


def _mod(
    stat: str,
    value: float,
    mod_type: str = "more",
    damage_types: list[DamageType] | None = None,
) -> Modifier:
    return Modifier(
        stat=stat, value=value, mod_type=mod_type,
        damage_types=damage_types or [], source="ascendancy",
    )


_NODES: dict[str, AscendancyNode] = {}


def _an(name: str, cls: str, **kw: object) -> None:
    _NODES[name] = AscendancyNode(name=name, class_name=cls, **kw)  # type: ignore[arg-type]


# ===================================================================
# Witch — Elementalist
# ===================================================================

_an("Shaper of Flames", "Elementalist",
    modifiers=[_mod("more_ignite_damage", 25, damage_types=[DamageType.FIRE])],
    special={"all_damage_can_ignite": True})

_an("Heart of Destruction", "Elementalist",
    modifiers=[_mod("more_area_damage", 25), _mod("more_elemental_damage", 25)])

_an("Mastermind of Discord", "Elementalist",
    penetration={
        DamageType.FIRE: 25.0,
        DamageType.COLD: 25.0,
        DamageType.LIGHTNING: 25.0,
    },
    special={"pen_requires_matching_herald": True})

_an("Shaper of Storms", "Elementalist",
    special={"all_damage_can_shock": True, "minimum_shock": 15.0})

# ===================================================================
# Shadow — Assassin
# ===================================================================

_an("Deadly Infusion", "Assassin",
    base_crit_bonus=2.0,
    crit_multi=25.0)

_an("Mistwalker", "Assassin",
    modifiers=[_mod("more_damage_while_elusive", 10)])

_an("Opportunistic", "Assassin",
    modifiers=[_mod("more_damage_vs_unique", 20)])

_an("Noxious Strike", "Assassin",
    modifiers=[_mod("more_poison_duration", 20)])

# ===================================================================
# Marauder — Berserker
# ===================================================================

_an("Aspect of Carnage", "Berserker",
    modifiers=[_mod("more_damage", 40)])

_an("Blitz", "Berserker",
    increased_speed=20.0,
    special={"blitz_charges": True})

_an("Flawless Savagery", "Berserker",
    crit_multi=30.0,
    modifiers=[_mod("increased_physical_damage", 40, mod_type="increased",
                     damage_types=[DamageType.PHYSICAL])])

_an("Pain Reaver", "Berserker")  # Leech, no DPS

# ===================================================================
# Templar — Inquisitor
# ===================================================================

_an("Inevitable Judgement", "Inquisitor",
    special={"crits_ignore_resist": True})

_an("Augury of Penitence", "Inquisitor",
    modifiers=[_mod("more_elemental_damage_nearby", 16,
                     damage_types=[DamageType.FIRE, DamageType.COLD, DamageType.LIGHTNING])])

_an("Righteous Providence", "Inquisitor",
    increased_crit=100.0)

_an("Instruments of Virtue", "Inquisitor",
    modifiers=[
        _mod("more_attack_damage", 10),
        _mod("more_spell_damage", 10),
    ])

# ===================================================================
# Templar — Hierophant
# ===================================================================

_an("Pursuit of Faith", "Hierophant",
    modifiers=[_mod("more_damage_per_totem", 3)],
    special={"per_totem_bonus": True})

_an("Conviction of Power", "Hierophant",
    special={"auto_power_charges": 4, "auto_endurance_charges": 4})

# ===================================================================
# Duelist — Champion
# ===================================================================

_an("Inspirational", "Champion",
    modifiers=[_mod("more_damage_with_banner", 12)])

_an("Master of Metal", "Champion",
    special={"intimidate_on_hit": True, "impale_bonus": True})

_an("First to Strike, Last to Fall", "Champion",
    special={"intimidate_on_hit": True, "adrenaline": True})

_an("Unstoppable Hero", "Champion",
    increased_speed=20.0,
    modifiers=[_mod("increased_damage", 20, mod_type="increased")])

# ===================================================================
# Duelist — Slayer
# ===================================================================

_an("Headsman", "Slayer",
    modifiers=[_mod("more_damage_vs_unique", 20)])

_an("Overwhelm", "Slayer",
    base_crit_bonus=3.0)

_an("Impact", "Slayer",
    modifiers=[_mod("more_area_damage", 15)])

# ===================================================================
# Ranger — Deadeye
# ===================================================================

_an("Gathering Winds", "Deadeye",
    special={"tailwind": True},
    increased_speed=10.0)

_an("Ricochet", "Deadeye",
    special={"chain_plus_1": True})

_an("Endless Munitions", "Deadeye",
    special={"additional_projectile": 1})

_an("Far Shot", "Deadeye",
    modifiers=[_mod("more_projectile_damage_far", 30)])

# ===================================================================
# Ranger — Raider
# ===================================================================

_an("Avatar of the Chase", "Raider",
    modifiers=[_mod("more_attack_speed_onslaught", 35)],
    special={"onslaught_permanent": True})

_an("Avatar of the Slaughter", "Raider",
    modifiers=[_mod("more_damage_frenzy", 4)],
    special={"extra_frenzy_charges": 2})

_an("Quartz Infusion", "Raider",
    special={"phasing_permanent": True})

# ===================================================================
# Shadow — Trickster
# ===================================================================

_an("Harness the Void", "Trickster",
    modifiers=[_mod("more_chaos_damage", 20, damage_types=[DamageType.CHAOS])],
    special={"non_chaos_as_extra_chaos_chance": True})

_an("Swift Killer", "Trickster",
    special={"frenzy_and_power_on_kill": True})

_an("Patient Reaper", "Trickster",
    modifiers=[_mod("more_dot_damage", 40)])

# ===================================================================
# Witch — Necromancer
# ===================================================================

_an("Unholy Might", "Necromancer",
    conversions=[
        ConversionEntry(
            type_from=DamageType.PHYSICAL, type_to=DamageType.CHAOS,
            percent=30.0, is_gained_as=True, source="ascendancy:Unholy Might",
        ),
    ])

_an("Essence Glutton", "Necromancer")  # ES regen, no DPS

# ===================================================================
# Witch — Occultist
# ===================================================================

_an("Void Beacon", "Occultist",
    special={"nearby_enemies_minus_resist": {DamageType.COLD: 20.0, DamageType.CHAOS: 20.0}})

_an("Profane Bloom", "Occultist",
    special={"curse_aoe_explosion": True})

_an("Malediction", "Occultist",
    modifiers=[_mod("more_damage_per_curse", 8)],
    special={"extra_curse": True})

_an("Withering Presence", "Occultist",
    special={"auto_wither_stacks": 6},
    modifiers=[_mod("more_chaos_damage", 15, damage_types=[DamageType.CHAOS])])

# ===================================================================
# Duelist — Gladiator
# ===================================================================

_an("Blood in the Eyes", "Gladiator",
    special={"bleed_maim_on_hit": True})

_an("Gratuitous Violence", "Gladiator",
    modifiers=[_mod("more_bleed_damage", 25)],
    special={"bleeding_explosion": True})

_an("Arena Challenger", "Gladiator",
    increased_speed=16.0)

# ===================================================================
# Marauder — Chieftain
# ===================================================================

_an("Ngamahu, Flame's Advance", "Chieftain",
    conversions=[
        ConversionEntry(
            type_from=DamageType.PHYSICAL, type_to=DamageType.FIRE,
            percent=50.0, is_gained_as=False, source="ascendancy:Ngamahu",
        ),
    ])

_an("Hinekora, Death's Fury", "Chieftain",
    penetration={DamageType.FIRE: 15.0})

# ===================================================================
# Marauder — Juggernaut
# ===================================================================

_an("Undeniable", "Juggernaut",
    increased_speed=10.0,
    increased_crit=100.0,
    special={"accuracy_bonus": True})

_an("Unbreakable", "Juggernaut")  # Armour/regen, no DPS


# ===================================================================
# Public API
# ===================================================================


def get_ascendancy_node(name: str) -> AscendancyNode | None:
    """Look up an ascendancy node by name."""
    return _NODES.get(name)


def get_all_class_nodes(class_name: str) -> list[AscendancyNode]:
    """Get all known nodes for a given ascendancy class."""
    return [n for n in _NODES.values() if n.class_name == class_name]


ASCENDANCY_NODE_NAMES: set[str] = set(_NODES.keys())
