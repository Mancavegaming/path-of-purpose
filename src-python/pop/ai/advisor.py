"""
AI Advisor — AI-powered PoE expert mentor.

Supports Anthropic Claude and Google Gemini via the provider abstraction.
"""

from __future__ import annotations

import logging

from pop.ai.models import ChatMessage, ChatResponse
from pop.ai.provider import chat_completion

logger = logging.getLogger(__name__)

MAX_HISTORY = 20

SYSTEM_PROMPT = """\
You are a Path of Exile 1 expert mentor embedded in the "Path of Purpose" desktop app. \
Your role is to provide helpful, accurate advice on:

- **Crafting**: Fossil crafting, essence crafting, harvest, bench crafts, meta-crafting, \
recombinators, and step-by-step crafting guides for specific items
- **Trade**: Pricing items, identifying valuable mods, search strategies, and when to buy vs craft
- **Builds**: Skill gem setups, support gem choices, passive tree optimization, \
ascendancy selection, defensive layering (armor, evasion, block, spell suppression, max res)
- **League mechanics**: Current and past league mechanics, atlas strategies, \
boss progression, and endgame optimization
- **Game math**: Damage calculations, stat interactions, breakpoints, and scaling

Guidelines:
- Be concise but thorough. Prefer bullet points for multi-step instructions.
- When discussing crafting, give step-by-step instructions including item bases, \
required currencies, and expected costs.
- When a build is loaded, reference the specific items, gems, and passives in your advice.
- If you're unsure about something, say so rather than guessing.
- Use PoE-specific terminology (orb of alteration, chaos spam, etc.) naturally.
- Be encouraging and supportive — this app serves Christian streamers who value \
grace-based mentoring.
"""


def _build_context_prompt(ctx: dict) -> str:
    """Format build context into a system prompt addendum."""
    parts = ["The user currently has a build loaded:"]

    if ctx.get("class_name"):
        asc = ctx.get("ascendancy_name", "")
        cls = ctx["class_name"]
        parts.append(f"- Class: {asc or cls} (Level {ctx.get('level', '?')})")

    if ctx.get("main_skill"):
        parts.append(f"- Main skill: {ctx['main_skill']}")

    if ctx.get("items"):
        items = ctx["items"]
        if isinstance(items, list):
            item_names = [
                i.get("name") or i.get("base_type", "Unknown")
                for i in items[:10]
            ]
            parts.append(f"- Key items: {', '.join(item_names)}")

    if ctx.get("skill_groups"):
        groups = ctx["skill_groups"]
        if isinstance(groups, list):
            skill_names = []
            for g in groups[:6]:
                gems = g.get("gems", [])
                active = next((gm for gm in gems if not gm.get("is_support")), None)
                if active:
                    skill_names.append(active.get("name", "Unknown"))
            if skill_names:
                parts.append(f"- Skills: {', '.join(skill_names)}")

    if ctx.get("top_gaps"):
        gaps = ctx["top_gaps"]
        if isinstance(gaps, list):
            gap_descs = [g.get("title", "") for g in gaps[:3] if g.get("title")]
            if gap_descs:
                parts.append(f"- Top gaps: {', '.join(gap_descs)}")

    if ctx.get("selected_item"):
        item = ctx["selected_item"]
        name = item.get("name") or item.get("base_type", "Unknown")
        parts.append(f"\nCurrently viewing item: {name} (slot: {item.get('slot', '?')})")
        mods = item.get("mods", [])
        if mods:
            parts.append(f"  Mods: {', '.join(mods[:8])}")

    if ctx.get("trade_listing"):
        tl = ctx["trade_listing"]
        name = tl.get("name") or tl.get("type_line", "Unknown")
        price = tl.get("price", "?")
        parts.append(f"\nComparing against trade listing: {name}")
        parts.append(f"  Price: {price}")
        mods = tl.get("mods", [])
        if mods:
            parts.append(f"  Mods: {', '.join(mods[:8])}")
        parts.append("The user may be considering this upgrade. Provide specific advice.")

    return "\n".join(parts)


class Advisor:
    """Stateless Claude advisor — history is provided by the caller each request."""

    async def chat(
        self,
        message: str,
        api_key: str,
        history: list[ChatMessage] | None = None,
        build_context: dict | None = None,
        provider: str = "gemini",
    ) -> ChatResponse:
        """Send a message and get a response from the AI provider.

        Args:
            message: The user's message.
            api_key: API key for the selected provider.
            history: Previous messages in this conversation.
            build_context: Optional build data to inject into system prompt.
            provider: "anthropic" or "gemini" (default: "gemini").

        Returns:
            ChatResponse with the assistant's reply.
        """
        # Build message list from provided history + new user message
        messages: list[ChatMessage] = list(history or [])
        messages.append(ChatMessage(role="user", content=message))

        # Trim to last MAX_HISTORY messages
        if len(messages) > MAX_HISTORY:
            messages = messages[-MAX_HISTORY:]

        # Build system prompt with optional build context
        system = SYSTEM_PROMPT
        if build_context:
            system += "\n\n" + _build_context_prompt(build_context)

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
