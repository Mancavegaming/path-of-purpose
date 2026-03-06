"""Auth API routes — Discord OAuth login + user info."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from pop_server.auth.discord import exchange_code, get_discord_user, check_guild_membership
from pop_server.auth.jwt_utils import create_token
from pop_server.auth.middleware import require_auth
from pop_server.config import settings
from pop_server.db import upsert_user
from pop_server.models import DiscordTokenRequest, TokenResponse, UserInfo

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/discord/token", response_model=TokenResponse)
async def discord_token(req: DiscordTokenRequest):
    """Exchange a Discord OAuth code for a JWT.

    1. Exchange code with Discord for access token
    2. Fetch Discord user profile
    3. Upsert user in DB
    4. Return a signed JWT + user info
    """
    tokens = await exchange_code(req.code, req.redirect_uri)
    access_token = tokens["access_token"]
    discord_user = await get_discord_user(access_token)

    # Verify the user is a member of the required Discord server
    if settings.discord_guild_id:
        is_member = await check_guild_membership(access_token, settings.discord_guild_id)
        if not is_member:
            raise HTTPException(
                status_code=403,
                detail="You must join the Path of Purpose Discord server to use this app. "
                "https://discord.gg/uSnAMzsTGP",
            )

    discord_id = discord_user["id"]
    username = discord_user.get("username", "")
    avatar = discord_user.get("avatar", "") or ""

    user = upsert_user(
        discord_id=discord_id,
        discord_username=username,
        discord_avatar=avatar,
    )

    jwt_token = create_token(
        user_id=user["id"],
        discord_id=discord_id,
        subscription_status=user["subscription_status"],
    )

    return TokenResponse(
        access_token=jwt_token,
        user=UserInfo(
            id=user["id"],
            discord_id=discord_id,
            discord_username=username,
            discord_avatar=avatar,
            subscription_status=user["subscription_status"],
        ),
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user: dict = Depends(require_auth)):
    """Get the current user's info (refreshed from DB)."""
    return UserInfo(
        id=user["id"],
        discord_id=user["discord_id"],
        discord_username=user["discord_username"],
        discord_avatar=user["discord_avatar"],
        subscription_status=user["subscription_status"],
    )
