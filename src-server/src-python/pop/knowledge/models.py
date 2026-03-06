"""Pydantic models for the PoE knowledge base."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GemInfo(BaseModel):
    """Compact reference for a single skill gem."""

    name: str
    required_level: int = 0
    is_support: bool = False
    tags: list[str] = Field(default_factory=list)


class UniqueInfo(BaseModel):
    """Compact reference for a unique item."""

    name: str
    base_type: str = ""
    item_class: str = ""


class PatchNote(BaseModel):
    """A single patch note entry."""

    patch: str
    date: str = ""
    notes: list[str] = Field(default_factory=list)


class KnowledgeBase(BaseModel):
    """Cached game knowledge injected into AI prompts."""

    gems: list[GemInfo] = Field(default_factory=list)
    uniques: list[UniqueInfo] = Field(default_factory=list)
    patch_notes: list[PatchNote] = Field(default_factory=list)
    version: str = ""
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())
