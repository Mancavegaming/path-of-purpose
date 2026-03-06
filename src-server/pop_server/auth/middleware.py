"""FastAPI dependencies for authentication and subscription checks."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from pop_server.auth.jwt_utils import decode_token
from pop_server.db import get_user_by_id, get_daily_usage_count

DAILY_AI_LIMIT = 200


def _extract_token(request: Request) -> str:
    """Extract Bearer token from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return auth[7:]


async def require_auth(request: Request) -> dict:
    """Dependency: verify JWT and return the user dict.

    Refreshes subscription_status from DB (JWT might be stale).
    """
    token = _extract_token(request)
    try:
        payload = decode_token(token)
    except Exception as exc:
        import logging
        logging.error("JWT decode failed: %s", exc)
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {exc}")

    user = get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def require_subscription(user: dict = Depends(require_auth)) -> dict:
    """Dependency: require an active subscription.

    Also enforces the daily AI request rate limit.
    """
    if user["subscription_status"] not in ("active", "trialing"):
        raise HTTPException(
            status_code=403,
            detail="Active subscription required. Subscribe at $4.99/month to use AI features.",
        )

    daily_count = get_daily_usage_count(user["id"])
    if daily_count >= DAILY_AI_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily AI request limit reached ({DAILY_AI_LIMIT}/day). Try again tomorrow.",
        )

    return user
