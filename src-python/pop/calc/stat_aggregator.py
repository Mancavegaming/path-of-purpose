"""
Stat aggregator for the damage calculation engine.

Collects all modifiers from every source in the build:
- Equipped items (mod text → mod_parser)
- Support gems (RePoE or hardcoded → modifiers)
- Passive tree nodes (stat text → mod_parser)
- Aura/herald effects from non-main skill groups
- Config (charges, buffs)

Produces a unified ParsedMods that the engine uses to build the StatPool.
"""

from __future__ import annotations

import logging

from pop.build_parser.models import Build, Item, SkillGroup
from pop.calc.ascendancy_effects import get_ascendancy_node, get_all_class_nodes
from pop.calc.aura_effects import AURA_GEM_NAMES, AuraEffect, get_aura_effect
from pop.calc.curse_effects import CURSE_GEM_NAMES, get_curse_effect
from pop.calc.flask_effects import get_flask_effect
from pop.calc.gem_data import SupportGemEffect, get_support_effect
from pop.calc.gem_quality import apply_quality_bonus
from pop.calc.keystone_effects import KEYSTONE_NAMES, get_keystone_flags
from pop.calc.mod_parser import ParsedMods, parse_mods
from pop.calc.models import CalcConfig, ConversionEntry, DamageType, Modifier
from pop.calc.repoe_loader import get_repoe_db

logger = logging.getLogger(__name__)

_WEAPON_SLOTS = {"Weapon 1", "Weapon 2"}


def collect_all_mods(
    build: Build,
    main_group: SkillGroup,
    is_attack: bool,
    use_tree: bool = True,
    use_repoe: bool = True,
    config: CalcConfig | None = None,
) -> tuple[ParsedMods, list[str]]:
    """Collect all modifiers from the build into a single ParsedMods.

    Args:
        build: Parsed PoB Build object.
        main_group: The main skill group being calculated.
        is_attack: Whether the main skill is an attack (vs spell).
        use_tree: Whether to extract passive tree node stats.
        use_repoe: Whether to use RePoE dynamic gem data.
        config: CalcConfig for curse effectiveness, flask toggle, etc.

    Returns:
        Tuple of (aggregated ParsedMods, list of warning strings).
    """
    all_parsed = ParsedMods()
    warnings: list[str] = []
    cfg = config or CalcConfig()

    # 1. Item mods
    _collect_item_mods(build, all_parsed)

    # 2. Support gem mods
    _collect_support_mods(main_group, all_parsed, warnings, use_repoe)

    # 2b. Active gem quality bonus
    active_gem = main_group.active_gem
    if active_gem and active_gem.quality > 0:
        apply_quality_bonus(active_gem.name, active_gem.quality, all_parsed)

    # 3. Aura/herald effects from other skill groups (scaled by aura effect)
    _collect_aura_effects(build, main_group, all_parsed, is_attack, warnings)

    # 4. Curse effects from non-main skill groups
    if cfg.use_curses:
        _collect_curse_effects(build, main_group, all_parsed, cfg, warnings)

    # 5. Flask effects (Flask 1-5 item slots)
    if cfg.use_flasks:
        _collect_flask_effects(build, all_parsed, warnings)

    # 6. Passive tree stats (real nodes or heuristic estimate)
    if use_tree:
        # Infer primary damage types from active gem for tree estimation
        tree_damage_types: set[DamageType] | None = None
        if active_gem:
            from pop.calc.gem_data import get_active_gem_stats
            gem_stats = get_active_gem_stats(active_gem.name)
            if gem_stats and gem_stats.base_damage:
                tree_damage_types = set(gem_stats.base_damage.keys())
        _collect_tree_stats(build, all_parsed, warnings, is_attack, tree_damage_types)

    # 7. Ascendancy effects
    _collect_ascendancy_effects(build, all_parsed, warnings)

    # 8. Keystone effects from passive tree or config
    _collect_keystone_effects(build, all_parsed, warnings)

    return all_parsed, warnings


