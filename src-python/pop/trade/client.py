"""
Async HTTP client for the PoE 1 public trade API.

Endpoints:
  POST /api/trade/search/{league}  → returns result IDs + query ID
  GET  /api/trade/fetch/{ids}      → returns item details

No OAuth needed — trade search is public.
Reuses RateLimiter from pop.poe_api.rate_limiter with conservative defaults.
"""

from __future__ import annotations

import asyncio
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
    NOTE: Each Python invocation is a fresh process, so this limiter
    only prevents bursts within a single search operation.
    """
    import time

    now = time.monotonic()
    return RateLimiter(
        windows=[
            _RateWindow(max_hits=4, period=4, penalty=10, window_start=now),
            _RateWindow(max_hits=10, period=30, penalty=60, window_start=now),
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

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        max_retries: int = 2,
        **kwargs: object,
    ) -> httpx.Response:
        """Make an HTTP request with automatic retry on 429 Too Many Requests."""
        assert self._client is not None
        for attempt in range(max_retries + 1):
            await self._limiter.wait()
            if method == "POST":
                resp = await self._client.post(url, **kwargs)  # type: ignore[arg-type]
            else:
                resp = await self._client.get(url, **kwargs)  # type: ignore[arg-type]

            if resp.status_code != 429:
                return resp

            # On 429, raise immediately with a clear message instead of blocking
            # for 60+ seconds. The user can retry manually.
            retry_after = resp.headers.get("Retry-After", "60")
            try:
                wait_secs = int(float(retry_after))
            except ValueError:
                wait_secs = 60

            if wait_secs > 10 or attempt >= max_retries:
                raise ValueError(
                    f"Trade API rate limited. Please wait ~{wait_secs}s and try again."
                )

            logger.warning("Trade API 429 — retrying in %ds (attempt %d/%d)", wait_secs, attempt + 1, max_retries)
            await asyncio.sleep(wait_secs)

        return resp  # Return last response even if still 429

    async def search_count(self, request: TradeSearchRequest) -> TradeSearchResult:
        """POST search only — returns total count and IDs but no item details.

        Costs 1 API call. Use this during relaxation to check if a query
        has results before fetching full details.
        """
        assert self._client is not None, "Use TradeClient as async context manager"

        payload = request.model_dump(exclude_none=True)
        search_resp = await self._request_with_retry(
            "POST", f"/api/trade/search/{self.league}", json=payload,
        )
        if search_resp.status_code == 400:
            body = search_resp.text
            # If the error is about an unknown base type, retry without the type filter
            if "Unknown item base type" in body and request.query.type:
                logger.warning(
                    "Trade API rejected base type %r — retrying without type filter",
                    request.query.type,
                )
                import copy
                retry_request = copy.deepcopy(request)
                retry_request.query.type = None
                retry_payload = retry_request.model_dump(exclude_none=True)
                search_resp = await self._request_with_retry(
                    "POST", f"/api/trade/search/{self.league}", json=retry_payload,
                )
                if search_resp.status_code == 400:
                    body = search_resp.text
                    logger.error("Trade API 400 (retry): payload=%s response=%s", retry_payload, body)
                    raise ValueError(f"Trade API rejected the query: {body[:300]}")
            else:
                logger.error("Trade API 400: payload=%s response=%s", payload, body)
                raise ValueError(f"Trade API rejected the query: {body[:300]}")
        search_resp.raise_for_status()
        search_data = search_resp.json()

        result_ids: list[str] = search_data.get("result", [])
        query_id = search_data.get("id", "")
        total = search_data.get("total", 0)
        trade_url = f"{BASE_URL}/trade/search/{self.league}/{query_id}"

        return TradeSearchResult(
            total=total,
            listings=[],
            query_id=query_id,
            trade_url=trade_url,
            result_ids=result_ids,
        )

    async def fetch_listings(
        self, result: TradeSearchResult, *, max_fetch: int = MAX_FETCH_IDS,
    ) -> TradeSearchResult:
        """Fetch full item details for a previous search_count result.

        Costs 1 API call per 10 items.
        """
        assert self._client is not None, "Use TradeClient as async context manager"

        ids = result.result_ids[:max_fetch]
        if not ids:
            return result

        all_listings: list[TradeListing] = []
        for i in range(0, len(ids), MAX_FETCH_IDS):
            batch = ids[i : i + MAX_FETCH_IDS]
            fetch_resp = await self._request_with_retry(
                "GET", f"/api/trade/fetch/{','.join(batch)}",
                params={"query": result.query_id},
            )
            fetch_resp.raise_for_status()
            fetch_data = fetch_resp.json()
            all_listings.extend(_parse_listings(fetch_data.get("result", [])))

        result.listings = all_listings
        return result

    async def search(
        self, request: TradeSearchRequest, *, max_fetch: int = MAX_FETCH_IDS,
    ) -> TradeSearchResult:
        """Full search: POST to get IDs, then GET to fetch item details.

        Costs 2 API calls minimum.
        """
        result = await self.search_count(request)
        if result.total == 0:
            return result
        return await self.fetch_listings(result, max_fetch=max_fetch)


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

        # Extract socket info
        # Trade API returns: [{"group": 0, "sColour": "R"}, ...]
        raw_sockets = item_data.get("sockets", [])
        sockets: list[dict[str, str | int]] = []
        socket_count = 0
        max_links = 0
        if raw_sockets:
            group_counts: dict[int, int] = {}
            for s in raw_sockets:
                group = s.get("group", 0)
                colour = s.get("sColour", s.get("attr", "W"))
                sockets.append({"group": group, "colour": colour})
                socket_count += 1
                group_counts[group] = group_counts.get(group, 0) + 1
            if group_counts:
                max_links = max(group_counts.values())

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
            sockets=sockets,
            socket_count=socket_count,
            max_links=max_links,
        ))

    return listings
