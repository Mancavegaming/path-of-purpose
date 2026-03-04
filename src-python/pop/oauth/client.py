"""
OAuth 2.0 Authorization Code + PKCE client for the PoE API.

Desktop flow:
  1. Generate code_verifier / code_challenge (S256)
  2. Open the user's browser to pathofexile.com/oauth/authorize
  3. Spin up a tiny localhost HTTP server to catch the redirect callback
  4. Exchange the authorization code for access + refresh tokens
  5. Persist tokens via token_store

All HTTP is async via httpx.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import http.server
import secrets
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass, field

import httpx

from pop.oauth.token_store import StoredTokens, save_tokens

# ---------------------------------------------------------------------------
# PoE OAuth endpoints
# ---------------------------------------------------------------------------

POE_AUTH_URL = "https://www.pathofexile.com/oauth/authorize"
POE_TOKEN_URL = "https://www.pathofexile.com/oauth/token"
DEFAULT_SCOPES = "account:profile account:characters account:stashes account:league_accounts"
CALLBACK_PORT = 8457
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------


def _generate_code_verifier(length: int = 128) -> str:
    """Generate a random code_verifier (43-128 chars, URL-safe)."""
    return secrets.token_urlsafe(length)[:length]


def _generate_code_challenge(verifier: str) -> str:
    """SHA-256 hash of the verifier, Base64url-encoded (no padding)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# Localhost callback server
# ---------------------------------------------------------------------------


@dataclass
class _CallbackResult:
    """Mutable container to pass the auth code out of the callback handler."""

    code: str | None = None
    error: str | None = None
    state: str | None = None
    event: threading.Event = field(default_factory=threading.Event)


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Handles the OAuth redirect back to localhost."""

    result: _CallbackResult  # set by the server before handling

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            self.result.code = params["code"][0]
            self.result.state = params.get("state", [None])[0]
            self._respond(
                200,
                "<html><body><h2>Path of Purpose</h2>"
                "<p>Authorization successful! You can close this tab.</p>"
                "</body></html>",
            )
        elif "error" in params:
            self.result.error = params["error"][0]
            self._respond(
                400,
                f"<html><body><h2>Authorization failed</h2>"
                f"<p>{self.result.error}</p></body></html>",
            )
        else:
            self._respond(404, "<html><body>Not found</body></html>")
            return  # Don't signal the event for unrelated requests

        self.result.event.set()

    def _respond(self, status: int, body: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        pass  # Suppress console output


def _wait_for_callback(result: _CallbackResult, timeout: float = 120) -> str:
    """
    Start a localhost HTTP server and block until the OAuth callback arrives.

    Returns the authorization code.
    Raises RuntimeError on timeout or error.
    """
    handler_class = type(
        "_BoundHandler",
        (_CallbackHandler,),
        {"result": result},
    )

    server = http.server.HTTPServer(("127.0.0.1", CALLBACK_PORT), handler_class)
    server.timeout = timeout

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        if not result.event.wait(timeout=timeout):
            raise RuntimeError(
                f"OAuth callback timed out after {timeout}s. "
                "Make sure you completed the authorization in your browser."
            )

        if result.error:
            raise RuntimeError(f"OAuth authorization denied: {result.error}")

        if not result.code:
            raise RuntimeError("No authorization code received.")

        return result.code
    finally:
        server.shutdown()
        thread.join(timeout=5)


# ---------------------------------------------------------------------------
# Token exchange
# ---------------------------------------------------------------------------


async def _exchange_code(
    client_id: str,
    code: str,
    code_verifier: str,
) -> StoredTokens:
    """Exchange authorization code for tokens via the PoE token endpoint."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            POE_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()

    return StoredTokens(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=time.time() + data.get("expires_in", 3600),
        scope=data.get("scope", ""),
    )


async def refresh_access_token(
    client_id: str,
    refresh_token: str,
) -> StoredTokens:
    """Use a refresh token to obtain a new access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            POE_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()

    tokens = StoredTokens(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", refresh_token),
        expires_at=time.time() + data.get("expires_in", 3600),
        scope=data.get("scope", ""),
    )
    save_tokens(tokens)
    return tokens


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def login(
    client_id: str,
    scopes: str = DEFAULT_SCOPES,
    timeout: float = 120,
) -> StoredTokens:
    """
    Run the full OAuth PKCE login flow.

    1. Opens the user's browser to pathofexile.com
    2. Waits for the callback on localhost
    3. Exchanges the code for tokens
    4. Saves tokens to the OS credential store

    Args:
        client_id: Your PoE API application client ID.
        scopes: Space-separated OAuth scopes.
        timeout: Max seconds to wait for user to authorize.

    Returns:
        StoredTokens with the access/refresh tokens.
    """
    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(32)

    # Build authorization URL
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "scope": scopes,
        "state": state,
        "redirect_uri": REDIRECT_URI,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    auth_url = f"{POE_AUTH_URL}?{params}"

    # Start callback server in background, then open browser
    result = _CallbackResult()

    print(f"Opening browser for PoE authorization...")
    print(f"If the browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Block until callback
    code = _wait_for_callback(result, timeout=timeout)

    # Verify state
    if result.state != state:
        raise RuntimeError("OAuth state mismatch — possible CSRF attack.")

    # Exchange code for tokens
    tokens = await _exchange_code(client_id, code, code_verifier)
    save_tokens(tokens)

    print("Login successful!")
    return tokens


def login_sync(
    client_id: str,
    scopes: str = DEFAULT_SCOPES,
    timeout: float = 120,
) -> StoredTokens:
    """Synchronous wrapper for login() — convenience for CLI usage."""
    return asyncio.run(login(client_id, scopes, timeout))
