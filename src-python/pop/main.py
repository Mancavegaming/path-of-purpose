"""
Path of Purpose — Engine entry point.

Phase 1: CLI mode for testing character import and delta analysis.
Phase 2+: JSON-RPC 2.0 server over stdio for Tauri IPC.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from pop.build_parser import decode_pob_code


def _safe_stdin_read() -> str:
    """Read stdin and strip surrogate characters that Windows can inject."""
    import sys
    raw = sys.stdin.buffer.read()
    return raw.decode("utf-8", errors="replace").strip()


def _resolve_api_key(api_key: str, provider: str = "anthropic") -> str:
    """Return the provided key, or fall back to the OS credential store."""
    if api_key:
        return api_key
    from pop.ai.key_store import load_api_key
    stored = load_api_key(provider)
    return stored or ""


def cmd_decode(args: argparse.Namespace) -> None:
    """Decode a PoB export code and print the build summary."""
    import sys
    code = _safe_stdin_read() if args.stdin else args.code
    if not code:
        print("No PoB code provided. Paste a Path of Building export code.", file=sys.stderr)
        sys.exit(1)
    try:
        build = decode_pob_code(code)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    print(build.summary())
    if args.verbose:
        print(json.dumps(build.model_dump(mode="json"), indent=2))


def cmd_login(args: argparse.Namespace) -> None:
    """Authenticate with the PoE API via OAuth PKCE."""
    from pop.oauth import login_sync

    tokens = login_sync(client_id=args.client_id)
    print(f"Logged in. Token expires in {tokens.expires_in_seconds}s.")


def cmd_logout(_args: argparse.Namespace) -> None:
    """Remove stored PoE API tokens."""
    from pop.oauth import delete_tokens

    delete_tokens()
    print("Logged out. Tokens removed.")


def cmd_characters(args: argparse.Namespace) -> None:
    """List all characters on the authenticated account."""
    from pop.poe_api import PoeClient

    async def _run() -> None:
        async with PoeClient(client_id=args.client_id) as poe:
            chars = await poe.list_characters()
            if not chars:
                print("No characters found.")
                return
            for c in chars:
                print(f"  {c.name:<30} Lv {c.level:>3}  {c.class_name:<20} {c.league}")

    asyncio.run(_run())


def cmd_character(args: argparse.Namespace) -> None:
    """Fetch full character detail (items, passives)."""
    from pop.poe_api import PoeClient

    async def _run() -> None:
        async with PoeClient(client_id=args.client_id) as poe:
            detail = await poe.get_character(args.name)
            print(detail.summary())
            print()

            # Show equipped items
            slots = detail.items_by_slot()
            if slots:
                print("Equipment:")
                for slot_name, item in sorted(slots.items()):
                    mods = len(item.all_mods)
                    label = item.name or item.type_line or item.base_type
                    print(f"  {slot_name:<20} {label:<35} ({mods} mods)")
            else:
                print("No equipment data.")

            # Show passive count
            n = len(detail.passives.hashes)
            if n:
                print(f"\nPassive nodes allocated: {n}")

            if args.verbose:
                print("\n" + json.dumps(detail.model_dump(mode="json"), indent=2))

    asyncio.run(_run())


def cmd_scrape_guide(args: argparse.Namespace) -> None:
    """Scrape a mobalytics.gg build guide and print structured JSON."""
    import sys
    from pop.scrapers.mobalytics import scrape_build_guide

    url = _safe_stdin_read() if args.stdin else args.url
    if not url:
        print("No URL provided. Paste a mobalytics.gg build guide URL.", file=sys.stderr)
        sys.exit(1)

    async def _run() -> None:
        try:
            guide = await scrape_build_guide(url)
        except Exception as exc:
            # Extract a clean message from httpx or ValueError
            msg = str(exc)
            if "404" in msg:
                msg = "Build guide not found (404). Check the URL is correct."
            elif "timeout" in msg.lower() or "timed out" in msg.lower():
                msg = "Request timed out. Mobalytics may be slow — try again."
            elif "connect" in msg.lower():
                msg = f"Could not connect to Mobalytics: {msg}"
            print(msg, file=sys.stderr)
            sys.exit(1)
        print(json.dumps(guide.model_dump(mode="json"), indent=2))

    asyncio.run(_run())


def cmd_trade_search(args: argparse.Namespace) -> None:
    """Search PoE trade for items similar to a build item.

    Auto-relaxes stat requirements if the initial search returns 0 results,
    progressively dropping stats until results are found (up to 4 levels).
    Also calculates DPS change for each listing vs the equipped item.
    """
    import sys
    from pop.build_parser.models import Item
    from pop.trade.stat_cache import StatCache
    from pop.trade.query_builder import build_trade_query, relax_query
    from pop.trade.client import TradeClient
    from pop.trade.dps_estimator import compare_items

    raw = _safe_stdin_read()
    if not raw:
        print("No input provided. Send JSON with 'item' and 'league' keys.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    item = Item(**data["item"])
    league = data.get("league", "Standard")
    # Optional: separate equipped item for DPS comparison (e.g. from Delta tab)
    equipped_data = data.get("equipped_item")
    equipped_item = Item(**equipped_data) if equipped_data else item
    # Optional: user-selected mod texts to include in the search
    enabled_mods: list[str] | None = data.get("enabled_mods")
    # Optional: socket/link filter from frontend
    min_links: int = data.get("min_links", 0)
    min_sockets: int = data.get("min_sockets", 0)
    # Optional: socket colour filter, e.g. {"sockets": {"r": 3, "g": 1}, "links": {"r": 2}}
    socket_colours: dict | None = data.get("socket_colours")

    async def _run() -> None:
        stat_cache = StatCache()

        if enabled_mods is not None:
            # User-controlled search: build query from only the enabled mods
            # Pass equipped item so weapon DPS floor filter can be applied
            request, trade_url = await _build_filtered_query(
                item, stat_cache, league, enabled_mods,
                equipped_item=equipped_item if equipped_item is not item else None,
                min_links=min_links,
                min_sockets=min_sockets,
                socket_colours=socket_colours,
            )
        else:
            request, trade_url = await build_trade_query(item, stat_cache, league)

        # Single search — no auto-relaxation (user controls stat filters)
        async with TradeClient(league=league) as client:
            result = await client.search(request)
            result.trade_url = trade_url

        # Compare DPS vs the equipped item (character's current gear, not guide target)
        _add_dps_changes(equipped_item, result)

        # Sort results: best DPS upgrades first, then by price for non-DPS items
        result.listings.sort(key=lambda l: -(l.dps_change or 0))

        print(json.dumps(result.model_dump(mode="json"), indent=2))

    asyncio.run(_run())


async def _build_filtered_query(
    item: "Item",
    stat_cache: "StatCache",
    league: str,
    enabled_mods: list[str],
    equipped_item: "Item | None" = None,
    min_links: int = 0,
    min_sockets: int = 0,
    socket_colours: dict | None = None,
) -> tuple["TradeSearchRequest", str]:
    """Build a trade query from user-selected mod texts.

    Only includes stats the user has checked. No auto-relaxation needed.
    For weapons, adds a DPS floor filter so only upgrades are returned.
    Supports socket/link/colour filters via the PoE trade API socket_filters.
    """
    from pop.trade.models import StatFilter, StatGroup, TradeQuery, TradeSearchRequest

    await stat_cache.ensure_loaded()

    filters: list[StatFilter] = []
    for mod_text in enabled_mods:
        entry = stat_cache.match_mod(mod_text, "explicit")
        if entry is None:
            entry = stat_cache.match_mod(mod_text, "crafted")
        if entry is None:
            entry = stat_cache.match_mod(mod_text, "implicit")
        if entry:
            filters.append(StatFilter(id=entry.id))

    stat_groups: list[StatGroup] = []
    if filters:
        # Use "count" with min=1 so items need at least 1 matching stat
        # This is more flexible than "and" which requires ALL stats
        min_count = max(1, len(filters) // 2)
        stat_groups.append(StatGroup(
            type="count",
            filters=filters,
            value={"min": min_count},
        ))
    else:
        stat_groups.append(StatGroup(type="and", filters=[]))

    # Build query filters (weapon DPS floor + socket/link requirements)
    query_filters: dict | None = None

    # Weapon DPS floor: filter out items far worse than what user has
    if equipped_item and _is_weapon_item(equipped_item):
        eq_dps = _calc_equipped_weapon_dps(equipped_item)
        if eq_dps > 0:
            dps_floor = int(eq_dps * 0.75)
            import sys
            print(f"[DPS floor] Equipped DPS: {eq_dps:.1f}, floor: {dps_floor}", file=sys.stderr)
            query_filters = query_filters or {}
            query_filters["weapon_filters"] = {
                "filters": {
                    "dps": {"min": dps_floor},
                },
            }

    # Socket/link filters — PoE trade API format:
    # "socket_filters": {"filters": {
    #   "links": {"min": 5, "r": 2, "g": 1, "b": 1},
    #   "sockets": {"min": 6, "r": 3, "g": 1, "b": 2}
    # }}
    has_socket_filter = (
        min_links > 0
        or min_sockets > 0
        or (socket_colours and (socket_colours.get("sockets") or socket_colours.get("links")))
    )
    if has_socket_filter:
        socket_filter_sockets: dict = {}
        socket_filter_links: dict = {}

        if min_sockets > 0:
            socket_filter_sockets["min"] = min_sockets
        if min_links > 0:
            socket_filter_links["min"] = min_links

        # Merge colour requirements from frontend
        if socket_colours:
            sock_colours = socket_colours.get("sockets", {})
            for colour in ("r", "g", "b", "w"):
                val = sock_colours.get(colour, 0)
                if val and val > 0:
                    socket_filter_sockets[colour] = val

            link_colours = socket_colours.get("links", {})
            for colour in ("r", "g", "b", "w"):
                val = link_colours.get(colour, 0)
                if val and val > 0:
                    socket_filter_links[colour] = val

        sf: dict = {}
        if socket_filter_sockets:
            sf["sockets"] = socket_filter_sockets
        if socket_filter_links:
            sf["links"] = socket_filter_links
        if sf:
            query_filters = query_filters or {}
            query_filters["socket_filters"] = {"filters": sf}

    # Sanitize base type — strip item name prefix, skip if looks like metadata
    from pop.trade.query_builder import _sanitize_base_type
    base_type = _sanitize_base_type(item.base_type, item.name, item.rarity)

    query = TradeQuery(
        type=base_type,
        stats=stat_groups,
        filters=query_filters,
    )
    request = TradeSearchRequest(query=query, sort={"price": "asc"})
    trade_url = f"https://www.pathofexile.com/trade/search/{league}"
    return request, trade_url


def _is_weapon_item(item: "Item") -> bool:
    """Check if an item is a weapon (not a shield/quiver)."""
    import re

    slot = (item.slot or "").lower()
    if "weapon" not in slot:
        return False
    base = item.base_type or ""
    non_weapon = re.compile(
        r"(?:Shield|Buckler|Quiver|Globe|Crest|Spirit Shield)",
        re.IGNORECASE,
    )
    return not non_weapon.search(base)


def _calc_equipped_weapon_dps(item: "Item") -> float:
    """Calculate weapon DPS from an equipped item's mods and raw text."""
    import re

    mods = [m.text for m in item.explicits] + [m.text for m in item.implicits]

    flat_phys_min = flat_phys_max = 0.0
    flat_ele_min = flat_ele_max = 0.0
    pct_phys = 0.0
    pct_aps = 0.0

    for mod in mods:
        m = re.search(r"Adds (\d+) to (\d+) Physical Damage", mod, re.IGNORECASE)
        if m:
            flat_phys_min += float(m.group(1))
            flat_phys_max += float(m.group(2))
            continue
        m = re.search(r"Adds (\d+) to (\d+) (?:Fire|Cold|Lightning) Damage", mod, re.IGNORECASE)
        if m:
            flat_ele_min += float(m.group(1))
            flat_ele_max += float(m.group(2))
            continue
        m = re.search(r"(\d+)% increased Physical Damage", mod, re.IGNORECASE)
        if m:
            pct_phys += float(m.group(1))
            continue
        m = re.search(r"(\d+)% increased Attack Speed", mod, re.IGNORECASE)
        if m:
            pct_aps += float(m.group(1))

    # Get base APS from raw_text
    base_aps = 1.2
    aps_match = re.search(r"Attacks per Second:\s*([\d.]+)", item.raw_text or "")
    if aps_match:
        base_aps = float(aps_match.group(1))

    aps = base_aps * (1.0 + pct_aps / 100.0)
    avg_phys = (flat_phys_min + flat_phys_max) / 2.0
    avg_ele = (flat_ele_min + flat_ele_max) / 2.0
    phys_dps = avg_phys * (1.0 + pct_phys / 100.0) * aps
    ele_dps = avg_ele * aps
    return phys_dps + ele_dps