def _collect_item_mods(build: Build, out: ParsedMods) -> None:
    """Extract modifiers from all equipped items."""
    items_by_slot = build.items_by_slot()
    for slot, item in items_by_slot.items():
        mod_texts = [m.text for m in item.all_mods]
        parsed = parse_mods(mod_texts, source=f"item:{slot}")

        if slot in _WEAPON_SLOTS:
            # Weapon mods are LOCAL — they modify the weapon's base stats,
            # not global modifiers.  The base weapon damage, APS, and crit
            # are already extracted from raw_text (which includes local mods).
            parsed.flat_added.clear()
            parsed.increased_attack_speed = 0.0  # local to weapon APS
            parsed.increased_crit = 0.0  # local to weapon crit chance
            # "increased Physical/Fire/Cold/Lightning/Chaos Damage" on weapons
            # is local (already baked into weapon damage line). Remove these
            # but keep global mods like "increased Elemental Damage with Attacks".
            parsed.increased = [
                m for m in parsed.increased
                if len(m.damage_types) != 1  # single-type = local
            ]

        out.merge(parsed)


def _collect_support_mods(
    main_group: SkillGroup,
    out: ParsedMods,
    warnings: list[str],
    use_repoe: bool,
) -> None:
    """Extract modifiers from support gems in the main skill group."""
    db = get_repoe_db() if use_repoe else None

    for support in main_group.support_gems:
        effect: SupportGemEffect | None = None

        # Try RePoE first
        if db and db.is_loaded:
            effect = db.get_support_stats(support.name, level=support.level)

        # Fall back to hardcoded
        if effect is None:
            effect = get_support_effect(support.name)

        if effect is None:
            warnings.append(f"Unknown support gem '{support.name}' — skipped.")
            continue

        # Apply gem quality bonus
        if support.quality > 0:
            apply_quality_bonus(support.name, support.quality, out)

        # Add modifiers
        for mod in effect.modifiers:
            if mod.mod_type == "more":
                out.more.append(mod)
            else:
                out.increased.append(mod)

        # Added damage
        for dtype, val in effect.added_damage.items():
            # Support flat damage is global (not weapon-local)
            out.flat_added[dtype] = out.flat_added.get(dtype, 0.0) + val

        # Penetration
        for dtype, val in effect.penetration.items():
            out.penetration[dtype] = out.penetration.get(dtype, 0.0) + val

        # Crit
        if effect.increased_crit:
            out.increased_crit += effect.increased_crit

        # Speed
        if effect.attack_speed_mod:
            out.increased_attack_speed += effect.attack_speed_mod
        if effect.cast_speed_mod:
            out.increased_cast_speed += effect.cast_speed_mod
        if effect.less_attack_speed:
            out.less_attack_speed.append(effect.less_attack_speed)

        # Impale
        if effect.impale_chance:
            out.impale_chance += effect.impale_chance
        if effect.increased_impale_effect:
            out.increased_impale_effect += effect.increased_impale_effect


def _collect_aura_effects(
    build: Build,
    main_group: SkillGroup,
    out: ParsedMods,
    is_attack: bool,
    warnings: list[str],
) -> None:
    """Collect aura/herald effects from non-main skill groups.

    Aura values are scaled by % increased Aura Effect from gear/tree.
    """
    # Aura effect multiplier from mods already collected (items, supports)
    aura_mult = 1.0 + out.increased_aura_effect / 100.0

    for group in build.skill_groups:
        if group is main_group:
            continue
        if not group.is_enabled:
            continue

        for gem in group.gems:
            if gem.is_support or not gem.is_enabled:
                continue
            if gem.name not in AURA_GEM_NAMES:
                continue

            effect = get_aura_effect(gem.name)
            if not effect:
                continue

            # Flat added damage (scaled by aura effect)
            for dtype, val in effect.flat_added.items():
                out.flat_added[dtype] = out.flat_added.get(dtype, 0.0) + val * aura_mult
            for dtype, val in effect.flat_added_attacks.items():
                out.flat_added_attacks[dtype] = (
                    out.flat_added_attacks.get(dtype, 0.0) + val * aura_mult
                )
            for dtype, val in effect.flat_added_spells.items():
                out.flat_added_spells[dtype] = (
                    out.flat_added_spells.get(dtype, 0.0) + val * aura_mult
                )

            # Modifiers (more/increased) — scale values by aura effect
            for mod in effect.modifiers:
                scaled_mod = Modifier(
                    stat=mod.stat,
                    value=mod.value * aura_mult,
                    mod_type=mod.mod_type,
                    damage_types=mod.damage_types,
                    category=mod.category,
                    source=mod.source,
                )
                if scaled_mod.mod_type == "more":
                    out.more.append(scaled_mod)
                else:
                    out.increased.append(scaled_mod)

            # Speed (scaled)
            if effect.increased_attack_speed:
                out.increased_attack_speed += effect.increased_attack_speed * aura_mult
            if effect.increased_cast_speed:
                out.increased_cast_speed += effect.increased_cast_speed * aura_mult

            # Crit (scaled)
            if effect.increased_crit:
                out.increased_crit += effect.increased_crit * aura_mult

            logger.debug("Applied aura effect: %s (%.0f%% aura effect)", gem.name, out.increased_aura_effect)


