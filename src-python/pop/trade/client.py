"""
Async HTTP client for the PoE 1 public trade API.

Endpoints:
  POST /api/trade/search/{league}  → returns result IDs + query ID
  GET  /api/trade/fetch/{ids}      → returns item details

No OAuth needed — trade search is public.
Reuses RateLimiter from pop.poe_api.rate_limiter with conservative defaults.
"""

from __future__ import annotations

import logging

import httpx

from pop.poe_api.rate_limiter import RateLimiter, _RateWindow
from pop.trade.models import TradeListing, TradePrice, TradeSearchRequest, TradeSearchResult

logger = logging.getLogger(__name__)

BASE_URL = "https://www.pathofexile.com"
USER_AGENT = "PathOfPurpose/0.1.0"
MAX_FETCH_IDS = 10  # Trade API allows up to 10 IDs per fetch


def _make_trade_limiter() -> RateLimiter:
    """Create a conservative rate limiter for the trade API.

    Trade API is stricter than the character API:
    ~12 req/6s with 60s penalty for exceeding.
    """
    import time

    now = time.monotonic()
    return RateLimiter(
        windows=[
            _RateWindow(max_hits=8, period=6, penalty=60, window_start=now),
            _RateWindow(max_hits=30, period=60, penalty=120, window_start=now),
        ],
        safety_margin=1,
    )


class TradeClient:
    """Async client for PoE trade search API."""

    def __init__(self, league: str = "Standard") -> None:
        self.league = league
        self._limiter = _make_trade_limiter()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> TradeClient:
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=15.0,
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()

    async def search(self, request: TradeSearchRequest) -> TradeSearchResult:
        """Execute a trade search and fetch the first page of results.

        Args:
            request: The trade search request body.

        Returns:
            TradeSearchResult with listings and metadata.
        """
        assert self._client is not None, "Use TradeClient as async context manager"

        # Step 1: POST search to get result IDs
        await self._limiter.wait()
        search_resp = await self._client.post(
            f"/api/trade/search/{self.league}",
            json=request.model_dump(exclude_none=True),
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()

        result_ids: list[str] = search_data.get("result", [])
        query_id = search_data.get("id", "")
        total = search_data.get("total", 0)

        trade_url = f"{BASE_URL}/trade/search/{self.league}/{query_id}"

        if not result_ids:
            return TradeSearchResult(
                total=total, listings=[], query_id=query_id, trade_url=trade_url
            )

        # Step 2: Fetch details for first N items
        fetch_ids = result_ids[:MAX_FETCH_IDS]
        await self._limiter.wait()
        fetch_resp = await self._client.get(
            f"/api/trade/fetch/{','.join(fetch_ids)}",
            params={"query": query_id},
        )
        fetch_resp.raise_for_status()
        fetch_data = fetch_resp.json()

        listings = _parse_listings(fetch_data.get("result", []))

        return TradeSearchResult(
            total=total,
            listings=listings,
            query_id=query_id,
            trade_url=trade_url,
        )


def _parse_listings(results: list[dict]) -> list[TradeListing]:
    """Parse trade fetch API results into TradeListing models."""
    listings: list[TradeListing] = []

    for entry in results:
        item_data = entry.get("item", {})
        listing_data = entry.get("listing", {})
        price_data = listing_data.get("price", {})

        price = None
        if price_data:
            price = TradePrice(
                amount=price_data.get("amount", 0),
                currency=price_data.get("currency", ""),
                type=price_data.get("type", "~price"),
            )

        account = listing_data.get("account", {})
        whisper = listing_data.get("whisper", "")

        # Extract attacks per second from item properties
        aps = 0.0
        for prop in item_data.get("properties", []):
            if prop.get("name") == "Attacks per Second":
                vals = prop.get("values", [])
                if vals and vals[0]:
                    try:
                        aps = float(vals[0][0])
                    except (ValueError, IndexError):
                        pass

        listings.append(TradeListing(
            id=entry.get("id", ""),
            item_name=item_data.get("name", ""),
            type_line=item_data.get("typeLine", ""),
            ilvl=item_data.get("ilvl", 0),
            corrupted=item_data.get("corrupted", False),
            price=price,
            explicit_mods=item_data.get("explicitMods", []),
            implicit_mods=item_data.get("implicitMods", []),
            crafted_mods=item_data.get("craftedMods", []),
            account_name=account.get("name", ""),
            whisper=whisper,
            icon_url=item_data.get("icon", ""),
            attacks_per_second=aps,
        ))

    return listings
