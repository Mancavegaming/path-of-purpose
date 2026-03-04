# Path of Purpose — Project Instructions

## Project Identity
- **Name**: Path of Purpose
- **Type**: Windows desktop app (.exe) for Christian streamers playing PoE/PoE2/WoW
- **Purpose**: Mentor-first companion bridging complex game math and grace-based advice
- **Repo**: https://github.com/Mancavegaming/path-of-purpose

## Architecture
- **Frontend**: Tauri v2 (Rust shell) + SolidJS + TypeScript
- **Backend**: Python sidecar spawned by Tauri via stdio JSON-RPC 2.0
- **Packaging**: Nuitka standalone folder mode (not PyInstaller — AV false positives)
- **Database**: SQLite (local, via stdlib sqlite3)
- **AI**: Poe.com OpenAI-compatible API (`api.poe.com/v1`, `openai` SDK)
- **IPC**: stdin/stdout JSON-RPC between Tauri and Python sidecar

## Project Layout
```
path-of-purpose/
├── CLAUDE.md                        # THIS FILE — Claude Code project context
├── .claude/settings.local.json      # Claude Code permission allowlist
├── docs/ROADMAP.md                  # Full 5-phase technical roadmap
├── build-tauri.bat / .ps1           # Windows build scripts
│
├── src-python/                      # Python sidecar
│   ├── pyproject.toml               # Python deps & config
│   ├── pop/                         # "Path of Purpose" package
│   │   ├── main.py                  # JSON-RPC entry point
│   │   ├── build_parser/
│   │   │   ├── pob_decode.py        # PoB code → XML → Build model
│   │   │   └── models.py            # Build, Item, PassiveSpec, SkillGroup, SkillSet, ItemSet
│   │   ├── delta/
│   │   │   ├── engine.py            # Core gap analysis orchestrator
│   │   │   ├── passive_diff.py      # Passive tree comparison
│   │   │   ├── gear_diff.py         # Gear slot comparison
│   │   │   ├── gem_diff.py          # Skill gem comparison
│   │   │   └── models.py            # DeltaReport, SlotDelta, GemGap, etc.
│   │   ├── oauth/
│   │   │   ├── client.py            # OAuth PKCE flow
│   │   │   └── token_store.py       # Encrypted token storage
│   │   ├── poe_api/
│   │   │   ├── character.py         # Character fetch + parse
│   │   │   ├── models.py            # Pydantic models for API responses
│   │   │   └── rate_limiter.py      # Token bucket rate limiter
│   │   └── db/                      # SQLite wrapper (placeholder)
│   └── tests/
│       ├── fixtures/                # Sample PoB codes, XML
│       ├── test_pob_decode.py       # Build parser tests
│       ├── test_delta_engine.py     # Delta engine tests
│       ├── test_oauth.py            # OAuth tests
│       ├── test_poe_api.py          # PoE API tests
│       └── test_rate_limiter.py     # Rate limiter tests
│
└── src-tauri-app/                   # Tauri v2 desktop app
    ├── package.json                 # Node deps
    ├── vite.config.ts               # Vite build config
    ├── index.html                   # Entry HTML
    ├── src/                         # SolidJS frontend
    │   ├── App.tsx                  # Root app with router + sidebar
    │   ├── index.tsx                # Entry point
    │   ├── styles.css               # Global dark theme CSS
    │   ├── lib/
    │   │   ├── types.ts             # TS interfaces matching Python models
    │   │   └── commands.ts          # Tauri invoke() wrappers
    │   ├── pages/
    │   │   ├── DecodePage.tsx        # Build paste + decode UI
    │   │   └── DeltaPage.tsx         # Delta analysis results
    │   └── components/
    │       ├── BuildSummary.tsx      # Build overview with variant tabs + gear categories
    │       ├── VariantTabs.tsx       # Reusable tab bar for build variants
    │       ├── PassiveTreePanel.tsx  # Node count + tree version + poe.com link
    │       ├── ItemCard.tsx          # Single item display
    │       ├── SkillGroupCard.tsx    # Skill group with gem list
    │       ├── GapCard.tsx          # Delta gap display card
    │       └── Sidebar.tsx          # Nav sidebar
    └── src-tauri/                   # Rust backend
        ├── Cargo.toml
        ├── src/lib.rs               # Tauri commands (decode, delta)
        ├── src/main.rs              # Tauri entry point
        ├── tauri.conf.json          # Tauri config
        ├── capabilities/            # Tauri v2 permissions
        ├── binaries/                # Python sidecar .exe goes here
        └── icons/                   # App icons

```

