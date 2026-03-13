import { createSignal, For, Show, onMount } from "solid-js";
import type { Build, CalcResult, ChatMessage, Item, Gem } from "../../lib/types";
import { aiChatRemote, synthesizeItems, listGemNames } from "../../lib/commands";
import { token, isLoggedIn, isSubscribed } from "../../lib/auth";

// Cached gem name database — loaded once from Python
let _activeGemNames: string[] = [];
let _supportGemNames: string[] = [];
let _allGemNamesLower: Set<string> = new Set();  // lowercased for matching
let _supportNamesLower: Set<string> = new Set();
let _gemDbLoaded = false;

async function loadGemDb() {
  if (_gemDbLoaded) return;
  try {
    const db = await listGemNames();
    _activeGemNames = db.active;
    _supportGemNames = db.support;
    _allGemNamesLower = new Set([
      ...db.active.map((n) => n.toLowerCase()),
      ...db.support.map((n) => n.toLowerCase()),
    ]);
    _supportNamesLower = new Set(db.support.map((n) => n.toLowerCase()));
    _gemDbLoaded = true;
    console.log(`Loaded gem DB: ${db.active.length} active, ${db.support.length} support`);
  } catch (e) {
    console.warn("Failed to load gem database:", e);
  }
}

/** Actions the AI panel can request on the build */
export interface BuildAction {
  type: "add_item" | "remove_item" | "add_gem" | "remove_gem" | "add_skill_group" | "set_passive";
  item?: Item;
  slot?: string;
  gem?: Gem;
  groupIndex?: number;
  passiveUpdate?: { total_points?: number; key_nodes?: string[]; priority?: string; url?: string };
}

interface EditorAiPanelProps {
  build: Build | null;
  dpsResult?: CalcResult | null;
  onAction: (action: BuildAction) => void;
  nextId: () => number;
}

// Slot aliases for natural language
const SLOT_ALIASES: Record<string, string> = {
  weapon: "Weapon 1", mainhand: "Weapon 1", "main hand": "Weapon 1",
  offhand: "Weapon 2", "off hand": "Weapon 2", shield: "Weapon 2",
  helmet: "Helmet", helm: "Helmet", hat: "Helmet",
  body: "Body Armour", chest: "Body Armour", "body armour": "Body Armour", "body armor": "Body Armour",
  gloves: "Gloves", gauntlets: "Gloves",
  boots: "Boots",
  amulet: "Amulet", ammy: "Amulet", necklace: "Amulet",
  ring: "Ring 1", "ring 1": "Ring 1", "ring 2": "Ring 2",
  belt: "Belt",
  "flask 1": "Flask 1", "flask 2": "Flask 2", "flask 3": "Flask 3",
  "flask 4": "Flask 4", "flask 5": "Flask 5",
};

// Tier aliases
const TIER_MAP: Record<string, "basic" | "max"> = {
  t1: "max", t2: "max", "tier 1": "max", "tier 2": "max",
  t3: "basic", t4: "basic", "tier 3": "basic", "tier 4": "basic",
  endgame: "max", max: "max", best: "max",
  budget: "basic", basic: "basic", starter: "basic", leveling: "basic",
};

function resolveSlot(text: string): string | null {
  const lower = text.toLowerCase().trim();
  if (SLOT_ALIASES[lower]) return SLOT_ALIASES[lower];
  // Check partial matches
  for (const [alias, slot] of Object.entries(SLOT_ALIASES)) {
    if (lower.includes(alias)) return slot;
  }
  return null;
}

function resolveTier(text: string): "basic" | "max" {
  const lower = text.toLowerCase();
  for (const [key, tier] of Object.entries(TIER_MAP)) {
    if (lower.includes(key)) return tier;
  }
  return "basic";
}

