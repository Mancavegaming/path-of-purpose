"""Tests for OAuth PKCE flow and token store."""

from __future__ import annotations

import json
import time

import pytest

from pop.oauth.client import (
    _generate_code_challenge,
    _generate_code_verifier,
)
from pop.oauth.token_store import StoredTokens


# ===========================================================================
# PKCE helpers
# ===========================================================================


class TestPKCE:
    def test_code_verifier_length(self):
        v = _generate_code_verifier(128)
        assert len(v) == 128

    def test_code_verifier_is_url_safe(self):
        v = _generate_code_verifier()
        # URL-safe Base64 chars only
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        assert set(v).issubset(allowed)

    def test_code_challenge_is_deterministic(self):
        v = "test_verifier_12345"
        c1 = _generate_code_challenge(v)
        c2 = _generate_code_challenge(v)
        assert c1 == c2

    def test_code_challenge_is_url_safe_base64(self):
        v = _generate_code_verifier()
        c = _generate_code_challenge(v)
        # No padding
        assert "=" not in c
        # URL-safe chars only
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        assert set(c).issubset(allowed)

    def test_different_verifiers_produce_different_challenges(self):
        v1 = _generate_code_verifier()
        v2 = _generate_code_verifier()
        assert v1 != v2
        assert _generate_code_challenge(v1) != _generate_code_challenge(v2)


# ===========================================================================
# Token store (in-memory, no keyring)
# ===========================================================================


class TestStoredTokens:
    def test_roundtrip_json(self):
        original = StoredTokens(
            access_token="acc_123",
            refresh_token="ref_456",
            expires_at=time.time() + 3600,
            scope="account:characters",
            account_name="TestPlayer",
        )
        json_str = original.to_json()
        restored = StoredTokens.from_json(json_str)
        assert restored.access_token == original.access_token
        assert restored.refresh_token == original.refresh_token
        assert restored.scope == original.scope
        assert restored.account_name == original.account_name

    def test_is_expired_false_when_future(self):
        t = StoredTokens(
            access_token="a", refresh_token="r",
            expires_at=time.time() + 3600,
        )
        assert t.is_expired is False

    def test_is_expired_true_when_past(self):
        t = StoredTokens(
            access_token="a", refresh_token="r",
            expires_at=time.time() - 100,
        )
        assert t.is_expired is True

    def test_expires_in_seconds(self):
        t = StoredTokens(
            access_token="a", refresh_token="r",
            expires_at=time.time() + 60,
        )
        assert 55 <= t.expires_in_seconds <= 61

    def test_expires_in_seconds_never_negative(self):
        t = StoredTokens(
            access_token="a", refresh_token="r",
            expires_at=time.time() - 100,
        )
        assert t.expires_in_seconds == 0

    def test_from_json_invalid_returns_error(self):
        with pytest.raises((json.JSONDecodeError, KeyError)):
            StoredTokens.from_json("not json")
