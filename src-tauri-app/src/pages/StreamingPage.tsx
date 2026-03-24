import { createSignal, createEffect, onCleanup, For, Show } from "solid-js";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-shell";

const TWITCH_CLIENT_ID = "nxcpw276lnupq2pty6tuj9hwtthhxl";
const TWITCH_REDIRECT_URI = "http://localhost:8460/callback";
import {
  loadTwitchToken,
  storeTwitchToken,
  clearTwitchToken,
  startOverlayServer,
  updateOverlayState,
} from "../lib/commands";

import {
  chatLog,
  viewerSuggestions,
  sessionStartTime,
  commandsHandled,
  startSession,
  stopSession,
  dismissSuggestion,
  getOverlayPayload,
  overlayShowDps, setOverlayShowDps,
  overlayShowMapStats, setOverlayShowMapStats,
  overlayShowTradeWhispers, setOverlayShowTradeWhispers,
  overlayShowBossBar, setOverlayShowBossBar,
  overlayShowBossTimer, setOverlayShowBossTimer,
  overlayShowSessionDash, setOverlayShowSessionDash,
  overlayShowGraceVerses, setOverlayShowGraceVerses,
  bossKillSoundPath, setBossKillSoundPath,
  bossKillSoundEnabled, setBossKillSoundEnabled,
  currencyDrops,
  addCurrencyDrop,
  clearCurrencyDrops,
  overlayShowCurrencyTicker, setOverlayShowCurrencyTicker,
} from "../lib/streamStore";
import {
  connect as ircConnect,
  disconnect as ircDisconnect,
  connectionStatus,
  connectedChannel,
  setCommandHandler,
  sendMessage,
} from "../lib/twitchIrc";
import {
  handleCommand,
  handleCommandAsync,
  getCommandNames,
  isCommandEnabled,
  toggleCommand,
} from "../lib/chatCommands";

