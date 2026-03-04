"""
Delta Engine output models.

These are the structured results of comparing a guide build (PoB)
against a live character (API). The UI consumes these to show the
player what to fix next.
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class GapCategory(str, Enum):
    """The type of gap identified by the Delta Engine."""

    PASSIVE = "passive"
    GEAR = "gear"
    GEM = "gem"


class Severity(str, Enum):
    """How impactful a gap is — drives the priority ranking."""

    CRITICAL = "critical"  # Build-defining (e.g., missing key unique, wrong ascendancy nodes)
    HIGH = "high"          # Major DPS/defense loss
    MEDIUM = "medium"      # Noticeable improvement
    LOW = "low"            # Minor optimization


# ---------------------------------------------------------------------------
# Passive diff
# ---------------------------------------------------------------------------


class PassiveDelta(BaseModel):
    """Result of comparing passive trees."""

    missing_nodes: list[int] = Field(default_factory=list)
    extra_nodes: list[int] = Field(default_factory=list)
    missing_count: int = 0
    extra_count: int = 0
    guide_total: int = 0
    character_total: int = 0
    match_pct: float = 0.0

    @property
    def severity(self) -> Severity:
        if self.match_pct < 50:
            return Severity.CRITICAL
        if self.match_pct < 80:
            return Severity.HIGH
        if self.match_pct < 95:
            return Severity.MEDIUM
        return Severity.LOW

    @property
    def summary(self) -> str:
        return (
            f"Passive tree {self.match_pct:.0f}% match — "
            f"{self.missing_count} nodes to allocate, "
            f"{self.extra_count} to respec"
        )


# ---------------------------------------------------------------------------
# Gear diff
# ---------------------------------------------------------------------------


class ModGap(BaseModel):
    """A single mod that the guide expects but the character is missing."""

    mod_text: str
    is_implicit: bool = False
    importance: float = 0.0  # 0-1 score


class SlotDelta(BaseModel):
    """Gear comparison for a single equipment slot."""

    slot: str
    guide_item_name: str = ""
    character_item_name: str = ""
    has_item: bool = True
    missing_mods: list[ModGap] = Field(default_factory=list)
    matched_mods: int = 0
    total_guide_mods: int = 0
    match_pct: float = 0.0
    priority_score: float = 0.0

    @property
    def severity(self) -> Severity:
        if not self.has_item:
            return Severity.CRITICAL
        if self.match_pct < 30:
            return Severity.CRITICAL
        if self.match_pct < 60:
            return Severity.HIGH
        if self.match_pct < 85:
            return Severity.MEDIUM
        return Severity.LOW

    @property
    def summary(self) -> str:
        if not self.has_item:
            return f"{self.slot}: EMPTY — guide expects '{self.guide_item_name}'"
        return (
            f"{self.slot}: {self.match_pct:.0f}% match — "
            f"{len(self.missing_mods)} missing mods"
        )


class GearDelta(BaseModel):
    """Result of comparing all gear slots."""

    slot_deltas: list[SlotDelta] = Field(default_factory=list)
    overall_match_pct: float = 0.0

    @property
    def worst_slots(self) -> list[SlotDelta]:
        """Return slots sorted by worst match first."""
        return sorted(self.slot_deltas, key=lambda s: s.priority_score, reverse=True)


# ---------------------------------------------------------------------------
# Gem diff
# ---------------------------------------------------------------------------


class GemGap(BaseModel):
    """A gem discrepancy between guide and character."""

    gem_name: str
    issue: str  # "missing", "wrong_level", "wrong_support", "disabled"
    guide_level: int = 0
    character_level: int = 0
    slot: str = ""


class SkillGroupDelta(BaseModel):
    """Comparison of a single skill group (active + supports)."""

    skill_name: str = ""
    slot: str = ""
    missing_supports: list[str] = Field(default_factory=list)
    extra_supports: list[str] = Field(default_factory=list)
    level_gaps: list[GemGap] = Field(default_factory=list)
    is_missing_entirely: bool = False
    match_pct: float = 0.0

    @property
    def severity(self) -> Severity:
        if self.is_missing_entirely:
            return Severity.CRITICAL
        if self.missing_supports:
            return Severity.HIGH
        if self.level_gaps:
            return Severity.MEDIUM
        return Severity.LOW

    @property
    def summary(self) -> str:
        if self.is_missing_entirely:
            return f"{self.skill_name}: NOT FOUND on character"
        parts = []
        if self.missing_supports:
            parts.append(f"missing {len(self.missing_supports)} supports")
        if self.level_gaps:
            parts.append(f"{len(self.level_gaps)} gems under-leveled")
        return f"{self.skill_name}: {', '.join(parts)}" if parts else f"{self.skill_name}: OK"


class GemDelta(BaseModel):
    """Result of comparing all skill gem setups."""

    group_deltas: list[SkillGroupDelta] = Field(default_factory=list)
    total_missing_supports: int = 0
    total_level_gaps: int = 0


# ---------------------------------------------------------------------------
# Top-level report
# ---------------------------------------------------------------------------


class DeltaGap(BaseModel):
    """A single prioritized gap for display to the user."""

    rank: int = 0
    category: GapCategory
    severity: Severity
    title: str
    detail: str
    score: float = 0.0  # normalized 0-100, higher = more impactful


class DeltaReport(BaseModel):
    """
    The top-level output of the Delta Engine.

    Contains the full analysis plus a ranked list of the most
    impactful gaps to fix.
    """

    # Full analysis
    passive_delta: PassiveDelta = Field(default_factory=PassiveDelta)
    gear_delta: GearDelta = Field(default_factory=GearDelta)
    gem_delta: GemDelta = Field(default_factory=GemDelta)

    # Ranked gaps (the "top 3")
    top_gaps: list[DeltaGap] = Field(default_factory=list)

    # Metadata
    guide_build_name: str = ""
    character_name: str = ""

    def display(self) -> str:
        """Format the report for CLI output."""
        lines = [
            f"Delta Report: '{self.character_name}' vs guide '{self.guide_build_name}'",
            "=" * 60,
            "",
            self.passive_delta.summary,
            f"Gear: {self.gear_delta.overall_match_pct:.0f}% overall match",
            f"Gems: {self.gem_delta.total_missing_supports} missing supports, "
            f"{self.gem_delta.total_level_gaps} under-leveled",
            "",
            "Top gaps to fix:",
        ]
        for gap in self.top_gaps:
            icon = {"critical": "!!", "high": "! ", "medium": "- ", "low": "  "}
            prefix = icon.get(gap.severity.value, "  ")
            lines.append(f"  {prefix}#{gap.rank} [{gap.category.value.upper()}] {gap.title}")
            lines.append(f"      {gap.detail}")

        return "\n".join(lines)
