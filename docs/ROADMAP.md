# Path of Purpose — Technical Roadmap (MVP)

> *"Whatever you do, work at it with all your heart, as working for the Lord."*
> — Colossians 3:23

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    TAURI v2 SHELL (Rust)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Main Window  │  │   Overlay    │  │  System Tray       │  │
│  │  (WebView2)   │  │  (WebView2)  │  │  + Hotkeys         │  │
│  │  React/Solid  │  │  Transparent │  │                    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────────────┘  │
│         │ Tauri IPC        │ Tauri IPC                        │
│  ┌──────┴──────────────────┴──────────────────────────────┐   │
│  │              Tauri Rust Commands Layer                  │   │
│  │   - Window management, file watchers, system events    │   │
│  └──────────────────────┬─────────────────────────────────┘   │
│                         │ stdio JSON-RPC                      │
│  ┌──────────────────────┴─────────────────────────────────┐   │
│  │             PYTHON SIDECAR (.exe via Nuitka)           │   │
│  │                                                        │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────────┐  │   │
│  │  │ Delta      │ │ Trade      │ │ AI Core            │  │   │
│  │  │ Engine     │ │ Scanner    │ │ (Poe.com API)      │  │   │
│  │  ├────────────┤ ├────────────┤ ├────────────────────┤  │   │
│  │  │ PoE OAuth  │ │ Budget     │ │ Grace Moderation   │  │   │
│  │  │ Client     │ │ Optimizer  │ │ Verse Selector     │  │   │
│  │  ├────────────┤ ├────────────┤ ├────────────────────┤  │   │
│  │  │ Build      │ │ Log Tailer │ │ Prayer Request DB  │  │   │
│  │  │ Parser     │ │ (Client.txt│ │ (SQLite)           │  │   │
│  │  │ (PoB XML)  │ │  + WoW)    │ │                    │  │   │
│  │  └────────────┘ └────────────┘ └────────────────────┘  │   │
│  └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Key Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Frontend shell** | Tauri v2 | ~5 MB vs Electron's ~150 MB. Native overlay support. Rust file watcher for logs. |
| **Frontend framework** | SolidJS + TypeScript | Smaller bundle than React, fine-grained reactivity for real-time overlay updates. |
| **Backend** | Python sidecar | Best ecosystem for data parsing (lxml, httpx), PoB XML parsing, and AI API integration. |
| **IPC** | stdio JSON-RPC 2.0 | Tauri's built-in sidecar stdin/stdout. No network ports to conflict with game clients. |
| **Python packaging** | Nuitka (standalone) | Fewer AV false positives than PyInstaller. Folder mode — Tauri handles the final bundle. |
| **Database** | SQLite (via sqlite3 stdlib) | Zero-config local storage for prayer requests, build snapshots, user preferences. |
| **AI provider** | Poe.com OpenAI-compatible API | Single subscription accesses Claude 3.5, GPT-4o, and others. Standard `openai` SDK works. |

---

## Phase 1 — Foundation: PoE Character Import + Math Engine

**Duration target**: 3–4 weeks
**Deliverable**: Python CLI that fetches a live PoE character and compares it against a PoB export code.

### 1.1 PoE OAuth 2.0 (PKCE) Client

The PoE API uses OAuth 2.0 with mandatory PKCE — functionally OAuth 2.1 for public (desktop) clients.

**Flow**:
```
1. Generate code_verifier (random 128 chars) + code_challenge (SHA256)
2. Open browser → pathofexile.com/oauth/authorize
   ?client_id=...&redirect_uri=http://localhost:8457/callback
   &response_type=code&scope=account:characters account:stashes
   &code_challenge=...&code_challenge_method=S256
3. User approves → redirect to localhost with ?code=...
4. Exchange code + code_verifier → access_token + refresh_token
5. Store tokens encrypted in SQLite (keyring or DPAPI)
```

**Libraries**:
```
httpx              — Async HTTP client (PoE API calls + token exchange)
authlib            — OAuth 2.0 / PKCE helpers (code_challenge generation)
keyring            — Secure OS credential storage (Windows DPAPI)
```

**Key endpoints to integrate**:
| Endpoint | Purpose |
|---|---|
| `GET /api/character` | List all characters on account |
| `GET /api/character/{name}` | Full character data: equipped items, passive tree nodes, skill gems |
| `GET /api/league` | Active leagues for dropdown UI |

**Rate limiting**: Respect `X-Rate-Limit-*` headers. Implement exponential backoff with a token bucket.

### 1.2 Build Parser (PoB Export Codes)

Path of Building exports are **Base64-encoded, zlib-compressed XML**. This is the universal build-sharing format.

**Decoding pipeline**:
```python
import base64, zlib, xml.etree.ElementTree as ET

def decode_pob_code(code: str) -> ET.Element:
    raw = base64.urlsafe_b64decode(code)
    xml_bytes = zlib.decompress(raw)
    return ET.fromstring(xml_bytes)
```

