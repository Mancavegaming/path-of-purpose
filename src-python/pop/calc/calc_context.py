"""
DPS context helpers for the AI advisor.

Provides functions to calculate DPS across all skill groups in a build
and format results into text summaries for inclusion in AI prompts.
"""

from __future__ import annotations

from pop.build_parser.models import Build
from pop.calc.engine import calculate_dps
from pop.calc.models import CalcConfig, CalcResult, DamageType


def format_dps_summary(result: CalcResult) -> str:
    """Format a single CalcResult into a concise text summary."""
    lines = []
    label = result.skill_name or "Unknown Skill"
    attack_str = "Attack" if result.is_attack else "Spell"

    # Skill sub-type tags
    tags = []
    if result.is_totem:
        tags.append(f"Totem x{result.num_totems}")
    if result.is_trap:
        tags.append("Trap")
    if result.is_mine:
        tags.append("Mine")
    if result.is_minion:
        tags.append("Minion")
    tag_str = f" [{', '.join(tags)}]" if tags else ""

    lines.append(f"{label} ({attack_str}{tag_str}):")
    lines.append(f"  Combined DPS: {_fmt(result.combined_dps)}")

    if result.total_dps > 0:
        lines.append(f"  Hit DPS: {_fmt(result.total_dps)}")
        lines.append(f"    Hit Damage: {_fmt(result.hit_damage)}")
        lines.append(f"    Hits/sec: {result.hits_per_second}")
        lines.append(f"    Crit Chance: {result.crit_chance}%")
        lines.append(f"    Crit Multi: {result.effective_crit_multi}x")
        lines.append(f"    Hit Chance: {result.hit_chance}%")

    # Per-type breakdown
    active_types = [t for t in result.type_breakdown if t.after_mitigation > 0]
    if active_types:
        type_parts = []
        for td in active_types:
            type_parts.append(f"{td.damage_type}: {_fmt(td.after_mitigation)}")
        lines.append(f"    By Type: {', '.join(type_parts)}")

    # Impale
    if result.impale_dps > 0:
        lines.append(f"  Impale DPS: {_fmt(result.impale_dps)}")

    # DoT
    if result.total_dot_dps > 0:
        lines.append(f"  DoT DPS: {_fmt(result.total_dot_dps)}")
        if result.ignite_dps > 0:
            lines.append(f"    Ignite: {_fmt(result.ignite_dps)}")
        if result.bleed_dps > 0:
            lines.append(f"    Bleed: {_fmt(result.bleed_dps)}")
        if result.poison_dps > 0:
            lines.append(f"    Poison: {_fmt(result.poison_dps)}")

    # Enemy damage taken
    if result.enemy_damage_taken_multi > 1.001:
        pct = (result.enemy_damage_taken_multi - 1) * 100
        lines.append(f"  Enemy takes {pct:.1f}% more damage (shock/wither/curses)")

    return "\n".join(lines)


def calculate_all_skills(
    build: Build,
    config: CalcConfig | None = None,
) -> list[CalcResult]:
    """Calculate DPS for every skill group in the build.

    Returns a list of CalcResult, one per skill group. Skill groups that
    fail to calculate are included with warnings but zero DPS.
    """
    results: list[CalcResult] = []
    skill_groups = build.skill_groups

    # Use active skill set if variants
    if build.skill_sets:
        idx = min(build.active_skill_set, len(build.skill_sets) - 1)
        skill_groups = build.skill_sets[idx].skills

    for i in range(len(skill_groups)):
        # Clone build with this skill as main
        build_copy = build.model_copy(deep=True)
        build_copy.main_socket_group = i + 1  # 1-based
        try:
            result = calculate_dps(build_copy, config_overrides=config)
            results.append(result)
        except Exception as exc:
            results.append(CalcResult(
                skill_name=_skill_name(skill_groups[i]),
                warnings=[f"Calc failed: {exc}"],
            ))

    return results


def format_all_skills_context(
    build: Build,
    config: CalcConfig | None = None,
) -> str:
    """Calculate all skills and format as a text block for the AI prompt."""
    results = calculate_all_skills(build, config)

    if not results:
        return ""

    lines = ["## DPS Breakdown (all skills)"]

    # Sort by combined DPS descending, but keep index for reference
    indexed = list(enumerate(results))
    indexed.sort(key=lambda x: x[1].combined_dps, reverse=True)

    main_idx = build.main_socket_group - 1

    for i, result in indexed:
        if result.combined_dps <= 0 and not result.warnings:
            continue
        marker = " [MAIN]" if i == main_idx else ""
        lines.append(f"\n### Skill #{i + 1}{marker}")
        lines.append(format_dps_summary(result))
        if result.warnings:
            for w in result.warnings[:3]:
                lines.append(f"  ⚠ {w}")

    # Best skill recommendation
    best = max(results, key=lambda r: r.combined_dps)
    if best.combined_dps > 0:
        lines.append(f"\n**Highest DPS skill**: {best.skill_name} "
                      f"({_fmt(best.combined_dps)} combined DPS)")

    return "\n".join(lines)


def format_single_dps_context(data: dict) -> str:
    """Format a pre-computed DPS result dict into text for the AI prompt.

    Used when the frontend has already calculated DPS and passes
    the result in the build context.
    """
    lines = ["## DPS Analysis"]

    skill = data.get("skill_name", "Unknown Skill")
    combined = data.get("combined_dps", 0)
    lines.append(f"**{skill}**: {_fmt(combined)} combined DPS")

    hit_dps = data.get("total_dps", 0)
    if hit_dps > 0:
        lines.append(f"  Hit DPS: {_fmt(hit_dps)}")
        lines.append(f"  Hit Damage: {_fmt(data.get('hit_damage', 0))}")
        lines.append(f"  Hits/sec: {data.get('hits_per_second', 0)}")
        lines.append(f"  Crit: {data.get('crit_chance', 0)}% chance, "
                      f"{data.get('effective_crit_multi', 1)}x multi")

    # Type breakdown
    breakdown = data.get("type_breakdown", [])
    active = [t for t in breakdown if t.get("after_mitigation", 0) > 0]
    if active:
        parts = [f"{t['damage_type']}: {_fmt(t['after_mitigation'])}" for t in active]
        lines.append(f"  By Type: {', '.join(parts)}")

    dot_dps = data.get("total_dot_dps", 0)
    if dot_dps > 0:
        lines.append(f"  DoT DPS: {_fmt(dot_dps)}")
        for key, label in [("ignite_dps", "Ignite"), ("bleed_dps", "Bleed"),
                           ("poison_dps", "Poison")]:
            v = data.get(key, 0)
            if v > 0:
                lines.append(f"    {label}: {_fmt(v)}")

    warnings = data.get("warnings", [])
    if warnings:
        for w in warnings[:3]:
            lines.append(f"  Note: {w}")

    return "\n".join(lines)


def _fmt(value: float) -> str:
    """Format a number for display."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.0f}"


def _skill_name(group) -> str:
    """Extract the active gem name from a skill group."""
    for gem in group.gems:
        if not gem.is_support and gem.is_enabled:
            return gem.name
    return group.label or "Unknown"
