"""
AI Build Generator — generates complete PoE 1 leveling guides from user preferences.

Supports Anthropic Claude and Google Gemini via the provider abstraction.
Multi-phase conversation:
1. Intake: gather user preferences (skill, class, budget, etc.)
2. Generate: produce a full BuildGuide with 13 level brackets
3. Refine: adjust endgame items to fit within budget based on trade prices
"""

from __future__ import annotations

import json
import logging
import re

from pop.ai.models import BuildPreferences, ChatMessage, ChatResponse
from pop.ai.provider import chat_completion
from pop.ai.prompts import (
    GENERATOR_SYSTEM_PROMPT,
    INTAKE_SYSTEM_PROMPT,
    REFINEMENT_SYSTEM_PROMPT,
    build_knowledge_addendum,
    build_knowledge_lite,
)
from pop.knowledge.cache import load_knowledge
from pop.build_parser.models import BuildGuide

logger = logging.getLogger(__name__)

MAX_HISTORY = 20


def _sanitize_text(text: str) -> str:
    """Remove surrogate characters that break UTF-8 encoding on Windows."""
    return text.encode("utf-8", errors="surrogateescape").decode("utf-8", errors="replace")


def _repair_json(text: str) -> str:
    """Attempt to fix common JSON syntax errors from AI output.

    Handles: trailing commas before ] or }, unescaped newlines in strings,
    and single-quoted strings.
    """
    # Remove trailing commas before closing brackets/braces
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Replace single-quoted strings with double-quoted (simple cases only)
    # This handles 'value' → "value" but avoids breaking apostrophes in text
    text = re.sub(r"(?<=[\[,{:\s])'([^']*?)'(?=\s*[,\]}:])", r'"\1"', text)
    return text


def _extract_json(text: str) -> dict:
    """Extract the first ```json ... ``` code block from AI response text.

    Falls back to finding the first { ... } if no code block is found.
    Applies JSON repair for common AI syntax errors before parsing.
    """
    raw = _extract_raw_json(text)
    # Try parsing as-is first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try with repair
    repaired = _repair_json(raw)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    # Last resort: try the original and let it raise with a clear error
    return json.loads(raw)


