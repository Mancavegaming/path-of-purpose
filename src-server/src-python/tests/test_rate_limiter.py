"""Tests for the PoE API rate limiter."""

from __future__ import annotations

import asyncio
import time

import pytest

from pop.poe_api.rate_limiter import RateLimiter, _RateWindow


# ===========================================================================
# RateWindow unit tests
# ===========================================================================


class TestRateWindow:
    def test_remaining_starts_at_max(self):
        w = _RateWindow(max_hits=45, period=60, penalty=60, window_start=time.monotonic())
        assert w.remaining == 45

    def test_remaining_decreases(self):
        w = _RateWindow(max_hits=45, period=60, penalty=60, window_start=time.monotonic())
        w.current_hits = 40
        assert w.remaining == 5

    def test_remaining_floors_at_zero(self):
        w = _RateWindow(max_hits=10, period=60, penalty=60, window_start=time.monotonic())
        w.current_hits = 99
        assert w.remaining == 0

    def test_reset_when_expired(self):
        w = _RateWindow(
            max_hits=10, period=60, penalty=60,
            current_hits=10, window_start=time.monotonic() - 120,
        )
        w.reset_if_expired(time.monotonic())
        assert w.current_hits == 0

    def test_no_reset_when_not_expired(self):
        w = _RateWindow(
            max_hits=10, period=60, penalty=60,
            current_hits=5, window_start=time.monotonic(),
        )
        w.reset_if_expired(time.monotonic())
        assert w.current_hits == 5


# ===========================================================================
# RateLimiter integration
# ===========================================================================


class TestRateLimiter:
    def test_creates_default_windows(self):
        rl = RateLimiter()
        rl._ensure_defaults()
        assert len(rl.windows) == 2

    @pytest.mark.asyncio
    async def test_wait_does_not_block_under_limit(self):
        rl = RateLimiter()
        start = time.monotonic()
        await rl.wait()
        elapsed = time.monotonic() - start
        assert elapsed < 1.0  # Should be near-instant

    @pytest.mark.asyncio
    async def test_wait_increments_hit_count(self):
        rl = RateLimiter()
        await rl.wait()
        assert rl.windows[0].current_hits == 1
        await rl.wait()
        assert rl.windows[0].current_hits == 2

    def test_update_from_headers_parses_limits(self):
        rl = RateLimiter()
        rl.update_from_headers({
            "x-rate-limit-ip": "45:60:60,240:240:900",
            "x-rate-limit-ip-state": "10:60:0,20:240:0",
        })
        assert len(rl.windows) == 2
        assert rl.windows[0].max_hits == 45
        assert rl.windows[0].period == 60
        assert rl.windows[0].current_hits == 10
        assert rl.windows[1].max_hits == 240
        assert rl.windows[1].current_hits == 20

    def test_update_from_headers_detects_penalty(self):
        rl = RateLimiter()
        rl.update_from_headers({
            "x-rate-limit-ip": "45:60:60",
            "x-rate-limit-ip-state": "45:60:30",  # penalty_active=30
        })
        assert rl.penalty_until > time.monotonic()

    def test_update_from_headers_no_op_on_missing(self):
        rl = RateLimiter()
        rl._ensure_defaults()
        original_count = len(rl.windows)
        rl.update_from_headers({})
        assert len(rl.windows) == original_count

    def test_update_from_headers_handles_malformed(self):
        rl = RateLimiter()
        rl._ensure_defaults()
        # Should not crash
        rl.update_from_headers({"x-rate-limit-ip": "garbage"})
        assert len(rl.windows) >= 1
