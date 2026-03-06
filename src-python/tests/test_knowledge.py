"""Tests for the PoE knowledge base system."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from pop.knowledge.cache import load_knowledge, save_knowledge
from pop.knowledge.models import GemInfo, KnowledgeBase, PatchNote, UniqueInfo
from pop.knowledge.patch_fetcher import fetch_patch_notes
from pop.knowledge.repoe_fetcher import fetch_gems, fetch_uniques
from pop.ai.prompts import build_knowledge_addendum, build_knowledge_lite


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_gem_info_creation(self):
        gem = GemInfo(name="Fireball", required_level=1, is_support=False, tags=["Fire", "Spell"])
        assert gem.name == "Fireball"
        assert gem.required_level == 1
        assert not gem.is_support
        assert gem.tags == ["Fire", "Spell"]

    def test_gem_info_defaults(self):
        gem = GemInfo(name="Test")
        assert gem.required_level == 0
        assert not gem.is_support
        assert gem.tags == []

    def test_unique_info_creation(self):
        u = UniqueInfo(name="Tabula Rasa", base_type="Simple Robe", item_class="Body Armour")
        assert u.name == "Tabula Rasa"
        assert u.base_type == "Simple Robe"
        assert u.item_class == "Body Armour"

    def test_patch_note_creation(self):
        pn = PatchNote(patch="3.28.0", date="2026-03-06", notes=["New skill: X", "Buffed Y"])
        assert pn.patch == "3.28.0"
        assert len(pn.notes) == 2

    def test_knowledge_base_creation(self):
        kb = KnowledgeBase(
            gems=[GemInfo(name="Fireball")],
            uniques=[UniqueInfo(name="Tabula Rasa")],
            patch_notes=[PatchNote(patch="3.28.0")],
            version="3.28.0",
        )
        assert len(kb.gems) == 1
        assert len(kb.uniques) == 1
        assert kb.version == "3.28.0"
        assert kb.last_updated  # Should have a default

    def test_knowledge_base_empty(self):
        kb = KnowledgeBase()
        assert kb.gems == []
        assert kb.uniques == []
        assert kb.patch_notes == []
        assert kb.version == ""


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------


class TestCache:
    def test_save_load_roundtrip(self, tmp_path):
        """Knowledge should survive save/load cycle."""
        cache_file = tmp_path / "knowledge.json"

        kb = KnowledgeBase(
            gems=[
                GemInfo(name="Fireball", required_level=1, tags=["Fire", "Spell"]),
                GemInfo(name="Added Fire Damage Support", required_level=8, is_support=True),
            ],
            uniques=[
                UniqueInfo(name="Tabula Rasa", base_type="Simple Robe", item_class="Body Armour"),
            ],
            patch_notes=[
                PatchNote(patch="3.28.0", date="2026-03-06", notes=["New skill gem: X"]),
            ],
            version="3.28.0",
            last_updated="2026-03-04T12:00:00",
        )

        # Patch CACHE_FILE to use tmp_path
        with patch("pop.knowledge.cache.CACHE_FILE", cache_file), \
             patch("pop.knowledge.cache.CACHE_DIR", tmp_path):
            save_knowledge(kb)
            assert cache_file.exists()

            loaded = load_knowledge()
            assert loaded is not None
            assert len(loaded.gems) == 2
            assert loaded.gems[0].name == "Fireball"
            assert loaded.gems[1].is_support
            assert len(loaded.uniques) == 1
            assert loaded.uniques[0].name == "Tabula Rasa"
            assert loaded.version == "3.28.0"

    def test_load_missing_cache(self, tmp_path):
        """Should return None when cache file doesn't exist."""
        cache_file = tmp_path / "nonexistent.json"
        with patch("pop.knowledge.cache.CACHE_FILE", cache_file):
            assert load_knowledge() is None

    def test_load_corrupt_cache(self, tmp_path):
        """Should return None on corrupt cache file."""
        cache_file = tmp_path / "knowledge.json"
        cache_file.write_text("not valid json", encoding="utf-8")
        with patch("pop.knowledge.cache.CACHE_FILE", cache_file):
            assert load_knowledge() is None


