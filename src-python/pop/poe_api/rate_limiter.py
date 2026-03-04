"""
Rate limiter that respects PoE API's X-Rate-Limit headers.

The PoE API returns headers like:
    X-Rate-Limit-Ip: 45:60:60,240:240:900
    X-Rate-Limit-Ip-State: 1:60:0,1:240:0

Format: "max_hits:period_seconds:penalty_seconds,..."

This module implements a pre-request check + post-response update pattern
so callers never exceed the advertised limits.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class _RateWindow:
    """A single rate limit window (e.g., 45 requests per 60 seconds)."""

    max_hits: int
    period: float  # seconds
    penalty: float  # seconds
    current_hits: int = 0
    window_start: float = 0.0

    def reset_if_expired(self, now: float) -> None:
        if now - self.window_start >= self.period:
            self.current_hits = 0
            self.window_start = now

    @property
    def remaining(self) -> int:
        return max(0, self.max_hits - self.current_hits)

    @property
    def wait_seconds(self) -> float:
        """Seconds to wait before this window allows another request."""
        if self.remaining > 0:
            return 0.0
        return max(0.0, self.period - (time.monotonic() - self.window_start))


@dataclass
class RateLimiter:
    """
    Adaptive rate limiter for the PoE API.

    Usage:
        limiter = RateLimiter()
        await limiter.wait()          # blocks if near limit
        response = await client.get(...)
        limiter.update(response)      # parse rate headers
    """

    windows: list[_RateWindow] = field(default_factory=list)
    penalty_until: float = 0.0  # monotonic time when penalty expires
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    # Safety margin: stop 2 requests before the hard limit
    safety_margin: int = 2

    def _ensure_defaults(self) -> None:
        """Set conservative default windows if we haven't seen headers yet."""
        if not self.windows:
            self.windows = [
                _RateWindow(max_hits=40, period=60, penalty=60, window_start=time.monotonic()),
                _RateWindow(max_hits=200, period=240, penalty=900, window_start=time.monotonic()),
            ]

    async def wait(self) -> None:
        """Wait until it's safe to make a request."""
        async with self._lock:
            self._ensure_defaults()
            now = time.monotonic()

            # Check penalty
            if now < self.penalty_until:
                wait = self.penalty_until - now
                await asyncio.sleep(wait)
                now = time.monotonic()

            # Check each window
            for window in self.windows:
                window.reset_if_expired(now)
                if window.remaining <= self.safety_margin:
                    wait = window.wait_seconds
                    if wait > 0:
                        await asyncio.sleep(wait)
                        window.reset_if_expired(time.monotonic())

            # Record the hit
            for window in self.windows:
                window.current_hits += 1

    def update_from_headers(self, headers: dict[str, str]) -> None:
        """
        Parse PoE rate-limit headers and update internal state.

        Looks for headers like:
            X-Rate-Limit-Ip: 45:60:60,240:240:900
            X-Rate-Limit-Ip-State: 1:60:0,1:240:0
        """
        # Find the limit definition header
        limit_header = None
        state_header = None
        for key in ("x-rate-limit-ip", "x-rate-limit-account", "x-rate-limit-policy"):
            if key in headers:
                limit_header = headers[key]
                state_key = f"{key}-state"
                state_header = headers.get(state_key, "")
                break

        if not limit_header:
            return

        # Parse limit windows
        try:
            limit_parts = limit_header.split(",")
            new_windows: list[_RateWindow] = []
            for part in limit_parts:
                max_hits, period, penalty = part.strip().split(":")
                new_windows.append(_RateWindow(
                    max_hits=int(max_hits),
                    period=float(period),
                    penalty=float(penalty),
                    window_start=time.monotonic(),
                ))
            self.windows = new_windows
        except (ValueError, IndexError):
            return  # Malformed header, keep current windows

        # Parse current state
        if state_header:
            try:
                state_parts = state_header.split(",")
                for i, part in enumerate(state_parts):
                    if i < len(self.windows):
                        hits, _period, penalty_active = part.strip().split(":")
                        self.windows[i].current_hits = int(hits)
                        if int(penalty_active) > 0:
                            self.penalty_until = time.monotonic() + self.windows[i].penalty
            except (ValueError, IndexError):
                pass

    def update(self, response: httpx.Response) -> None:
        """Convenience: extract headers from an httpx response."""
        # httpx headers are case-insensitive
        headers = {k.lower(): v for k, v in response.headers.items()}
        self.update_from_headers(headers)