def _add_dps_changes(
    equipped: "Item",
    result: "TradeSearchResult",
) -> None:
    """Estimate DPS change for each trade listing vs the equipped item."""
    from pop.trade.dps_estimator import compare_items

    slot = equipped.slot or ""
    # Build equipped item dict for comparison
    eq_dict: dict = {
        "name": equipped.name,
        "base_type": equipped.base_type,
        "slot": slot,
        "explicit_mods": [m.text for m in equipped.explicits],
        "implicit_mods": [m.text for m in equipped.implicits],
        "crafted_mods": [m.text for m in equipped.explicits if m.is_crafted],
        "raw_text": equipped.raw_text or "",
    }

    # Try to extract APS from raw_text for weapon comparison
    import re
    aps_match = re.search(r"Attacks per Second:\s*([\d.]+)", equipped.raw_text or "")
    if aps_match:
        eq_dict["attacks_per_second"] = float(aps_match.group(1))

    for listing in result.listings:
        try:
            tr_dict: dict = {
                "name": listing.item_name,
                "type_line": listing.type_line,
                "slot": slot,
                "explicit_mods": listing.explicit_mods,
                "implicit_mods": listing.implicit_mods,
                "crafted_mods": listing.crafted_mods,
                "attacks_per_second": listing.attacks_per_second,
            }
            comparison = compare_items(eq_dict, tr_dict, slot, weapon_aps=0.0)
            if comparison.is_weapon and comparison.dps_change_pct != 0:
                listing.dps_change = comparison.dps_change_pct
            elif comparison.flat_dps_change != 0:
                listing.dps_change = comparison.flat_dps_change
        except Exception:
            pass  # Skip DPS calc errors silently