/** Try to parse an "add item" request from user message */
function parseAddItemRequest(msg: string): { name: string; slot: string; tier: "basic" | "max"; statPriority: string[] } | null {
  // Patterns: "add X as weapon", "add X to weapon slot", "put X in weapon", "add X with T3 rolls as weapon"
  const patterns = [
    /add\s+(?:a\s+)?(.+?)\s+(?:as|to|in|for)\s+(?:the\s+)?(?:my\s+)?(.+?)(?:\s+slot)?$/i,
    /(?:put|equip|use)\s+(?:a\s+)?(.+?)\s+(?:as|in|on|for)\s+(?:the\s+)?(?:my\s+)?(.+?)(?:\s+slot)?$/i,
    /add\s+(?:a\s+)?(.+?)\s+(?:with\s+.+?\s+)?(?:as|to|in|for)\s+(?:the\s+)?(?:my\s+)?(.+?)(?:\s+slot)?$/i,
  ];

  for (const pattern of patterns) {
    const match = msg.match(pattern);
    if (match) {
      let itemPart = match[1].trim();
      const slotPart = match[2].trim();
      const slot = resolveSlot(slotPart);
      if (!slot) continue;

      // Extract tier from item part (e.g., "Royal Bow with T3 rolls")
      const tier = resolveTier(msg);

      // Clean item name — remove tier/roll qualifiers
      itemPart = itemPart
        .replace(/\s+with\s+(?:t\d|tier\s*\d|endgame|max|budget|basic|best)\s*(?:rolls?|mods?)?/i, "")
        .replace(/\s+(?:t\d|tier\s*\d)\s*(?:rolls?|mods?)?/i, "")
        .trim();

      // Extract stat priorities from message context
      const statPriority = extractStatPriorities(msg, slot);

      return { name: itemPart, slot, tier, statPriority };
    }
  }

  return null;
}

function extractStatPriorities(msg: string, slot: string): string[] {
  const lower = msg.toLowerCase();
  const priorities: string[] = [];

  // Common stat keywords
  const statKeywords: Record<string, string> = {
    life: "life", hp: "life", health: "life",
    "fire res": "fire resistance", "cold res": "cold resistance",
    "lightning res": "lightning resistance", "ele res": "elemental resistances",
    resistance: "elemental resistances", res: "elemental resistances",
    "attack speed": "attack speed", aps: "attack speed",
    "crit chance": "critical strike chance", crit: "critical strike chance",
    "crit multi": "critical strike multiplier",
    "phys damage": "physical damage", "physical damage": "physical damage",
    "spell damage": "spell damage",
    "added fire": "added fire damage", "added cold": "added cold damage",
    "added lightning": "added lightning damage",
    accuracy: "accuracy",
    "movement speed": "movement speed",
    armour: "armour", armor: "armour", evasion: "evasion",
    "energy shield": "energy shield", es: "energy shield",
  };

  for (const [kw, stat] of Object.entries(statKeywords)) {
    if (lower.includes(kw) && !priorities.includes(stat)) {
      priorities.push(stat);
    }
  }

  // Default priorities by slot if none specified
  if (priorities.length === 0) {
    if (slot.startsWith("Weapon")) {
      priorities.push("physical damage", "attack speed", "critical strike chance");
    } else if (["Helmet", "Body Armour", "Gloves", "Boots"].includes(slot)) {
      priorities.push("life", "elemental resistances");
    } else if (slot.startsWith("Ring") || slot === "Amulet" || slot === "Belt") {
      priorities.push("life", "elemental resistances");
    }
  }

  return priorities;
}

