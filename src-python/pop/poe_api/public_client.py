"""Public PoE character API client (no OAuth required).

Uses the character-window endpoints that work for any account with a
public profile. No API key or session needed.

Endpoints:
  POST /character-window/get-characters  (form: accountName)
  GET  /character-window/get-items       (accountName, character)
  GET  /character-window/get-passive-skills (accountName, character)
"""

from __future__ import annotations

import logging

import httpx

from pop.poe_api.models import CharacterEntry, EquippedItem, PassiveData
from pop.poe_api.rate_limiter import RateLimiter, _RateWindow

logger = logging.getLogger(__name__)

BASE_URL = "https://www.pathofexile.com"
USER_AGENT = "PathOfPurpose/1.0 (contact: mancavegaming@proton.me)"


class ProfilePrivateError(Exception):
    """Raised when the account's profile is set to private."""


class CharacterNotFoundError(Exception):
    """Raised when the character doesn't exist on the account."""


def _make_limiter() -> RateLimiter:
    import time
    now = time.monotonic()
    return RateLimiter(
        windows=[
            _RateWindow(max_hits=6, period=10, penalty=60, window_start=now),
            _RateWindow(max_hits=20, period=60, penalty=120, window_start=now),
        ],
        safety_margin=1,
    )


class PublicPoeClient:
    """Async client for PoE public character-window API."""

    def __init__(self) -> None:
        self._limiter = _make_limiter()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> PublicPoeClient:
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=20.0,
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()

    def _check_error(self, resp: httpx.Response, context: str) -> None:
        if resp.status_code == 403:
            raise ProfilePrivateError(
                "This profile is private. The player needs to uncheck "
                "'Hide Characters' at pathofexile.com/account/privacy"
            )
        if resp.status_code == 404:
            raise CharacterNotFoundError(f"{context} not found.")
        if resp.status_code == 429:
            raise RuntimeError("Rate limited by PoE API. Please wait a moment and try again.")
        resp.raise_for_status()

    async def list_characters(self, account_name: str) -> list[CharacterEntry]:
        """Fetch all characters on a public account."""
        assert self._client is not None
        await self._limiter.wait()

        resp = await self._client.get(
            "/character-window/get-characters",
            params={"accountName": account_name},
        )
        self._check_error(resp, f"Account '{account_name}'")

        data = resp.json()
        if isinstance(data, dict) and "error" in data:
            msg = data["error"].get("message", str(data["error"]))
            if "private" in msg.lower() or "forbidden" in msg.lower():
                raise ProfilePrivateError(
                    "This profile is private. The player needs to uncheck "
                    "'Hide Characters' at pathofexile.com/account/privacy"
                )
            raise RuntimeError(f"PoE API error: {msg}")

        chars = data if isinstance(data, list) else []
        return [CharacterEntry.model_validate(c) for c in chars]

    async def get_items(self, account_name: str, character: str) -> list[EquippedItem]:
        """Fetch all equipped items (with socketed gems) for a character."""
        assert self._client is not None
        await self._limiter.wait()

        resp = await self._client.get(
            "/character-window/get-items",
            params={"accountName": account_name, "character": character},
        )
        self._check_error(resp, f"Character '{character}'")

        data = resp.json()
        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(f"PoE API error: {data['error']}")

        items_list = data.get("items", []) if isinstance(data, dict) else data
        character_data = data.get("character", {}) if isinstance(data, dict) else {}

        items = [EquippedItem.model_validate(i) for i in items_list]

        logger.info(
            "Fetched %d items for %s (account: %s)",
            len(items), character, account_name,
        )
        return items

    async def get_passives(
        self, account_name: str, character: str,
    ) -> PassiveData:
        """Fetch passive tree allocations for a character."""
        assert self._client is not None
        await self._limiter.wait()

        resp = await self._client.get(
            "/character-window/get-passive-skills",
            params={
                "accountName": account_name,
                "character": character,
                "reqData": "0",
            },
        )
        self._check_error(resp, f"Character '{character}' passives")

        data = resp.json()
        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(f"PoE API error: {data['error']}")

        return PassiveData.model_validate(data)
