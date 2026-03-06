"""Pydantic models for PoE 1 Trade API requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Stat catalog (from /api/trade/data/stats)
# ---------------------------------------------------------------------------


class StatEntry(BaseModel):
    """A single stat from the trade stats catalog."""

    id: str  # e.g. "explicit.stat_3299347043"
    text: str  # e.g. "+# to maximum Life"
    type: str  # "explicit", "implicit", "crafted", etc.


# ---------------------------------------------------------------------------
# Trade query construction
# ---------------------------------------------------------------------------


class StatFilter(BaseModel):
    """A single stat filter in a trade search."""

    id: str
    value: dict[str, float] | None = None  # {"min": ..., "max": ...}
    disabled: bool = False


class StatGroup(BaseModel):
    """A group of stat filters with a matching mode."""

    type: str = "and"  # "and", "count", "weighted"
    filters: list[StatFilter] = Field(default_factory=list)
    value: dict[str, int] | None = None  # for "count" mode: {"min": N}


class TradeQuery(BaseModel):
    """The 'query' portion of a trade search request."""

    name: str | None = None
    type: str | None = None
    stats: list[StatGroup] = Field(default_factory=list)
    status: dict[str, str] = Field(default_factory=lambda: {"option": "online"})


class TradeSearchRequest(BaseModel):
    """Full trade search request body for POST /api/trade/search/{league}."""

    query: TradeQuery
    sort: dict[str, str] = Field(default_factory=lambda: {"price": "asc"})


# ---------------------------------------------------------------------------
# Trade search results
# ---------------------------------------------------------------------------


class TradePrice(BaseModel):
    """Price of a listed item."""

    amount: float
    currency: str  # "chaos", "divine", etc.
    type: str = "~price"  # "~price" or "~b/o"


class TradeListing(BaseModel):
    """A single item listing from trade search results."""

    id: str
    item_name: str = ""
    type_line: str = ""
    ilvl: int = 0
    corrupted: bool = False
    price: TradePrice | None = None
    explicit_mods: list[str] = Field(default_factory=list)
    implicit_mods: list[str] = Field(default_factory=list)
    crafted_mods: list[str] = Field(default_factory=list)
    account_name: str = ""
    whisper: str = ""
    icon_url: str = ""
    attacks_per_second: float = 0.0


class TradeSearchResult(BaseModel):
    """Aggregated result of a trade search."""

    total: int = 0
    listings: list[TradeListing] = Field(default_factory=list)
    query_id: str = ""
    trade_url: str = ""


# ---------------------------------------------------------------------------
# Item comparison / DPS estimation
# ---------------------------------------------------------------------------


class WeaponDps(BaseModel):
    """Weapon DPS breakdown."""

    physical_dps: float = 0.0
    elemental_dps: float = 0.0
    total_dps: float = 0.0
    attacks_per_second: float = 0.0


class StatDelta(BaseModel):
    """Difference in a single stat between two items."""

    stat_name: str
    equipped_value: float = 0.0
    trade_value: float = 0.0
    difference: float = 0.0
    pct_change: float = 0.0


class ItemComparison(BaseModel):
    """Full comparison between an equipped item and a trade listing."""

    equipped_name: str = ""
    trade_name: str = ""
    slot: str = ""
    is_weapon: bool = False
    equipped_dps: WeaponDps | None = None
    trade_dps: WeaponDps | None = None
    dps_change_pct: float = 0.0
    # Flat DPS contribution for non-weapon items (flat added damage × weapon APS)
    equipped_flat_dps: float = 0.0
    trade_flat_dps: float = 0.0
    flat_dps_change: float = 0.0
    stat_deltas: list[StatDelta] = Field(default_factory=list)
    summary: str = ""