/** Try to parse gem/skill requests — supports multiple gems and flexible phrasing */
function parseGemRequests(msg: string): { gems: { name: string; isSupport: boolean }[]; slot?: string } | null {
  const lower = msg.toLowerCase();

  // Must contain skill/gem-related keywords
  const actionKeywords = ["add", "put", "use", "link", "socket", "include", "set up", "setup", "skill", "gem", "support"];
  if (!actionKeywords.some((kw) => lower.includes(kw))) return null;

  // Avoid matching item-related requests
  if (parseAddItemRequest(msg)) return null;

  // Try to extract a slot for the skill group
  let slot: string | undefined;
  const slotMatch = msg.match(/(?:in|to|on|for)\s+(?:the\s+)?(?:my\s+)?(body armou?r|helmet|gloves|boots|weapon\s*[12])/i);
  if (slotMatch) slot = resolveSlot(slotMatch[1]) ?? undefined;

  // Extract gem names from the message
  let gemText = msg;

  // Strip common prefixes
  gemText = gemText.replace(/^(?:can you |please |could you )?(?:add|put|use|link|socket|include|set up|setup)\s+/i, "");
  // Strip trailing slot/group references
  gemText = gemText.replace(/\s+(?:to|in|on|for)\s+(?:the\s+)?(?:my\s+)?(?:main\s+)?(?:skill|group|setup|links|body|helmet|gloves|boots|weapon).*$/i, "");
  // Strip "as my main skill" etc.
  gemText = gemText.replace(/\s+as\s+(?:my\s+)?(?:main\s+)?(?:skill|active|main).*$/i, "");

  // Strategy 1: split on commas, "and", semicolons, newlines
  let parts = gemText
    .split(/\s*(?:,|;|\band\b|\n)\s*/i)
    .map((s) => s.trim())
    .filter((s) => s.length > 1);

  // Strategy 2: try splitting each part on gem name boundaries from the full database.
  // This handles run-on text like "Galvanic Arrow Mirage Archer Added Cold Damage"
  if (_gemDbLoaded) {
    const expanded: string[] = [];
    for (const part of parts) {
      const split = splitOnGemBoundaries(part);
      if (split.length > 1) {
        expanded.push(...split);
      } else {
        expanded.push(part);
      }
    }
    parts = expanded;
  }

  if (parts.length === 0) return null;

  const gems: { name: string; isSupport: boolean }[] = [];
  for (let part of parts) {
    // Clean up: remove "a ", leading numbers/dashes
    part = part.replace(/^(?:a\s+|an\s+|\d+[\.\)]\s*|-\s*)/i, "").trim();
    if (part.length < 2) continue;

    // Check if it's already a canonical gem name from the DB
    const partLower = part.toLowerCase();
    const isKnown = _allGemNamesLower.has(partLower);
    const isKnownSupport = _supportNamesLower.has(partLower)
      || _supportNamesLower.has(partLower + " support");

    // Use canonical name if known, otherwise title-case it
    let name: string;
    if (isKnown) {
      // Find the canonical casing
      name = _activeGemNames.find((n) => n.toLowerCase() === partLower)
        ?? _supportGemNames.find((n) => n.toLowerCase() === partLower)
        ?? titleCase(part);
    } else if (isKnownSupport) {
      name = _supportGemNames.find((n) => n.toLowerCase() === partLower + " support")
        ?? titleCase(part);
    } else {
      name = titleCase(part);
    }

    const isSupport = /support/i.test(name) || isKnownSupport;
    gems.push({ name, isSupport });
  }

  return gems.length > 0 ? { gems, slot } : null;
}

/** Split a run-on gem string using the full gem database.
 *  Uses greedy matching: at each word position, finds the longest matching gem name.
 *  e.g. "Galvanic Arrow Mirage Archer Added Cold Damage" →
 *       ["Galvanic Arrow", "Mirage Archer Support", "Added Cold Damage Support"]
 */