def _collect_tree_stats(
    build: Build,
    out: ParsedMods,
    warnings: list[str],
    is_attack: bool = True,
    damage_types: set[DamageType] | None = None,
) -> None:
    """Extract modifiers from allocated passive tree nodes.

    If real node IDs are available (PoB imports), uses exact node stats.
    Otherwise (AI-generated builds), falls back to heuristic estimation
    from total_points and key_nodes.
    """
    spec = build.active_passive_spec
    if not spec:
        return

    # Try real node stats first
    if spec.nodes:
        try:
            from pop.calc.tree_stats import get_node_stats
            tree_mods = get_node_stats(spec.nodes)
            out.merge(tree_mods)
            logger.debug("Collected stats from %d passive nodes", len(spec.nodes))
            return
        except Exception as e:
            warnings.append(f"Failed to load passive tree stats: {e}")
            logger.warning("Failed to load passive tree stats: %s", e)

    # Fall back to heuristic estimation for AI-generated builds
    if spec.total_points or spec.key_nodes:
        from pop.calc.tree_estimator import estimate_passive_stats
        estimated = estimate_passive_stats(spec, is_attack, damage_types)
        out.merge(estimated)
        logger.debug(
            "Estimated passive stats: %d points, %d key nodes",
            spec.total_points or 0, len(spec.key_nodes or []),
        )


def _collect_curse_effects(
    build: Build,
    main_group: SkillGroup,
    out: ParsedMods,
    config: CalcConfig,
    warnings: list[str],
) -> None:
    """Collect curse effects from non-main skill groups."""
    for group in build.skill_groups:
        if group is main_group:
            continue
        if not group.is_enabled:
            continue

        for gem in group.gems:
            if gem.is_support or not gem.is_enabled:
                continue
            if gem.name not in CURSE_GEM_NAMES:
                continue

            effect = get_curse_effect(gem.name)
            if not effect:
                continue

            eff_mult = config.curse_effectiveness

            # Resist reduction (scaled by curse effectiveness)
            for dtype, val in effect.resist_reduction.items():
                scaled = val * eff_mult
                out.curse_resist_reduction[dtype] = (
                    out.curse_resist_reduction.get(dtype, 0.0) + scaled
                )

            # Increased damage taken (scaled by curse effectiveness)
            for dtype, val in effect.increased_damage_taken.items():
                scaled = val * eff_mult
                out.enemy_increased_damage_taken[dtype] = (
                    out.enemy_increased_damage_taken.get(dtype, 0.0) + scaled
                )

            if effect.increased_damage_taken_generic > 0:
                out.enemy_increased_damage_taken_generic += (
                    effect.increased_damage_taken_generic * eff_mult
                )

            logger.debug("Applied curse effect: %s (%.0f%% effectiveness)", gem.name, eff_mult * 100)


_FLASK_SLOTS = {"Flask 1", "Flask 2", "Flask 3", "Flask 4", "Flask 5"}


