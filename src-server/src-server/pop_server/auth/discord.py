"""Discord OAuth2 code exchange and user info fetch."""

from __future__ import annotations

import httpx

from pop_server.config import settings

DISCORD_API = "https://discord.com/api/v10"


async def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange an authorization code for Discord tokens.

    Returns the token response dict with access_token, etc.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{DISCORD_API}/oauth2/token",
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def get_discord_user(access_token: str) -> dict:
    """Fetch the Discord user profile using an access token.

    Returns dict with id, username, avatar, etc.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


async def check_guild_membership(access_token: str, guild_id: str) -> bool:
    """Check if the user is a member of the required Discord server.

    Requires the guilds.members.read or guilds scope on the OAuth token.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{DISCORD_API}/users/@me/guilds",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        guilds = resp.json()
        return any(g["id"] == guild_id for g in guilds)
