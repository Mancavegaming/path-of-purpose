"""
Secure storage for AI provider API keys via OS credential manager.

Supports multiple providers (Anthropic, Gemini). Uses keyring
to store keys in Windows Credential Locker (DPAPI).
"""

from __future__ import annotations

import keyring

SERVICE_NAME = "PathOfPurpose"

# Key names per provider
_KEY_NAMES = {
    "anthropic": "anthropic_api_key",
    "gemini": "gemini_api_key",
}
_PROVIDER_KEY = "ai_provider"


def save_api_key(api_key: str, provider: str = "anthropic") -> None:
    """Store an API key in the OS credential store."""
    key_name = _KEY_NAMES.get(provider, f"{provider}_api_key")
    keyring.set_password(SERVICE_NAME, key_name, api_key)


def load_api_key(provider: str = "anthropic") -> str | None:
    """Load an API key from the OS credential store."""
    key_name = _KEY_NAMES.get(provider, f"{provider}_api_key")
    return keyring.get_password(SERVICE_NAME, key_name)


def has_api_key(provider: str = "anthropic") -> bool:
    """Check whether an API key is stored for the given provider."""
    return load_api_key(provider) is not None


def save_provider(name: str) -> None:
    """Persist the user's preferred AI provider."""
    keyring.set_password(SERVICE_NAME, _PROVIDER_KEY, name)


def load_provider() -> str:
    """Load the user's preferred AI provider. Defaults to 'gemini'."""
    val = keyring.get_password(SERVICE_NAME, _PROVIDER_KEY)
    return val if val in ("anthropic", "gemini") else "gemini"
