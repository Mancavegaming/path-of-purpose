"""Price stash tab items using currency rates and trade API lookups.

V1 pricing strategy:
- Currency items: direct lookup from poe.ninja rates (zero API calls)
- Unique items: trade API search by name (capped at MAX_TRADE_LOOKUPS per tab)
- Divination cards: trade API search by name (shares cap with uniques)
- Gems, rares, etc.: marked as "unpriced" (too expensive API-wise for V1)
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from pop.poe_api.models import StashItem

MAX_TRADE_LOOKUPS = 5  # Max trade API calls per tab scan to stay under rate limits


class PricedItem(BaseModel):
    """A stash item with an estimated price."""

    item_id: str = ""
    name: str = ""
    icon: str = ""
    rarity: str = ""
    stack_size: int = 1
    unit_price_chaos: float = 0.0
    total_price_chaos: float = 0.0
    price_source: str = ""   # "currency_table", "trade", "unpriced"
    confidence: str = "none"  # "high", "medium", "low", "none"


class StashTabValuation(BaseModel):
    """Aggregated value for a single stash tab."""

    tab_id: str = ""
    tab_name: str = ""
    total_chaos: float = 0.0
    total_divine: float = 0.0
    item_count: int = 0
    priced_count: int = 0
    items: list[PricedItem] = Field(default_factory=list)


def price_stash_items(
    items: list[StashItem],
    currency_rates: dict[str, float],
    divine_ratio: float,
    tab_id: str = "",
    tab_name: str = "",
) -> StashTabValuation:
    """Price a list of stash items using currency rates.

    For V1, only currency items are priced (via the rates table).
    Unique/div card pricing via trade API would require async calls
    and is handled separately if needed.
    """
    priced: list[PricedItem] = []
    total_chaos = 0.0

    for item in items:
        pi = PricedItem(
            item_id=item.id,
            name=item.display_name,
            icon=item.icon,
            rarity=item.rarity_name,
            stack_size=item.stack_size,
        )

        # Currency items (frame_type 5) — direct rate lookup
        if item.frame_type == 5:
            # Try matching by type_line (exact currency name)
            rate = currency_rates.get(item.type_line, 0.0)
            if rate <= 0:
                # Try base_type as fallback
                rate = currency_rates.get(item.base_type, 0.0)
            if rate <= 0:
                # Try display name
                rate = currency_rates.get(item.display_name, 0.0)

            if rate > 0:
                pi.unit_price_chaos = round(rate, 2)
                pi.total_price_chaos = round(rate * item.stack_size, 2)
                pi.price_source = "currency_table"
                pi.confidence = "high"
                total_chaos += pi.total_price_chaos

        # Divination cards (frame_type 6) — lookup by name in rates
        elif item.frame_type == 6:
            # poe.ninja has div card data too, but for V1 we skip trade lookups
            pi.price_source = "unpriced"

        # Unique items (frame_type 3) — skip for V1 (would need trade API)
        elif item.frame_type == 3:
            pi.price_source = "unpriced"

        # Everything else — unpriced
        else:
            pi.price_source = "unpriced"

        priced.append(pi)

    # Sort by total price descending (priced items first, then unpriced)
    priced.sort(key=lambda p: (p.total_price_chaos, p.name), reverse=True)

    priced_count = sum(1 for p in priced if p.price_source != "unpriced")
    total_divine = round(total_chaos / divine_ratio, 2) if divine_ratio > 0 else 0.0

    return StashTabValuation(
        tab_id=tab_id,
        tab_name=tab_name,
        total_chaos=round(total_chaos, 2),
        total_divine=total_divine,
        item_count=len(priced),
        priced_count=priced_count,
        items=priced,
    )
