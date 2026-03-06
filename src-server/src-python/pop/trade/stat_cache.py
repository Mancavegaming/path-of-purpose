"""
Stat catalog cache for PoE 1 Trade API.

Fetches the stats catalog from pathofexile.com/api/trade/data/stats,
caches to disk with 1h TTL, and provides fuzzy matching of mod text to stat IDs.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import time

import httpx
from rapidfuzz import fuzz, process

from pop.trade.models import StatEntry

logger = logging.getLogger(__name__)

STATS_URL = "https://www.pathofexile.com/api/trade/data/stats"
CACHE_DIR = os.path.join(tempfile.gettempdir(), "path-of-purpose")
CACHE_FILE = os.path.join(CACHE_DIR, "trade_stats_cache.json")
CACHE_TTL = 3600  # 1 hour
USER_AGENT = "PathOfPurpose/0.1.0"
MATCH_THRESHOLD = 75


def _normalize_mod(text: str) -> str:
    """Normalize a mod string for fuzzy comparison.

    Strips numbers so "+120 to maximum Life" and "+# to maximum Life"
    compare as the same mod type.
    """
    normalized = re.sub(r"[\d.]+", "#", text)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.lower()


class StatCache:
    """Loads and caches the trade stats catalog, with fuzzy mod matching."""

    def __init__(self) -> None:
        self._stats: list[StatEntry] = []
        self._by_type: dict[str, list[StatEntry]] = {}
        # Pre-computed normalized text → StatEntry for fast lookup
        self._norm_index: dict[str, list[StatEntry]] = {}

    @property
    def loaded(self) -> bool:
        return len(self._stats) > 0

    async def ensure_loaded(self) -> None:
        """Load stats from disk cache or fetch from API if stale."""
        if self.loaded:
            return

        cached = self._load_from_disk()
        if cached is not None:
            self._ingest(cached)
            return

        raw = await self._fetch_from_api()
        self._save_to_disk(raw)
        self._ingest(raw)

    def _load_from_disk(self) -> list[dict] | None:
        """Load cached stats JSON from disk if fresh enough."""
        if not os.path.exists(CACHE_FILE):
            return None
        try:
            mtime = os.path.getmtime(CACHE_FILE)
            if time.time() - mtime > CACHE_TTL:
                return None
            with open(CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load stat cache: %s", exc)
            return None

    def _save_to_disk(self, entries: list[dict]) -> None:
        """Save stats JSON to disk cache."""
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(entries, f)
        except OSError as exc:
            logger.warning("Failed to save stat cache: %s", exc)

    async def _fetch_from_api(self) -> list[dict]:
        """Fetch stats catalog from pathofexile.com trade API."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                STATS_URL,
                headers={"User-Agent": USER_AGENT},
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()

        # API returns {"result": [{"label": "...", "entries": [...]}]}
        entries: list[dict] = []
        for group in data.get("result", []):
            stat_type = group.get("label", "").lower()
            for entry in group.get("entries", []):
                entries.append({
                    "id": entry["id"],
                    "text": entry.get("text", ""),
                    "type": stat_type,
                })
        logger.info("Fetched %d stats from trade API", len(entries))
        return entries

    def _ingest(self, raw: list[dict]) -> None:
        """Build internal indexes from raw stat entries."""
        self._stats = [StatEntry(**e) for e in raw]
        self._by_type = {}
        self._norm_index = {}

        for stat in self._stats:
            self._by_type.setdefault(stat.type, []).append(stat)
            norm = _normalize_mod(stat.text)
            self._norm_index.setdefault(norm, []).append(stat)

    def match_mod(
        self,
        mod_text: str,
        stat_type: str = "explicit",
    ) -> StatEntry | None:
        """Fuzzy-match a mod line to a stat ID.

        Args:
            mod_text: The modifier text from a PoB item (e.g. "+120 to maximum Life").
            stat_type: The stat type to search within ("explicit", "implicit", "crafted").

        Returns:
            The best matching StatEntry, or None if no match above threshold.
        """
        norm = _normalize_mod(mod_text)

        # Fast path: exact normalized match
        if norm in self._norm_index:
            for entry in self._norm_index[norm]:
                if entry.type == stat_type:
                    return entry

        # Fuzzy match within the correct type
        candidates = self._by_type.get(stat_type, [])
        if not candidates:
            return None

        choices = {i: _normalize_mod(s.text) for i, s in enumerate(candidates)}
        result = process.extractOne(
            norm,
            choices,
            scorer=fuzz.ratio,
            score_cutoff=MATCH_THRESHOLD,
        )
        if result is None:
            return None

        _text, score, idx = result
        logger.debug("Matched '%s' → '%s' (score=%.0f)", mod_text, candidates[idx].text, score)
        return candidates[idx]
