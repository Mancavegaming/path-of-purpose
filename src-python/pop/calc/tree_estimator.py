"""
Passive tree stat estimator for AI-generated builds.

AI builds have key_nodes + total_points but no node IDs, so the real
tree_stats module can't extract exact values. This module provides a
heuristic estimate based on:
- total_points (how many passives are allocated)
- key_nodes (named keystones/notables — we know what some of these do)
- The build's main damage type

This is inherently approximate, but MUCH better than 0% from passives.
"""

from __future__ import annotations

from pop.build_parser.models import PassiveSpec
from pop.calc.mod_parser import ParsedMods
from pop.calc.models import DamageType, Modifier

# Known keystones and their effects
_KEYSTONE_EFFECTS: dict[str, list[Modifier]] = {
    "Resolute Technique": [
        # Hits can't be evaded, never crit (crit handled separately)
    ],
    "Elemental Overload": [
        Modifier(stat="more_elemental_damage", value=40, mod_type="more",
                 damage_types=[DamageType.FIRE, DamageType.COLD, DamageType.LIGHTNING],
                 source="tree:Elemental Overload"),
    ],
    "Avatar of Fire": [],  # Conversion — complex, skip for now
    "Point Blank": [
        Modifier(stat="more_projectile_damage", value=30, mod_type="more",
                 source="tree:Point Blank"),
    ],
    "Iron Will": [
        # Strength applies to spell damage — can't estimate without knowing str
    ],
    "Pain Attunement": [
        Modifier(stat="more_spell_damage", value=30, mod_type="more",
                 source="tree:Pain Attunement"),
    ],
    "Crimson Dance": [],  # Bleed mechanic change
    "Perfect Agony": [],  # Crit multi applies to ailments at 50%
    "Mind Over Matter": [],  # Defensive
    "Acrobatics": [],  # Defensive
    "Iron Reflexes": [],  # Defensive
    "Unwavering Stance": [],  # Defensive
    "Chaos Inoculation": [],  # Defensive
    "Vaal Pact": [],  # Defensive
    "Zealot's Oath": [],  # Defensive
    "Ghost Reaver": [],  # Defensive
    "Ancestral Bond": [],  # Can't deal damage yourself
}

# Known notable nodes that provide significant damage
_NOTABLE_EFFECTS: dict[str, list[Modifier]] = {
    # Weapon-specific notables (~20-30% increased each)
    "Blade of Cunning": [Modifier(stat="inc_sword", value=28, mod_type="increased",
                                   source="tree:Blade of Cunning")],
    "Fatal Blade": [Modifier(stat="inc_sword_crit", value=25, mod_type="increased",
                              source="tree:Fatal Blade")],
    "Butchery": [Modifier(stat="inc_axe", value=28, mod_type="increased",
                           source="tree:Butchery")],
    "Splitting Strikes": [Modifier(stat="inc_axe", value=20, mod_type="increased",
                                    source="tree:Splitting Strikes")],
    "Claws of the Falcon": [Modifier(stat="inc_claw", value=25, mod_type="increased",
                                      source="tree:Claws of the Falcon")],
    "King of the Hill": [Modifier(stat="inc_proj", value=30, mod_type="increased",
                                   source="tree:King of the Hill")],
    "Ballistic Mastery": [Modifier(stat="inc_proj", value=20, mod_type="increased",
                                    source="tree:Ballistic Mastery")],
    "Wandslinger": [Modifier(stat="inc_wand", value=25, mod_type="increased",
                              source="tree:Wandslinger")],
    "Crackling Speed": [Modifier(stat="inc_wand", value=20, mod_type="increased",
                                  source="tree:Crackling Speed")],
    "Annihilation": [Modifier(stat="inc_spell_crit", value=30, mod_type="increased",
                               source="tree:Annihilation")],
    # Generic damage notables
    "Coordination": [Modifier(stat="inc_attack_speed", value=8, mod_type="increased",
                               source="tree:Coordination")],
    "Finesse": [Modifier(stat="inc_attack_speed", value=6, mod_type="increased",
                           source="tree:Finesse")],
    "Heartseeker": [Modifier(stat="inc_crit_multi", value=25, mod_type="increased",
                               source="tree:Heartseeker")],
    "Lethality": [Modifier(stat="inc_proj_crit", value=35, mod_type="increased",
                             source="tree:Lethality")],
}


