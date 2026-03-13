"""
Main damage calculation engine — aligned with Path of Building formulas.

PoB DPS pipeline:
    1. Base damage (weapon for attacks, gem for spells)
    2. Flat added damage × damage effectiveness
    3. Per damage type: (base × INC × MORE) + flat_added  [PoB order]
    4. Conversion with source tracking (both source + final type mods apply)
    5. Enemy mitigation (resist - exposure - penetration)
    6. Crit: avgHit = nonCritHit × (1-cc) + critHit × cc
    7. Hit chance (attacks only, spells always hit)
    8. Speed: base × (1 + INC%) × product(MORE)
    9. TotalDPS = AverageDamage × Speed
"""

from __future__ import annotations

import re

from pop.build_parser.models import Build, Item, Gem, SkillGroup
from pop.calc.config_reader import read_config
from pop.calc.crit_calc import calc_effective_crit
from pop.calc.defense_calc import calc_mitigation_multi
from pop.calc.dot_calc import (
    calc_bleed_dps,
    calc_effective_ailment_chance,
    calc_ignite_dps,
    calc_poison_dps,
)
from pop.calc.gem_data import ActiveGemStats, get_active_gem_stats
from pop.calc.impale_calc import calc_impale_dps
from pop.calc.map_mods import apply_map_mods
from pop.calc.player_defense_calc import calc_player_defences
from pop.calc.mod_parser import ParsedMods
from pop.calc.models import (
    CalcConfig,
    CalcResult,
    DamageType,
    Modifier,
    StatPool,
    TypeDamage,
)
from pop.calc.repoe_loader import get_repoe_db
from pop.calc.speed_calc import calc_hits_per_second
from pop.calc.stat_aggregator import collect_all_mods

# Regex for weapon damage range lines in PoB item raw text
_RE_WEAPON_DMG_LINE = re.compile(
    r"(Physical|Fire|Cold|Lightning|Chaos) Damage:\s*(\d+)[–\-](\d+)",
    re.IGNORECASE,
)

_RE_WEAPON_APS = re.compile(
    r"Attacks per Second:\s*([\d.]+)",
    re.IGNORECASE,
)

_RE_WEAPON_CRIT = re.compile(
    r"Critical (?:Strike )?Chance:\s*([\d.]+)%",
    re.IGNORECASE,
)

_DTYPE_MAP: dict[str, DamageType] = {
    "physical": DamageType.PHYSICAL,
    "fire": DamageType.FIRE,
    "cold": DamageType.COLD,
    "lightning": DamageType.LIGHTNING,
    "chaos": DamageType.CHAOS,
}

