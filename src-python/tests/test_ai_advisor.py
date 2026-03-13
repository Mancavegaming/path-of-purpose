"""Tests for the AI Advisor with mocked provider."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pop.ai.advisor import Advisor, _build_context_prompt
from pop.ai.key_store import SERVICE_NAME
from pop.ai.models import ChatMessage, ChatResponse


# ===========================================================================
# Build context formatting
# ===========================================================================


class TestBuildContextPrompt:
    def test_basic_context(self):
        ctx = {
            "class_name": "Witch",
            "ascendancy_name": "Necromancer",
            "level": 90,
            "main_skill": "Summon Raging Spirits",
        }
        result = _build_context_prompt(ctx)
        assert "Necromancer" in result
        assert "Level 90" in result
        assert "Summon Raging Spirits" in result

    def test_items_context(self):
        ctx = {
            "class_name": "Ranger",
            "items": [
                {"name": "Headhunter", "base_type": "Leather Belt"},
                {"name": "", "base_type": "Diamond Ring"},
            ],
        }
        result = _build_context_prompt(ctx)
        assert "Headhunter" in result
        assert "Diamond Ring" in result

    def test_skill_groups_context(self):
        ctx = {
            "class_name": "Shadow",
            "skill_groups": [
                {
                    "gems": [
                        {"name": "Blade Vortex", "is_support": False},
                        {"name": "Unleash", "is_support": True},
                    ]
                },
            ],
        }
        result = _build_context_prompt(ctx)
        assert "Blade Vortex" in result

    def test_gaps_context(self):
        ctx = {
            "class_name": "Marauder",
            "top_gaps": [
                {"title": "Missing life on helmet"},
                {"title": "Upgrade boots"},
            ],
        }
        result = _build_context_prompt(ctx)
        assert "Missing life on helmet" in result

    def test_empty_context(self):
        result = _build_context_prompt({})
        assert "User's Current Build" in result

    def test_selected_item_context(self):
        ctx = {
            "class_name": "Witch",
            "selected_item": {
                "name": "Starforge",
                "slot": "Weapon 1",
                "mods": ["+400 Physical Damage", "50% increased Damage"],
            },
        }
        result = _build_context_prompt(ctx)
        assert "Starforge" in result
        assert "Weapon 1" in result
        assert "+400 Physical Damage" in result

    def test_atlas_strategy_context(self):
        ctx = {
            "class_name": "Ranger",
            "bracket_atlas": {
                "90 Early Maps (T1-T5)": "Spec into Legion nodes for fast monolith clear.",
                "94 Late Maps (T12-T16)": "Breach farming with scarabs for splinters.",
            },
        }
        result = _build_context_prompt(ctx)
        assert "Atlas Strategy" in result
        assert "Legion" in result
        assert "Breach" in result

    def test_map_warnings_context(self):
        ctx = {
            "class_name": "Duelist",
            "bracket_map_warnings": {
                "90 Early Maps (T1-T5)": ["Physical Reflect", "No Leech"],
                "94 Late Maps (T12-T16)": ["Physical Reflect", "No Leech", "-max res"],
            },
        }
        result = _build_context_prompt(ctx)
        assert "Map Mod Warnings" in result
        assert "Physical Reflect" in result
        assert "No Leech" in result

    def test_atlas_and_warnings_empty(self):
        """Empty atlas/warnings dicts should not produce section headers."""
        ctx = {
            "class_name": "Witch",
            "bracket_atlas": {},
            "bracket_map_warnings": {},
        }
        result = _build_context_prompt(ctx)
        assert "Atlas Strategy" not in result
        assert "Map Mod Warnings" not in result

    def test_trade_listing_context(self):
        ctx = {
            "class_name": "Witch",
            "trade_listing": {
                "name": "Atziri's Disfavour",
                "price": "5 divine",
                "mods": ["+600 Physical Damage"],
            },
        }
        result = _build_context_prompt(ctx)
        assert "Atziri's Disfavour" in result
        assert "5 divine" in result
        assert "upgrade" in result.lower()


# ===========================================================================
# Advisor chat (mocked provider)
# ===========================================================================


class TestAdvisorChat:
    @pytest.mark.asyncio
    async def test_new_conversation(self):
        with patch(
            "pop.ai.advisor.chat_completion",
            return_value=("I recommend focusing on life and resistances.", 150),
        ) as mock_cc:
            advisor = Advisor()
            result = await advisor.chat(
                message="What should I upgrade first?",
                api_key="sk-test-key",
                provider="anthropic",
            )

        assert isinstance(result, ChatResponse)
        assert result.message == "I recommend focusing on life and resistances."
        assert result.tokens_used == 150
        mock_cc.assert_called_once()
        call_kwargs = mock_cc.call_args.kwargs
        assert call_kwargs["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_conversation_continuity(self):
        with patch(
            "pop.ai.advisor.chat_completion",
            return_value=("Sure, let me elaborate.", 300),
        ) as mock_cc:
            advisor = Advisor()

            history = [
                ChatMessage(role="user", content="Help with my build"),
                ChatMessage(role="assistant", content="Sure, what do you need?"),
            ]

            result = await advisor.chat(
                message="Tell me more",
                api_key="sk-test",
                history=history,
                provider="gemini",
            )

        assert result.message == "Sure, let me elaborate."
        call_kwargs = mock_cc.call_args.kwargs
        messages = call_kwargs["messages"]
        # Should have: user1, assistant1, user2
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "Tell me more"

    @pytest.mark.asyncio
    async def test_build_context_injected(self):
        with patch(
            "pop.ai.advisor.chat_completion",
            return_value=("Based on your Necromancer build...", 225),
        ) as mock_cc:
            advisor = Advisor()
            await advisor.chat(
                message="What gems should I use?",
                api_key="sk-test",
                build_context={
                    "class_name": "Witch",
                    "ascendancy_name": "Necromancer",
                    "level": 85,
                },
            )

        call_kwargs = mock_cc.call_args.kwargs
        system = call_kwargs["system"]
        assert "Necromancer" in system

    @pytest.mark.asyncio
    async def test_knowledge_addendum_injected(self):
        """Verify that boss/damage/atlas/map knowledge is injected into system prompt."""
        with patch(
            "pop.ai.advisor.chat_completion",
            return_value=("Here's the boss info...", 100),
        ) as mock_cc:
            advisor = Advisor()
            await advisor.chat(
                message="Can I do Sirus?",
                api_key="sk-test",
            )

        call_kwargs = mock_cc.call_args.kwargs
        system = call_kwargs["system"]
        # Knowledge addendum should contain boss encounter data
        assert "Boss & Endgame Encounter Reference" in system
        assert "Damage Mechanics Reference" in system
        assert "Atlas Strategy Reference" in system
        assert "Map Mod Danger Reference" in system

    @pytest.mark.asyncio
    async def test_atlas_context_in_system_prompt(self):
        """Verify atlas strategy and map warnings are in the system prompt."""
        with patch(
            "pop.ai.advisor.chat_completion",
            return_value=("Run Legion maps!", 100),
        ) as mock_cc:
            advisor = Advisor()
            await advisor.chat(
                message="What atlas strategy?",
                api_key="sk-test",
                build_context={
                    "class_name": "Duelist",
                    "bracket_atlas": {"90 Early Maps": "Spec into Legion for fast clear."},
                    "bracket_map_warnings": {"90 Early Maps": ["Phys Reflect", "No Leech"]},
                },
            )

        call_kwargs = mock_cc.call_args.kwargs
        system = call_kwargs["system"]
        assert "Legion" in system
        assert "Phys Reflect" in system

    @pytest.mark.asyncio
    async def test_history_trimming(self):
        with patch(
            "pop.ai.advisor.chat_completion",
            return_value=("Reply", 75),
        ) as mock_cc:
            advisor = Advisor()

            # Build a history with 25 messages (exceeds MAX_HISTORY of 20)
            history: list[ChatMessage] = []
            for i in range(24):
                role = "user" if i % 2 == 0 else "assistant"
                history.append(ChatMessage(role=role, content=f"Message {i}"))

            await advisor.chat(
                message="Message 24",
                api_key="sk-test",
                history=history,
            )

        # History (24) + new user message (1) = 25, trimmed to last 20
        call_kwargs = mock_cc.call_args.kwargs
        messages = call_kwargs["messages"]
        assert len(messages) == 20

    @pytest.mark.asyncio
    async def test_default_provider_is_gemini(self):
        with patch(
            "pop.ai.advisor.chat_completion",
            return_value=("Hello!", 50),
        ) as mock_cc:
            advisor = Advisor()
            await advisor.chat(message="hi", api_key="test-key")

        call_kwargs = mock_cc.call_args.kwargs
        assert call_kwargs["provider"] == "gemini"


# ===========================================================================
# Key store
# ===========================================================================


class TestKeyStore:
    def test_save_and_load_default_provider(self):
        with patch("pop.ai.key_store.keyring") as mock_kr:
            from pop.ai.key_store import save_api_key, load_api_key

            save_api_key("sk-test-123")
            mock_kr.set_password.assert_called_once_with(
                SERVICE_NAME, "anthropic_api_key", "sk-test-123"
            )

            mock_kr.get_password.return_value = "sk-test-123"
            result = load_api_key()
            assert result == "sk-test-123"

    def test_save_and_load_gemini(self):
        with patch("pop.ai.key_store.keyring") as mock_kr:
            from pop.ai.key_store import save_api_key, load_api_key

            save_api_key("AIza-test", provider="gemini")
            mock_kr.set_password.assert_called_once_with(
                SERVICE_NAME, "gemini_api_key", "AIza-test"
            )

            mock_kr.get_password.return_value = "AIza-test"
            result = load_api_key(provider="gemini")
            assert result == "AIza-test"

    def test_has_key_true(self):
        with patch("pop.ai.key_store.keyring") as mock_kr:
            from pop.ai.key_store import has_api_key

            mock_kr.get_password.return_value = "sk-test"
            assert has_api_key() is True

    def test_has_key_false(self):
        with patch("pop.ai.key_store.keyring") as mock_kr:
            from pop.ai.key_store import has_api_key

            mock_kr.get_password.return_value = None
            assert has_api_key() is False

    def test_save_and_load_provider(self):
        with patch("pop.ai.key_store.keyring") as mock_kr:
            from pop.ai.key_store import save_provider, load_provider

            save_provider("gemini")
            mock_kr.set_password.assert_called_once_with(
                SERVICE_NAME, "ai_provider", "gemini"
            )

            mock_kr.get_password.return_value = "gemini"
            assert load_provider() == "gemini"

    def test_load_provider_default(self):
        with patch("pop.ai.key_store.keyring") as mock_kr:
            from pop.ai.key_store import load_provider

            mock_kr.get_password.return_value = None
            assert load_provider() == "gemini"
