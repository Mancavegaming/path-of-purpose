"""JWT token creation and verification."""

from __future__ import annotations

import time

import jwt

from pop_server.config import settings


def create_token(user_id: int, discord_id: str, subscription_status: str) -> str:
    """Create a signed JWT for the given user."""
    now = time.time()
    payload = {
        "sub": user_id,
        "discord_id": discord_id,
        "subscription_status": subscription_status,
        "iat": int(now),
        "exp": int(now + settings.jwt_expiry_hours * 3600),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