_WEAPON_SLOTS = {"Weapon 1", "Weapon 2"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def calculate_dps(
    build: Build,
    config_overrides: CalcConfig | None = None,
    use_tree: bool = True,
    use_repoe: bool = True,
) -> CalcResult:
    """Calculate full DPS for a build's main skill (PoB-aligned).

    Args:
        build: Parsed PoB Build object.
        config_overrides: Optional config overrides (enemy resist, etc.).
        use_tree: Whether to extract passive tree node stats.
        use_repoe: Whether to use RePoE dynamic gem data.

    Returns:
        CalcResult with total DPS and per-type breakdown.
    """
    warnings: list[str] = []

    # Step 1: Resolve config
    tree_ver = build.passive_specs[0].tree_version if build.passive_specs else ""
    config = config_overrides or read_config(build.config, tree_ver)

    # Step 1b: Apply map mods if specified
    map_less_damage = 0.0
    if config.map_mod_names:
        map_warnings, map_less_damage = apply_map_mods(config, config.map_mod_names)
        warnings.extend(map_warnings)

    # Step 2: Identify main skill
    main_group = build.main_skill
    if not main_group:
        return CalcResult(warnings=["No main skill group found."])

    active_gem = main_group.active_gem
    if not active_gem:
        return CalcResult(warnings=["No active gem in main skill group."])

    # Try RePoE first for gem stats, fall back to hardcoded
    gem_stats: ActiveGemStats | None = None
    db = get_repoe_db() if use_repoe else None
    if db and db.is_loaded:
        gem_stats = db.get_active_stats(active_gem.name, level=active_gem.level)
    if gem_stats is None:
        gem_stats = get_active_gem_stats(active_gem.name)

    is_attack = gem_stats.is_attack if gem_stats else _guess_is_attack(active_gem, main_group)
    is_spell = gem_stats.is_spell if gem_stats else not is_attack

    # Detect skill sub-types from gem tags
    gem_tags = set(gem_stats.tags) if gem_stats else set()
    is_totem = "totem" in gem_tags
    is_trap = "trap" in gem_tags
    is_mine = "mine" in gem_tags
    is_minion = "minion" in gem_tags
    is_projectile = "projectile" in gem_tags
    is_brand = "brand" in gem_tags

    # Check support gems for totem/trap/mine conversion
    for sg in main_group.support_gems:
        sn = sg.name.lower()
        if "spell totem" in sn or "ballista totem" in sn:
            is_totem = True
        elif "trap support" in sn:
            is_trap = True
        elif "mine support" in sn or "blastchain" in sn or "high-impact" in sn:
            is_mine = True

    if not gem_stats:
        warnings.append(f"Unknown gem '{active_gem.name}' — using heuristic detection.")

    # Step 3: Determine base damage
    weapon = _find_main_weapon(build)
    weapon_base = _extract_weapon_damage(weapon) if weapon else {}
    weapon_aps = _extract_weapon_aps(weapon) if weapon else 1.2
    weapon_crit = _extract_weapon_crit(weapon) if weapon else 5.0

    if is_attack:
        base_damage = dict(weapon_base)
        base_speed = weapon_aps
        base_crit = weapon_crit
        if not base_damage:
            # Debug: show what items we received and their slots
            warnings.append("No weapon damage found — using default.")
            base_damage = {DamageType.PHYSICAL: 50.0}
    else:
        base_damage = dict(gem_stats.base_damage) if gem_stats else {}
        base_speed = (
            1.0 / gem_stats.base_cast_time
            if gem_stats and gem_stats.base_cast_time > 0
            else 1.0
        )
        base_crit = gem_stats.base_crit if gem_stats else 5.0
        if not base_damage:
            warnings.append(f"No base damage data for spell '{active_gem.name}'.")

    if is_attack and gem_stats and gem_stats.attack_speed_multiplier != 1.0:
        base_speed *= gem_stats.attack_speed_multiplier

    dmg_effectiveness = gem_stats.damage_effectiveness if gem_stats else 1.0

    # Step 4: Collect ALL modifiers (items + supports + tree + auras + curses + flasks)
    all_parsed, agg_warnings = collect_all_mods(
        build, main_group, is_attack,
        use_tree=use_tree, use_repoe=use_repoe,
        config=config,
    )
    warnings.extend(agg_warnings)

    # Step 5: Build StatPool
    pool = StatPool()
    pool.base_crit_chance = base_crit
    pool.base_speed = base_speed

    # Flat added damage (scaled by damage effectiveness)
    # For attacks: gem's own "adds X damage" (e.g. Elemental Hit) is flat added too
    flat_source = all_parsed.flat_added_attacks if is_attack else all_parsed.flat_added_spells
    for dtype in DamageType:
        generic = all_parsed.flat_added.get(dtype, 0.0)
        specific = flat_source.get(dtype, 0.0)
        # Attack gems with base_damage (Elemental Hit, Smite, etc.) —
        # their "adds X to Y damage" is flat added on top of weapon damage
        gem_flat = 0.0
        if is_attack and gem_stats and gem_stats.base_damage:
            gem_flat = gem_stats.base_damage.get(dtype, 0.0)
        total_flat = (generic + specific + gem_flat) * dmg_effectiveness
        if total_flat > 0:
            pool.flat_added[dtype] = total_flat

    pool.increased_mods = _filter_mods_by_skill_type(all_parsed.increased, is_attack, is_spell)
    pool.more_mods = _filter_mods_by_skill_type(all_parsed.more, is_attack, is_spell)
    pool.conversions = all_parsed.conversions
    pool.increased_crit = all_parsed.increased_crit
    if is_spell:
        pool.increased_crit += all_parsed.increased_crit_spells
    pool.crit_multiplier = 150.0 + all_parsed.crit_multi
    pool.increased_speed = (
        all_parsed.increased_attack_speed if is_attack else all_parsed.increased_cast_speed
    )
    pool.more_speed = (
        all_parsed.more_attack_speed if is_attack else all_parsed.more_cast_speed
    )
    pool.penetration = dict(all_parsed.penetration)
    pool.exposure = dict(all_parsed.exposure)

    _apply_charge_bonuses(pool, config)

    # Apply ascendancy base crit bonus (e.g. Assassin's Deadly Infusion: +2% base)
    base_crit_bonus = float(all_parsed.special_flags.get("base_crit_bonus", 0.0))
    if base_crit_bonus > 0:
        pool.base_crit_chance += base_crit_bonus

    # --- Keystone effects ---
    resolute_technique = bool(all_parsed.special_flags.get("resolute_technique"))
    elemental_overload = bool(all_parsed.special_flags.get("elemental_overload"))
    avatar_of_fire = bool(all_parsed.special_flags.get("avatar_of_fire"))
    point_blank = bool(all_parsed.special_flags.get("point_blank"))
    crimson_dance = bool(all_parsed.special_flags.get("crimson_dance"))
    ancestral_bond = bool(all_parsed.special_flags.get("ancestral_bond"))
    pain_attunement = bool(all_parsed.special_flags.get("pain_attunement"))

    # Avatar of Fire: 50% of non-fire converted to fire (add conversion entries)
    if avatar_of_fire:
        for src_type in [DamageType.PHYSICAL, DamageType.LIGHTNING, DamageType.COLD]:
            from pop.calc.models import ConversionEntry
            pool.conversions.append(ConversionEntry(
                type_from=src_type, type_to=DamageType.FIRE,
                percent=50.0, source="keystone:Avatar of Fire",
            ))

    # Pain Attunement: 30% more spell damage on low life
    if pain_attunement and is_spell:
        pool.more_mods.append(Modifier(
            stat="more_spell_damage_low_life", value=30.0,
            mod_type="more", source="keystone:Pain Attunement",
        ))

    # =======================================================================
    # PoB-aligned damage calculation
    # =======================================================================
    #
    # PoB's calcDamage() per type:
    #   result = (base * INC * MORE) + flat_added
    #
    # Then conversion tracks source→final, and INC/MORE for BOTH source
    # and final types apply to the base portion.
    #
    # Our approach: compute base+flat per type, then do conversion,
    # then apply INC/MORE per contribution. This is equivalent because
    # all INC/MORE are applied to each contribution (base portion that
    # went through conversion).

    # Step 6: Base + flat per type (pre-conversion)
    damage_per_type: dict[DamageType, float] = {}
    for dtype in DamageType:
        base = base_damage.get(dtype, 0.0)
        flat = pool.flat_added.get(dtype, 0.0)
        damage_per_type[dtype] = base + flat

    # Step 7: Apply conversion with source tracking
    from pop.calc.conversion import apply_conversion_tracked
    conv_result = apply_conversion_tracked(damage_per_type, pool.conversions)

    # Step 8: Apply increased + more per contribution
    # For each contribution, modifiers matching EITHER source or final type apply.
    type_totals: dict[DamageType, float] = {dt: 0.0 for dt in DamageType}

    for contrib in conv_result.contributions:
        if contrib.amount <= 0:
            continue

        relevant_types = {contrib.source_type, contrib.final_type}

        # INC: sum all applicable increased% (additive pool)
        total_inc = pool.total_increased_for_types(relevant_types)
        after_inc = contrib.amount * (1.0 + total_inc / 100.0)

        # MORE: product of all applicable more multipliers
        total_more = pool.total_more_for_types(relevant_types)
        after_more = after_inc * total_more

        type_totals[contrib.final_type] += after_more

    # Step 9: Enemy mitigation per type
    type_breakdowns: list[TypeDamage] = []
    total_hit_after_mit = 0.0
    total_hit_before_mit = 0.0

    crits_ignore_resist = bool(all_parsed.special_flags.get("crits_ignore_resist"))
    # Track per-type damage before/after mitigation for Inquisitor crit calc
    per_type_before_mit: dict[DamageType, float] = {}
    per_type_after_mit: dict[DamageType, float] = {}

    for dtype in DamageType:
        dmg_after_mods = type_totals[dtype]

        if dmg_after_mods <= 0:
            type_breakdowns.append(TypeDamage(damage_type=dtype))
            continue

        total_hit_before_mit += dmg_after_mods
        per_type_before_mit[dtype] = dmg_after_mods

        pen = pool.penetration.get(dtype, 0.0)
        exp = pool.exposure.get(dtype, 0.0)
        curse_red = all_parsed.curse_resist_reduction.get(dtype, 0.0)
        mit_multi = calc_mitigation_multi(dtype, config, pen, dmg_after_mods, exp, curse_red)
        after_mit = dmg_after_mods * mit_multi

        total_hit_after_mit += after_mit
        per_type_after_mit[dtype] = after_mit

        base_val = base_damage.get(dtype, 0.0)
        pre_conv = damage_per_type.get(dtype, 0.0)
        post_conv = conv_result.final_damage.get(dtype, 0.0)

        type_breakdowns.append(TypeDamage(
            damage_type=dtype,
            base=base_val,
            after_flat=pre_conv,
            after_conversion=post_conv,
            after_increased=dmg_after_mods,
            after_more=dmg_after_mods,
            final_hit=dmg_after_mods,
            after_mitigation=after_mit,
        ))

    # Step 9b: Enemy "increased damage taken" multiplier
    # Shock, Vulnerability, Wither, Intimidate, Unnerve, flask effects — all additive
    damage_taken_inc = 0.0
    damage_taken_inc += config.shock_value  # Shock (all types)
    damage_taken_inc += all_parsed.enemy_increased_damage_taken_generic  # Bottled Faith etc.

    # Per-type contributions (applied uniformly to total for simplicity)
    # Vulnerability: physical damage taken
    vuln_phys = all_parsed.enemy_increased_damage_taken.get(DamageType.PHYSICAL, 0.0)

    # Wither: chaos damage taken
    wither_chaos = config.wither_stacks * 6.0

    # Intimidate: 10% increased attack damage taken
    intimidate_val = 10.0 if config.enemy_is_intimidated and is_attack else 0.0
    # Unnerve: 10% increased spell damage taken
    unnerve_val = 10.0 if config.enemy_is_unnerved and is_spell else 0.0

    # Apply per-type damage taken adjustments
    adjusted_hit_after_mit = 0.0
    for dtype in DamageType:
        type_dmg = per_type_after_mit.get(dtype, 0.0)
        if type_dmg <= 0:
            continue

        type_taken_inc = damage_taken_inc + intimidate_val + unnerve_val
        if dtype == DamageType.PHYSICAL:
            type_taken_inc += vuln_phys
        if dtype == DamageType.CHAOS:
            type_taken_inc += wither_chaos

        type_dmg *= (1.0 + type_taken_inc / 100.0)
        adjusted_hit_after_mit += type_dmg

    if adjusted_hit_after_mit > 0:
        total_hit_after_mit = adjusted_hit_after_mit

    enemy_damage_taken_multi = (
        total_hit_after_mit / sum(per_type_after_mit.values())
        if sum(per_type_after_mit.values()) > 0
        else 1.0
    )

    # Step 10: Crit — PoB formula:
    #   AverageHit = nonCritAvg × (1 - cc) + critAvg × cc
    #   critAvg = nonCritAvg × (critMulti / 100)
    #   So: AverageHit = nonCritAvg × (1 + cc × (critMulti/100 - 1))
    lucky_crit = bool(all_parsed.special_flags.get("lucky_crit"))

    if resolute_technique:
        # Resolute Technique: always hit, never crit
        crit_chance = 0.0
        crit_multi_pct = 100.0
        crit_multi_decimal = 1.0
        effective_crit_multi = 1.0
        avg_hit = total_hit_after_mit
    elif elemental_overload:
        # Elemental Overload: 40% more elemental damage, crit multi locked to 100%
        # Must have recently crit (assumed yes in PoB with any crit chance)
        crit_chance = calc_effective_crit(
            pool.base_crit_chance, pool.increased_crit, config.is_poe2, lucky=lucky_crit,
        )
        crit_multi_pct = 100.0  # No extra crit damage
        crit_multi_decimal = 1.0
        effective_crit_multi = 1.0
        # 40% more elemental damage applied as a multiplier
        eo_bonus = 0.0
        for dtype in [DamageType.FIRE, DamageType.COLD, DamageType.LIGHTNING]:
            eo_bonus += per_type_after_mit.get(dtype, 0.0) * 0.40
        avg_hit = total_hit_after_mit + eo_bonus
    else:
        crit_chance = calc_effective_crit(
            pool.base_crit_chance, pool.increased_crit, config.is_poe2, lucky=lucky_crit,
        )
        crit_multi_pct = pool.crit_multiplier  # e.g. 150%
        crit_multi_decimal = crit_multi_pct / 100.0  # 1.5

        if crits_ignore_resist:
            # Inquisitor: crits ignore enemy elemental resistances
            non_crit_hit = total_hit_after_mit
            crit_hit = total_hit_before_mit * crit_multi_decimal
            avg_hit = non_crit_hit * (1.0 - crit_chance) + crit_hit * crit_chance
            effective_crit_multi = (
                avg_hit / total_hit_after_mit if total_hit_after_mit > 0 else 1.0
            )
        else:
            # Standard PoB formula
            effective_crit_multi = 1.0 + crit_chance * (crit_multi_decimal - 1.0)
            avg_hit = total_hit_after_mit * effective_crit_multi

    # Point Blank: 30% more projectile damage at close range (single target assumed)
    if point_blank and is_projectile:
        avg_hit *= 1.30

    # Step 11: Hit chance — attacks need accuracy, spells always hit
    if resolute_technique:
        hit_chance = 1.0  # RT always hits
    elif is_attack:
        hit_chance = _calc_hit_chance(all_parsed, config)
    else:
        hit_chance = 1.0

    # PoB: AverageDamage = AverageHit × HitChance
    avg_damage = avg_hit * hit_chance

    # Step 12: Speed
    less_spd = all_parsed.less_attack_speed if is_attack else []
    hits_per_second = calc_hits_per_second(
        pool.base_speed,
        pool.increased_speed,
        pool.more_speed,
        less_spd,
    )

    # Step 13: Final DPS — PoB: TotalDPS = AverageDamage × Speed
    total_dps = avg_damage * hits_per_second

    # Map mod: "Players deal X% less Damage"
    if map_less_damage > 0:
        total_dps *= (1.0 - map_less_damage / 100.0)

    # Ancestral Bond: you cannot deal damage with hits directly (totems do)
    if ancestral_bond and not is_totem:
        total_dps = 0.0
        warnings.append("Ancestral Bond: player hits deal no damage (totems only).")

    # Avatar of Fire: deal no non-fire damage (already converted above, but zero out remnants)
    if avatar_of_fire:
        for tb in type_breakdowns:
            if tb.damage_type != DamageType.FIRE:
                tb.after_mitigation = 0.0

    # Step 13b: Totem multiplier — multiply DPS by number of active totems
    num_totems = 0
    if is_totem:
        base_totems = 1
        bonus_totems = all_parsed.max_totem_bonus
        # Multiple Totems Support adds +2
        for sg in main_group.support_gems:
            if "multiple totems" in sg.name.lower():
                bonus_totems += 2
        num_totems = base_totems + bonus_totems
        total_dps *= num_totems

    # Step 13c: Minion detection — warn that minion DPS is not fully calculated
    if is_minion:
        warnings.append(
            f"'{active_gem.name}' is a minion skill — DPS shown is base hit, "
            "not minion DPS (minion scaling not yet implemented)."
        )

    # Step 13d: Impale DPS
    impale_dps_val = 0.0
    if is_attack and all_parsed.impale_chance > 0:
        # Get physical damage after mitigation
        phys_after_mit = per_type_after_mit.get(DamageType.PHYSICAL, 0.0)
        # Apply crit averaging to phys portion
        phys_avg_hit = phys_after_mit * effective_crit_multi * hit_chance
        max_impale_stacks = 5 + all_parsed.extra_impale_stacks
        impale_dps_val = calc_impale_dps(
            phys_avg_hit,
            min(all_parsed.impale_chance / 100.0, 1.0),
            hits_per_second,
            all_parsed.increased_impale_effect,
            max_impale_stacks,
        )

    # Step 14: DoT ailment calculations
    pool.increased_dot_mods = all_parsed.increased_dot
    pool.more_dot_mods = all_parsed.more_dot
    pool.dot_multi = all_parsed.dot_multi
    pool.dot_multi_fire = all_parsed.dot_multi_fire
    pool.dot_multi_phys = all_parsed.dot_multi_phys
    pool.dot_multi_chaos = all_parsed.dot_multi_chaos
    pool.chance_to_ignite = all_parsed.chance_to_ignite
    pool.chance_to_bleed = all_parsed.chance_to_bleed
    pool.chance_to_poison = all_parsed.chance_to_poison
    pool.increased_ignite_duration = all_parsed.increased_ignite_duration
    pool.increased_bleed_duration = all_parsed.increased_bleed_duration
    pool.increased_poison_duration = all_parsed.increased_poison_duration

    # Use pre-mitigation hit damage per type for ailment base
    hit_fire = type_totals.get(DamageType.FIRE, 0.0)
    hit_phys = type_totals.get(DamageType.PHYSICAL, 0.0)
    hit_chaos = type_totals.get(DamageType.CHAOS, 0.0)

    eff_ignite = calc_effective_ailment_chance(
        pool.chance_to_ignite, crit_chance, "ignite",
    )
    eff_bleed = calc_effective_ailment_chance(
        pool.chance_to_bleed, crit_chance, "bleed",
    )
    eff_poison = calc_effective_ailment_chance(
        pool.chance_to_poison, crit_chance, "poison",
    )

    ignite_dps = calc_ignite_dps(hit_fire, pool, config, eff_ignite)
    bleed_dps = calc_bleed_dps(hit_phys, pool, config, eff_bleed, is_attack)
    poison_dps = calc_poison_dps(
        hit_phys, hit_chaos, pool, config, eff_poison, hits_per_second,
    )

    # Crimson Dance: bleed stacks up to 8 times, 50% less while moving
    if crimson_dance:
        # Override bleed_dps calc: stacks 8x, but 50% less while moving
        # For simplicity, re-scale: 8 stacks * 0.5 moving penalty = 4x base
        # vs default 1 stack * 3x moving = 3x. So Crimson Dance is better for
        # builds with high bleed chance / attack speed
        pass  # DoT calc already handles base; flagged for future refinement

    total_dot = ignite_dps + bleed_dps + poison_dps
    combined = total_dps + total_dot + impale_dps_val

    # Step 15: Player defence calculation
    defence = calc_player_defences(all_parsed, config)

    return CalcResult(
        total_dps=round(total_dps, 1),
        hit_damage=round(avg_hit, 1),
        hits_per_second=round(hits_per_second, 2),
        effective_crit_multi=round(effective_crit_multi, 3),
        crit_chance=round(crit_chance * 100, 1),
        hit_chance=round(hit_chance * 100, 1),
        type_breakdown=type_breakdowns,
        ignite_dps=round(ignite_dps, 1),
        bleed_dps=round(bleed_dps, 1),
        poison_dps=round(poison_dps, 1),
        total_dot_dps=round(total_dot, 1),
        impale_dps=round(impale_dps_val, 1),
        combined_dps=round(combined, 1),
        enemy_damage_taken_multi=round(enemy_damage_taken_multi, 3),
        skill_name=active_gem.name,
        is_attack=is_attack,
        is_totem=is_totem,
        is_trap=is_trap,
        is_mine=is_mine,
        is_minion=is_minion,
        num_totems=num_totems,
        defence=defence,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_main_weapon(build: Build) -> Item | None:
    items_by_slot = build.items_by_slot()
    return items_by_slot.get("Weapon 1")


def _extract_weapon_damage(weapon: Item) -> dict[DamageType, float]:
    result: dict[DamageType, float] = {}
    text = weapon.raw_text
    if not text:
        return _extract_weapon_damage_from_mods(weapon)
    for m in _RE_WEAPON_DMG_LINE.finditer(text):
        dtype = _DTYPE_MAP.get(m.group(1).lower())
        if dtype:
            avg = (float(m.group(2)) + float(m.group(3))) / 2.0
            result[dtype] = result.get(dtype, 0.0) + avg
    if not result:
        result = _extract_weapon_damage_from_mods(weapon)
    # Fall back to base type lookup if still empty
    if not result:
        result = _extract_weapon_damage_from_base(weapon)
    return result


def _extract_weapon_damage_from_mods(weapon: Item) -> dict[DamageType, float]:
    result: dict[DamageType, float] = {}
    _RE_ADDS = re.compile(
        r"Adds (\d+) to (\d+) (Physical|Fire|Cold|Lightning|Chaos) Damage",
        re.IGNORECASE,
    )
    # Check parsed mod objects
    for mod in weapon.all_mods:
        m = _RE_ADDS.search(mod.text)
        if m:
            dtype = _DTYPE_MAP.get(m.group(3).lower())
            if dtype:
                avg = (float(m.group(1)) + float(m.group(2))) / 2.0
                result[dtype] = result.get(dtype, 0.0) + avg
    # Also scan raw_text (PoB may have mod lines not parsed into mod objects)
    if not result and weapon.raw_text:
        for m in _RE_ADDS.finditer(weapon.raw_text):
            dtype = _DTYPE_MAP.get(m.group(3).lower())
            if dtype:
                avg = (float(m.group(1)) + float(m.group(2))) / 2.0
                result[dtype] = result.get(dtype, 0.0) + avg
    return result


def _extract_weapon_damage_from_base(weapon: Item) -> dict[DamageType, float]:
    """Look up base weapon damage from the weapon bases DB using item base_type."""
    bt = getattr(weapon, "base_type", "") or ""
    if not bt:
        return {}
    try:
        from pop.calc.synthetic_items import _WEAPON_BASES
        entry = _WEAPON_BASES.get(bt)
        if entry:
            _, phys_min, phys_max, _, _, _ = entry
            if phys_min > 0 or phys_max > 0:
                return {DamageType.PHYSICAL: (phys_min + phys_max) / 2.0}
    except ImportError:
        pass
    return {}


def _extract_weapon_aps(weapon: Item) -> float:
    if weapon.raw_text:
        m = _RE_WEAPON_APS.search(weapon.raw_text)
        if m:
            return float(m.group(1))
    # Fall back to base type
    bt = getattr(weapon, "base_type", "") or ""
    if bt:
        try:
            from pop.calc.synthetic_items import _WEAPON_BASES
            entry = _WEAPON_BASES.get(bt)
            if entry:
                return entry[3]  # aps
        except ImportError:
            pass
    return 1.2


def _extract_weapon_crit(weapon: Item) -> float:
    if weapon.raw_text:
        m = _RE_WEAPON_CRIT.search(weapon.raw_text)
        if m:
            return float(m.group(1))
    # Fall back to base type
    bt = getattr(weapon, "base_type", "") or ""
    if bt:
        try:
            from pop.calc.synthetic_items import _WEAPON_BASES
            entry = _WEAPON_BASES.get(bt)
            if entry:
                return entry[4]  # crit
        except ImportError:
            pass
    return 5.0


def _guess_is_attack(gem: Gem, group: SkillGroup) -> bool:
    name = gem.name.lower()
    attack_keywords = [
        "strike", "slash", "slam", "cleave", "cyclone", "lacerate",
        "flicker", "shot", "arrow", "barrage", "rain of", "blast",
        "split", "shrapnel", "tornado", "kinetic", "power siphon",
        "blade flurry", "molten", "frost blades", "lightning strike",
        "wild", "spectral", "reave", "double", "dual", "viper",
        "puncture", "bleed", "smite", "consecrated path",
        "elemental hit", "hit",
    ]
    if any(kw in name for kw in attack_keywords):
        return True
    if group.slot in _WEAPON_SLOTS:
        return True
    return False


# Stat names that only apply to spells (not attacks)
_SPELL_ONLY_STATS = frozenset({
    "increased_spell_damage", "more_spell_damage", "more_spell_lightning",
})

# Stat names that only apply to attacks (not spells)
_ATTACK_ONLY_STATS = frozenset({
    "increased_attack_damage", "more_attack_damage",
    "more_melee_damage", "more_melee_damage_vs_bleeding", "more_melee_physical_damage",
    "more_elemental_attack_damage",
})


def _filter_mods_by_skill_type(
    mods: list[Modifier], is_attack: bool, is_spell: bool,
) -> list[Modifier]:
    """Remove modifiers that don't apply to the current skill type."""
    result = []
    for mod in mods:
        if is_attack and mod.stat in _SPELL_ONLY_STATS:
            continue
        if is_spell and mod.stat in _ATTACK_ONLY_STATS:
            continue
        result.append(mod)
    return result


def _apply_charge_bonuses(pool: StatPool, config: CalcConfig) -> None:
    if config.use_power_charges and config.power_charges > 0:
        pool.increased_crit += config.power_charges * 40.0

    if config.use_frenzy_charges and config.frenzy_charges > 0:
        pool.more_mods.append(Modifier(
            stat="frenzy_charge_damage",
            value=config.frenzy_charges * 4.0,
            mod_type="more",
            source="charges:frenzy",
        ))
        pool.increased_speed += config.frenzy_charges * 4.0

    # Endurance charges: purely defensive (no DPS effect)
    # +4% physical damage reduction per charge
    # +4% to all elemental resistances per charge
    # Tracked via DefenceResult, not applied to damage pool


def _calc_hit_chance(parsed: ParsedMods, config: CalcConfig) -> float:
    """Calculate attack hit chance using PoB accuracy formula.

    PoB formula: hitChance = accuracy / (accuracy + (evasion/4)^0.8)
    Clamped to 5%-100%.

    Base accuracy ≈ level * 2 (default level 90 → 180 base).
    Dexterity adds +2 accuracy per point (not tracked separately yet).
    """
    # Base accuracy from character level (default 90)
    level = config.enemy_level if config.enemy_level > 0 else 90
    # PoB base accuracy = 0.5 * level (but effective base from level + base is ~2*level)
    base_accuracy = level * 2.0

    # Add flat accuracy from gear/tree/gems
    total_flat = base_accuracy + parsed.flat_accuracy

    # Apply increased accuracy rating
    accuracy = total_flat * (1.0 + parsed.increased_accuracy / 100.0)

    # Enemy evasion — if not set, use level-based estimate
    enemy_evasion = config.enemy_evasion
    if enemy_evasion <= 0:
        # Default: no evasion specified → use 95% hit chance fallback
        return 0.95

    # PoB formula: hit = acc / (acc + (evasion/4)^0.8)
    evasion_term = (enemy_evasion / 4.0) ** 0.8
    if accuracy + evasion_term <= 0:
        return 0.05

    hit_chance = accuracy / (accuracy + evasion_term)

    # Clamp 5%-100%
    return max(0.05, min(1.0, hit_chance))
