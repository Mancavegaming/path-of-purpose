"""
Damage type conversion chain with source tracking.

PoE conversion flows in one direction:
    Physical → Lightning → Cold → Fire → Chaos

Key mechanic: When damage converts from type A to type B, increased/more
modifiers for BOTH type A and type B apply to the converted portion.
This module tracks source→final contributions to enable correct modifier
application.

Total conversion out of a type is capped at 100%. If mods sum above 100%,
each conversion is scaled proportionally. "Gained as extra" adds without
removing from the source.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pop.calc.models import ConversionEntry, DamageType, CONVERSION_ORDER


@dataclass
class DamageContribution:
    """A portion of final damage that originated from a specific source type.

    Tracks how much damage in the final type came from each source type,
    so that increased/more modifiers for both source and final types can
    be applied correctly.
    """

    source_type: DamageType
    final_type: DamageType
    amount: float  # damage amount before increased/more


@dataclass
class ConversionResult:
    """Result of damage conversion with full source tracking.

    Attributes:
        final_damage: Total damage per final type (sum of all contributions).
        contributions: List of every source→final contribution for modifier application.
    """

    final_damage: dict[DamageType, float] = field(default_factory=dict)
    contributions: list[DamageContribution] = field(default_factory=list)


def apply_conversion(
    base_damage: dict[DamageType, float],
    conversions: list[ConversionEntry],
) -> dict[DamageType, float]:
    """Apply conversion and return final damage per type (simple API, no tracking).

    Backward-compatible with Phase A/B callers.
    """
    result = apply_conversion_tracked(base_damage, conversions)
    return result.final_damage


def apply_conversion_tracked(
    base_damage: dict[DamageType, float],
    conversions: list[ConversionEntry],
) -> ConversionResult:
    """Apply conversion with full source→final contribution tracking.

    Uses a portions-based approach: each damage type holds a list of
    (original_source, amount) tuples. When damage converts through a chain
    (e.g. phys→lightning→cold), the original source is preserved so that
    modifiers for ALL types in the chain apply correctly.

    Args:
        base_damage: Damage per type BEFORE conversion (base + flat added).
        conversions: All conversion entries from the build.

    Returns:
        ConversionResult with final damage per type and source tracking.
    """
    # Each type holds portions as (original_source_type, amount).
    # This lets chain conversions preserve the original source.
    portions: dict[DamageType, list[tuple[DamageType, float]]] = {
        dt: [] for dt in DamageType
    }
    for dt in DamageType:
        amt = base_damage.get(dt, 0.0)
        if amt > 0:
            portions[dt].append((dt, amt))

    # Process in chain order so upstream conversions feed downstream
    for current_type in CONVERSION_ORDER:
        if not portions[current_type]:
            continue

        # Gather all conversions FROM this type
        true_convs: list[ConversionEntry] = []
        gained_as: list[ConversionEntry] = []

        for c in conversions:
            if c.type_from != current_type:
                continue
            if c.is_gained_as:
                gained_as.append(c)
            else:
                true_convs.append(c)

        if not true_convs and not gained_as:
            continue

        # Snapshot current portions (they'll be modified)
        current_portions = list(portions[current_type])

        # "Gained as extra" — copy portions to target without removing from source
        for c in gained_as:
            for orig_source, amt in current_portions:
                gained_amount = amt * c.percent / 100.0
                if gained_amount > 0:
                    portions[c.type_to].append((orig_source, gained_amount))

        # True conversion — cap total at 100%
        if true_convs:
            total_conv_pct = sum(c.percent for c in true_convs)
            scale = min(total_conv_pct, 100.0) / total_conv_pct if total_conv_pct > 0 else 0.0

            # Move portions from current_type to targets
            remaining_portions: list[tuple[DamageType, float]] = []
            total_converted_frac = min(total_conv_pct, 100.0) / 100.0

            for orig_source, amt in current_portions:
                # Distribute to each conversion target
                for c in true_convs:
                    effective_pct = c.percent * scale / 100.0
                    conv_amount = amt * effective_pct
                    if conv_amount > 0:
                        portions[c.type_to].append((orig_source, conv_amount))

                # Whatever remains stays as current_type
                remain = amt * (1.0 - total_converted_frac)
                if remain > 0:
                    remaining_portions.append((orig_source, remain))

            portions[current_type] = remaining_portions

    # Build contributions and final damage from settled portions
    contributions: list[DamageContribution] = []
    final_damage: dict[DamageType, float] = {dt: 0.0 for dt in DamageType}

    for final_type in DamageType:
        for orig_source, amt in portions[final_type]:
            if amt <= 0:
                continue
            final_damage[final_type] += amt
            contributions.append(DamageContribution(
                source_type=orig_source,
                final_type=final_type,
                amount=amt,
            ))

    return ConversionResult(
        final_damage=final_damage,
        contributions=contributions,
    )