function splitOnGemBoundaries(text: string): string[] {
  if (!_gemDbLoaded) return [text];

  // Build sorted list of all gem names (longest first for greedy matching)
  // Include both with and without "Support" suffix for matching
  const allNames: { lower: string; canonical: string; isSupport: boolean }[] = [];
  for (const name of _activeGemNames) {
    allNames.push({ lower: name.toLowerCase(), canonical: name, isSupport: false });
  }
  for (const name of _supportGemNames) {
    allNames.push({ lower: name.toLowerCase(), canonical: name, isSupport: true });
    // Also match without " Support" suffix (users often omit it)
    if (name.toLowerCase().endsWith(" support")) {
      const short = name.slice(0, -8); // Remove " Support"
      allNames.push({ lower: short.toLowerCase(), canonical: name, isSupport: true });
    }
  }
  // Sort by length descending for greedy matching
  allNames.sort((a, b) => b.lower.length - a.lower.length);

  const lower = text.toLowerCase().trim();
  const result: string[] = [];
  let pos = 0;

  while (pos < lower.length) {
    // Skip whitespace
    while (pos < lower.length && lower[pos] === " ") pos++;
    if (pos >= lower.length) break;

    const remaining = lower.slice(pos);
    let matched = false;

    // Try to match the longest gem name at current position
    for (const entry of allNames) {
      if (remaining.startsWith(entry.lower)) {
        // Make sure it's a word boundary (next char is space, comma, end, etc.)
        const endPos = pos + entry.lower.length;
        if (endPos >= lower.length || /[\s,;]/.test(lower[endPos])) {
          result.push(entry.canonical);
          pos = endPos;
          matched = true;
          break;
        }
      }
    }

    if (!matched) {
      // Skip to next word
      const nextSpace = lower.indexOf(" ", pos);
      pos = nextSpace === -1 ? lower.length : nextSpace + 1;
    }
  }

  return result.length > 0 ? result : [text];
}

