# Path of Purpose — Project Instructions

## Project Identity
- **Name**: Path of Purpose
- **Type**: Windows desktop app (.exe) for Christian streamers playing PoE/PoE2/WoW
- **Purpose**: Mentor-first companion bridging complex game math and grace-based advice
- **Repo**: https://github.com/Mancavegaming/path-of-purpose
- **Version**: 0.2.0 (beta)

## Architecture
- **Frontend**: Tauri v2 (Rust shell) + SolidJS + TypeScript
- **Backend**: Python sidecar spawned by Tauri via stdio JSON-RPC 2.0
- **Server**: Optional remote API (src-server/) for hosted AI features
- **Packaging**: Nuitka standalone folder mode (not PyInstaller — AV false positives)
- **Database**: SQLite (local, via stdlib sqlite3)
- **AI**: Poe.com OpenAI-compatible API (`api.poe.com/v1`, `openai` SDK)
- **Auth**: Discord OAuth for user accounts + Patreon for subscriptions
- **Streaming**: Twitch IRC integration for chat overlay
- **IPC**: stdin/stdout JSON-RPC between Tauri and Python sidecar
- **Updater**: Tauri v2 NSIS updater with minisign signatures, served from GitHub releases
- **Signing key**: `~/.tauri/path-of-purpose.key` (password-protected)

## Project Layout
```
path-of-purpose/
├── CLAUDE.md                        # THIS FILE
├── build-tauri.bat / .ps1           # Windows build scripts
├── release.sh                       # GitHub release script
├── docs/ROADMAP.md                  # Full 5-phase technical roadmap
│
├── src-python/                      # Python sidecar (29 CLI commands)
│   ├── pyproject.toml
│   ├── pop/
│   │   ├── main.py                  # CLI entry — decode, trade, ai_chat, calc_dps, delta, etc.
│   │   ├── ai/                      # AI advisor + build generator
│   │   │   ├── advisor.py           # Stateless advisor (history per call)
│   │   │   ├── generator.py         # Build generator / refiner
│   │   │   ├── prompts.py           # Prompt templates
│   │   │   └── provider.py          # AI provider abstraction
│   │   ├── build_parser/            # PoB code → Build model
│   │   │   ├── pob_decode.py        # Base64+zlib XML decode
│   │   │   ├── models.py            # Build, Item, PassiveSpec, SkillGroup, etc.
│   │   │   └── tree_data.py         # Passive tree node data
│   │   ├── calc/                    # PoB-aligned damage calculator (Phase A-J)
│   │   │   ├── engine.py            # Main calc pipeline
│   │   │   ├── models.py            # CalcResult, CalcConfig, DefenceResult
│   │   │   ├── mod_parser.py        # Item mod → stat extraction
│   │   │   ├── stat_aggregator.py   # Aggregate stats from all sources
│   │   │   ├── conversion.py        # Damage type conversion
│   │   │   ├── crit_calc.py         # Crit chance/multiplier
│   │   │   ├── speed_calc.py        # Attack/cast speed
│   │   │   ├── dot_calc.py          # Damage over time
│   │   │   ├── impale_calc.py       # Impale DPS
│   │   │   ├── player_defense_calc.py # Life, armour, evasion, ES, block, resists
│   │   │   ├── ascendancy_effects.py
│   │   │   ├── flask_effects.py
│   │   │   ├── curse_effects.py
│   │   │   ├── aura_effects.py
│   │   │   ├── keystone_effects.py
│   │   │   ├── map_mods.py
│   │   │   ├── gem_data.py / gem_quality.py
│   │   │   ├── synthetic_items.py / unique_db.py
│   │   │   ├── tree_stats.py / tree_estimator.py
│   │   │   └── repoe_loader.py / config_reader.py / calc_context.py
│   │   ├── delta/                   # Gap analysis engine
│   │   │   ├── engine.py            # Orchestrator
│   │   │   ├── gear_diff.py / gem_diff.py
│   │   │   └── models.py
│   │   ├── gamedata/                # Game data registry + RePoE sync
│   │   ├── knowledge/               # Patch notes, knowledge cache
│   │   ├── trade/                   # Trade API client + DPS estimator
│   │   ├── poe_api/                 # PoE API (characters, public stash)
│   │   ├── oauth/                   # OAuth PKCE flow
│   │   ├── scrapers/                # Mobalytics build scraper
│   │   └── db/                      # SQLite wrapper
│   └── tests/                       # 672+ tests (23 test files)
│
├── src-server/                      # Remote API server (optional)
│   └── pop_server/
│       ├── ai/routes.py             # Hosted AI endpoints
│       └── models.py
│
└── src-tauri-app/                   # Tauri v2 desktop app (50 commands)
    ├── package.json
    ├── vite.config.ts
    ├── src/                         # SolidJS frontend
    │   ├── App.tsx                  # Router + sidebar layout
    │   ├── styles.css               # Dark gaming theme
    │   ├── lib/
    │   │   ├── types.ts             # TS interfaces (mirrors Python models)
    │   │   ├── commands.ts          # Tauri invoke() wrappers
    │   │   ├── auth.ts              # Discord OAuth + Patreon
    │   │   ├── buildStore.ts        # Global build state
    │   │   ├── buildUtils.ts        # Build helper functions
    │   │   ├── streamStore.ts       # Streaming/overlay state
    │   │   ├── twitchIrc.ts         # Twitch IRC client
    │   │   ├── chatCommands.ts      # Chat command handler
    │   │   └── gemColors.ts         # Gem color mappings
    │   ├── pages/
    │   │   ├── DecodePage.tsx        # PoB paste + decode
    │   │   ├── DeltaPage.tsx         # Delta analysis + AI advisor
    │   │   ├── CharacterPage.tsx     # Live character import
    │   │   ├── GeneratorPage.tsx     # AI build generator
    │   │   ├── EditorPage.tsx        # Build editor
    │   │   └── StreamingPage.tsx     # Twitch overlay controls
    │   └── components/
    │       ├── BuildSummary.tsx / VariantTabs.tsx
    │       ├── ItemCard.tsx / SkillGroupCard.tsx / GapCard.tsx
    │       ├── PassiveTreePanel.tsx / PassiveTreeCanvas.tsx
    │       ├── TradePanel.tsx / TradeListingCard.tsx
    │       ├── ItemComparisonPanel.tsx
    │       ├── AiAdvisorPanel.tsx / RightPanel.tsx
    │       ├── DpsBanner.tsx / DpsBreakdown.tsx / SkillSelector.tsx
    │       ├── DefenceSummary.tsx / ConfigBar.tsx
    │       ├── BossReadiness.tsx / BudgetOptimizer.tsx
    │       ├── Sidebar.tsx
    │       └── editor/              # Build editor sub-components
    │           ├── BuildHeaderEditor.tsx / GearEditor.tsx
    │           ├── SkillsEditor.tsx / SkillGroupEditor.tsx
    │           ├── TreeEditor.tsx / AtlasEditor.tsx
    │           ├── ItemEditorCard.tsx / EditorAiPanel.tsx
    └── src-tauri/
        ├── Cargo.toml
        ├── src/lib.rs               # 50 Tauri commands (local + remote variants)
        ├── src/main.rs
        ├── tauri.conf.json          # NSIS bundle + updater config
        ├── binaries/                # pop-engine sidecar .exe
        ├── capabilities/            # Tauri v2 permissions
        └── icons/

```

