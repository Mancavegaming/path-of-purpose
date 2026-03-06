"""Tests for the trade API client with mocked HTTP."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pop.trade.client import TradeClient, _parse_listings
from pop.trade.models import TradeSearchRequest, TradeQuery, StatGroup, StatFilter


# ===========================================================================
# Parse listings
# ===========================================================================


class TestParseListings:
    def test_empty_results(self):
        assert _parse_listings([]) == []

    def test_single_listing(self):
        raw = [
            {
                "id": "abc123",
                "item": {
                    "name": "Headhunter",
                    "typeLine": "Leather Belt",
                    "ilvl": 40,
                    "corrupted": False,
                    "explicitMods": ["+70 to maximum Life"],
                    "implicitMods": ["+30 to Strength"],
                    "craftedMods": [],
                    "icon": "https://example.com/icon.png",
                },
                "listing": {
                    "price": {
                        "amount": 50,
                        "currency": "divine",
                        "type": "~price",
                    },
                    "account": {"name": "TestPlayer"},
                    "whisper": "@TestPlayer Hi, I'd like to buy...",
                },
            }
        ]
        listings = _parse_listings(raw)
        assert len(listings) == 1

        li = listings[0]
        assert li.id == "abc123"
        assert li.item_name == "Headhunter"
        assert li.type_line == "Leather Belt"
        assert li.ilvl == 40
        assert li.corrupted is False
        assert li.price is not None
        assert li.price.amount == 50
        assert li.price.currency == "divine"
        assert li.explicit_mods == ["+70 to maximum Life"]
        assert li.implicit_mods == ["+30 to Strength"]
        assert li.account_name == "TestPlayer"
        assert li.whisper.startswith("@TestPlayer")
        assert li.icon_url == "https://example.com/icon.png"

    def test_listing_without_price(self):
        raw = [
            {
                "id": "xyz",
                "item": {"name": "Some Item", "typeLine": "Ring"},
                "listing": {"account": {"name": "Player"}, "whisper": ""},
            }
        ]
        listings = _parse_listings(raw)
        assert listings[0].price is None

    def test_multiple_listings(self):
        raw = [
            {
                "id": f"id{i}",
                "item": {"name": f"Item {i}", "typeLine": "Base"},
                "listing": {
                    "price": {"amount": i * 10, "currency": "chaos", "type": "~b/o"},
                    "account": {"name": f"Player{i}"},
                    "whisper": "",
                },
            }
            for i in range(5)
        ]
        listings = _parse_listings(raw)
        assert len(listings) == 5
        assert listings[2].price.amount == 20


# ===========================================================================
# TradeClient search flow (mocked HTTP)
# ===========================================================================


class TestTradeClientSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.raise_for_status = MagicMock()
        mock_search_response.json.return_value = {
            "id": "query123",
            "total": 50,
            "result": ["id1", "id2", "id3"],
        }

        mock_fetch_response = MagicMock()
        mock_fetch_response.status_code = 200
        mock_fetch_response.raise_for_status = MagicMock()
        mock_fetch_response.json.return_value = {
            "result": [
                {
                    "id": "id1",
                    "item": {"name": "Test Item", "typeLine": "Ring"},
                    "listing": {
                        "price": {"amount": 5, "currency": "chaos", "type": "~price"},
                        "account": {"name": "Seller"},
                        "whisper": "@Seller hi",
                    },
                }
            ]
        }

        with patch("pop.trade.client.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_search_response)
            mock_client.get = AsyncMock(return_value=mock_fetch_response)
            mock_client.aclose = AsyncMock()
            MockClient.return_value = mock_client

            async with TradeClient(league="Standard") as client:
                client._client = mock_client

                request = TradeSearchRequest(query=TradeQuery(name="Test Item"))
                result = await client.search(request)

            assert result.total == 50
            assert result.query_id == "query123"
            assert len(result.listings) == 1
            assert result.listings[0].item_name == "Test Item"
            assert result.trade_url.endswith("/trade/search/Standard/query123")

    @pytest.mark.asyncio
    async def test_search_with_no_results(self):
        mock_search_response = MagicMock()
        mock_search_response.raise_for_status = MagicMock()
        mock_search_response.json.return_value = {
            "id": "empty_query",
            "total": 0,
            "result": [],
        }

        with patch("pop.trade.client.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_search_response)
            mock_client.aclose = AsyncMock()
            MockClient.return_value = mock_client

            async with TradeClient(league="Standard") as client:
                client._client = mock_client

                request = TradeSearchRequest(query=TradeQuery(name="Nonexistent"))
                result = await client.search(request)

            assert result.total == 0
            assert len(result.listings) == 0
