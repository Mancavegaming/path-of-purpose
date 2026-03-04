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


def cmd_decode(args: argparse.Namespace) -> None:
    """Decode a PoB export code and print the build summary."""
    import sys
    code = sys.stdin.read().strip() if args.stdin else args.code
    build = decode_pob_code(code)
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
