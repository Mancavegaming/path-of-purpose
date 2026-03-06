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
│   │   ├── main.py                  # CLI entry point (decode, trade_search, ai_chat, compare_items, etc.)
│   │   ├── build_parser/
│   │   │   ├── pob_decode.py        # PoB code → XML → Build model
│   │   │   └── models.py            # Build, Item, PassiveSpec, SkillGroup, SkillSet, ItemSet
│   │   ├── delta/
│   │   │   ├── engine.py            # Core gap analysis orchestrator
│   │   │   ├── passive_diff.py      # Passive tree comparison
│   │   │   ├── gear_diff.py         # Gear slot comparison
│   │   │   ├── gem_diff.py          # Skill gem comparison
│   │   │   └── models.py            # DeltaReport, SlotDelta, GemGap, etc.
│   │   ├── ai/
│   │   │   ├── advisor.py           # Stateless Claude advisor (history provided per call)
│   │   │   ├── models.py            # ChatMessage, ChatRequest, ChatResponse
│   │   │   └── key_store.py         # Anthropic API key storage (keyring)
│   │   ├── trade/
│   │   │   ├── client.py            # Async trade API client (search + fetch)
│   │   │   ├── models.py            # TradeQuery, TradeListing, WeaponDps, StatDelta, ItemComparison
│   │   │   ├── query_builder.py     # Build → trade search query conversion
│   │   │   ├── stat_cache.py        # Stat ID cache for trade API
│   │   │   └── dps_estimator.py     # Weapon DPS calc + stat extraction + item comparison
│   │   ├── scrapers/
│   │   │   └── mobalytics.py        # Mobalytics.gg build guide scraper
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
│       ├── test_dps_estimator.py    # DPS estimator + item comparison tests
│       ├── test_ai_advisor.py       # AI advisor tests (mocked Anthropic)
│       ├── test_trade_client.py     # Trade client tests
│       ├── test_trade_query_builder.py # Trade query builder tests
│       ├── test_trade_stat_cache.py # Stat cache tests
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
    │       ├── ItemCard.tsx          # Single item display (clickable for trade search)
    │       ├── SkillGroupCard.tsx    # Skill group with gem list
    │       ├── GapCard.tsx           # Delta gap display card
    │       ├── Sidebar.tsx           # Nav sidebar
    │       ├── RightPanel.tsx        # Split layout: trade results (top) + AI chat (bottom)
    │       ├── TradePanel.tsx        # Trade search results with listing selection
    │       ├── TradeListingCard.tsx   # Trade listing with Compare button
    │       ├── ItemComparisonPanel.tsx # Side-by-side DPS/stat comparison
    │       └── AiAdvisorPanel.tsx    # AI chat with build/item/trade context
    └── src-tauri/                   # Rust backend
        ├── Cargo.toml
        ├── src/lib.rs               # Tauri commands (decode, trade_search, compare_items, ai_chat, etc.)
        ├── src/main.rs              # Tauri entry point
        ├── tauri.conf.json          # Tauri config
        ├── capabilities/            # Tauri v2 permissions
        ├── binaries/                # Python sidecar .exe goes here
        └── icons/                   # App icons

```

## Phase Status (as of 2026-03-04)
- **Phase 1: COMPLETE** — PoB decoder, OAuth, PoE API, Delta Engine
  - BLOCKED on live testing: OAuth registration requires emailing oauth@grindinggear.com
- **Phase 2: IN PROGRESS** — 192 tests passing. Tauri desktop shell + UI
  - Build decode page with variant tabs (5 variants supported)
  - Gear grouped by slot category (Weapons, Armour, Jewelry, Flasks)
  - Passive tree panel with pathofexile.com tree viewer link
  - Delta analysis page (UI complete, awaiting live data from OAuth)
  - Mobalytics.gg build guide scraper
  - Trade search panel with item selection from build
  - Item comparison: DPS estimator for weapons, stat deltas for armor/jewelry
  - AI Advisor (Anthropic Claude) with stateless history, build/item/trade context
  - Right panel: merged split layout (trade top / AI chat bottom)
  - Compare button on trade listings for side-by-side item comparison
- Phase 3: Trade API / Budget Stewardship
- Phase 4: Sacred Overlay (log monitor + verse triggers)
- Phase 5: Grace AI moderation

## Technical Notes
- PoE uses OAuth 2.0 with mandatory PKCE (effectively 2.1 for public clients)
- **OAuth registration is NOT self-service** — must email oauth@grindinggear.com with detailed request. They reject LLM-generated requests. Low priority for GGG.
- PoB exports are Base64 + zlib-compressed XML — parse with lxml, NOT run PoB headlessly
- Builds with variants wrap skills in `<SkillSet>` and items in `<ItemSet>` elements
- Delta Engine does structural gap analysis, NOT full DPS calculation (unsolved outside PoB's Lua)
- DPS Estimator provides simplified weapon DPS (phys+ele+APS) and stat deltas for item comparison
- PoE API rate limit: 45 req/period, must cache aggressively
- PoE 2 passive tree is completely different from PoE 1 — abstract behind interface
- Python packaging: Nuitka standalone folder mode. Tauri bundles the folder.
- AI Advisor is stateless — frontend sends full `messages[]` history each call (Python subprocess is fresh each invocation)
- AI context includes build info, selected item, and trade listing for contextual advice

## Dependencies
**Python** (src-python/pyproject.toml):
- httpx, authlib, keyring, lxml, pydantic, rapidfuzz, anthropic
- Dev: pytest, pytest-asyncio, nuitka, ruff

**Node** (src-tauri-app/package.json):
- solid-js, @solidjs/router, vite, vite-plugin-solid
- @tauri-apps/api, @tauri-apps/cli

**Rust** (src-tauri-app/src-tauri/Cargo.toml):
- tauri v2

## Dev Commands
```bash
# Run Python tests (192 tests)
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
