"""Tests for the AI Build Generator with mocked provider."""

from __future__ import annotations

import json
from unittest.mock import patch, call

import pytest

from pop.ai.generator import BuildGenerator, _extract_json, _repair_json
from pop.ai.models import BuildPreferences, ChatMessage, ChatResponse
from pop.build_parser.models import BuildGuide


# ===========================================================================
# JSON extraction
# ===========================================================================


class TestExtractJson:
    def test_extract_from_code_block(self):
        text = 'Here is your build:\n```json\n{"title": "Test Build"}\n```\nEnjoy!'
        result = _extract_json(text)
        assert result == {"title": "Test Build"}

    def test_extract_from_code_block_no_newline(self):
        text = '```json{"key": "value"}```'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_extract_nested_json(self):
        text = '```json\n{"brackets": [{"title": "1-15", "gems": []}]}\n```'
        result = _extract_json(text)
        assert result["brackets"][0]["title"] == "1-15"

    def test_fallback_to_raw_json(self):
        text = 'Some text {"key": "value"} more text'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_fallback_nested_braces(self):
        text = 'Before {"outer": {"inner": 1}} after'
        result = _extract_json(text)
        assert result == {"outer": {"inner": 1}}

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No JSON found"):
            _extract_json("No JSON here at all")

    def test_intake_complete_marker(self):
        text = (
            "Great choices! Here are your preferences:\n"
            '```json\n{"intake_complete": true, "preferences": '
            '{"main_skill": "Fireball", "class_name": "Witch", '
            '"ascendancy_name": "Elementalist"}}\n```'
        )
        result = _extract_json(text)
        assert result["intake_complete"] is True
        assert result["preferences"]["main_skill"] == "Fireball"

    def test_repair_trailing_comma(self):
        text = '```json\n{"items": ["a", "b", ], "x": 1}\n```'
        result = _extract_json(text)
        assert result == {"items": ["a", "b"], "x": 1}

    def test_repair_trailing_comma_in_object(self):
        text = '```json\n{"a": 1, "b": 2, }\n```'
        result = _extract_json(text)
        assert result == {"a": 1, "b": 2}


# ===========================================================================
# BuildGuide validation from generated JSON
# ===========================================================================


SAMPLE_GUIDE_JSON = {
    "url": "",
    "title": "Elementalist Fireball League Starter",
    "class_name": "Witch",
    "ascendancy_name": "Elementalist",
    "brackets": [
        {
            "title": "1-12",
            "notes": "Focus on links over stats. Rush to Act 2 for Herald of Ash.",
            "gem_groups": [
                {
                    "slot": "Body Armour",
                    "gems": [
                        {"name": "Fireball", "icon_url": "", "is_support": False},
                        {
                            "name": "Added Fire Damage Support",
                            "icon_url": "",
                            "is_support": True,
                        },
                    ],
                }
            ],
            "items": [
                {
                    "slot": "Weapon 1",
                    "name": "Lifesprig",
                    "base_type": "Driftwood Wand",
                    "icon_url": "",
                    "stat_priority": ["spell damage", "+1 to fire gems"],
                    "notes": "BiS leveling wand, cheap",
                }
            ],
        },
        {
            "title": "12-24",
            "gem_groups": [],
            "items": [],
        },
    ],
}


class TestBuildGuideValidation:
    def test_valid_guide_parses(self):
        guide = BuildGuide(**SAMPLE_GUIDE_JSON)
        assert guide.title == "Elementalist Fireball League Starter"
        assert guide.class_name == "Witch"
        assert len(guide.brackets) == 2
        assert guide.brackets[0].title == "1-12"
        assert len(guide.brackets[0].gem_groups) == 1
        assert guide.brackets[0].gem_groups[0].gems[0].name == "Fireball"

    def test_bracket_notes_passthrough(self):
        guide = BuildGuide(**SAMPLE_GUIDE_JSON)
        assert guide.brackets[0].notes == "Focus on links over stats. Rush to Act 2 for Herald of Ash."
        assert guide.brackets[1].notes == ""

    def test_item_stat_priority_and_notes(self):
        guide = BuildGuide(**SAMPLE_GUIDE_JSON)
        item = guide.brackets[0].items[0]
        assert item.stat_priority == ["spell damage", "+1 to fire gems"]
        assert item.notes == "BiS leveling wand, cheap"

    def test_guide_with_all_brackets(self):
        brackets = [
            {"title": t, "gem_groups": [], "items": []}
            for t in [
                "1-12", "12-24", "24-36", "36-50", "50-60",
                "60-70", "70-80", "80-85", "85-90",
                "90 Early Maps (T1-T5)", "92 Mid Maps (T6-T11)",
                "94 Late Maps (T12-T16)", "100 Endgame",
            ]
        ]
        guide = BuildGuide(
            url="", title="Test", class_name="Witch",
            ascendancy_name="Elementalist", brackets=brackets,
        )
        assert len(guide.brackets) >= 10
        assert len(guide.brackets) == 13