def _extract_raw_json(text: str) -> str:
    """Extract raw JSON string from AI response text."""
    # Try ```json ... ``` first
    match = re.search(r"```json\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: find outermost { ... }
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON found in AI response")

    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    raise ValueError("No complete JSON object found in AI response")


class BuildGenerator:
    """AI-powered build guide generator."""

    async def chat_intake(
        self,
        message: str,
        api_key: str,
        history: list[ChatMessage] | None = None,
        provider: str = "gemini",
    ) -> ChatResponse:
        """Drive the intake conversation to collect build preferences.

        Returns a ChatResponse. If the AI has collected enough info, the response
        message will contain a JSON block with {"intake_complete": true, "preferences": {...}}.
        """
        messages: list[ChatMessage] = list(history or [])
        messages.append(ChatMessage(role="user", content=message))

        if len(messages) > MAX_HISTORY:
            messages = messages[-MAX_HISTORY:]

        # Append lightweight knowledge context to intake prompt
        system = INTAKE_SYSTEM_PROMPT
        kb = load_knowledge()
        if kb:
            system += build_knowledge_lite(kb)

        assistant_text, tokens_used = chat_completion(
            provider=provider,
            api_key=api_key,
            system=system,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            max_tokens=1024,
        )

        return ChatResponse(
            message=assistant_text,
            conversation_id="",
            tokens_used=tokens_used,
        )

    async def generate(
        self,
        api_key: str,
        preferences: BuildPreferences,
        history: list[ChatMessage] | None = None,
        provider: str = "gemini",
    ) -> BuildGuide:
        """Generate a full BuildGuide from collected preferences.

        Uses two-phase generation to keep each API call within token limits:
        Phase 1: Leveling brackets (1-12 through 70-80) — 7 brackets
        Phase 2: Endgame brackets (80-85 through 100 Endgame) — 6 brackets
        Retries once on parse failure.
        """
        pref_block = (
            f"- Main Skill: {preferences.main_skill}\n"
            f"- Class: {preferences.class_name}\n"
            f"- Ascendancy: {preferences.ascendancy_name}\n"
            f"- Weapon Type: {preferences.weapon_type or 'any'}\n"
            f"- Budget: {preferences.budget_chaos} chaos\n"
            f"- League: {preferences.league}\n"
            f"- Playstyle: {preferences.playstyle or 'general'}\n"
        )

        # Build system prompt with knowledge reference
        system = GENERATOR_SYSTEM_PROMPT
        kb = load_knowledge()
        if kb:
            system += build_knowledge_addendum(kb)

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                guide = await self._generate_two_phase(
                    provider, api_key, system, pref_block, history,
                )
                return guide
            except Exception as exc:
                last_error = exc
                logger.warning("Generate attempt %d failed: %s", attempt + 1, exc)

        raise ValueError(f"Failed to generate valid build guide after 2 attempts: {last_error}")

    async def _generate_two_phase(
        self,
        provider: str,
        api_key: str,
        system: str,
        pref_block: str,
        history: list[ChatMessage] | None,
    ) -> BuildGuide:
        """Generate the guide in two API calls (leveling + endgame).

        Phase 1 produces the outer structure + first 7 brackets.
        Phase 2 produces the remaining 6 brackets, given phase 1 as context.
        The results are merged into one BuildGuide.
        """
        messages = list(history or [])
        if len(messages) > MAX_HISTORY:
            messages = messages[-MAX_HISTORY:]

        api_history = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        # --- Phase 1: leveling brackets ---
        phase1_msg = (
            f"Generate a leveling guide for:\n{pref_block}\n"
            "Output ONLY the FIRST 7 brackets: "
            '"1-12", "12-24", "24-36", "36-50", "50-60", "60-70", "70-80".\n'
            "Include the full outer structure (url, title, class_name, ascendancy_name) "
            "but ONLY these 7 brackets in the brackets array.\n"
            "Use compact JSON — no unnecessary whitespace or indentation."
        )

        phase1_messages = api_history + [{"role": "user", "content": phase1_msg}]

        logger.info("Phase 1: generating leveling brackets (1-12 through 70-80)...")
        text1, _ = chat_completion(
            provider=provider,
            api_key=api_key,
            system=system,
            messages=phase1_messages,
            max_tokens=16384,
        )

        data1 = _extract_json(text1)
        # Validate phase 1 parses as a partial guide
        guide1 = BuildGuide(**data1)
        logger.info("Phase 1 complete: %d brackets", len(guide1.brackets))

        # --- Phase 2: endgame brackets ---
        phase2_msg = (
            "Now generate the remaining 6 brackets for the same build:\n"
            '"80-85", "85-90", "90 Early Maps (T1-T5)", "92 Mid Maps (T6-T11)", '
            '"94 Late Maps (T12-T16)", "100 Endgame".\n\n'
            "Output the SAME outer structure (url, title, class_name, ascendancy_name) "
            "with ONLY these 6 brackets in the brackets array.\n"
            "Continue the gear/gem progression from the 70-80 bracket. "
            "Use compact JSON — no unnecessary whitespace or indentation."
        )

        phase2_messages = api_history + [
            {"role": "user", "content": phase1_msg},
            {"role": "assistant", "content": text1},
            {"role": "user", "content": phase2_msg},
        ]

        logger.info("Phase 2: generating endgame brackets (80-85 through 100 Endgame)...")
        text2, _ = chat_completion(
            provider=provider,
            api_key=api_key,
            system=system,
            messages=phase2_messages,
            max_tokens=16384,
        )

        data2 = _extract_json(text2)
        guide2 = BuildGuide(**data2)
        logger.info("Phase 2 complete: %d brackets", len(guide2.brackets))

        # --- Merge: combine all brackets ---
        merged = data1.copy()
        merged["brackets"] = data1["brackets"] + data2["brackets"]

        guide = BuildGuide(**merged)
        logger.info("Merged guide: %d total brackets", len(guide.brackets))
        return guide

    async def refine(
        self,
        api_key: str,
        guide: dict,
        trade_prices: list[dict],
        budget_chaos: int,
        history: list[ChatMessage] | None = None,
        message: str = "",
        provider: str = "gemini",
    ) -> BuildGuide:
        """Refine a build guide based on trade prices and budget.

        Sends the current guide + prices to AI for adjustment.
        """
        price_summary = "\n".join(
            f"- {p.get('name', '?')}: {p.get('price_chaos', '?')} chaos"
            for p in trade_prices
        )

        user_content = (
            f"Current build guide:\n```json\n{json.dumps(guide, indent=2)}\n```\n\n"
            f"Trade prices for endgame items:\n{price_summary}\n\n"
            f"Budget: {budget_chaos} chaos orbs\n"
        )
        if message:
            user_content += f"\nUser feedback: {message}\n"

        messages = list(history or [])
        messages.append(ChatMessage(role="user", content=user_content))

        if len(messages) > MAX_HISTORY:
            messages = messages[-MAX_HISTORY:]

        text, _ = chat_completion(
            provider=provider,
            api_key=api_key,
            system=REFINEMENT_SYSTEM_PROMPT,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            max_tokens=16384,
        )

        data = _extract_json(text)
        return BuildGuide(**data)
