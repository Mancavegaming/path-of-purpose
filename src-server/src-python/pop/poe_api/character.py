"""
PoE API client for fetching character and league data.

All requests go through the rate limiter and use the OAuth access token.
Handles automatic token refresh when the access token expires.
"""

from __future__ import annotations

import httpx

from pop.oauth.token_store import StoredTokens, load_tokens, save_tokens
from pop.oauth.client import refresh_access_token
from pop.poe_api.models import (
    CharacterDetail,
    CharacterEntry,
    EquippedItem,
    League,
    PassiveData,
    Profile,
)
from pop.poe_api.rate_limiter import RateLimiter

POE_API_BASE = "https://www.pathofexile.com/api"


class PoeApiError(Exception):
    """Raised when the PoE API returns an error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"PoE API error {status_code}: {message}")


class PoeClient:
    """
    Async client for the PoE API.

    Usage:
        async with PoeClient(client_id="...") as poe:
            chars = await poe.list_characters()
            detail = await poe.get_character(chars[0].name)
    """

    def __init__(self, client_id: str, tokens: StoredTokens | None = None):
        self.client_id = client_id
        self._tokens = tokens or load_tokens()
        self._rate_limiter = RateLimiter()
        self._http: httpx.AsyncClient | None = None

    async def __aenter__(self) -> PoeClient:
        self._http = httpx.AsyncClient(
            base_url=POE_API_BASE,
            timeout=30.0,
            headers={"User-Agent": "PathOfPurpose/0.1.0"},
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def _ensure_tokens(self) -> StoredTokens:
        if self._tokens is None:
            raise PoeApiError(401, "Not logged in. Run 'pop login' first.")
        return self._tokens

    async def _ensure_valid_token(self) -> str:
        """Return a valid access token, refreshing if expired."""
        tokens = self._ensure_tokens()
        if tokens.is_expired:
            tokens = await refresh_access_token(self.client_id, tokens.refresh_token)
            self._tokens = tokens
            save_tokens(tokens)
        return tokens.access_token

    # ------------------------------------------------------------------
    # Request helper
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: object,
    ) -> httpx.Response:
        """Make an authenticated, rate-limited request to the PoE API."""
        assert self._http is not None, "Use PoeClient as async context manager"

        token = await self._ensure_valid_token()
        await self._rate_limiter.wait()

        resp = await self._http.request(
            method,
            path,
            headers={"Authorization": f"Bearer {token}"},
            **kwargs,
        )

        self._rate_limiter.update(resp)

        if resp.status_code == 401:
            # Token might have been revoked server-side — try one refresh
            tokens = self._ensure_tokens()
            new_tokens = await refresh_access_token(self.client_id, tokens.refresh_token)
            self._tokens = new_tokens
            save_tokens(new_tokens)

            # Retry once
            await self._rate_limiter.wait()
            resp = await self._http.request(
                method,
                path,
                headers={"Authorization": f"Bearer {new_tokens.access_token}"},
                **kwargs,
            )
            self._rate_limiter.update(resp)

        if resp.status_code >= 400:
            try:
                body = resp.json()
                msg = body.get("error", {}).get("message", resp.text)
            except Exception:
                msg = resp.text
            raise PoeApiError(resp.status_code, msg)

        return resp

    # ------------------------------------------------------------------
    # API methods
    # ------------------------------------------------------------------

    async def get_profile(self) -> Profile:
        """Fetch the authenticated account profile."""
        resp = await self._request("GET", "/profile")
        return Profile.model_validate(resp.json())

    async def list_characters(self) -> list[CharacterEntry]:
        """List all characters on the account."""
        resp = await self._request("GET", "/character")
        data = resp.json()
        # API returns {"characters": [...]} or just [...]
        chars = data.get("characters", data) if isinstance(data, dict) else data
        return [CharacterEntry.model_validate(c) for c in chars]

    async def get_character(self, name: str) -> CharacterDetail:
        """
        Fetch full character detail including equipment and passives.

        Args:
            name: Character name (case-sensitive).

        Returns:
            CharacterDetail with all equipment and passive allocations.
        """
        resp = await self._request("GET", f"/character/{name}")
        data = resp.json()

        # The API nests character info; handle different response shapes
        char_data = data.get("character", data) if isinstance(data, dict) else data

        detail = CharacterDetail(
            id=char_data.get("id", ""),
            name=char_data.get("name", name),
            class_name=char_data.get("class", ""),
            level=char_data.get("level", 0),
            league=char_data.get("league", ""),
            experience=char_data.get("experience", 0),
        )

        # Parse equipment
        items_data = char_data.get("equipment", char_data.get("items", []))
        detail.equipment = [EquippedItem.model_validate(i) for i in items_data]

        # Parse passives
        passives_data = char_data.get("passives", {})
        if passives_data:
            detail.passives = PassiveData.model_validate(passives_data)

        return detail

    async def list_leagues(self) -> list[League]:
        """Fetch active leagues."""
        resp = await self._request("GET", "/league")
        data = resp.json()
        leagues = data.get("leagues", data) if isinstance(data, dict) else data
        return [League.model_validate(lg) for lg in leagues]