# ===========================================================================
# Intake chat (mocked provider)
# ===========================================================================


class TestIntakeChat:
    @pytest.mark.asyncio
    async def test_basic_intake_message(self):
        with patch(
            "pop.ai.generator.chat_completion",
            return_value=("What main skill interests you for your build?", 150),
        ):
            gen = BuildGenerator()
            result = await gen.chat_intake(
                message="I want to make a new build",
                api_key="sk-test",
            )

        assert isinstance(result, ChatResponse)
        assert "main skill" in result.message.lower()
        assert result.tokens_used == 150

    @pytest.mark.asyncio
    async def test_intake_with_history(self):
        with patch(
            "pop.ai.generator.chat_completion",
            return_value=("Great choice!", 300),
        ) as mock_cc:
            gen = BuildGenerator()
            history = [
                ChatMessage(role="user", content="I want Fireball"),
                ChatMessage(role="assistant", content="Nice! What class?"),
            ]
            result = await gen.chat_intake(
                message="Witch Elementalist",
                api_key="sk-test",
                history=history,
            )

        call_kwargs = mock_cc.call_args.kwargs
        messages = call_kwargs["messages"]
        assert len(messages) == 3  # history (2) + new user message
        assert messages[2]["content"] == "Witch Elementalist"

    @pytest.mark.asyncio
    async def test_intake_uses_intake_prompt(self):
        with patch(
            "pop.ai.generator.chat_completion",
            return_value=("reply", 75),
        ) as mock_cc:
            gen = BuildGenerator()
            await gen.chat_intake(message="hello", api_key="sk-test")

        call_kwargs = mock_cc.call_args.kwargs
        system = call_kwargs["system"]
        assert "intake" in system.lower() or "preferences" in system.lower()

    @pytest.mark.asyncio
    async def test_intake_default_provider_gemini(self):
        with patch(
            "pop.ai.generator.chat_completion",
            return_value=("reply", 75),
        ) as mock_cc:
            gen = BuildGenerator()
            await gen.chat_intake(message="hello", api_key="test-key")

        call_kwargs = mock_cc.call_args.kwargs
        assert call_kwargs["provider"] == "gemini"


# ===========================================================================
# Generate (mocked provider)
# ===========================================================================


SAMPLE_PHASE1_JSON = {
    "url": "",
    "title": "Elementalist Fireball League Starter",
    "class_name": "Witch",
    "ascendancy_name": "Elementalist",
    "brackets": [SAMPLE_GUIDE_JSON["brackets"][0]],
}

