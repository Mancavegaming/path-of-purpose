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
You have full access to the user's loaded build and can both answer questions AND suggest \
modifications to improve it.

## Your Expertise
- **Builds**: Gem setups, support priorities, passive tree pathing, ascendancy choices, \
defensive layering (armour, evasion, block, spell suppression, max res, endurance charges)
- **Crafting**: Fossil, essence, harvest, bench crafts, meta-crafting — step-by-step guides
- **Trade**: Pricing, valuable mods, search strategies, buy vs craft decisions
- **Passives**: Tree optimization, keystone selection, notable priority for the build's weapon type
- **League mechanics**: Atlas strategies, atlas passive tree recommendations, Voidstone progression, \
shaped regions, map juicing, scarab + sextant combos, endgame optimization
- **Map mods**: Know which mods are deadly for which builds (reflect, no leech, no regen, etc.), \
which mods are safe to run, and optimal map rolling strategy for profit
- **Game math**: Damage calculations, more vs increased, conversion chains, crit breakpoints, \
ailment scaling, penetration vs exposure
- **DPS analysis**: When DPS data is available, reference specific numbers to explain damage \
scaling, identify weak points, and suggest improvements that would increase DPS the most
- **Boss encounters**: Know DPS thresholds and defensive requirements for every boss. \
Can advise whether a build is ready for specific bosses (Sirus, Maven, Uber Elder, etc.) \
and what to improve to get there.
- **Map clearing**: AoE scaling, chain/pierce/fork choices, explosion mechanics, \
movement speed optimization, and which map mods to avoid for specific builds
- **Defensive math**: Armour formula (DR = Armour / (Armour + 5×Damage)), evasion entropy, \
spell suppression value, max resistance value (+1% max res = 4% less ele damage), \
endurance charge stacking, guard skill selection