def cmd_ai_chat(args: argparse.Namespace) -> None:
    """Send a message to the AI advisor."""
    import sys
    from pop.ai.advisor import Advisor
    from pop.ai.models import ChatMessage

    raw = _safe_stdin_read()
    if not raw:
        print("No input provided. Send JSON with chat request.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    message = data.get("message", "")
    build_context = data.get("build_context")
    provider = data.get("provider", "gemini")
    api_key = _resolve_api_key(data.get("api_key", ""), provider)
    raw_history = data.get("history", [])

    # Parse history into ChatMessage objects
    history = [ChatMessage(role=h["role"], content=h["content"]) for h in raw_history]

    if not message:
        print("No message provided.", file=sys.stderr)
        sys.exit(1)
    if not api_key:
        print("No API key provided.", file=sys.stderr)
        sys.exit(1)

    async def _run() -> None:
        advisor = Advisor()
        response = await advisor.chat(
            message=message,
            api_key=api_key,
            history=history,
            build_context=build_context,
            provider=provider,
        )
        print(json.dumps(response.model_dump(mode="json"), indent=2))

    asyncio.run(_run())


def cmd_generator_chat(args: argparse.Namespace) -> None:
    """Drive the build generator intake conversation."""
    import sys
    from pop.ai.generator import BuildGenerator
    from pop.ai.models import ChatMessage

    raw = _safe_stdin_read()
    if not raw:
        print("No input provided. Send JSON with chat request.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    message = data.get("message", "")
    provider = data.get("provider", "gemini")
    api_key = _resolve_api_key(data.get("api_key", ""), provider)
    raw_history = data.get("history", [])
    history = [ChatMessage(role=h["role"], content=h["content"]) for h in raw_history]

    if not message:
        print("No message provided.", file=sys.stderr)
        sys.exit(1)
    if not api_key:
        print("No API key provided.", file=sys.stderr)
        sys.exit(1)

    async def _run() -> None:
        gen = BuildGenerator()
        response = await gen.chat_intake(
            message=message, api_key=api_key, history=history, provider=provider,
        )
        print(json.dumps(response.model_dump(mode="json"), indent=2))

    try:
        asyncio.run(_run())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_generate_build(args: argparse.Namespace) -> None:
    """Generate a full BuildGuide from preferences."""
    import sys
    from pop.ai.generator import BuildGenerator
    from pop.ai.models import BuildPreferences, ChatMessage

    raw = _safe_stdin_read()
    if not raw:
        print("No input provided. Send JSON with preferences.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    provider = data.get("provider", "gemini")
    api_key = _resolve_api_key(data.get("api_key", ""), provider)
    prefs = BuildPreferences(**data.get("preferences", {}))
    raw_history = data.get("history", [])
    history = [ChatMessage(role=h["role"], content=h["content"]) for h in raw_history]

    if not api_key:
        print("No API key provided.", file=sys.stderr)
        sys.exit(1)

    async def _run() -> None:
        gen = BuildGenerator()
        guide = await gen.generate(
            api_key=api_key, preferences=prefs, history=history, provider=provider,
        )
        print(json.dumps(guide.model_dump(mode="json"), indent=2))

    try:
        asyncio.run(_run())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_refine_build(args: argparse.Namespace) -> None:
    """Refine a BuildGuide based on trade prices and budget."""
    import sys
    from pop.ai.generator import BuildGenerator
    from pop.ai.models import ChatMessage

    raw = _safe_stdin_read()
    if not raw:
        print("No input provided. Send JSON with guide and prices.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    provider = data.get("provider", "gemini")
    api_key = _resolve_api_key(data.get("api_key", ""), provider)
    guide = data.get("guide", {})
    trade_prices = data.get("trade_prices", [])
    budget_chaos = int(data.get("budget_chaos", 0))
    raw_history = data.get("history", [])
    history = [ChatMessage(role=h["role"], content=h["content"]) for h in raw_history]
    message = data.get("message", "")

    if not api_key:
        print("No API key provided.", file=sys.stderr)
        sys.exit(1)

    async def _run() -> None:
        gen = BuildGenerator()
        refined = await gen.refine(
            api_key=api_key,
            guide=guide,
            trade_prices=trade_prices,
            budget_chaos=budget_chaos,
            history=history,
            message=message,
            provider=provider,
        )
        print(json.dumps(refined.model_dump(mode="json"), indent=2))

    try:
        asyncio.run(_run())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_synthesize_items(args: argparse.Namespace) -> None:
    """Synthesize real Item objects from GuideItem stat priorities."""
    import sys
    from pop.build_parser.models import GuideItem
    from pop.calc.synthetic_items import synthesize_build_items

    raw = _safe_stdin_read()
    if not raw:
        print("No input provided. Send JSON with 'items' and optional 'tier'.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    guide_items = [GuideItem(**gi) for gi in data["items"]]
    tier = data.get("tier", "basic")
    start_id = int(data.get("start_id", 1))

    items = synthesize_build_items(guide_items, tier=tier, start_id=start_id)
    output = [item.model_dump(mode="json") for item in items]
    print(json.dumps(output, indent=2))


def cmd_compare_items(args: argparse.Namespace) -> None:
    """Compare an equipped item against a trade listing."""
    import sys
    from pop.trade.dps_estimator import compare_items

    raw = _safe_stdin_read()
    if not raw:
        print("No input provided. Send JSON with equipped_item, trade_listing, slot.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    equipped_item = data.get("equipped_item", {})
    trade_listing = data.get("trade_listing", {})
    slot = data.get("slot", "")
    weapon_aps = float(data.get("weapon_aps", 0.0))

    result = compare_items(equipped_item, trade_listing, slot, weapon_aps=weapon_aps)
    print(json.dumps(result.model_dump(mode="json"), indent=2))


def cmd_compare_build_dps(args: argparse.Namespace) -> None:
    """Compare full build DPS with current item vs trade item swapped in."""
    import copy
    import sys

    from pop.build_parser.models import Build, Item, ItemMod
    from pop.calc.engine import calculate_dps
    from pop.calc.models import CalcConfig

    raw = _safe_stdin_read()
    if not raw:
        print("No input. Send JSON with build, trade_listing, slot.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    build = Build(**data["build"])
    slot = data.get("slot", "")
    listing = data.get("trade_listing", {})
    config_data = data.get("config")
    config = CalcConfig(**config_data) if config_data else None

    # Calculate baseline DPS with current items
    baseline = calculate_dps(build, config_overrides=config)

    # Build a synthetic Item from the trade listing
    implicit_mods = [ItemMod(text=t) for t in listing.get("implicit_mods", [])]
    explicit_mods = [ItemMod(text=t) for t in listing.get("explicit_mods", [])]
    crafted_mods = [ItemMod(text=t) for t in listing.get("crafted_mods", [])]

    # Construct raw_text for weapon damage parsing
    raw_lines = []
    for m in implicit_mods + explicit_mods + crafted_mods:
        raw_lines.append(m.text)
    # Include weapon-header fields if present in listing
    for field in ("physical_damage", "elemental_damage", "attacks_per_second",
                  "critical_strike_chance"):
        if field in listing:
            raw_lines.append(str(listing[field]))

    trade_item = Item(
        slot=slot,
        name=listing.get("item_name", "") or listing.get("name", ""),
        base_type=listing.get("type_line", "") or listing.get("base_type", ""),
        rarity=listing.get("rarity", "RARE"),
        level=listing.get("ilvl", 0),
        quality=listing.get("quality", 0),
        implicits=implicit_mods,
        explicits=explicit_mods + crafted_mods,
        raw_text="\n".join(raw_lines),
    )

    # Clone the build and swap the item
    swapped_build = build.model_copy(deep=True)
    found = False
    for i, item in enumerate(swapped_build.items):
        if item.slot == slot:
            swapped_build.items[i] = trade_item
            found = True
            break
    if not found:
        swapped_build.items.append(trade_item)

    swapped = calculate_dps(swapped_build, config_overrides=config)

    base_dps = baseline.combined_dps
    swap_dps = swapped.combined_dps
    change_pct = ((swap_dps - base_dps) / base_dps * 100) if base_dps > 0 else 0.0

    result = {
        "baseline_dps": round(base_dps, 1),
        "swapped_dps": round(swap_dps, 1),
        "dps_change": round(swap_dps - base_dps, 1),
        "dps_change_pct": round(change_pct, 1),
        "baseline_hit_dps": round(baseline.total_dps, 1),
        "swapped_hit_dps": round(swapped.total_dps, 1),
        "baseline_dot_dps": round(baseline.total_dot_dps, 1),
        "swapped_dot_dps": round(swapped.total_dot_dps, 1),
        "skill_name": baseline.skill_name,
    }
    print(json.dumps(result, indent=2))


def cmd_batch_compare_build_dps(args: argparse.Namespace) -> None:
    """Compare build DPS for multiple trade listings in a single invocation."""
    import sys

    from pop.build_parser.models import Build, Item, ItemMod
    from pop.calc.engine import calculate_dps
    from pop.calc.models import CalcConfig

    raw = _safe_stdin_read()
    if not raw:
        print("No input. Send JSON with build, listings, slot.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    build = Build(**data["build"])
    slot = data.get("slot", "")
    listings = data.get("listings", [])
    config_data = data.get("config")
    config = CalcConfig(**config_data) if config_data else None

    # Calculate baseline DPS once
    baseline = calculate_dps(build, config_overrides=config)
    base_dps = baseline.combined_dps

    results = []
    for i, listing in enumerate(listings):
        try:
            implicit_mods = [ItemMod(text=t) for t in listing.get("implicit_mods", [])]
            explicit_mods = [ItemMod(text=t) for t in listing.get("explicit_mods", [])]
            crafted_mods = [ItemMod(text=t) for t in listing.get("crafted_mods", [])]

            raw_lines = [m.text for m in implicit_mods + explicit_mods + crafted_mods]
            for field in ("physical_damage", "elemental_damage", "attacks_per_second",
                          "critical_strike_chance"):
                if field in listing:
                    raw_lines.append(str(listing[field]))

            trade_item = Item(
                slot=slot,
                name=listing.get("item_name", "") or listing.get("name", ""),
                base_type=listing.get("type_line", "") or listing.get("base_type", ""),
                rarity=listing.get("rarity", "RARE"),
                level=listing.get("ilvl", 0),
                quality=listing.get("quality", 0),
                implicits=implicit_mods,
                explicits=explicit_mods + crafted_mods,
                raw_text="\n".join(raw_lines),
            )

            swapped_build = build.model_copy(deep=True)
            found = False
            for j, item in enumerate(swapped_build.items):
                if item.slot == slot:
                    swapped_build.items[j] = trade_item
                    found = True
                    break
            if not found:
                swapped_build.items.append(trade_item)

            swapped = calculate_dps(swapped_build, config_overrides=config)
            swap_dps = swapped.combined_dps
            change = swap_dps - base_dps
            change_pct = (change / base_dps * 100) if base_dps > 0 else 0.0

            results.append({
                "listing_index": i,
                "dps_change": round(change, 1),
                "dps_change_pct": round(change_pct, 1),
            })
        except Exception:
            results.append({
                "listing_index": i,
                "dps_change": None,
                "dps_change_pct": None,
            })

    print(json.dumps({
        "baseline_dps": round(base_dps, 1),
        "skill_name": baseline.skill_name,
        "results": results,
    }, indent=2))


def cmd_suggest_passive_nodes(args: argparse.Namespace) -> None:
    """Find the top unallocated passive nodes by DPS impact."""
    import sys

    from pop.build_parser.models import Build
    from pop.build_parser.tree_data import TreeData, fetch_tree_data
    from pop.calc.engine import calculate_dps
    from pop.calc.models import CalcConfig

    raw = _safe_stdin_read()
    if not raw:
        print("No input. Send JSON with build.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    build = Build(**data["build"])
    config_data = data.get("config")
    config = CalcConfig(**config_data) if config_data else None
    max_suggestions = data.get("max_suggestions", 5)

    # Get the active passive spec
    spec_idx = data.get("spec_index", 0)
    if spec_idx >= len(build.passive_specs):
        print(json.dumps({"suggestions": [], "error": "No passive spec found"}))
        return

    spec = build.passive_specs[spec_idx]
    if not spec.nodes:
        print(json.dumps({"suggestions": [], "error": "No allocated nodes"}))
        return

    # Load tree data for adjacency
    version = spec.tree_version.replace("_", ".") if spec.tree_version else "3.28.0"
    try:
        tree_raw = fetch_tree_data(version)
    except Exception:
        print(json.dumps({"suggestions": [], "error": "Could not load tree data"}))
        return

    tree = TreeData(tree_raw, version)
    allocated = set(spec.nodes)

    # Find adjacent unallocated nodes (1-hop from allocated)
    candidates: list[int] = []
    for nid in allocated:
        for neighbor in tree.adjacency.get(nid, set()):
            if neighbor not in allocated and neighbor not in candidates:
                node = tree.nodes.get(neighbor)
                if not node:
                    continue
                # Skip ascendancy nodes, start nodes, mastery nodes
                if node.get("ascendancyName") or node.get("classStartIndex") is not None:
                    continue
                if node.get("isMastery"):
                    continue
                candidates.append(neighbor)

    if not candidates:
        print(json.dumps({"suggestions": []}))
        return

    # Calculate baseline DPS once
    baseline = calculate_dps(build, config_overrides=config)
    base_dps = baseline.combined_dps

    # Evaluate each candidate node
    results = []
    for nid in candidates:
        try:
            swapped = build.model_copy(deep=True)
            swapped.passive_specs[spec_idx].nodes.append(nid)
            swapped_result = calculate_dps(swapped, config_overrides=config)
            change = swapped_result.combined_dps - base_dps
            node = tree.nodes[nid]
            results.append({
                "node_id": nid,
                "name": node.get("name", ""),
                "stats": [s for s in node.get("stats", []) if isinstance(s, str)],
                "is_notable": bool(node.get("isNotable")),
                "is_keystone": bool(node.get("isKeystone")),
                "dps_change": round(change, 1),
                "dps_change_pct": round((change / base_dps * 100) if base_dps > 0 else 0, 1),
            })
        except Exception:
            continue

    # Sort by DPS change descending, take top N
    results.sort(key=lambda r: r["dps_change"], reverse=True)
    suggestions = results[:max_suggestions]

    print(json.dumps({
        "baseline_dps": round(base_dps, 1),
        "skill_name": baseline.skill_name,
        "candidates_evaluated": len(candidates),
        "suggestions": suggestions,
    }, indent=2))


def _normalize_price_to_chaos(price: dict | None, divine_ratio: float = 200.0) -> float:
    """Convert a trade price to chaos equivalent."""
    if not price:
        return 0.0
    amount = price.get("amount", 0)
    currency = (price.get("currency", "") or "").lower()
    rates = {
        "chaos": 1.0,
        "divine": divine_ratio,
        "exalted": 1.0,
        "alch": 0.25,
        "fusing": 0.5,
        "vaal": 0.5,
        "alteration": 0.05,
        "jeweller": 0.1,
        "chromatic": 0.05,
        "chance": 0.1,
        "regret": 0.5,
        "scouring": 0.3,
    }
    return amount * rates.get(currency, 1.0)


def cmd_budget_optimize(args: argparse.Namespace) -> None:
    """Find the best DPS upgrades across all gear slots within a budget."""
    import sys

    from pop.build_parser.models import Build, Item, ItemMod
    from pop.calc.engine import calculate_dps
    from pop.calc.models import CalcConfig
    from pop.trade.client import TradeClient
    from pop.trade.query_builder import build_trade_query
    from pop.trade.stat_cache import StatCache

    raw = _safe_stdin_read()
    if not raw:
        print("No input. Send JSON with build, budget_chaos, league.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    build = Build(**data["build"])
    budget_chaos = data.get("budget_chaos", 50)
    league = data.get("league", "Standard")
    divine_ratio = data.get("divine_ratio", 200.0)
    requested_slots = data.get("slots")
    max_per_slot = data.get("max_listings_per_slot", 5)
    config_data = data.get("config")
    config = CalcConfig(**config_data) if config_data else None

    # Default slots to search if not specified
    default_slots = [
        "Weapon 1", "Body Armour", "Helmet", "Gloves", "Boots",
        "Belt", "Ring 1", "Ring 2", "Amulet",
    ]
    slots = requested_slots or default_slots

    # Build a map of slot → equipped item
    items_by_slot: dict[str, Item] = {}
    for item in build.items:
        if item.slot:
            items_by_slot[item.slot] = item

    # Calculate baseline DPS once
    baseline = calculate_dps(build, config_overrides=config)
    base_dps = baseline.combined_dps

    async def _run() -> None:
        stat_cache = StatCache()
        recommendations: list[dict] = []
        slots_searched = 0
        total_evaluated = 0

        async with TradeClient(league=league) as client:
            for slot in slots:
                equipped = items_by_slot.get(slot)
                if not equipped:
                    continue

                slots_searched += 1

                try:
                    # Build trade query for this slot's item
                    request, _url = await build_trade_query(
                        equipped, stat_cache, league,
                    )

                    # Add price filter — max budget in chaos
                    # Trade API price filter format
                    if request.query.filters is None:
                        request.query.filters = {}
                    request.query.filters["trade_filters"] = {
                        "filters": {
                            "price": {"max": budget_chaos},
                        },
                    }

                    # Search with limited results
                    result = await client.search(request, max_fetch=max_per_slot)

                    for listing in result.listings:
                        total_evaluated += 1
                        price_dict = listing.price.model_dump() if listing.price else None
                        price_chaos = _normalize_price_to_chaos(
                            price_dict, divine_ratio,
                        )

                        # Skip free/zero-price items
                        if price_chaos <= 0:
                            continue

                        # Calculate DPS with this item swapped in
                        try:
                            implicit_mods = [
                                ItemMod(text=t) for t in listing.implicit_mods
                            ]
                            explicit_mods = [
                                ItemMod(text=t) for t in listing.explicit_mods
                            ]
                            crafted_mods = [
                                ItemMod(text=t) for t in listing.crafted_mods
                            ]

                            raw_lines = [
                                m.text
                                for m in implicit_mods + explicit_mods + crafted_mods
                            ]

                            trade_item = Item(
                                slot=slot,
                                name=listing.item_name or "",
                                base_type=listing.type_line or "",
                                rarity="RARE",
                                level=listing.ilvl,
                                implicits=implicit_mods,
                                explicits=explicit_mods + crafted_mods,
                                raw_text="\n".join(raw_lines),
                            )

                            swapped_build = build.model_copy(deep=True)
                            found = False
                            for j, it in enumerate(swapped_build.items):
                                if it.slot == slot:
                                    swapped_build.items[j] = trade_item
                                    found = True
                                    break
                            if not found:
                                swapped_build.items.append(trade_item)

                            swapped = calculate_dps(
                                swapped_build, config_overrides=config,
                            )
                            dps_gain = swapped.combined_dps - base_dps

                            # Only recommend upgrades (positive DPS gain)
                            if dps_gain > 0:
                                gain_pct = (
                                    (dps_gain / base_dps * 100)
                                    if base_dps > 0
                                    else 0.0
                                )
                                efficiency = dps_gain / price_chaos

                                recommendations.append({
                                    "slot": slot,
                                    "item_name": (
                                        listing.item_name
                                        or listing.type_line
                                        or "Unknown"
                                    ),
                                    "type_line": listing.type_line,
                                    "icon_url": listing.icon_url,
                                    "price_chaos": round(price_chaos, 1),
                                    "price_currency": (
                                        listing.price.currency
                                        if listing.price
                                        else "chaos"
                                    ),
                                    "price_amount": (
                                        listing.price.amount
                                        if listing.price
                                        else 0
                                    ),
                                    "dps_gain": round(dps_gain, 1),
                                    "dps_gain_pct": round(gain_pct, 1),
                                    "efficiency": round(efficiency, 1),
                                    "new_total_dps": round(
                                        swapped.combined_dps, 1,
                                    ),
                                    "whisper": listing.whisper,
                                    "account_name": listing.account_name,
                                    "explicit_mods": listing.explicit_mods,
                                    "implicit_mods": listing.implicit_mods,
                                })
                        except Exception:
                            continue

                except Exception as exc:
                    print(
                        f"[budget] Slot {slot} search failed: {exc}",
                        file=sys.stderr,
                    )
                    continue

        # Sort by efficiency (DPS gain per chaos spent)
        recommendations.sort(key=lambda r: r["efficiency"], reverse=True)

        print(json.dumps({
            "baseline_dps": round(base_dps, 1),
            "skill_name": baseline.skill_name,
            "slots_searched": slots_searched,
            "total_listings_evaluated": total_evaluated,
            "recommendations": recommendations,
        }, indent=2))

    asyncio.run(_run())


def cmd_ai_set_key(args: argparse.Namespace) -> None:
    """Store an AI provider API key in the OS credential store."""
    import sys
    from pop.ai.key_store import save_api_key, save_provider

    raw = _safe_stdin_read()
    if not raw:
        print("No API key provided on stdin.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
        key = data.get("api_key", raw)
        provider = data.get("provider", "anthropic")
    except json.JSONDecodeError:
        key = raw
        provider = "anthropic"

    save_api_key(key, provider)
    save_provider(provider)
    print(json.dumps({"status": "ok"}))


def cmd_ai_check_key(args: argparse.Namespace) -> None:
    """Check whether an AI provider API key is stored."""
    from pop.ai.key_store import has_api_key, load_provider

    provider = load_provider()
    raw = _safe_stdin_read()
    if raw:
        try:
            data = json.loads(raw)
            provider = data.get("provider", provider)
        except json.JSONDecodeError:
            pass

    print(json.dumps({"has_key": has_api_key(provider), "provider": provider}))


def cmd_refresh_knowledge(args: argparse.Namespace) -> None:
    """Fetch latest game data from RePoE and patch notes, save to local cache."""
    from pop.knowledge.cache import refresh_knowledge

    async def _run() -> None:
        kb = await refresh_knowledge()
        result = {
            "status": "ok",
            "gems": len(kb.gems),
            "uniques": len(kb.uniques),
            "patch_notes": len(kb.patch_notes),
            "version": kb.version,
            "last_updated": kb.last_updated,
        }
        print(json.dumps(result, indent=2))

    asyncio.run(_run())


def cmd_check_knowledge(args: argparse.Namespace) -> None:
    """Check knowledge cache status; auto-refresh if stale."""
    from pop.knowledge.cache import is_knowledge_stale, load_knowledge, refresh_knowledge

    kb = load_knowledge()
    stale = is_knowledge_stale()

    if kb and not stale:
        print(json.dumps({
            "status": "current",
            "gems": len(kb.gems),
            "uniques": len(kb.uniques),
            "patch_notes": len(kb.patch_notes),
            "version": kb.version,
            "last_updated": kb.last_updated,
            "stale": False,
        }, indent=2))
        return

    # Stale or missing — auto-refresh
    async def _run() -> None:
        kb = await refresh_knowledge()
        print(json.dumps({
            "status": "refreshed",
            "gems": len(kb.gems),
            "uniques": len(kb.uniques),
            "patch_notes": len(kb.patch_notes),
            "version": kb.version,
            "last_updated": kb.last_updated,
            "stale": False,
        }, indent=2))

    asyncio.run(_run())


def cmd_resolve_tree_urls(args: argparse.Namespace) -> None:
    """Resolve passive tree URLs for a BuildGuide's key_nodes."""
    import sys
    from pop.build_parser.tree_data import resolve_guide_tree_urls

    raw = _safe_stdin_read()
    if not raw:
        print("No input provided. Send JSON with guide data.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    guide = data.get("guide", data)
    version = data.get("tree_version", "3.28.0")

    async def _run() -> None:
        result = await resolve_guide_tree_urls(guide, version)
        print(json.dumps(result, indent=2))

    try:
        asyncio.run(_run())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_list_public_characters(args: argparse.Namespace) -> None:
    """List characters on a public PoE account."""
    import sys
    from pop.poe_api.public_client import PublicPoeClient, ProfilePrivateError

    raw = _safe_stdin_read()
    if not raw:
        print("No input. Send JSON with 'account_name'.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(raw)
    account_name = data.get("account_name", "")
    if not account_name:
        print(json.dumps({"error": "account_name is required"}))
        return

    async def _run() -> None:
        async with PublicPoeClient() as client:
            try:
                chars = await client.list_characters(account_name)
                result = [
                    {
                        "name": c.name,
                        "class_name": c.class_name,
                        "level": c.level,
                        "league": c.league,
                    }
                    for c in chars
                ]
                print(json.dumps(result))
            except ProfilePrivateError as e:
                print(json.dumps({"error": str(e), "private": True}))
            except Exception as e:
                print(json.dumps({"error": str(e)}))

    asyncio.run(_run())


def cmd_import_character(args: argparse.Namespace) -> None:
    """Import a character from a public PoE profile into a Build."""
    import sys
    from pop.poe_api.public_client import PublicPoeClient, ProfilePrivateError
    from pop.poe_api.character_to_build import character_to_build
    from pop.poe_api.models import CharacterEntry

    raw = _safe_stdin_read()
    if not raw:
        print("No input. Send JSON with 'account_name' and 'character_name'.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(raw)
    account_name = data.get("account_name", "")
    character_name = data.get("character_name", "")

    if not account_name or not character_name:
        print(json.dumps({"error": "account_name and character_name are required"}))
        return

    async def _run() -> None:
        async with PublicPoeClient() as client:
            try:
                # Fetch character list to get class/level info
                chars = await client.list_characters(account_name)
                char_entry = None
                for c in chars:
                    if c.name == character_name:
                        char_entry = c
                        break
                if not char_entry:
                    print(json.dumps({"error": f"Character '{character_name}' not found"}))
                    return

                # Fetch items and passives
                items = await client.get_items(account_name, character_name)
                passives = await client.get_passives(account_name, character_name)

                # Convert to Build
                build = character_to_build(char_entry, items, passives)
                print(json.dumps(build.model_dump(mode="json")))

            except ProfilePrivateError as e:
                print(json.dumps({"error": str(e), "private": True}))
            except Exception as e:
                print(json.dumps({"error": str(e)}))

    asyncio.run(_run())


def cmd_list_gem_names(args: argparse.Namespace) -> None:
    """Return all known gem names (active + support)."""
    from pop.calc.gem_data import _ACTIVE_GEMS, _SUPPORT_GEMS

    active = sorted(_ACTIVE_GEMS.keys())
    support = sorted(_SUPPORT_GEMS.keys())
    print(json.dumps({"active": active, "support": support}))


def cmd_calc_dps(args: argparse.Namespace) -> None:
    """Calculate DPS for a build's skill."""
    import sys
    from pop.build_parser.models import Build
    from pop.calc.engine import calculate_dps
    from pop.calc.models import CalcConfig

    raw = _safe_stdin_read()
    if not raw:
        print("No input provided. Send JSON with 'build' key.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    build = Build(**data["build"])
    skill_index = data.get("skill_index")
    config_data = data.get("config")

    # Override main skill if requested
    if skill_index is not None:
        build.main_socket_group = int(skill_index) + 1  # 1-based in PoB

    config = CalcConfig(**config_data) if config_data else None
    result = calculate_dps(build, config_overrides=config)
    print(json.dumps(result.model_dump(mode="json"), indent=2))


def cmd_calc_all_dps(args: argparse.Namespace) -> None:
    """Calculate DPS for all skill groups in a build."""
    import sys
    from pop.build_parser.models import Build
    from pop.calc.calc_context import calculate_all_skills
    from pop.calc.models import CalcConfig

    raw = _safe_stdin_read()
    if not raw:
        print("No input provided. Send JSON with 'build' key.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    build = Build(**data["build"])
    config_data = data.get("config")
    config = CalcConfig(**config_data) if config_data else None

    results = calculate_all_skills(build, config)
    output = [r.model_dump(mode="json") for r in results]
    print(json.dumps(output, indent=2))


def cmd_delta(args: argparse.Namespace) -> None:
    """Compare a PoB build against a live character via Delta Engine."""
    from pop.build_parser import decode_pob_code
    from pop.poe_api import PoeClient
    from pop.delta import analyze

    guide = decode_pob_code(args.pob_code)
    print(f"Guide: {guide.summary()}")

    async def _run() -> None:
        async with PoeClient(client_id=args.client_id) as poe:
            character = await poe.get_character(args.character_name)
            print(f"Character: {character.summary()}")
            print()

            report = analyze(guide, character)
            print(report.display())

            if args.verbose:
                print("\n" + json.dumps(report.model_dump(mode="json"), indent=2))

    asyncio.run(_run())


def cmd_delta_builds(args: argparse.Namespace) -> None:
    """Compare two Build objects (guide vs imported character)."""
    import sys
    from pop.build_parser.models import Build
    from pop.delta.engine import analyze_builds

    raw = _safe_stdin_read() if args.stdin else ""
    if not raw:
        print(json.dumps({"error": "No input provided"}))
        sys.exit(1)

    data = json.loads(raw)
    guide = Build.model_validate(data["guide_build"])
    character = Build.model_validate(data["character_build"])

    report = analyze_builds(guide, character)
    print(json.dumps(report.model_dump(mode="json")))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pop",
        description="Path of Purpose — PoE build analysis engine",
    )
    parser.add_argument(
        "--client-id",
        default="",
        help="PoE API OAuth client ID (register at pathofexile.com/developer/apps)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- decode ---
    p_decode = subparsers.add_parser("decode", help="Decode a PoB export code")
    p_decode.add_argument("code", nargs="?", default="", help="PoB export code (Base64 string)")
    p_decode.add_argument("--stdin", action="store_true", help="Read code from stdin")
    p_decode.add_argument("-v", "--verbose", action="store_true", help="Print full JSON")
    p_decode.set_defaults(func=cmd_decode)

    # --- login ---
    p_login = subparsers.add_parser("login", help="Authenticate with PoE API")
    p_login.set_defaults(func=cmd_login)

    # --- logout ---
    p_logout = subparsers.add_parser("logout", help="Remove stored PoE API tokens")
    p_logout.set_defaults(func=cmd_logout)

    # --- characters ---
    p_chars = subparsers.add_parser("characters", help="List all characters")
    p_chars.set_defaults(func=cmd_characters)

    # --- character ---
    p_char = subparsers.add_parser("character", help="Fetch character details")
    p_char.add_argument("name", help="Character name (case-sensitive)")
    p_char.add_argument("-v", "--verbose", action="store_true", help="Print full JSON")
    p_char.set_defaults(func=cmd_character)

    # --- scrape_guide ---
    p_scrape = subparsers.add_parser("scrape_guide", help="Scrape a mobalytics.gg build guide")
    p_scrape.add_argument("url", nargs="?", default="", help="Mobalytics guide URL")
    p_scrape.add_argument("--stdin", action="store_true", help="Read URL from stdin")
    p_scrape.set_defaults(func=cmd_scrape_guide)

    # --- trade_search ---
    p_trade = subparsers.add_parser("trade_search", help="Search PoE trade for similar items")
    p_trade.add_argument("--stdin", action="store_true", default=True)
    p_trade.set_defaults(func=cmd_trade_search)

    # --- synthesize_items ---
    p_synth = subparsers.add_parser(
        "synthesize_items", help="Convert GuideItem stat priorities into real Items"
    )
    p_synth.add_argument("--stdin", action="store_true", default=True)
    p_synth.set_defaults(func=cmd_synthesize_items)

    # --- compare_items ---
    p_compare = subparsers.add_parser("compare_items", help="Compare equipped vs trade item")
    p_compare.add_argument("--stdin", action="store_true", default=True)
    p_compare.set_defaults(func=cmd_compare_items)

    # --- ai_chat ---
    p_ai_chat = subparsers.add_parser("ai_chat", help="Send a message to the AI advisor")
    p_ai_chat.add_argument("--stdin", action="store_true", default=True)
    p_ai_chat.set_defaults(func=cmd_ai_chat)

    # --- generator_chat ---
    p_gen_chat = subparsers.add_parser("generator_chat", help="Build generator intake chat")
    p_gen_chat.add_argument("--stdin", action="store_true", default=True)
    p_gen_chat.set_defaults(func=cmd_generator_chat)

    # --- generate_build ---
    p_gen_build = subparsers.add_parser("generate_build", help="Generate a full build guide")
    p_gen_build.add_argument("--stdin", action="store_true", default=True)
    p_gen_build.set_defaults(func=cmd_generate_build)

    # --- refine_build ---
    p_refine = subparsers.add_parser("refine_build", help="Refine build guide with trade prices")
    p_refine.add_argument("--stdin", action="store_true", default=True)
    p_refine.set_defaults(func=cmd_refine_build)

    # --- ai_set_key ---
    p_ai_set = subparsers.add_parser("ai_set_key", help="Store Anthropic API key")
    p_ai_set.add_argument("--stdin", action="store_true", default=True)
    p_ai_set.set_defaults(func=cmd_ai_set_key)

    # --- ai_check_key ---
    p_ai_check = subparsers.add_parser("ai_check_key", help="Check if Anthropic API key is stored")
    p_ai_check.set_defaults(func=cmd_ai_check_key)

    # --- refresh_knowledge ---
    p_knowledge = subparsers.add_parser(
        "refresh_knowledge", help="Fetch latest game data (gems, uniques, patch notes)"
    )
    p_knowledge.set_defaults(func=cmd_refresh_knowledge)

    # --- check_knowledge ---
    p_check_kb = subparsers.add_parser(
        "check_knowledge", help="Check game data cache; auto-refresh if stale (>24h)"
    )
    p_check_kb.set_defaults(func=cmd_check_knowledge)

    # --- resolve_tree_urls ---
    p_tree = subparsers.add_parser("resolve_tree_urls", help="Resolve passive tree URLs for a build guide")
    p_tree.add_argument("--stdin", action="store_true", default=True)
    p_tree.set_defaults(func=cmd_resolve_tree_urls)

    # --- list_gem_names ---
    p_gems = subparsers.add_parser("list_gem_names", help="List all known gem names")
    p_gems.set_defaults(func=cmd_list_gem_names)

    # --- compare_build_dps ---
    p_cbdps = subparsers.add_parser("compare_build_dps", help="Compare full build DPS with item swap")
    p_cbdps.add_argument("--stdin", action="store_true", default=True)
    p_cbdps.set_defaults(func=cmd_compare_build_dps)

    # --- batch_compare_build_dps ---
    p_batch_dps = subparsers.add_parser("batch_compare_build_dps", help="Batch compare build DPS for multiple trade listings")
    p_batch_dps.add_argument("--stdin", action="store_true", default=True)
    p_batch_dps.set_defaults(func=cmd_batch_compare_build_dps)

    # --- suggest_passive_nodes ---
    p_suggest = subparsers.add_parser("suggest_passive_nodes", help="Suggest top passive nodes by DPS impact")
    p_suggest.add_argument("--stdin", action="store_true", default=True)
    p_suggest.set_defaults(func=cmd_suggest_passive_nodes)

    # --- budget_optimize ---
    p_budget = subparsers.add_parser("budget_optimize", help="Find best DPS upgrades within budget")
    p_budget.add_argument("--stdin", action="store_true", default=True)
    p_budget.set_defaults(func=cmd_budget_optimize)

    # --- calc_dps ---
    p_calc = subparsers.add_parser("calc_dps", help="Calculate DPS for a build skill")
    p_calc.add_argument("--stdin", action="store_true", default=True)
    p_calc.set_defaults(func=cmd_calc_dps)

    # --- calc_all_dps ---
    p_calc_all = subparsers.add_parser("calc_all_dps", help="Calculate DPS for all skills in a build")
    p_calc_all.add_argument("--stdin", action="store_true", default=True)
    p_calc_all.set_defaults(func=cmd_calc_all_dps)

    # --- list_public_characters ---
    p_chars = subparsers.add_parser("list_public_characters", help="List characters on a public PoE account")
    p_chars.add_argument("--stdin", action="store_true", default=True)
    p_chars.set_defaults(func=cmd_list_public_characters)

    # --- import_character ---
    p_import = subparsers.add_parser("import_character", help="Import a character from public PoE profile")
    p_import.add_argument("--stdin", action="store_true", default=True)
    p_import.set_defaults(func=cmd_import_character)

    # --- delta ---
    p_delta = subparsers.add_parser("delta", help="Compare a PoB build against a live character")
    p_delta.add_argument("pob_code", help="PoB export code (Base64 string)")
    p_delta.add_argument("character_name", help="Character name to compare against")
    p_delta.add_argument("-v", "--verbose", action="store_true", help="Print full JSON")
    p_delta.set_defaults(func=cmd_delta)

    # --- delta_builds ---
    p_delta_b = subparsers.add_parser("delta_builds", help="Compare two Build objects (guide vs character)")
    p_delta_b.add_argument("--stdin", action="store_true", default=True)
    p_delta_b.set_defaults(func=cmd_delta_builds)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
