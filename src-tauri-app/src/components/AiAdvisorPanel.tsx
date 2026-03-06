import { createSignal, For, Show } from "solid-js";
import type { Build, ChatMessage, Item, TradeListing } from "../lib/types";
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
      main_skill: mainSkill?.name ?? null,
      items: b.items.slice(0, 10).map((i) => ({
        name: i.name,
        base_type: i.base_type,
        slot: i.slot,
      })),
      skill_groups: b.skill_groups.slice(0, 6).map((g) => ({
        gems: g.gems.map((gm) => ({
          name: gm.name,
          is_support: gm.is_support,
        })),
      })),
    };

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
              {props.build ? " I can see your loaded build." : ""}
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