def _collect_flask_effects(
    build: Build,
    out: ParsedMods,
    warnings: list[str],
) -> None:
    """Collect flask effects from Flask 1-5 item slots."""
    items_by_slot = build.items_by_slot()

    for slot in _FLASK_SLOTS:
        flask_item = items_by_slot.get(slot)
        if not flask_item:
            continue

        flask_name = flask_item.name or ""

        # Try unique flask database first
        effect = get_flask_effect(flask_name)
        if effect:
            # Lucky crit
            if effect.lucky_crit:
                out.special_flags["lucky_crit"] = True

            # Enemy increased damage taken
            if effect.enemy_increased_damage_taken > 0:
                out.enemy_increased_damage_taken_generic += effect.enemy_increased_damage_taken

            # Flat added damage
            for dtype, val in effect.flat_added.items():
                out.flat_added[dtype] = out.flat_added.get(dtype, 0.0) + val

            # Modifiers
            for mod in effect.modifiers:
                if mod.mod_type == "more":
                    out.more.append(mod)
                else:
                    out.increased.append(mod)

            # Penetration
            for dtype, val in effect.penetration.items():
                out.penetration[dtype] = out.penetration.get(dtype, 0.0) + val

            # Gained-as conversions
            for from_type, to_type, pct in effect.conversions_gained_as:
                out.conversions.append(ConversionEntry(
                    type_from=from_type, type_to=to_type,
                    percent=pct, is_gained_as=True,
                    source=f"flask:{flask_name}",
                ))

            # Crit
            if effect.increased_crit:
                out.increased_crit += effect.increased_crit
            if effect.crit_multi:
                out.crit_multi += effect.crit_multi

            # Speed
            if effect.increased_attack_speed:
                out.increased_attack_speed += effect.increased_attack_speed
            if effect.increased_cast_speed:
                out.increased_cast_speed += effect.increased_cast_speed

            logger.debug("Applied flask effect: %s", flask_name)
        else:
            # Parse flask mod text for suffix effects
            mod_texts = [m.text for m in flask_item.all_mods]
            if mod_texts:
                parsed = parse_mods(mod_texts, source=f"flask:{slot}")
                out.merge(parsed)


def _collect_ascendancy_effects(
    build: Build,
    out: ParsedMods,
    warnings: list[str],
) -> None:
    """Collect ascendancy node effects from allocated passive nodes.

    Ascendancy nodes are only applied if they appear in the build's
    allocated_ascendancy_nodes list (set by PoB imports or AI builds).
    """
    # Get explicitly allocated ascendancy node names
    allocated_names: list[str] = getattr(build, "allocated_ascendancy_nodes", None) or []
    if not allocated_names:
        return

    for node_name in allocated_names:
        node_effect = get_ascendancy_node(node_name)
        if not node_effect:
            continue

        _apply_ascendancy_node(node_effect, out)
        logger.debug("Applied ascendancy node: %s (%s)", node_name, node_effect.class_name)


def _apply_ascendancy_node(node: object, out: ParsedMods) -> None:
    """Apply a single ascendancy node's effects to ParsedMods."""
    from pop.calc.ascendancy_effects import AscendancyNode
    if not isinstance(node, AscendancyNode):
        return

    # Modifiers
    for mod in node.modifiers:
        if mod.mod_type == "more":
            out.more.append(mod)
        else:
            out.increased.append(mod)

    # Conversions
    for conv in node.conversions:
        out.conversions.append(conv)

    # Penetration
    for dtype, val in node.penetration.items():
        out.penetration[dtype] = out.penetration.get(dtype, 0.0) + val

    # Crit
    if node.increased_crit:
        out.increased_crit += node.increased_crit
    if node.crit_multi:
        out.crit_multi += node.crit_multi
    if node.base_crit_bonus:
        out.special_flags["base_crit_bonus"] = (
            float(out.special_flags.get("base_crit_bonus", 0.0))
            + node.base_crit_bonus
        )

    # Speed
    if node.increased_speed:
        out.increased_attack_speed += node.increased_speed
        out.increased_cast_speed += node.increased_speed

    # Special flags
    for key, val in node.special.items():
        out.special_flags[key] = val


def _collect_keystone_effects(
    build: Build,
    out: ParsedMods,
    warnings: list[str],
) -> None:
    """Detect allocated keystones and apply their special flags.

    Keystones can be detected from:
    1. Build's allocated_keystones list (explicit)
    2. PoB config entries (e.g. keystone_ResoluteTechnique)
    """
    # Check explicit keystone list
    allocated_keystones: list[str] = getattr(build, "allocated_keystones", None) or []

    for ks_name in allocated_keystones:
        flags = get_keystone_flags(ks_name)
        if flags:
            for key, val in flags.items():
                out.special_flags[key] = val
            logger.debug("Applied keystone: %s", ks_name)