SAMPLE_PHASE2_JSON = {
    "url": "",
    "title": "Elementalist Fireball League Starter",
    "class_name": "Witch",
    "ascendancy_name": "Elementalist",
    "brackets": [SAMPLE_GUIDE_JSON["brackets"][1]],
}


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_success_two_phase(self):
        """Two-phase generation: phase 1 + phase 2 merge into full guide."""
        phase1_json = json.dumps(SAMPLE_PHASE1_JSON)
        phase2_json = json.dumps(SAMPLE_PHASE2_JSON)

        with patch(
            "pop.ai.generator.chat_completion",
            side_effect=[
                (f"```json\n{phase1_json}\n```", 1000),
                (f"```json\n{phase2_json}\n```", 1000),
            ],
        ) as mock_cc:
            gen = BuildGenerator()
            prefs = BuildPreferences(
                main_skill="Fireball",
                class_name="Witch",
                ascendancy_name="Elementalist",
                budget_chaos=500,
            )
            result = await gen.generate(api_key="sk-test", preferences=prefs)

        assert isinstance(result, BuildGuide)
        assert result.title == "Elementalist Fireball League Starter"
        # Merged: 1 bracket from phase 1 + 1 from phase 2
        assert len(result.brackets) == 2
        assert result.brackets[0].title == "1-12"
        assert result.brackets[1].title == "12-24"
        assert mock_cc.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_retry_on_bad_phase1(self):
        """If phase 1 returns bad JSON, retry the entire two-phase flow."""
        phase1_json = json.dumps(SAMPLE_PHASE1_JSON)
        phase2_json = json.dumps(SAMPLE_PHASE2_JSON)

        with patch(
            "pop.ai.generator.chat_completion",
            side_effect=[
                ("Not valid JSON at all", 100),  # Attempt 1: fail
                (f"```json\n{phase1_json}\n```", 1000),  # Attempt 2: phase 1
                (f"```json\n{phase2_json}\n```", 1000),  # Attempt 2: phase 2
            ],
        ) as mock_cc:
            gen = BuildGenerator()
            prefs = BuildPreferences(
                main_skill="Fireball",
                class_name="Witch",
                ascendancy_name="Elementalist",
            )
            result = await gen.generate(api_key="sk-test", preferences=prefs)

        assert isinstance(result, BuildGuide)
        assert mock_cc.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_fails_after_retries(self):
        with patch(
            "pop.ai.generator.chat_completion",
            return_value=("No JSON here", 100),
        ):
            gen = BuildGenerator()
            prefs = BuildPreferences(
                main_skill="Fireball",
                class_name="Witch",
                ascendancy_name="Elementalist",
            )
            with pytest.raises(ValueError, match="Failed to generate"):
                await gen.generate(api_key="sk-test", preferences=prefs)


# ===========================================================================
# Refine (mocked provider)
# ===========================================================================


class TestRefine:
    @pytest.mark.asyncio
    async def test_refine_success(self):
        refined_guide = SAMPLE_GUIDE_JSON.copy()
        refined_guide["title"] = "Elementalist Fireball (Budget)"
        guide_json = json.dumps(refined_guide)

        with patch(
            "pop.ai.generator.chat_completion",
            return_value=(f"```json\n{guide_json}\n```", 3000),
        ):
            gen = BuildGenerator()
            result = await gen.refine(
                api_key="sk-test",
                guide=SAMPLE_GUIDE_JSON,
                trade_prices=[
                    {"name": "Lifesprig", "price_chaos": 1},
                ],
                budget_chaos=500,
            )

        assert isinstance(result, BuildGuide)
        assert result.title == "Elementalist Fireball (Budget)"

    @pytest.mark.asyncio
    async def test_refine_with_user_message(self):
        guide_json = json.dumps(SAMPLE_GUIDE_JSON)

        with patch(
            "pop.ai.generator.chat_completion",
            return_value=(f"```json\n{guide_json}\n```", 3000),
        ) as mock_cc:
            gen = BuildGenerator()
            await gen.refine(
                api_key="sk-test",
                guide=SAMPLE_GUIDE_JSON,
                trade_prices=[],
                budget_chaos=200,
                message="Can you use a cheaper weapon?",
            )

        call_kwargs = mock_cc.call_args.kwargs
        messages = call_kwargs["messages"]
        user_content = messages[-1]["content"]
        assert "cheaper weapon" in user_content


# ===========================================================================
# BuildPreferences model
# ===========================================================================


class TestBuildPreferences:
    def test_defaults(self):
        prefs = BuildPreferences()
        assert prefs.budget_chaos == 0
        assert prefs.league == "Standard"

    def test_from_dict(self):
        prefs = BuildPreferences(
            main_skill="Arc",
            class_name="Witch",
            ascendancy_name="Elementalist",
            budget_chaos=1000,
        )
        assert prefs.main_skill == "Arc"
        assert prefs.budget_chaos == 1000
