"""Tests for the PoE API client with mocked HTTP responses."""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest

from pop.oauth.token_store import StoredTokens
from pop.poe_api.character import PoeClient, PoeApiError
from pop.poe_api.models import (
    CharacterDetail,
    CharacterEntry,
    EquippedItem,
    League,
    PassiveData,
    Profile,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_TOKENS = StoredTokens(
    access_token="test_access_token",
    refresh_token="test_refresh_token",
    expires_at=time.time() + 3600,
    scope="account:characters account:stashes",
    account_name="TestPlayer",
)

MOCK_PROFILE = {"name": "TestPlayer", "realm": "pc", "uuid": "abc-123"}

MOCK_CHARACTERS = [
    {"id": "1", "name": "SRS_Necro", "class": "Necromancer", "level": 92, "league": "Settlers"},
    {"id": "2", "name": "Arc_Witch", "class": "Elementalist", "level": 85, "league": "Settlers"},
    {"id": "3", "name": "Cyclone_Slayer", "class": "Slayer", "level": 78, "league": "Standard"},
]

MOCK_CHARACTER_DETAIL = {
    "character": {
        "id": "1",
        "name": "SRS_Necro",
        "class": "Necromancer",
        "level": 92,
        "league": "Settlers",
        "experience": 3_000_000_000,
        "equipment": [
            {
                "id": "item1",
                "name": "Glyph Hold",
                "typeLine": "Titanium Spirit Shield",
                "baseType": "Titanium Spirit Shield",
                "inventoryId": "Offhand",
                "ilvl": 84,
                "rarity": 2,
                "implicitMods": ["15% increased Spell Damage"],
                "explicitMods": [
                    "+120 to maximum Life",
                    "+45% to Fire Resistance",
                    "+32% to Cold Resistance",
                ],
                "craftedMods": ["+40 to maximum Energy Shield"],
                "sockets": [{"group": 0, "colour": "B"}, {"group": 0, "colour": "B"}],
            },
            {
                "id": "item2",
                "name": "Bones of Ullr",
                "typeLine": "Silk Slippers",
                "baseType": "Silk Slippers",
                "inventoryId": "Boots",
                "ilvl": 70,
                "rarity": 3,
                "implicitMods": [],
                "explicitMods": [
                    "+20 to maximum Life",
                    "+20 to maximum Mana",
                    "+1 to Level of all Raise Zombie Gems",
                ],
            },
        ],
        "passives": {
            "hashes": [1, 2, 3, 4, 5, 100, 200, 300],
            "hashes_ex": [9000, 9001],
        },
    }
}

MOCK_LEAGUES = [
    {"id": "Settlers", "text": "Settlers", "realm": "pc", "startAt": "2025-01-01T00:00:00Z"},
    {"id": "Standard", "text": "Standard", "realm": "pc", "startAt": "2013-01-01T00:00:00Z"},
]


def _mock_response(data: dict | list, status_code: int = 200) -> httpx.Response:
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=data,
        headers={
            "x-rate-limit-ip": "45:60:60,240:240:900",
            "x-rate-limit-ip-state": "1:60:0,1:240:0",
        },
        request=httpx.Request("GET", "https://test"),
    )


# ===========================================================================
# Model tests
# ===========================================================================


class TestModels:
    def test_character_entry_alias(self):
        entry = CharacterEntry.model_validate(MOCK_CHARACTERS[0])
        assert entry.class_name == "Necromancer"
        assert entry.name == "SRS_Necro"

    def test_equipped_item_slot_mapping(self):
        item = EquippedItem.model_validate(
            MOCK_CHARACTER_DETAIL["character"]["equipment"][0]
        )
        assert item.slot == "Weapon 2"  # "Offhand" maps to "Weapon 2"
        assert item.rarity_name == "RARE"

    def test_equipped_item_all_mods(self):
        item = EquippedItem.model_validate(
            MOCK_CHARACTER_DETAIL["character"]["equipment"][0]
        )
        assert len(item.all_mods) == 5  # 1 implicit + 3 explicit + 1 crafted

    def test_character_detail_summary(self):
        detail = CharacterDetail(
            name="TestChar", class_name="Witch", level=50,
            passives=PassiveData(hashes=[1, 2, 3]),
        )
        s = detail.summary()
        assert "50" in s
        assert "Witch" in s

    def test_character_detail_items_by_slot(self):
        items = [
            EquippedItem(name="Helm1", inventory_id="Helm"),
            EquippedItem(name="Boot1", inventory_id="Boots"),
        ]
        detail = CharacterDetail(name="Test", equipment=items)
        slots = detail.items_by_slot()
        assert "Helmet" in slots
        assert "Boots" in slots

    def test_league_model(self):
        league = League.model_validate(MOCK_LEAGUES[0])
        assert league.id == "Settlers"


# ===========================================================================
# PoeClient with mocked HTTP
# ===========================================================================


class TestPoeClient:
    @pytest.fixture()
    def client(self):
        return PoeClient(client_id="test_client", tokens=MOCK_TOKENS)

    @pytest.mark.asyncio
    async def test_get_profile(self, client: PoeClient):
        mock_resp = _mock_response(MOCK_PROFILE)
        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp):
            async with client:
                profile = await client.get_profile()
        assert profile.name == "TestPlayer"
        assert profile.realm == "pc"

    @pytest.mark.asyncio
    async def test_list_characters(self, client: PoeClient):
        mock_resp = _mock_response(MOCK_CHARACTERS)
        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp):
            async with client:
                chars = await client.list_characters()
        assert len(chars) == 3
        assert chars[0].name == "SRS_Necro"
        assert chars[0].class_name == "Necromancer"
        assert chars[0].level == 92

    @pytest.mark.asyncio
    async def test_get_character_detail(self, client: PoeClient):
        mock_resp = _mock_response(MOCK_CHARACTER_DETAIL)
        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp):
            async with client:
                detail = await client.get_character("SRS_Necro")
        assert detail.name == "SRS_Necro"
        assert detail.level == 92
        assert len(detail.equipment) == 2
        assert len(detail.passives.hashes) == 8

    @pytest.mark.asyncio
    async def test_get_character_items_parsed(self, client: PoeClient):
        mock_resp = _mock_response(MOCK_CHARACTER_DETAIL)
        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp):
            async with client:
                detail = await client.get_character("SRS_Necro")
        slots = detail.items_by_slot()
        shield = slots.get("Weapon 2")
        assert shield is not None
        assert shield.name == "Glyph Hold"
        assert "+120 to maximum Life" in shield.explicit_mods

    @pytest.mark.asyncio
    async def test_list_leagues(self, client: PoeClient):
        mock_resp = _mock_response(MOCK_LEAGUES)
        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp):
            async with client:
                leagues = await client.list_leagues()
        assert len(leagues) == 2
        assert leagues[0].id == "Settlers"

    @pytest.mark.asyncio
    async def test_api_error_raised(self, client: PoeClient):
        mock_resp = _mock_response(
            {"error": {"message": "Character not found"}},
            status_code=404,
        )
        with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_resp):
            async with client:
                with pytest.raises(PoeApiError) as exc_info:
                    await client.get_character("NonExistent")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_no_tokens_raises(self):
        client = PoeClient(client_id="test", tokens=None)
        # Patch load_tokens to return None
        with patch("pop.poe_api.character.load_tokens", return_value=None):
            client._tokens = None
            async with client:
                with pytest.raises(PoeApiError, match="Not logged in"):
                    await client.get_profile()