**What the XML contains**:
- `<Build>` — class, ascendancy, level, main skill
- `<Items>` — every item with full mod text
- `<Tree>` — passive tree spec (node hash IDs per version)
- `<Skills>` — skill gem links (active + supports)
- `<Config>` — PoB-specific config toggles (enemy type, charges, etc.)

**Libraries**:
```
lxml               — Faster XML parsing than stdlib ET for large build files
pydantic           — Data models for Build, Item, PassiveTree, SkillGem
```

### 1.3 Math Engine: Delta Analysis (Core MVP Logic)

This is the heart of the app. It does NOT replicate full PoB DPS calculations (that's an unsolved problem outside of PoB's Lua runtime). Instead, it performs **structural gap analysis**.

**What Delta Analysis compares**:

| Dimension | Guide Build (PoB XML) | Live Character (API) | Delta Output |
|---|---|---|---|
| **Passive tree** | Set of node hash IDs | Set of node hash IDs | Missing/extra nodes, optimal respec path |
| **Gem links** | Skill + support combos | Equipped gem links | Missing supports, wrong gem levels |
| **Gear slots** | Item base types + key mods | Equipped items + mods | Slot-by-slot mod gap (e.g., "helmet missing +2 to gems") |
| **Mod weights** | Extract mods from XML | Extract mods from API JSON | Priority ranking by mod importance |

**Priority scoring** — rank the top 3 gaps:
```python
@dataclass
class GearGap:
    slot: str                    # "helmet", "ring1", etc.
    missing_mods: list[str]      # ["# to Maximum Life", "+2 to Level of Socketed Gems"]
    priority_score: float        # weighted by mod importance (life > res > damage)
    estimated_cost: str | None   # filled in Phase 3 (Trade API)
```

**Libraries**:
```
difflib / custom   — Tree-diff for passive node sets
rapidfuzz          — Fuzzy matching for mod text (API wording ≠ PoB wording)
```

### 1.4 Project Structure (Phase 1)

```
path-of-purpose/
├── src-tauri/                    # Tauri shell (Phase 2+)
├── src-frontend/                 # SolidJS UI (Phase 2+)
├── src-python/                   # Python sidecar
│   ├── pop/                      # "Path of Purpose" package
│   │   ├── __init__.py
│   │   ├── main.py               # JSON-RPC entry point
│   │   ├── oauth/
│   │   │   ├── __init__.py
│   │   │   ├── client.py         # OAuth PKCE flow
│   │   │   └── token_store.py    # Encrypted token storage
│   │   ├── poe_api/
│   │   │   ├── __init__.py
│   │   │   ├── character.py      # Character fetch + parse
│   │   │   ├── models.py         # Pydantic models for API responses
│   │   │   └── rate_limiter.py   # Token bucket rate limiter
│   │   ├── build_parser/
│   │   │   ├── __init__.py
│   │   │   ├── pob_decode.py     # PoB code → XML → Python objects
│   │   │   └── models.py         # Build, Item, PassiveTree, SkillGem
│   │   ├── delta/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py         # Core gap analysis
│   │   │   ├── passive_diff.py   # Passive tree comparison
│   │   │   ├── gear_diff.py      # Gear slot comparison
│   │   │   └── gem_diff.py       # Skill gem comparison
│   │   └── db/
│   │       ├── __init__.py
│   │       └── store.py          # SQLite wrapper
│   ├── tests/
│   │   ├── test_pob_decode.py
│   │   ├── test_delta_engine.py
│   │   └── fixtures/             # Sample PoB codes, API responses
│   ├── pyproject.toml
│   └── nuitka.build.cmd          # Nuitka build script
├── docs/
│   └── ROADMAP.md                # This file
└── README.md
```

### 1.5 Python Packaging (.exe)

**Recommended: Nuitka in standalone folder mode**

```bash
# Install Nuitka
pip install nuitka ordered-set zstandard

# Build command (Windows, requires MSVC or MinGW)
python -m nuitka ^
    --standalone ^
    --output-dir=build ^
    --include-package=pop ^
    --enable-plugin=anti-bloat ^
    --windows-console-mode=disable ^
    src-python/pop/main.py
```

**Why Nuitka over PyInstaller for this project**:
1. **AV false positives**: PyInstaller .exe files are routinely flagged by Windows Defender. For a desktop app distributed to streamers, this is a dealbreaker.
2. **Startup speed**: PyInstaller's `--onefile` extracts to a temp directory on every launch (~2-5s). Nuitka's standalone folder starts instantly.
3. **Tauri integration**: Tauri bundles the folder contents anyway — no need for `--onefile`. Folder mode is the correct choice.
4. **Performance**: Nuitka compiles to C → machine code. The delta engine's mod-matching loops benefit from this.

**pyproject.toml (Phase 1 dependencies)**:
```toml
[project]
name = "path-of-purpose-engine"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "httpx>=0.27",
    "authlib>=1.3",
    "keyring>=25.0",
    "lxml>=5.0",
    "pydantic>=2.5",
    "rapidfuzz>=3.6",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "nuitka>=2.0",
    "ruff>=0.3",
]
```

