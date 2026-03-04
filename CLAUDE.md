# Path of Purpose — Project Instructions

## Project Identity
- **Name**: Path of Purpose
- **Type**: Windows desktop app (.exe) for Christian streamers playing PoE/PoE2/WoW
- **Purpose**: Mentor-first companion bridging complex game math and grace-based advice

## Architecture
- **Frontend**: Tauri v2 (Rust shell) + SolidJS + TypeScript (`src-tauri-app/`)
- **Backend**: Python sidecar spawned by Tauri via stdio JSON-RPC 2.0 (`src-python/pop/`)
- **Packaging**: Nuitka standalone folder mode (not PyInstaller — AV false positives)
- **Database**: SQLite (local, via stdlib sqlite3)
- **AI**: Poe.com OpenAI-compatible API (`api.poe.com/v1`, `openai` SDK)
- **IPC**: stdin/stdout JSON-RPC between Tauri and Python sidecar

## Key Paths
- `docs/ROADMAP.md` — Full 5-phase technical roadmap
- `src-python/pop/` — Python package root
- `src-python/tests/` — Python test suite (121 tests)
- `src-tauri-app/src-tauri/` — Rust/Tauri backend
- `src-tauri-app/src/` — SolidJS frontend

## Phase Status
- **Phase 1: COMPLETE** — 121 tests passing
  - PoB decoder (with SkillSet/ItemSet variant support), OAuth PKCE client, PoE API client, Rate limiter, Delta Engine
  - BLOCKED on live testing: OAuth registration requires emailing oauth@grindinggear.com
- **Phase 2: IN PROGRESS** — Tauri desktop shell + UI
  - Build decode page with variant tabs, gear categories, passive tree panel
- Phase 3: Trade API / Budget Stewardship
- Phase 4: Sacred Overlay (log monitor + verse triggers)
- Phase 5: Grace AI moderation

## Technical Notes
- PoE uses OAuth 2.0 with mandatory PKCE (effectively 2.1 for public clients)
- **OAuth registration is NOT self-service** — must email oauth@grindinggear.com. They reject LLM-generated requests.
- PoB exports are Base64 + zlib-compressed XML — parse with lxml, NOT run PoB headlessly
- Delta Engine does structural gap analysis, NOT full DPS calculation (unsolved outside PoB's Lua)
- PoE API rate limit: 45 req/period, must cache aggressively
- PoE 2 passive tree is completely different from PoE 1 — abstract behind interface

## Dev Commands
```bash
# Run Python tests
cd src-python && python -m pytest

# TypeScript type check
cd src-tauri-app && npx tsc --noEmit

# Dev server (frontend only)
cd src-tauri-app && npm run dev

# Full Tauri dev (requires Rust toolchain)
cd src-tauri-app && npm run tauri dev
```