function titleCase(text: string): string {
  return text
    .split(/\s+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ")
    .replace(/\bsupport\b/i, "Support")
    .replace(/\bOf\b/g, "of")
    .replace(/\bWith\b/g, "with")
    .replace(/\bOn\b/g, "on")
    .replace(/\bThe\b/g, "the")
    .replace(/\bAnd\b/g, "and");
}

export default function EditorAiPanel(props: EditorAiPanelProps) {
  const [messages, setMessages] = createSignal<ChatMessage[]>([]);
  const [input, setInput] = createSignal("");
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");

  // Load gem database on first render
  onMount(() => { loadGemDb(); });

  function buildContext(): Record<string, unknown> | null {
    const b = props.build;
    if (!b) return null;
    const mainIdx = b.main_socket_group - 1;
    const mainGroup = b.skill_groups[mainIdx];
    const mainSkill = mainGroup?.gems.find((g) => !g.is_support && g.is_enabled);
    return {
      class_name: b.class_name,
      ascendancy_name: b.ascendancy_name,
      level: b.level,
      build_name: b.build_name || "",
      main_skill: mainSkill?.name ?? null,
      mode: "build_editor",
      items: b.items.slice(0, 15).map((i) => ({
        name: i.name, base_type: i.base_type, slot: i.slot,
      })),
      skill_groups: b.skill_groups.slice(0, 8).map((g) => ({
        slot: g.slot,
        gems: g.gems.map((gm) => ({ name: gm.name, is_support: gm.is_support })),
      })),
    };
  }

  async function processLocalActions(msg: string): Promise<string | null> {
    // Try add item
    const itemReq = parseAddItemRequest(msg);
    if (itemReq) {
      try {
        const guideItems = [{
          slot: itemReq.slot,
          name: itemReq.name,
          base_type: "",
          icon_url: "",
          stat_priority: itemReq.statPriority,
        }];
        const synthesized = await synthesizeItems(guideItems, itemReq.tier);
        if (synthesized.length > 0) {
          const item = { ...synthesized[0], id: props.nextId() };
          props.onAction({ type: "add_item", item, slot: itemReq.slot });
          const tierLabel = itemReq.tier === "max" ? "endgame (T1-T2)" : "budget (T3-T4)";
          return `Added **${item.name || item.base_type}** to **${itemReq.slot}** with ${tierLabel} rolls.\n\nBase: ${item.base_type}\nMods:\n${item.explicits.map((m) => `- ${m.text}`).join("\n")}`;
        }
      } catch (e) {
        return `Failed to synthesize item: ${String(e)}`;
      }
    }

    // Try add gems/skills
    const gemReq = parseGemRequests(msg);
    if (gemReq && gemReq.gems.length > 0) {
      // If no skill groups exist, create one first
      const b = props.build;
      if (b && b.skill_groups.length === 0) {
        props.onAction({
          type: "add_skill_group",
          slot: gemReq.slot,
        });
      }

      const added: string[] = [];
      for (const g of gemReq.gems) {
        const gem: Gem = {
          name: g.name,
          gem_id: "",
          level: 20,
          quality: 0,
          is_support: g.isSupport,
          is_enabled: true,
        };
        props.onAction({
          type: "add_gem",
          gem,
          groupIndex: 0,
        });
        added.push(`**${g.name}**${g.isSupport ? " (support)" : ""}`);
      }
      return `Added ${added.join(", ")} to your skill group.`;
    }

    return null;
  }

  async function handleSend() {
    const msg = input().trim();
    if (!msg || loading()) return;

    setInput("");
    const userMsg: ChatMessage = { role: "user", content: msg };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError("");

    try {
      // Process local build actions first
      const localResult = await processLocalActions(msg);

      if (localResult) {
        // Action was processed locally — show result
        setMessages((prev) => [...prev, { role: "assistant", content: localResult }]);
      }

      // Also forward to AI for conversational response (if logged in)
      const t = token();
      if (t && isSubscribed()) {
        const history = messages().slice(-10);
        const resp = await aiChatRemote(t, msg, history, buildContext());
        if (!localResult) {
          // Only show AI response if no local action was taken
          setMessages((prev) => [...prev, { role: "assistant", content: resp.message }]);
        }
        // If local action was taken, AI response is supplementary — append it
        else {
          setMessages((prev) => [...prev, { role: "assistant", content: resp.message }]);
        }
      } else if (!localResult) {
        // Not logged in and no local action
        setMessages((prev) => [...prev, {
          role: "assistant",
          content: "I can add items and gems to your build directly! Try:\n- \"Add a Royal Bow with T3 rolls as weapon\"\n- \"Add Hatred gem to main skill\"\n- \"Put a Diamond Ring in ring 1\"\n\nLog in for full AI advice.",
        }]);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div class="ai-panel" style={{ height: "100%", display: "flex", "flex-direction": "column" }}>
      <div class="chat-messages" style={{ flex: "1", "overflow-y": "auto" }}>
        <Show when={messages().length === 0}>
          <div class="panel-empty" style={{ "font-size": "0.8rem", padding: "12px" }}>
            I can edit your build! Try:
            <ul style={{ "margin-top": "8px", "padding-left": "16px", "line-height": "1.8" }}>
              <li>"Add Cyclone, Melee Physical Damage Support, and Fortify Support"</li>
              <li>"Add a Royal Bow with T3 rolls as weapon"</li>
              <li>"Put a Diamond Ring in ring 1"</li>
              <li>"Add an Astral Plate with endgame rolls as body armour"</li>
            </ul>
            {isLoggedIn() && isSubscribed() ? "I can also answer build questions!" : ""}
          </div>
        </Show>
        <For each={messages()}>
          {(msg) => (
            <div
              class={msg.role === "user" ? "chat-bubble chat-bubble-user" : "chat-bubble chat-bubble-assistant"}
              innerHTML={msg.role === "assistant" ? formatMessage(msg.content) : undefined}
            >
              {msg.role === "user" ? msg.content : undefined}
            </div>
          )}
        </For>
        <Show when={loading()}>
          <div class="chat-bubble chat-bubble-assistant chat-bubble-loading">
            <span class="spinner" /> Working...
          </div>
        </Show>
      </div>

      <Show when={error()}>
        <div class="error-toast">{error()}</div>
      </Show>

      <div class="chat-input-row">
        <textarea
          placeholder="Add items, gems, or ask questions..."
          value={input()}
          onInput={(e) => setInput(e.currentTarget.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          disabled={loading()}
        />
        <button onClick={handleSend} disabled={loading() || !input().trim()}>
          Send
        </button>
      </div>
    </div>
  );
}

/** Simple markdown-like formatting for AI responses */
function formatMessage(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>")
    .replace(/^- /gm, "&bull; ");
}
