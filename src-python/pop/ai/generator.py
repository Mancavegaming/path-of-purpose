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
from pop.knowledge.models import KnowledgeBase
from pop.build_parser.models import BuildGuide

logger = logging.getLogger(__name__)

MAX_HISTORY = 20


def _build_valid_gem_names(kb: KnowledgeBase | None = None) -> set[str]:
    """Build a set of all valid PoE 1 gem names.

    Uses the knowledge base as the primary source (refreshed from RePoE),
    with fallback to the calc engine's gem_data module.
    """
    names: set[str] = set()

    # Primary: knowledge base gems
    if kb and kb.gems:
        for g in kb.gems:
            names.add(g.name)

    # Fallback: calc engine's hardcoded gem database
    try:
        from pop.calc.gem_data import _ACTIVE_GEMS, _SUPPORT_GEMS
        names.update(_ACTIVE_GEMS.keys())
        names.update(_SUPPORT_GEMS.keys())
    except ImportError:
        pass

    return names


def _validate_guide_gems(guide: BuildGuide, kb: KnowledgeBase | None = None) -> BuildGuide:
    """Remove invalid/hallucinated gem names from a generated build guide.

    Checks every gem in every bracket against the known gem database.
    Unknown gems are removed and logged as warnings.
    """
    valid_names = _build_valid_gem_names(kb)
    if not valid_names:
        logger.warning("No valid gem names loaded — skipping gem validation")
        return guide

    removed: list[str] = []

    for bracket in guide.brackets:
        for group in bracket.gem_groups:
            kept = []
            for gem in group.gems:
                if _is_valid_gem(gem.name, valid_names):
                    kept.append(gem)
                else:
                    removed.append(f"{gem.name} (bracket: {bracket.title}, slot: {group.slot})")
            group.gems = kept

    if removed:
        logger.warning(
            "Removed %d invalid/hallucinated gem(s) from generated build: %s",
            len(removed), "; ".join(removed),
        )

    return guide


def _is_valid_gem(name: str, valid_names: set[str]) -> bool:
    """Check if a gem name is valid, with common suffix normalization."""
    if name in valid_names:
        return True
    # Try adding/removing " Support" suffix
    if name.endswith(" Support"):
        base = name[: -len(" Support")]
        if base in valid_names:
            return True
    else:
        if f"{name} Support" in valid_names:
            return True
    # Vaal variants: "Vaal X" where "X" is valid
    if name.startswith("Vaal ") and name[5:] in valid_names:
        return True
    return False


# ---------------------------------------------------------------------------
# Item validation — fix hallucinated base types and unique names
# ---------------------------------------------------------------------------

def _build_valid_base_types() -> tuple[set[str], set[str]]:
    """Build sets of valid weapon base types and armour base types."""
    weapon_bases: set[str] = set()
    armour_bases: set[str] = set()
    try:
        from pop.calc.synthetic_items import _WEAPON_BASES, _ARMOUR_BASES
        weapon_bases.update(_WEAPON_BASES.keys())
        for slot_bases in _ARMOUR_BASES.values():
            armour_bases.update(slot_bases.keys())
    except ImportError:
        pass
    return weapon_bases, armour_bases


def _build_valid_unique_names(kb: KnowledgeBase | None = None) -> set[str]:
    """Build a set of all valid unique item names."""
    names: set[str] = set()
    if kb and kb.uniques:
        for u in kb.uniques:
            name = u.name if hasattr(u, "name") else str(u)
            names.add(name)
    try:
        from pop.calc.unique_db import list_uniques
        for u in list_uniques():
            names.add(u if isinstance(u, str) else u.name)
    except ImportError:
        pass
    return names


def _validate_guide_items(guide: BuildGuide, kb: KnowledgeBase | None = None) -> BuildGuide:
    """Fix invalid/hallucinated item base types and unique names in a generated build guide.

    - Clears invalid base_type so synthetic_items.py picks a correct one
    - Logs warnings for any corrections made
    """
    weapon_bases, armour_bases = _build_valid_base_types()
    unique_names = _build_valid_unique_names(kb)
    if not weapon_bases and not armour_bases:
        return guide

    fixed: list[str] = []

    for bracket in guide.brackets:
        for item in bracket.items:
            bt = item.base_type
            if not bt:
                continue

            is_weapon = item.slot in ("Weapon 1", "Weapon 2")

            # Check if this looks like a unique item (name matches a known unique)
            if item.name and item.name in unique_names:
                continue  # Unique — trust the base type from the DB

            # Validate base type
            if is_weapon:
                if bt not in weapon_bases:
                    fixed.append(f"{bt} → auto (slot: {item.slot}, bracket: {bracket.title})")
                    item.base_type = ""
            else:
                if bt and bt not in armour_bases:
                    # Also allow jewelry/flask names that aren't in armour bases
                    # (e.g., "Diamond Ring", "Leather Belt" are in _ARMOUR_BASES under their slot)
                    fixed.append(f"{bt} → auto (slot: {item.slot}, bracket: {bracket.title})")
                    item.base_type = ""

    if fixed:
        logger.warning(
            "Fixed %d invalid item base type(s): %s",
            len(fixed), "; ".join(fixed),
        )

    return guide


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
                # Validate gem names and item base types — remove hallucinated data
                guide = _validate_guide_gems(guide, kb)
                guide = _validate_guide_items(guide, kb)
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
            json_output=True,
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
            json_output=True,
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
            json_output=True,
        )

        data = _extract_json(text)
        guide = BuildGuide(**data)
        # Validate gem names and item base types — remove hallucinated data
        kb = load_knowledge()
        guide = _validate_guide_gems(guide, kb)
        guide = _validate_guide_items(guide, kb)
        return guide