## Phase Status (as of 2026-03-03)
- **Phase 1: COMPLETE** — 121 tests passing
  - PoB decoder with SkillSet/ItemSet variant support (multi-variant builds)
  - OAuth PKCE client for PoE API
  - PoE API client with rate limiter (token bucket)
  - Delta Engine: passive/gear/gem diff with top-3 gap ranking
  - BLOCKED on live testing: OAuth registration requires emailing oauth@grindinggear.com
- **Phase 2: IN PROGRESS** — Tauri desktop shell + UI
  - Build decode page with variant tabs (5 variants supported)
  - Gear grouped by slot category (Weapons, Armour, Jewelry, Flasks)
  - Passive tree panel with pathofexile.com tree viewer link
  - Delta analysis page (UI complete, awaiting live data from OAuth)
- Phase 3: Trade API / Budget Stewardship
- Phase 4: Sacred Overlay (log monitor + verse triggers)
- Phase 5: Grace AI moderation

## Technical Notes
- PoE uses OAuth 2.0 with mandatory PKCE (effectively 2.1 for public clients)
- **OAuth registration is NOT self-service** — must email oauth@grindinggear.com with detailed request. They reject LLM-generated requests. Low priority for GGG.
- PoB exports are Base64 + zlib-compressed XML — parse with lxml, NOT run PoB headlessly
- Builds with variants wrap skills in `<SkillSet>` and items in `<ItemSet>` elements
- Delta Engine does structural gap analysis, NOT full DPS calculation (unsolved outside PoB's Lua)
- PoE API rate limit: 45 req/period, must cache aggressively
- PoE 2 passive tree is completely different from PoE 1 — abstract behind interface
- Python packaging: Nuitka standalone folder mode. Tauri bundles the folder.

## Dependencies
**Python** (src-python/pyproject.toml):
- httpx, authlib, keyring, lxml, pydantic, rapidfuzz
- Dev: pytest, pytest-asyncio, nuitka, ruff

**Node** (src-tauri-app/package.json):
- solid-js, @solidjs/router, vite, vite-plugin-solid
- @tauri-apps/api, @tauri-apps/cli

**Rust** (src-tauri-app/src-tauri/Cargo.toml):
- tauri v2

## Dev Commands
```bash
# Run Python tests (121 tests)
cd src-python && python -m pytest

# Run specific test file
cd src-python && python -m pytest tests/test_pob_decode.py -v

# TypeScript type check
cd src-tauri-app && npx tsc --noEmit

# Dev server (frontend only, no Tauri)
cd src-tauri-app && npm run dev

# Full Tauri dev (requires Rust toolchain + Python sidecar built)
cd src-tauri-app && npm run tauri dev

# Lint Python
cd src-python && ruff check pop/

# Build Python sidecar with Nuitka
cd src-python && python -m nuitka --standalone --output-dir=build --include-package=pop pop/main.py
```

## Conventions
- Python: Pydantic models for all data structures. Type hints everywhere.
- Python style: ruff with line-length 100, target py311
- Frontend: SolidJS with TypeScript. TS interfaces mirror Python Pydantic models exactly.
- CSS: Dark gaming theme with CSS custom properties (--bg-primary, --accent, etc.)
- Testing: pytest with fixtures in tests/fixtures/. Aim for high coverage on core logic.
- IPC: JSON-RPC 2.0 over stdio between Tauri and Python sidecar