---

## Phase 2 — Desktop Shell: Tauri + UI + IPC

**Duration target**: 3–4 weeks
**Deliverable**: Tauri desktop app with character import UI, build paste field, and delta results display.

### Key work items:
- **Tauri v2 project scaffold** with SolidJS frontend
- **JSON-RPC 2.0 IPC** between Tauri ↔ Python sidecar over stdio
- **Character import flow**: OAuth popup → character selector → fetch
- **Build paste field**: Accept PoB export code or Maxroll/PoE Vault URL
- **Delta results panel**: Display top 3 gaps with clear visual indicators
- **Build guide URL scraper**: Parse Maxroll/PoE Vault pages to extract the embedded PoB code (cheerio or server-side fetch)
- **Settings page**: Poe.com API key, default league, notification preferences
- **Auto-updater**: Tauri's built-in updater for seamless .exe updates

---

## Phase 3 — Budget Stewardship: Trade API Integration

**Duration target**: 2–3 weeks
**Deliverable**: Trade search that finds highest power-per-currency upgrade within a user budget.

### Key work items:
- **PoE Trade API client**: `POST /api/trade/search/{league}` + `GET /api/trade/fetch/{ids}`
- **Mod-to-query translator**: Convert delta engine's "missing mods" into trade search parameters
- **Power-per-Currency scorer**: Score each trade result by how many delta gaps it fills per chaos orb cost
- **Budget input**: User sets max budget, app returns ranked upgrade suggestions across ALL slots
- **Trade result caching**: SQLite cache with TTL to avoid hammering the trade API (strict rate limits)

---

## Phase 4 — Sacred Overlay: Log Monitor + Stream Events

**Duration target**: 3–4 weeks
**Deliverable**: Transparent overlay that triggers verse animations and manages prayer requests.

### Key work items:
- **Rust file watcher** (Tauri-side): `notify` crate watching `Client.txt` and WoW `SavedVariables/`
- **Log parser**: Detect events — level up, boss kill, death, zone change, high-damage hit
- **Verse engine**: Categorized Bible verse database (SQLite). Map event types → verse categories (victory, perseverance, humility, etc.)
- **Overlay renderer**: Transparent always-on-top Tauri window with CSS animations
- **Altar widget**: Viewer prayer request queue (Twitch chat integration via IRC/EventSub)
- **OBS integration**: Browser source alternative for streamers who prefer OBS capture over overlay
- **WoW support**: Parse `WTF/SavedVariables/` for addon data (combat log events, achievement triggers)

---

## Phase 5 — Grace AI: Moderation + Wise Counsel

**Duration target**: 2–3 weeks
**Deliverable**: AI-powered moderation bot with restorative dialogue and contextual "wise counsel" responses.

### Key work items:
- **Poe.com API integration**: OpenAI-compatible client hitting `api.poe.com/v1/chat/completions`
- **System prompt engineering**: Grace-based moderation persona — restorative, not punitive. Focus on de-escalation and community building.
- **Moderation triggers**: Twitch EventSub for chat messages → AI classifies severity → responds with grace-toned message
- **Wise counsel mode**: Contextual tips triggered by game state (e.g., "You've died 5 times to this boss — here's what the build guide suggests" paired with an encouraging verse)
- **Prompt safety rails**: Content filtering to ensure AI responses stay theologically appropriate and non-judgmental
- **Rate limiting**: Limit AI calls per minute per user to control Poe.com compute point costs

---

## Milestone Summary

| Phase | Deliverable | Stack |
|---|---|---|
| **1** | CLI: Character import + PoB compare + delta output | Python, httpx, lxml, pydantic |
| **2** | Desktop app: Tauri shell + React/Solid UI + IPC | Tauri v2, SolidJS, JSON-RPC |
| **3** | Trade integration: Budget optimizer | Python, PoE Trade API |
| **4** | Stream overlay: Verse triggers + prayer altar | Tauri overlay, notify crate, SQLite |
| **5** | AI moderation: Grace bot + wise counsel | Poe.com API, openai SDK |

---

## Risk Register

| Risk | Mitigation |
|---|---|
| **PoE API rate limits** (45 req/period) | Aggressive caching + background refresh. Never fetch on-demand during stream. |
| **PoB XML format changes** | Version-pin parser. PoB community fork has stable export format; monitor their GitHub releases. |
| **PoE 2 passive tree differences** | Abstract tree comparison behind an interface. PoE 1 and PoE 2 share API patterns but have different tree structures. |
| **AV false positives** | Nuitka + code-signing certificate (even a self-signed cert reduces flags). |
| **Poe.com API cost/availability** | Abstract AI provider behind interface. Can swap to direct Anthropic API or local Ollama if needed. |
| **Twitch API changes** | Use EventSub (webhook/WebSocket) — Twitch's forward-looking API, not deprecated IRC. |