def estimate_passive_stats(
    spec: PassiveSpec,
    is_attack: bool,
    damage_types: set[DamageType] | None = None,
) -> ParsedMods:
    """Estimate passive tree modifiers for AI-generated builds.

    Uses total_points to estimate generic increased% from the tree,
    and key_nodes to add specific keystone/notable effects.

    Args:
        spec: The passive spec with key_nodes and total_points.
        is_attack: Whether the main skill is an attack.
        damage_types: Primary damage types of the build.

    Returns:
        ParsedMods with estimated modifiers.
    """
    out = ParsedMods()
    total_points = spec.total_points or 0
    key_nodes = spec.key_nodes or []

    if total_points == 0 and not key_nodes:
        return out

    # --- Heuristic: estimate generic stats from total_points ---
    # A typical optimized PoE tree allocates roughly:
    # - 45-55% of points to damage (increased%, crit, attack/cast speed)
    # - 30-35% of points to life/defense
    # - 15-20% of points to pathing (travel nodes with small bonuses)
    #
    # Real per-point damage breakdown:
    # - Notables: ~20-30% increased damage each (~15% of allocated points)
    # - Small nodes in clusters: ~5-10% each (~30% of allocated points)
    # - Travel nodes: ~2-4% each (~10% of allocated points)
    # Weighted average: ~7% increased per damage-allocated point
    #
    # A 100-point build should yield ~150-200% total increased damage
    # from the tree (matching PoB for typical optimized builds).
    damage_points = int(total_points * 0.50)
    avg_inc_per_point = 7.0
    estimated_inc = damage_points * avg_inc_per_point

    # Split between generic damage, specific damage type, and attack/spell
    generic_inc = estimated_inc * 0.35  # ~35% is generic
    specific_inc = estimated_inc * 0.40  # ~40% is type-specific
    speed_inc = estimated_inc * 0.25  # ~25% is attack/cast speed + crit

    # Generic increased damage
    out.increased.append(Modifier(
        stat="estimated_generic_damage", value=generic_inc,
        mod_type="increased", source="tree:estimate",
    ))

    # Type-specific increased damage
    dtypes = list(damage_types or [])
    if dtypes:
        per_type = specific_inc / len(dtypes)
        for dt in dtypes:
            out.increased.append(Modifier(
                stat=f"estimated_{dt.value}_damage", value=per_type,
                mod_type="increased", damage_types=[dt],
                source="tree:estimate",
            ))
    else:
        # No specific types — add as generic
        out.increased.append(Modifier(
            stat="estimated_damage", value=specific_inc,
            mod_type="increased", source="tree:estimate",
        ))

    # Speed estimate
    speed_portion = speed_inc * 0.5
    crit_portion = speed_inc * 0.5
    if is_attack:
        out.increased_attack_speed += speed_portion
    else:
        out.increased_cast_speed += speed_portion
    out.increased_crit += crit_portion
    out.crit_multi += min(total_points * 0.8, 120)  # ~0.8% crit multi per point, cap 120%

    # --- Apply known keystone and notable effects ---
    resolute_technique = False
    for node in key_nodes:
        node_clean = node.strip()

        # Check keystones
        if node_clean in _KEYSTONE_EFFECTS:
            for mod in _KEYSTONE_EFFECTS[node_clean]:
                if mod.mod_type == "more":
                    out.more.append(mod)
                else:
                    out.increased.append(mod)
            if node_clean == "Resolute Technique":
                resolute_technique = True

        # Check notables
        if node_clean in _NOTABLE_EFFECTS:
            for mod in _NOTABLE_EFFECTS[node_clean]:
                if "crit_multi" in mod.stat:
                    out.crit_multi += mod.value
                elif "attack_speed" in mod.stat:
                    out.increased_attack_speed += mod.value
                elif "cast_speed" in mod.stat:
                    out.increased_cast_speed += mod.value
                elif "crit" in mod.stat:
                    out.increased_crit += mod.value
                else:
                    out.increased.append(mod)

    # Resolute Technique: zero out crit
    if resolute_technique:
        out.increased_crit = 0.0
        out.crit_multi = 0.0

    return out