## Phase Status (as of 2026-03-13)
- **Phase 1: COMPLETE** — PoB decoder, OAuth, PoE API, Delta Engine
- **Phase 2: COMPLETE** — Desktop shell, all UI pages, trade, AI advisor, build generator
- **Calc Engine (Phase A-J): COMPLETE** — Full PoB-aligned DPS pipeline, 672 tests
  - Phases A-D: Conversion, penetration, crit, speed, DoT
  - Phase E: UI integration (DpsBanner, DpsBreakdown, SkillSelector)
  - Phase F: Synthetic builds + smart trade
  - Phase G: Curses, shock/chill, wither, ascendancy, flasks
  - Phase H: Impale, projectile, totem/trap/mine/brand, minion, keystones
  - Phase I: Accuracy, aura scaling, endurance charges, player defence
  - Phase J: Enemy map mods, gem quality, awakened supports
- **Beta release**: v0.2.0 NSIS installer built + signed, ready for GitHub
- Phase 3: Trade API / Budget Stewardship
- Phase 4: Sacred Overlay (log monitor + verse triggers)
- Phase 5: Grace AI moderation

## Build & Release
```bash
# Build Python sidecar with Nuitka
cd src-python && python -m nuitka --standalone --output-dir=build --include-package=pop pop/main.py

# Copy sidecar to Tauri binaries
cp build/main.dist/main.exe src-tauri-app/src-tauri/binaries/pop-engine-x86_64-pc-windows-msvc.exe

# Build signed Tauri installer (requires signing key)
cd src-tauri-app && \
  TAURI_SIGNING_PRIVATE_KEY="$(cat ~/.tauri/path-of-purpose.key)" \
  TAURI_SIGNING_PRIVATE_KEY_PASSWORD="Lakeshow0824!" \
  npx tauri build

# Output: src-tauri-app/src-tauri/target/release/bundle/nsis/
#   Path of Purpose_0.2.0_x64-setup.exe       (installer)
#   Path of Purpose_0.2.0_x64-setup.nsis.zip  (updater bundle)
#   *.sig files                                (signatures)

# GitHub release
gh release create v0.2.0 \
  "Path of Purpose_0.2.0_x64-setup.exe" \
  "Path of Purpose_0.2.0_x64-setup.nsis.zip" \
  latest.json
```

## Dev Commands
```bash
# Run Python tests (672+ tests)
cd src-python && python -m pytest

# Run specific test file
cd src-python && python -m pytest tests/test_damage_calc.py -v

# TypeScript type check
cd src-tauri-app && npx tsc --noEmit

# Dev server (frontend only)
cd src-tauri-app && npm run dev

# Full Tauri dev (requires sidecar built)
cd src-tauri-app && npm run tauri dev

# Lint Python
cd src-python && ruff check pop/
```

## Technical Notes
- PoB exports are Base64 + zlib-compressed XML — parse with lxml
- Builds with variants wrap skills in `<SkillSet>` and items in `<ItemSet>` elements
- Engine returns `CalcResult` with `.dps` and `.defence` (life, armour, evasion, ES, block, resists)
- `CalcConfig` supports all config toggles (enemy type, charges, flasks, curses, conditions, map mods)
- AI Advisor is stateless — frontend sends full `messages[]` history each call
- PoE API rate limit: 45 req/period, must cache aggressively
- Updater checks `https://github.com/Mancavegaming/path-of-purpose/releases/latest/download/latest.json`

## Conventions
- Python: Pydantic models for all data structures. Type hints everywhere.
- Python style: ruff with line-length 100, target py311
- Frontend: SolidJS with TypeScript. TS interfaces mirror Python models exactly.
- CSS: Dark gaming theme with CSS custom properties (--bg-primary, --accent, etc.)
- Testing: pytest with fixtures in tests/fixtures/. 672+ tests.
- IPC: JSON-RPC 2.0 over stdio between Tauri and Python sidecar
- **No duplicate data sources** — all features read from centralized calc engine modules