# ---------------------------------------------------------------------------
# Fetcher tests (mocked HTTP)
# ---------------------------------------------------------------------------


def _mock_response(data, status_code=200):
    """Create a mock httpx.Response."""
    resp = httpx.Response(
        status_code=status_code,
        json=data,
        request=httpx.Request("GET", "https://example.com"),
    )
    return resp


class TestRepoeFetcher:
    @pytest.mark.asyncio
    async def test_fetch_gems_filters_released(self):
        """Only released gems should be included."""
        mock_data = {
            "Fireball": {
                "base_item": {"display_name": "Fireball", "release_state": "released"},
                "per_level": {"1": {"required_level": 1}},
                "is_support": False,
                "active_skill": {"types": ["Fire", "Spell", "Projectile"]},
            },
            "SecretSkill": {
                "base_item": {"display_name": "Secret Skill", "release_state": "unreleased"},
                "per_level": {"1": {"required_level": 50}},
                "is_support": False,
                "active_skill": {"types": ["Lightning"]},
            },
            "Added Fire Damage Support": {
                "base_item": {"display_name": "Added Fire Damage Support", "release_state": "released"},
                "per_level": {"1": {"required_level": 8}},
                "is_support": True,
                "tags": ["Fire", "Support"],
            },
        }

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(mock_data))

        gems = await fetch_gems(client)

        assert len(gems) == 2
        names = {g.name for g in gems}
        assert "Fireball" in names
        assert "Added Fire Damage Support" in names
        assert "Secret Skill" not in names

    @pytest.mark.asyncio
    async def test_fetch_gems_deduplicates(self):
        """Duplicate gem names should be collapsed."""
        mock_data = {
            "Fireball": {
                "base_item": {"display_name": "Fireball", "release_state": "released"},
                "per_level": {"1": {"required_level": 1}},
                "is_support": False,
                "active_skill": {"types": ["Fire"]},
            },
            "Vaal Fireball": {
                "base_item": {"display_name": "Fireball", "release_state": "released"},
                "per_level": {"1": {"required_level": 1}},
                "is_support": False,
                "active_skill": {"types": ["Fire"]},
            },
        }

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(mock_data))

        gems = await fetch_gems(client)
        assert len(gems) == 1

    @pytest.mark.asyncio
    async def test_fetch_uniques_list_format(self):
        """Handle uniques.json as a list of objects."""
        mock_data = [
            {"name": "Tabula Rasa", "base_type": "Simple Robe", "item_class": "Body Armour"},
            {"name": "Goldrim", "base_type": "Leather Cap", "item_class": "Helmet"},
        ]

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(mock_data))

        uniques = await fetch_uniques(client)
        assert len(uniques) == 2
        names = {u.name for u in uniques}
        assert "Tabula Rasa" in names
        assert "Goldrim" in names

    @pytest.mark.asyncio
    async def test_fetch_uniques_dict_format(self):
        """Handle uniques.json as a dict keyed by ID."""
        mock_data = {
            "1": {"name": "Tabula Rasa", "base_type": "Simple Robe", "item_class": "Body Armour"},
            "2": {"name": "Goldrim", "base_type": "Leather Cap", "item_class": "Helmet"},
        }

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(mock_data))

        uniques = await fetch_uniques(client)
        assert len(uniques) == 2


class TestPatchFetcher:
    @pytest.mark.asyncio
    async def test_fetch_patch_notes(self):
        """Should parse and return latest patches."""
        mock_data = [
            {"patch": "3.28.0", "date": "2026-03-06", "notes": ["New skill: X"]},
            {"patch": "3.27.1", "date": "2026-02-15", "notes": ["Bug fix"]},
            {"patch": "3.27.0", "date": "2026-01-10", "notes": ["League start"]},
            {"patch": "3.26.0", "date": "2025-10-01", "notes": ["Old patch"]},
        ]

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(mock_data))

        patches = await fetch_patch_notes(client)
        assert len(patches) == 3  # MAX_PATCHES = 3
        assert patches[0].patch == "3.28.0"
        assert patches[1].patch == "3.27.1"

    @pytest.mark.asyncio
    async def test_fetch_empty_response(self):
        """Handle empty array response."""
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response([]))

        patches = await fetch_patch_notes(client)
        assert patches == []


