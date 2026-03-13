import { createSignal, For, Show } from "solid-js";
import type { Build, CalcResult, ChatMessage, DeltaReport, Item, TradeListing } from "../lib/types";
import { aiChatRemote } from "../lib/commands";
import {
  token,
  isLoggedIn,
  isSubscribed,
  discordLogin,
  openCheckout,
  refreshUserStatus,
} from "../lib/auth";

// Discord client ID — set via env or hardcode after creating Discord app
const DISCORD_CLIENT_ID = "1479135178650554510";

interface AiAdvisorPanelProps {
  build: Build | null;
  selectedItem?: Item | null;
  selectedListing?: TradeListing | null;
  dpsResult?: CalcResult | null;
  deltaReport?: DeltaReport | null;
}

export default function AiAdvisorPanel(props: AiAdvisorPanelProps) {
  const [messages, setMessages] = createSignal<ChatMessage[]>([]);
  const [input, setInput] = createSignal("");
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");
  const [loginLoading, setLoginLoading] = createSignal(false);

  function buildContext(): Record<string, unknown> | null {
    const b = props.build;
    if (!b) return null;

    const mainIdx = b.main_socket_group - 1;
    const mainGroup = b.skill_groups[mainIdx];
    const mainSkill = mainGroup?.gems.find((g) => !g.is_support && g.is_enabled);

    const ctx: Record<string, unknown> = {
      class_name: b.class_name,
      ascendancy_name: b.ascendancy_name,
      level: b.level,
      build_name: b.build_name || "",
      main_skill: mainSkill?.name ?? null,
      items: b.items.slice(0, 15).map((i) => ({
        name: i.name,
        base_type: i.base_type,
        slot: i.slot,
        mods: [
          ...i.implicits.map((m) => m.text),
          ...i.explicits.map((m) => m.text),
        ].slice(0, 6),
        ...(i.stat_priority?.length ? { stat_priority: i.stat_priority } : {}),
      })),
      skill_groups: b.skill_groups.slice(0, 8).map((g) => ({
        slot: g.slot,
        label: g.label,
        gems: g.gems.map((gm) => ({
          name: gm.name,
          level: gm.level,
          is_support: gm.is_support,
        })),
      })),
      passive_trees: b.passive_specs.map((ps) => ({
        title: ps.title,
        total_nodes: ps.nodes.length,
        total_points: ps.total_points || ps.nodes.length,
        key_nodes: ps.key_nodes || [],
        priority: ps.priority || "",
        url: ps.url || "",
      })),
      bracket_notes: b.bracket_notes || {},
      bracket_atlas: b.bracket_atlas || {},
      bracket_map_warnings: b.bracket_map_warnings || {},
    };

    // Include DPS data if available
    const dps = props.dpsResult;
    if (dps && dps.combined_dps > 0) {
      ctx.dps_data = {
        skill_name: dps.skill_name,
        is_attack: dps.is_attack,
        combined_dps: dps.combined_dps,
        total_dps: dps.total_dps,
        hit_damage: dps.hit_damage,
        hits_per_second: dps.hits_per_second,
        crit_chance: dps.crit_chance,
        effective_crit_multi: dps.effective_crit_multi,
        type_breakdown: dps.type_breakdown,
        ignite_dps: dps.ignite_dps,
        bleed_dps: dps.bleed_dps,
        poison_dps: dps.poison_dps,
        total_dot_dps: dps.total_dot_dps,
        warnings: dps.warnings,
      };
    }

    const selItem = props.selectedItem;
    if (selItem) {
      const allMods = [
        ...selItem.implicits.map((m) => m.text),
        ...selItem.explicits.map((m) => m.text),
      ];
      ctx.selected_item = {
        name: selItem.name || selItem.base_type,
        base_type: selItem.base_type,
        slot: selItem.slot,
        mods: allMods,
        ...(selItem.stat_priority?.length ? { stat_priority: selItem.stat_priority } : {}),
      };
    }

    const selListing = props.selectedListing;
    if (selListing) {
      const price = selListing.price
        ? `${selListing.price.amount} ${selListing.price.currency}`
        : "unlisted";
      ctx.trade_listing = {
        name: selListing.item_name || selListing.type_line,
        type_line: selListing.type_line,
        price,
        mods: [
          ...selListing.implicit_mods,
          ...selListing.explicit_mods,
          ...selListing.crafted_mods,
        ],
      };
    }

    const delta = props.deltaReport;
    if (delta) {
      ctx.delta_report = {
        guide_build_name: delta.guide_build_name,
        character_name: delta.character_name,
        top_gaps: delta.top_gaps.map((g) => ({
          rank: g.rank,
          category: g.category,
          severity: g.severity,
          title: g.title,
          detail: g.detail,
        })),
        passive_match_pct: delta.passive_delta.match_pct,
        passive_missing: delta.passive_delta.missing_count,
        gear_match_pct: delta.gear_delta.overall_match_pct,
        gear_slots: delta.gear_delta.slot_deltas.map((s) => ({
          slot: s.slot,
          match_pct: s.match_pct,
          guide_item: s.guide_item_name,
          character_item: s.character_item_name,
          missing_mods: s.missing_mods.slice(0, 3).map((m) => m.mod_text),
        })),
        gem_missing_supports: delta.gem_delta.total_missing_supports,
        gem_groups: delta.gem_delta.group_deltas
          .filter((g) => g.missing_supports.length > 0 || g.is_missing_entirely)
          .map((g) => ({
            skill: g.skill_name,
            missing: g.missing_supports,
            is_missing_entirely: g.is_missing_entirely,
          })),
      };
    }

    return ctx;
  }

  async function handleLogin() {
    setLoginLoading(true);
    setError("");
    try {
      const ok = await discordLogin(DISCORD_CLIENT_ID);
      if (!ok) setError("Login failed. Please try again.");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoginLoading(false);
    }
  }

  async function handleSubscribe() {
    setError("");
    try {
      await openCheckout();
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleRefreshStatus() {
    try {
      await refreshUserStatus();
    } catch (e) {
      setError(String(e));
    }
  }

  function handleQuickAsk(question: string) {
    setInput(question);
    handleSend();
  }

  async function handleSend() {
    const msg = input().trim();
    if (!msg || loading()) return;

    const t = token();
    if (!t) {
      setError("Please log in first.");
      return;
    }

    setInput("");
    const userMsg: ChatMessage = { role: "user", content: msg };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError("");

    try {
      const history = messages().slice(0, -1);
      const resp = await aiChatRemote(t, msg, history, buildContext());
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: resp.message },
      ]);
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
    <div class="ai-panel">
      {/* Not logged in */}
      <Show when={!isLoggedIn()}>
        <div class="ai-auth-gate">
          <p class="ai-auth-prompt">Log in with Discord to use the AI Advisor</p>
          <button
            class="discord-login-btn"
            onClick={handleLogin}
            disabled={loginLoading()}
          >
            <Show when={loginLoading()} fallback="Login with Discord">
              Connecting...
            </Show>
          </button>
        </div>
      </Show>

      {/* Logged in but not subscribed */}
      <Show when={isLoggedIn() && !isSubscribed()}>
        <div class="ai-auth-gate">
          <p class="ai-auth-prompt">
            Subscribe to Path of Purpose to unlock AI features
          </p>
          <button class="subscribe-btn" onClick={handleSubscribe}>
            Subscribe — $4.99/mo
          </button>
          <button class="refresh-status-btn" onClick={handleRefreshStatus}>
            I already subscribed (refresh)
          </button>
        </div>
      </Show>

      {/* Subscribed — show chat */}
      <Show when={isLoggedIn() && isSubscribed()}>
        <div class="chat-messages">
          <Show when={messages().length === 0}>
            <div class="panel-empty">
              Ask me about crafting, trade, builds, or any PoE topic.
              {props.deltaReport ? " I can see your delta report — ask me what to upgrade next!" : props.build ? " I can see your loaded build." : ""}
            </div>
            <div class="ai-suggestions">
              <Show when={props.deltaReport}>
                <button class="ai-suggestion-btn" onClick={() => handleQuickAsk("What should I upgrade first and why?")}>
                  What should I upgrade first?
                </button>
                <button class="ai-suggestion-btn" onClick={() => handleQuickAsk("Which of my gear slots is the biggest DPS loss compared to the guide?")}>
                  Biggest DPS gap?
                </button>
                <button class="ai-suggestion-btn" onClick={() => handleQuickAsk("Am I missing any critical gem supports? What should I socket?")}>
                  Missing gem supports?
                </button>
                <button class="ai-suggestion-btn" onClick={() => handleQuickAsk("What's the cheapest upgrade I can make right now to improve my build?")}>
                  Cheapest upgrade?
                </button>
              </Show>
              <Show when={!props.deltaReport && props.build}>
                <button class="ai-suggestion-btn" onClick={() => handleQuickAsk("What should I improve on my build?")}>
                  How can I improve?
                </button>
                <button class="ai-suggestion-btn" onClick={() => handleQuickAsk("Am I ready for endgame bosses like Sirus or Maven?")}>
                  Am I boss-ready?
                </button>
              </Show>
              <Show when={props.selectedListing}>
                <button class="ai-suggestion-btn" onClick={() => handleQuickAsk("Is this trade item worth buying? How does it compare to what I have?")}>
                  Is this item worth it?
                </button>
              </Show>
            </div>
          </Show>
          <For each={messages()}>
            {(msg) => (
              <div
                class={
                  msg.role === "user"
                    ? "chat-bubble chat-bubble-user"
                    : "chat-bubble chat-bubble-assistant"
                }
              >
                {msg.content}
              </div>
            )}
          </For>
          <Show when={loading()}>
            <div class="chat-bubble chat-bubble-assistant chat-bubble-loading">
              <span class="spinner" /> Thinking...
            </div>
          </Show>
        </div>

        <Show when={error()}>
          <div class="error-toast">{error()}</div>
        </Show>

        <div class="chat-input-row">
          <textarea
            placeholder="Ask about crafting, builds, trade..."
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
      </Show>

      {/* Error display (always visible) */}
      <Show when={error() && (isLoggedIn() || !isSubscribed())}>
        <div class="error-toast">{error()}</div>
      </Show>
    </div>
  );
}