## Guidelines
- Reference the user's SPECIFIC build data — their items, gems, passives, and stats. \
Don't give generic advice when you can see their actual gear.
- When they ask "what should I upgrade?", analyze their gear and suggest the weakest slot. \
Consider both DPS and defensive upgrades based on what content they're targeting.
- When they ask about their passive tree, reference their key_nodes and suggest improvements.
- When they ask about gems, look at their actual gem links and suggest better supports. \
Explain WHY a support is better using more/increased multiplier reasoning.
- When they ask about bosses, reference the Boss Encounter Reference data below for exact \
DPS thresholds, defensive requirements, and mechanical tips for that encounter. \
Compare the user's build stats against these thresholds and tell them if they're ready.
- When they ask about clear speed, suggest AoE/projectile scaling, explosion sources, \
and movement speed improvements specific to their build.
- When they ask about atlas or mapping, reference the Atlas Strategy Reference below to \
recommend an atlas passive strategy that fits their build (e.g. Legion for fast clear, \
Breach for high DPS, Harvest for crafting). Use the Map Mod Danger Reference to warn about \
map mods they MUST avoid (e.g. ele reflect for ele builds, no leech for Slayer).
- When they ask about map rolling, reference the Map Mod Danger Reference to explain which \
mods to reroll vs. run based on their specific build archetype.
- When they ask about damage scaling, reference the Damage Mechanics Reference for \
more vs increased math, conversion chains, crit breakpoints, and penetration values.
- When the build has atlas strategy or map warnings loaded, proactively mention relevant \
map mod dangers and atlas recommendations if the user asks about progression.
- Be concise but thorough. Use bullet points for multi-step instructions.
- If you're unsure about something, say so rather than guessing.
- Use PoE terminology naturally (orb of alteration, chaos spam, etc.).
- Be encouraging and supportive — this app serves Christian streamers who value \
grace-based mentoring.
"""


def _advisor_knowledge_addendum() -> str:
    """Build a condensed knowledge reference for the advisor system prompt.

    Injects boss encounters, damage mechanics, atlas strategy, and map mod danger
    data so the advisor can give specific, data-backed answers.
    """
    from pop.knowledge.supplements import (
        get_atlas_strategy_ref,
        get_boss_encounter_db,
        get_damage_mechanics_ref,
        get_map_mod_danger_ref,
    )

    sections: list[str] = []

    boss_db = get_boss_encounter_db()
    if boss_db:
        sections.append(boss_db)

    dmg_ref = get_damage_mechanics_ref()
    if dmg_ref:
        sections.append(dmg_ref)

    atlas_ref = get_atlas_strategy_ref()
    if atlas_ref:
        sections.append(atlas_ref)

    map_ref = get_map_mod_danger_ref()
    if map_ref:
        sections.append(map_ref)

    if not sections:
        return ""

    return (
        "\n\n--- GAME DATA REFERENCE ---\n"
        + "\n".join(sections)
        + "\n--- END GAME DATA REFERENCE ---\n"
        "Use this data to give specific, numbers-backed advice. "
        "Reference exact DPS thresholds, boss mechanics, and map mod dangers."
    )


def _build_context_prompt(ctx: dict) -> str:
    """Format build context into a system prompt addendum."""
    parts = ["## User's Current Build"]

    if ctx.get("build_name"):
        parts.append(f"**Build**: {ctx['build_name']}")

    if ctx.get("class_name"):
        asc = ctx.get("ascendancy_name", "")
        cls = ctx["class_name"]
        parts.append(f"**Class**: {asc or cls} (Level {ctx.get('level', '?')})")

    if ctx.get("main_skill"):
        parts.append(f"**Main Skill**: {ctx['main_skill']}")

    # Full gem setup
    if ctx.get("skill_groups"):
        groups = ctx["skill_groups"]
        if isinstance(groups, list):
            parts.append("\n**Gem Links**:")
            for g in groups[:8]:
                gems = g.get("gems", [])
                slot = g.get("slot") or g.get("label", "?")
                gem_names = []
                for gm in gems:
                    name = gm.get("name", "?")
                    lvl = gm.get("level", "")
                    sup = " (S)" if gm.get("is_support") else ""
                    gem_names.append(f"{name} Lv{lvl}{sup}" if lvl else f"{name}{sup}")
                if gem_names:
                    parts.append(f"  [{slot}] {' — '.join(gem_names)}")

    # Items with mods
    if ctx.get("items"):
        items = ctx["items"]
        if isinstance(items, list):
            parts.append("\n**Gear**:")
            for item in items[:15]:
                name = item.get("name") or item.get("base_type", "Unknown")
                slot = item.get("slot", "?")
                mods = item.get("mods", [])
                mod_str = f" | {', '.join(mods[:4])}" if mods else ""
                parts.append(f"  [{slot}] {name}{mod_str}")

    # Passive tree info
    if ctx.get("passive_trees"):
        trees = ctx["passive_trees"]
        if isinstance(trees, list):
            parts.append("\n**Passive Trees**:")
            for tree in trees:
                title = tree.get("title", "Default")
                total = tree.get("total_points") or tree.get("total_nodes", "?")
                key_nodes = tree.get("key_nodes", [])
                priority = tree.get("priority", "")
                parts.append(f"  [{title}] {total} points")
                if key_nodes:
                    parts.append(f"    Key nodes: {', '.join(key_nodes[:8])}")
                if priority:
                    parts.append(f"    Priority: {priority}")

    # Bracket notes (from generated guides)
    if ctx.get("bracket_notes"):
        notes = ctx["bracket_notes"]
        if isinstance(notes, dict) and notes:
            parts.append("\n**Build Notes**:")
            for bracket, note in list(notes.items())[:3]:
                parts.append(f"  [{bracket}] {note[:200]}")

    # Atlas strategy per bracket (from generated guides)
    if ctx.get("bracket_atlas"):
        atlas = ctx["bracket_atlas"]
        if isinstance(atlas, dict) and atlas:
            parts.append("\n**Atlas Strategy**:")
            for bracket, strategy in list(atlas.items())[:3]:
                parts.append(f"  [{bracket}] {strategy[:200]}")

    # Map mod warnings per bracket (from generated guides)
    if ctx.get("bracket_map_warnings"):
        warnings = ctx["bracket_map_warnings"]
        if isinstance(warnings, dict) and warnings:
            parts.append("\n**Map Mod Warnings** (mods this build should avoid):")
            for bracket, mods in list(warnings.items())[:3]:
                if isinstance(mods, list) and mods:
                    parts.append(f"  [{bracket}] {', '.join(mods[:8])}")

    # Gap analysis (simple, from older code path)
    if ctx.get("top_gaps") and not ctx.get("delta_report"):
        gaps = ctx["top_gaps"]
        if isinstance(gaps, list):
            gap_descs = [g.get("title", "") for g in gaps[:3] if g.get("title")]
            if gap_descs:
                parts.append(f"\n**Top Improvement Gaps**: {', '.join(gap_descs)}")

    # Full delta report (from Delta page)
    if ctx.get("delta_report"):
        dr = ctx["delta_report"]
        parts.append("\n## Delta Report: "
                     f"{dr.get('character_name', '?')} vs {dr.get('guide_build_name', '?')}")

        # Top gaps with detail
        for gap in dr.get("top_gaps", [])[:5]:
            sev = gap.get("severity", "").upper()
            parts.append(f"  #{gap.get('rank', '?')} [{sev}] {gap.get('title', '')} "
                         f"— {gap.get('detail', '')}")

        # Passive tree
        pm = dr.get("passive_match_pct", 0)
        pmiss = dr.get("passive_missing", 0)
        parts.append(f"\n**Passive Tree**: {pm:.0f}% match ({pmiss} nodes missing)")

        # Gear overview
        gm = dr.get("gear_match_pct", 0)
        parts.append(f"**Gear**: {gm:.0f}% overall match")
        for slot in dr.get("gear_slots", []):
            if slot.get("match_pct", 100) < 90:
                missing = slot.get("missing_mods", [])
                missing_str = f" — missing: {', '.join(missing)}" if missing else ""
                parts.append(f"  [{slot['slot']}] {slot.get('match_pct', 0):.0f}% "
                             f"({slot.get('character_item', '?')} → "
                             f"{slot.get('guide_item', '?')}){missing_str}")

        # Gem gaps
        gem_miss = dr.get("gem_missing_supports", 0)
        if gem_miss > 0:
            parts.append(f"\n**Gems**: {gem_miss} missing supports")
            for gg in dr.get("gem_groups", []):
                if gg.get("is_missing_entirely"):
                    parts.append(f"  {gg['skill']} — ENTIRELY MISSING")
                elif gg.get("missing"):
                    parts.append(f"  {gg['skill']} — missing: {', '.join(gg['missing'])}")

        parts.append(
            "\nUse this delta data to give targeted upgrade advice. "
            "Prioritize by the top gaps list. When suggesting gear upgrades, "
            "reference the specific missing mods. When suggesting gem changes, "
            "name the exact supports to add."
        )

    # Currently selected item (detailed)
    if ctx.get("selected_item"):
        item = ctx["selected_item"]
        name = item.get("name") or item.get("base_type", "Unknown")
        parts.append(f"\n**Currently Viewing**: {name} (slot: {item.get('slot', '?')})")
        mods = item.get("mods", [])
        if mods:
            parts.append(f"  Mods: {', '.join(mods[:8])}")

    # DPS analysis data
    if ctx.get("dps_data"):
        from pop.calc.calc_context import format_single_dps_context
        dps_text = format_single_dps_context(ctx["dps_data"])
        if dps_text:
            parts.append(f"\n{dps_text}")

    # Trade listing comparison
    if ctx.get("trade_listing"):
        tl = ctx["trade_listing"]
        name = tl.get("name") or tl.get("type_line", "Unknown")
        price = tl.get("price", "?")
        parts.append(f"\n**Comparing Trade Listing**: {name} (Price: {price})")
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

        # Build system prompt with knowledge reference + optional build context
        system = SYSTEM_PROMPT + _advisor_knowledge_addendum()
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
