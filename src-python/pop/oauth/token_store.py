"""
Secure token storage using the OS credential manager.

On Windows this uses the Windows Credential Locker (DPAPI) via the
``keyring`` library. Tokens are stored per-account so multiple PoE
accounts can be used without conflict.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

import keyring

SERVICE_NAME = "PathOfPurpose"
TOKEN_KEY = "poe_oauth_tokens"


@dataclass
class StoredTokens:
    """OAuth token set persisted between sessions."""

    access_token: str
    refresh_token: str
    expires_at: float  # Unix timestamp
    scope: str = ""
    account_name: str = ""

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at

    @property
    def expires_in_seconds(self) -> int:
        return max(0, int(self.expires_at - time.time()))

    def to_json(self) -> str:
        return json.dumps({
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "scope": self.scope,
            "account_name": self.account_name,
        })

    @classmethod
    def from_json(cls, data: str) -> StoredTokens:
        d = json.loads(data)
        return cls(
            access_token=d["access_token"],
            refresh_token=d["refresh_token"],
            expires_at=d["expires_at"],
            scope=d.get("scope", ""),
            account_name=d.get("account_name", ""),
        )


def save_tokens(tokens: StoredTokens) -> None:
    """Persist tokens to the OS credential store."""
    keyring.set_password(SERVICE_NAME, TOKEN_KEY, tokens.to_json())


def load_tokens() -> StoredTokens | None:
    """Load tokens from the OS credential store, or None if not found."""
    data = keyring.get_password(SERVICE_NAME, TOKEN_KEY)
    if data is None:
        return None
    try:
        return StoredTokens.from_json(data)
    except (json.JSONDecodeError, KeyError):
        return None


def delete_tokens() -> None:
    """Remove stored tokens (logout)."""
    try:
        keyring.delete_password(SERVICE_NAME, TOKEN_KEY)
    except keyring.errors.PasswordDeleteError:
        pass  # Already deleted
