"""Fetch recent patch notes from poepatchnotes.com."""

from __future__ import annotations

import logging

import httpx

from pop.knowledge.models import PatchNote

logger = logging.getLogger(__name__)

PATCH_NOTES_URL = "https://poepatchnotes.com/poe1_data.json"

_HEADERS = {
    "User-Agent": "PathOfPurpose/1.0 (build advisor)",
    "Accept": "application/json",
}

MAX_PATCHES = 3


async def fetch_patch_notes(
    client: httpx.AsyncClient | None = None,
) -> list[PatchNote]:
    """Fetch recent PoE 1 patch notes and return the latest few.

    The API returns an array of {patch, date, notes[]} entries.
    We keep only the most recent MAX_PATCHES entries.
    """
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(headers=_HEADERS, timeout=30)

    try:
        resp = await client.get(PATCH_NOTES_URL)
        resp.raise_for_status()
        data = resp.json()
    finally:
        if owns_client:
            await client.aclose()

    patches: list[PatchNote] = []
    entries = data if isinstance(data, list) else []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        patch = entry.get("patch", "")
        if not patch:
            continue
        notes = entry.get("notes", [])
        if not isinstance(notes, list):
            notes = []
        patches.append(PatchNote(
            patch=patch,
            date=entry.get("date", ""),
            notes=[str(n) for n in notes],
        ))

    # API returns entries in reverse chronological order (newest first).
    # Just take the first MAX_PATCHES entries — no re-sorting needed.
    result = patches[:MAX_PATCHES]

    logger.info(
        "Fetched %d patch notes, keeping latest %d",
        len(patches),
        len(result),
    )
    return result