export default function StreamingPage() {
  // Twitch auth state
  const [twitchToken, setTwitchToken] = createSignal("");
  const [twitchUsername, setTwitchUsername] = createSignal("");
  const [twitchChannel, setTwitchChannel] = createSignal("");
  const [authLoading, setAuthLoading] = createSignal(false);
  const [authError, setAuthError] = createSignal("");

  // Overlay state
  const [overlayUrl, setOverlayUrl] = createSignal("");
  const [overlayRunning, setOverlayRunning] = createSignal(false);



  // Command toggles (track in a signal for reactivity)
  const initStates = (): Record<string, boolean> => {
    const states: Record<string, boolean> = {};
    for (const cmd of getCommandNames()) states[cmd] = true;
    return states;
  };
  const [commandStates, setCommandStates] = createSignal<Record<string, boolean>>(initStates());

  // Load stored token on mount
  const loadToken = async () => {
    try {
      const stored = await loadTwitchToken();
      if (stored.token) setTwitchToken(stored.token);
      if (stored.username) setTwitchUsername(stored.username);
      if (stored.channel) setTwitchChannel(stored.channel);
    } catch {
      // No stored token
    }
  };
  loadToken();

  // Wire up command handler (sync + async)
  setCommandHandler((user, command, args) => {
    const response = handleCommand(user, command, args);
    if (response) {
      sendMessage(response);
    } else {
      handleCommandAsync(user, command, args, (msg) => sendMessage(msg));
    }
  });

  // Push overlay state on a 2-second timer
  let overlayTimer: ReturnType<typeof setInterval> | null = null;

  createEffect(() => {
    // Always clear old timer first to prevent duplicates
    if (overlayTimer) {
      clearInterval(overlayTimer);
      overlayTimer = null;
    }
    if (overlayRunning()) {
      overlayTimer = setInterval(async () => {
        try {
          await updateOverlayState(getOverlayPayload());
        } catch {
          // Overlay server may not be ready
        }
      }, 2000);
    }
  });

  onCleanup(() => {
    if (overlayTimer) clearInterval(overlayTimer);
  });

  async function handleTwitchLogin() {
    setAuthLoading(true);
    setAuthError("");

    try {
      const scopes = "chat:read chat:edit";
      const authUrl =
        `https://id.twitch.tv/oauth2/authorize` +
        `?client_id=${TWITCH_CLIENT_ID}` +
        `&redirect_uri=${encodeURIComponent(TWITCH_REDIRECT_URI)}` +
        `&response_type=token` +
        `&scope=${encodeURIComponent(scopes)}`;

      // Start the local callback listener (Rust-side, port 8460)
      const callbackPromise = invoke<string>("listen_for_twitch_callback");

      // Open the browser
      await open(authUrl);

      // Wait for the callback
      const tokenData = await callbackPromise;

      if (!tokenData) {
        setAuthError("No token received from Twitch. Try again.");
        return;
      }

      // Validate the token and get the username
      const validateResp = await fetch("https://id.twitch.tv/oauth2/validate", {
        headers: { Authorization: `OAuth ${tokenData}` },
      });

      if (!validateResp.ok) {
        setAuthError("Token validation failed. Try logging in again.");
        return;
      }

      const validateData = await validateResp.json();
      const username = validateData.login || "";

      setTwitchToken(tokenData);
      setTwitchUsername(username);
      setTwitchChannel(username);

      await storeTwitchToken(tokenData, username, username);
    } catch (e) {
      setAuthError(`Twitch login failed: ${String(e)}`);
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleConnect() {
    if (!twitchToken() || !twitchUsername() || !twitchChannel()) {
      setAuthError("Fill in all fields: token, username, and channel.");
      return;
    }

    setAuthError("");
    setAuthLoading(true);

    try {
      await storeTwitchToken(twitchToken(), twitchUsername(), twitchChannel());
      ircConnect(twitchToken(), twitchUsername(), twitchChannel());
      startSession();
    } catch (e) {
      setAuthError(String(e));
    } finally {
      setAuthLoading(false);
    }
  }

  function handleDisconnect() {
    ircDisconnect();
    stopSession();
  }

  async function handleClearToken() {
    ircDisconnect();
    stopSession();
    setTwitchToken("");
    setTwitchUsername("");
    setTwitchChannel("");
    try {
      await clearTwitchToken();
    } catch {
      // ignore
    }
  }

  async function handleStartOverlay() {
    try {
      const msg = await startOverlayServer();
      setOverlayUrl("http://localhost:8459/overlay");
      setOverlayRunning(true);
      // Push initial state
      await updateOverlayState(getOverlayPayload());
      console.log(msg);
    } catch (e) {
      setAuthError(`Overlay error: ${String(e)}`);
    }
  }

  function handleToggleCommand(cmd: string) {
    const current = isCommandEnabled(cmd);
    toggleCommand(cmd, !current);
    setCommandStates((prev) => ({ ...prev, [cmd]: !current }));
  }

  function formatTime(ts: number): string {
    const d = new Date(ts);
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  function formatUptime(): string {
    const start = sessionStartTime();
    if (!start) return "—";
    const secs = Math.floor((Date.now() - start) / 1000);
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }

  const statusColor = () => {
    const s = connectionStatus();
    if (s === "connected") return "#4ade80";
    if (s === "connecting") return "#fbbf24";
    if (s === "error") return "#f87171";
    return "#6e7681";
  };

  return (
    <div class="streaming-page">
      <h1 class="page-title">Streaming</h1>
      <p class="page-subtitle">
        Connect to Twitch chat and run the stream overlay.
      </p>

      <div class="streaming-layout">
        {/* Left: Connection + Overlay */}
        <div class="streaming-left">
          {/* Twitch Connection */}
          <div class="stream-section">
            <div class="stream-section-title">
              <span
                class="stream-status-dot"
                style={{ background: statusColor() }}
              />
              Twitch Chat Bot
              <Show when={connectionStatus() === "connected"}>
                <span class="stream-connected-badge">
                  Connected to #{connectedChannel()}
                </span>
              </Show>
            </div>

            <Show when={connectionStatus() !== "connected"}>
              <div class="stream-form">
                <Show
                  when={twitchToken()}
                  fallback={
                    <div class="stream-login-prompt">
                      <p class="stream-hint">
                        Login with your Twitch account to connect the chat bot.
                        This uses Twitch's official OAuth — your password is never shared.
                      </p>
                      <button
                        class="twitch-login-btn"
                        onClick={handleTwitchLogin}
                        disabled={authLoading()}
                      >
                        {authLoading() ? "Logging in..." : "Login with Twitch"}
                      </button>
                    </div>
                  }
                >
                  <div class="stream-field">
                    <label>Channel</label>
                    <input
                      type="text"
                      placeholder="channel_to_join (defaults to your username)"
                      value={twitchChannel()}
                      onInput={(e) => setTwitchChannel(e.currentTarget.value)}
                      class="stream-input"
                    />
                    <span class="stream-hint">
                      Leave blank to join your own channel ({twitchUsername()}).
                    </span>
                  </div>
                  <div class="stream-actions">
                    <button
                      class="dps-calc-btn"
                      onClick={handleConnect}
                      disabled={authLoading()}
                    >
                      {authLoading() ? "Connecting..." : "Connect to Chat"}
                    </button>
                    <button class="btn-secondary" onClick={handleClearToken}>
                      Logout ({twitchUsername()})
                    </button>
                  </div>
                </Show>
              </div>
            </Show>

            <Show when={connectionStatus() === "connected"}>
              <div class="stream-actions">
                <button class="btn-secondary" onClick={handleDisconnect}>
                  Disconnect
                </button>
              </div>
            </Show>

            <Show when={authError()}>
              <div class="error-toast">{authError()}</div>
            </Show>
          </div>

          {/* Overlay Server */}
          <div class="stream-section">
            <div class="stream-section-title">Stream Overlay</div>
            <Show
              when={overlayRunning()}
              fallback={
                <button class="dps-calc-btn" onClick={handleStartOverlay}>
                  Start Overlay Server
                </button>
              }
            >
              <div class="stream-overlay-info">
                <span class="stream-overlay-url">{overlayUrl()}</span>
                <button
                  class="btn-secondary"
                  onClick={() =>
                    navigator.clipboard.writeText(overlayUrl())
                  }
                >
                  Copy URL
                </button>
              </div>
              <p class="stream-hint">
                Add this URL as a Browser Source in OBS (1920x1080, transparent background).
              </p>
              <div class="stream-overlay-preview">
                <iframe
                  src={overlayUrl()}
                  style={{
                    width: "100%",
                    height: "200px",
                    border: "1px solid var(--border)",
                    "border-radius": "6px",
                    background: "#0d1117",
                  }}
                  title="Overlay Preview"
                />
              </div>
            </Show>
          </div>

          {/* Overlay Section Toggles */}
          <div class="stream-section">
            <div class="stream-section-title">Overlay Sections</div>
            <p class="stream-hint" style={{ "margin-bottom": "8px" }}>
              Choose which sections appear on the stream overlay.
            </p>
            <div class="stream-command-grid">
              <label class="stream-command-toggle">
                <input type="checkbox" checked={overlayShowDps()} onChange={(e) => setOverlayShowDps(e.currentTarget.checked)} />
                <span class="stream-command-name">DPS Ticker</span>
              </label>
              <label class="stream-command-toggle">
                <input type="checkbox" checked={overlayShowBossBar()} onChange={(e) => setOverlayShowBossBar(e.currentTarget.checked)} />
                <span class="stream-command-name">Boss Readiness</span>
              </label>
              <label class="stream-command-toggle">
                <input type="checkbox" checked={overlayShowMapStats()} onChange={(e) => setOverlayShowMapStats(e.currentTarget.checked)} />
                <span class="stream-command-name">Map Analytics</span>
              </label>
              <label class="stream-command-toggle">
                <input type="checkbox" checked={overlayShowTradeWhispers()} onChange={(e) => setOverlayShowTradeWhispers(e.currentTarget.checked)} />
                <span class="stream-command-name">Trade Whispers</span>
              </label>
              <label class="stream-command-toggle">
                <input type="checkbox" checked={overlayShowBossTimer()} onChange={(e) => setOverlayShowBossTimer(e.currentTarget.checked)} />
                <span class="stream-command-name">Boss Timer</span>
              </label>
              <label class="stream-command-toggle">
                <input type="checkbox" checked={overlayShowSessionDash()} onChange={(e) => setOverlayShowSessionDash(e.currentTarget.checked)} />
                <span class="stream-command-name">Session Dashboard</span>
              </label>
              <label class="stream-command-toggle">
                <input type="checkbox" checked={overlayShowGraceVerses()} onChange={(e) => setOverlayShowGraceVerses(e.currentTarget.checked)} />
                <span class="stream-command-name">Grace Verses</span>
              </label>
              <label class="stream-command-toggle">
                <input type="checkbox" checked={overlayShowCurrencyTicker()} onChange={(e) => setOverlayShowCurrencyTicker(e.currentTarget.checked)} />
                <span class="stream-command-name">Currency Ticker</span>
              </label>
            </div>
          </div>

          {/* Currency Drop Tracker */}
          <div class="stream-section">
            <div class="stream-section-title">Currency Drops</div>
            <p class="stream-hint" style={{ "margin-bottom": "8px" }}>
              Track notable currency drops this session. Viewers can see the tally on the overlay and use !drops in chat.
            </p>
            <div style={{ display: "flex", gap: "6px", "flex-wrap": "wrap", "margin-bottom": "8px" }}>
              {[
                { name: "Divine Orb", chaos: 180 },
                { name: "Exalted Orb", chaos: 8 },
                { name: "Annulment Orb", chaos: 15 },
                { name: "Chaos Orb", chaos: 1 },
                { name: "Vaal Orb", chaos: 2 },
                { name: "Mirror Shard", chaos: 2000 },
              ].map((c) => (
                <button
                  style={{ "font-size": "12px", padding: "4px 10px" }}
                  onClick={() => addCurrencyDrop(c.name, c.chaos)}
                >
                  + {c.name}
                </button>
              ))}
            </div>
            <Show when={currencyDrops().length > 0}>
              <div style={{ display: "flex", "flex-direction": "column", gap: "2px", "margin-bottom": "8px" }}>
                <For each={currencyDrops()}>
                  {(d) => (
                    <div style={{ display: "flex", "justify-content": "space-between", "font-size": "13px", padding: "2px 0" }}>
                      <span style={{ color: "var(--accent)" }}>{d.name} x{d.count}</span>
                      <span style={{ color: "var(--text-muted)" }}>~{Math.round(d.count * d.chaosValue)}c</span>
                    </div>
                  )}
                </For>
                <div style={{ display: "flex", "justify-content": "space-between", "font-size": "13px", "border-top": "1px solid var(--border)", "padding-top": "4px", "margin-top": "4px" }}>
                  <span style={{ "font-weight": "600" }}>Total</span>
                  <span style={{ color: "var(--accent)", "font-weight": "600" }}>
                    ~{Math.round(currencyDrops().reduce((s, d) => s + d.count * d.chaosValue, 0))}c
                  </span>
                </div>
              </div>
              <button style={{ "font-size": "12px", padding: "4px 10px" }} onClick={clearCurrencyDrops}>
                Clear Session Drops
              </button>
            </Show>
          </div>

          {/* Boss Kill Sound */}
          <div class="stream-section">
            <div class="stream-section-title">
              Boss Kill Sound
              <label class="stream-death-toggle">
                <input
                  type="checkbox"
                  checked={bossKillSoundEnabled()}
                  onChange={(e) => setBossKillSoundEnabled(e.currentTarget.checked)}
                />
                <span>{bossKillSoundEnabled() ? "On" : "Off"}</span>
              </label>
            </div>
            <Show when={bossKillSoundEnabled()}>
              <div class="stream-field">
                <label>Sound File</label>
                <div class="stream-actions" style={{ gap: "8px" }}>
                  <input
                    type="text"
                    class="stream-input"
                    placeholder="C:\path\to\victory.mp3"
                    value={bossKillSoundPath()}
                    onInput={(e) => setBossKillSoundPath(e.currentTarget.value)}
                    style={{ flex: "1" }}
                  />
                  <button
                    class="btn-secondary"
                    onClick={async () => {
                      try {
                        const { open } = await import("@tauri-apps/plugin-dialog");
                        const file = await open({
                          filters: [{ name: "Audio", extensions: ["mp3", "wav", "ogg", "m4a", "flac"] }],
                          multiple: false,
                        });
                        if (file) setBossKillSoundPath(file as string);
                      } catch {
                        // dialog plugin not available, user can type path
                      }
                    }}
                  >
                    Browse
                  </button>
                  <Show when={bossKillSoundPath()}>
                    <button
                      class="btn-secondary"
                      onClick={() => {
                        const audio = new Audio("asset://localhost/" + bossKillSoundPath().replace(/\\/g, "/"));
                        audio.volume = 0.5;
                        audio.play().catch(() => {});
                      }}
                    >
                      Test
                    </button>
                  </Show>
                </div>
                <p class="stream-hint">
                  Plays on the overlay when a boss is killed. Choose any .mp3, .wav, or .ogg file.
                </p>
              </div>
            </Show>
          </div>

          {/* Command Toggles */}
          <div class="stream-section">
            <div class="stream-section-title">Chat Commands</div>
            <div class="stream-command-grid">
              <For each={getCommandNames()}>
                {(cmd) => (
                  <label class="stream-command-toggle">
                    <input
                      type="checkbox"
                      checked={commandStates()[cmd] !== false}
                      onChange={() => handleToggleCommand(cmd)}
                    />
                    <span class="stream-command-name">!{cmd}</span>
                  </label>
                )}
              </For>
            </div>
          </div>

          {/* Session Stats */}
          <div class="stream-section">
            <div class="stream-section-title">Session</div>
            <div class="stream-session-stats">
              <div class="stream-stat">
                <span class="stream-stat-label">Status</span>
                <span class="stream-stat-value">{connectionStatus()}</span>
              </div>
              <div class="stream-stat">
                <span class="stream-stat-label">Uptime</span>
                <span class="stream-stat-value">{formatUptime()}</span>
              </div>
              <div class="stream-stat">
                <span class="stream-stat-label">Commands</span>
                <span class="stream-stat-value">{commandsHandled()}</span>
              </div>
            </div>
          </div>

        </div>

        {/* Right: Activity Feed */}
        <div class="streaming-right">
          {/* Viewer Suggestions */}
          <Show when={viewerSuggestions().length > 0}>
            <div class="stream-section">
              <div class="stream-section-title">
                Viewer Suggestions ({viewerSuggestions().length})
              </div>
              <div class="stream-suggestions">
                <For each={viewerSuggestions()}>
                  {(s) => (
                    <div class="stream-suggestion-card">
                      <span class="stream-suggestion-user">{s.user}</span>
                      <span class="stream-suggestion-text">{s.text}</span>
                      <button
                        class="stream-suggestion-dismiss"
                        onClick={() => dismissSuggestion(s.timestamp)}
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                </For>
              </div>
            </div>
          </Show>

          {/* Chat Log */}
          <div class="stream-section stream-log-section">
            <div class="stream-section-title">
              Activity Log ({chatLog().length})
            </div>
            <div class="stream-log">
              <For each={[...chatLog()].reverse()}>
                {(entry) => (
                  <div class="stream-log-entry">
                    <span class="stream-log-time">
                      {formatTime(entry.timestamp)}
                    </span>
                    <span class="stream-log-user">{entry.user}</span>
                    <span class="stream-log-cmd">{entry.command}</span>
                    <div class="stream-log-response">{entry.response}</div>
                  </div>
                )}
              </For>
              <Show when={chatLog().length === 0}>
                <div class="panel-empty">
                  No commands yet. Connect to Twitch chat and viewers can use !build, !dps, etc.
                </div>
              </Show>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