# ---------------------------------------------------------------------------
# Prompt addendum tests
# ---------------------------------------------------------------------------


class TestPromptAddendum:
    def test_addendum_with_knowledge(self):
        kb = KnowledgeBase(
            gems=[
                GemInfo(name="Fireball", required_level=1, tags=["Fire", "Spell"]),
                GemInfo(
                    name="Added Fire Damage Support",
                    required_level=8,
                    is_support=True,
                    tags=["Fire", "Support"],
                ),
            ],
            uniques=[
                UniqueInfo(name="Tabula Rasa", base_type="Simple Robe", item_class="Body Armour"),
            ],
            patch_notes=[
                PatchNote(patch="3.28.0", notes=["New skill gem: Voltaic Burst"]),
            ],
            version="3.28.0",
            last_updated="2026-03-04T12:00:00",
        )

        result = build_knowledge_addendum(kb)
        assert "Fireball" in result
        assert "Added Fire Damage Support" in result
        assert "3.28.0" in result
        assert "ONLY use gems" in result

    def test_addendum_empty_knowledge(self):
        kb = KnowledgeBase()
        result = build_knowledge_addendum(kb)
        # Even with empty knowledge, balance/meta data is injected
        assert "GAME DATA REFERENCE" in result

    def test_lite_addendum_with_knowledge(self):
        kb = KnowledgeBase(
            version="3.28.0",
            patch_notes=[
                PatchNote(patch="3.28.0", notes=["New skill gem added", "Balance changes"]),
            ],
        )

        result = build_knowledge_lite(kb)
        assert "3.28.0" in result
        assert "new" in result.lower() or "Game data" in result

    def test_lite_addendum_empty(self):
        kb = KnowledgeBase()
        result = build_knowledge_lite(kb)
        # Even with empty knowledge, balance/meta data is injected
        assert "GAME DATA" in result


# ---------------------------------------------------------------------------
# Integration: refresh_knowledge (mocked)
# ---------------------------------------------------------------------------


class TestRefreshKnowledge:
    @pytest.mark.asyncio
    async def test_refresh_saves_and_returns(self, tmp_path):
        """refresh_knowledge should fetch all sources and save cache."""
        from pop.knowledge.cache import refresh_knowledge
        from pop.knowledge.models import GemInfo, PatchNote, UniqueInfo

        # Mock the individual fetcher functions instead of httpx directly
        mock_gems = [GemInfo(name="Ice Nova", required_level=12, tags=["Cold", "Spell", "AoE"])]
        mock_uniques = [UniqueInfo(name="Lifesprig", base_type="Driftwood Wand", item_class="Wand")]
        mock_patches = [PatchNote(patch="3.28.0", date="2026-03-06", notes=["Patch note 1"])]

        cache_file = tmp_path / "knowledge.json"

        with patch("pop.knowledge.cache.CACHE_FILE", cache_file), \
             patch("pop.knowledge.cache.CACHE_DIR", tmp_path), \
             patch("pop.knowledge.cache.fetch_gems", return_value=mock_gems), \
             patch("pop.knowledge.cache.fetch_uniques", return_value=mock_uniques), \
             patch("pop.knowledge.cache.fetch_patch_notes", return_value=mock_patches):

            kb = await refresh_knowledge()

        # Supplements merge in new 3.28 gems, so count > 1
        gem_names = {g.name for g in kb.gems}
        assert "Ice Nova" in gem_names  # from mock RePoE data
        assert "Holy Hammers" in gem_names  # from supplements
        assert "Greater Spell Echo Support" in gem_names  # exceptional support
        assert len(kb.uniques) == 1
        assert kb.version == "3.28.0"
        assert cache_file.exists()
