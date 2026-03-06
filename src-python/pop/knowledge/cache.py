"""Cache manager for the PoE knowledge base."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from pop.knowledge.models import GemInfo, KnowledgeBase
from pop.knowledge.patch_fetcher import fetch_patch_notes
from pop.knowledge.repoe_fetcher import fetch_gems, fetch_uniques
from pop.knowledge.supplements import get_removed_gem_names, get_supplement_gems

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_FILE = CACHE_DIR / "knowledge.json"


STALE_HOURS = 24


def load_knowledge() -> KnowledgeBase | None:
    """Load cached knowledge from disk. Returns None if no cache exists."""
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return KnowledgeBase(**data)
    except Exception as exc:
        logger.warning("Failed to load knowledge cache: %s", exc)
        return None


def is_knowledge_stale() -> bool:
    """Return True if knowledge cache is missing or older than STALE_HOURS."""
    kb = load_knowledge()
    if kb is None:
        return True
    try:
        updated = datetime.fromisoformat(kb.last_updated)
        age_hours = (datetime.now() - updated).total_seconds() / 3600
        return age_hours > STALE_HOURS
    except (ValueError, TypeError):
        return True


def save_knowledge(kb: KnowledgeBase) -> None:
    """Save knowledge base to the cache file."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        kb.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info("Knowledge cache saved to %s", CACHE_FILE)


def _merge_supplements(gems: list[GemInfo]) -> list[GemInfo]:
    """Merge supplement gems into RePoE data.

    - Removes gems that were removed/replaced in the current patch
    - Adds new gems from supplements that aren't already in RePoE
    """
    removed = get_removed_gem_names()
    supplements = get_supplement_gems()

    # Filter out removed gems
    filtered = [g for g in gems if g.name not in removed]

    # Add supplements that aren't already present
    existing_names = {g.name for g in filtered}
    for gem in supplements:
        if gem.name not in existing_names:
            filtered.append(gem)
            existing_names.add(gem.name)

    return sorted(filtered, key=lambda g: (g.is_support, g.required_level, g.name))


async def refresh_knowledge() -> KnowledgeBase:
    """Fetch all knowledge sources and save to cache.

    Returns the assembled KnowledgeBase.
    """
    import httpx

    async with httpx.AsyncClient(
        headers={"User-Agent": "PathOfPurpose/1.0 (build advisor)"},
        timeout=60,
    ) as client:
        gems = await fetch_gems(client)
        uniques = await fetch_uniques(client)
        patch_notes = await fetch_patch_notes(client)

    # Derive version from the most significant recent patch (content update > hotfix)
    version = "unknown"
    if patch_notes:
        for pn in patch_notes:
            if "content update" in pn.patch.lower():
                version = pn.patch
                break
        else:
            version = patch_notes[0].patch

    # Merge supplement data (new gems not yet in RePoE, removed gem filtering)
    gems = _merge_supplements(gems)

    kb = KnowledgeBase(
        gems=gems,
        uniques=uniques,
        patch_notes=patch_notes,
        version=version,
        last_updated=datetime.now().isoformat(),
    )

    save_knowledge(kb)
    return kb
