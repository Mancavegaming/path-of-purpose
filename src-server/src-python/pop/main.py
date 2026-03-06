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
    """Search PoE trade for items similar to a build item."""
    import sys
    from pop.build_parser.models import Item
    from pop.trade.stat_cache import StatCache
    from pop.trade.query_builder import build_trade_query
    from pop.trade.client import TradeClient

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

    async def _run() -> None:
        stat_cache = StatCache()
        request, trade_url = await build_trade_query(item, stat_cache, league)

        async with TradeClient(league=league) as client:
            result = await client.search(request)
            result.trade_url = trade_url

        print(json.dumps(result.model_dump(mode="json"), indent=2))

    asyncio.run(_run())


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

    # --- delta ---
    p_delta = subparsers.add_parser("delta", help="Compare a PoB build against a live character")
    p_delta.add_argument("pob_code", help="PoB export code (Base64 string)")
    p_delta.add_argument("character_name", help="Character name to compare against")
    p_delta.add_argument("-v", "--verbose", action="store_true", help="Print full JSON")
    p_delta.set_defaults(func=cmd_delta)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
