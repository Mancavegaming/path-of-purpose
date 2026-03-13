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
  logSnapshot,
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
  logWatcherStats,
  logWatcherOffset,
  logWatcherPath,
  updateLogWatcherStats,
  overlayShowDps, setOverlayShowDps,
  overlayShowDeathRecap, setOverlayShowDeathRecap,
  overlayShowMapStats, setOverlayShowMapStats,
  overlayShowTradeWhispers, setOverlayShowTradeWhispers,
  overlayShowBossBar, setOverlayShowBossBar,
  overlayShowBossTimer, setOverlayShowBossTimer,
  overlayShowSessionDash, setOverlayShowSessionDash,
  overlayShowGraceVerses, setOverlayShowGraceVerses,
  bossKillSoundPath, setBossKillSoundPath,
  bossKillSoundEnabled, setBossKillSoundEnabled,
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

  // Death recap polling
  const [deathRecapEnabled, setDeathRecapEnabled] = createSignal(false);
  const [logError, setLogError] = createSignal("");

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

  // Wire up command handler
  setCommandHandler((user, command, args) => {
    const response = handleCommand(user, command, args);
    if (response) {
      sendMessage(response);
    }
  });

  // Push overlay state on a 2-second timer
  let overlayTimer: ReturnType<typeof setInterval> | null = null;

  createEffect(() => {
    if (overlayRunning()) {
      overlayTimer = setInterval(async () => {
        try {
          await updateOverlayState(getOverlayPayload());
        } catch {
          // Overlay server may not be ready
        }
      }, 2000);
    } else {
      if (overlayTimer) {
        clearInterval(overlayTimer);
        overlayTimer = null;
      }
    }
  });

  // Death recap polling — read Client.txt every 5s from last offset
  let logTimer: ReturnType<typeof setInterval> | null = null;

  createEffect(() => {
    if (deathRecapEnabled()) {
      // Initial snapshot (full scan)
      pollLogSnapshot();
      logTimer = setInterval(pollLogSnapshot, 5000);
    } else {
      if (logTimer) {
        clearInterval(logTimer);
        logTimer = null;
      }
    }
  });

  async function pollLogSnapshot() {
    try {
      const offset = logWatcherOffset();
      const path = logWatcherPath() || undefined;
      const snap = await logSnapshot(path, offset || undefined);
      if (snap.error) {
        setLogError(snap.error);
      } else {
        setLogError("");
        updateLogWatcherStats(snap);
      }
    } catch (e) {
      setLogError(String(e));
    }
  }

  onCleanup(() => {
    if (overlayTimer) clearInterval(overlayTimer);
    if (logTimer) clearInterval(logTimer);
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
                <input type="checkbox" checked={overlayShowDeathRecap()} onChange={(e) => setOverlayShowDeathRecap(e.currentTarget.checked)} />
                <span class="stream-command-name">Death Recap</span>
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
            </div>
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

          {/* Death Recap / Log Watcher */}
          <div class="stream-section">
            <div class="stream-section-title">
              Death Recap
              <label class="stream-death-toggle">
                <input
                  type="checkbox"
                  checked={deathRecapEnabled()}
                  onChange={(e) => setDeathRecapEnabled(e.currentTarget.checked)}
                />
                <span>{deathRecapEnabled() ? "Tracking" : "Off"}</span>
              </label>
            </div>

            <Show when={logError()}>
              <div class="error-toast" style={{ "margin-bottom": "8px" }}>{logError()}</div>
            </Show>

            <Show when={deathRecapEnabled() && logWatcherPath()}>
              <p class="stream-hint" style={{ "margin-bottom": "4px" }}>
                Reading: {logWatcherPath()}
              </p>
            </Show>

            <Show
              when={deathRecapEnabled() && logWatcherStats()}
              fallback={
                <p class="stream-hint">
                  Enable to auto-detect and parse your PoE Client.txt log.
                  Shows deaths, map runs, and what killed you on the overlay.
                </p>
              }
            >
              {(() => {
                const stats = logWatcherStats()!;
                return (
                  <>
                    <div class="stream-session-stats" style={{ "margin-bottom": "12px" }}>
                      <div class="stream-stat">
                        <span class="stream-stat-label">Zone</span>
                        <span class="stream-stat-value">{stats.current_zone || "—"}</span>
                      </div>
                      <div class="stream-stat">
                        <span class="stream-stat-label">Maps</span>
                        <span class="stream-stat-value">{stats.maps_completed}</span>
                      </div>
                      <div class="stream-stat">
                        <span class="stream-stat-label">Deaths</span>
                        <span class="stream-stat-value" style={{ color: stats.total_deaths > 0 ? "#f87171" : undefined }}>
                          {stats.total_deaths}
                        </span>
                      </div>
                      <div class="stream-stat">
                        <span class="stream-stat-label">Levels</span>
                        <span class="stream-stat-value">{stats.levels_gained}</span>
                      </div>
                      <div class="stream-stat">
                        <span class="stream-stat-label">Maps/hr</span>
                        <span class="stream-stat-value">{stats.maps_per_hour.toFixed(1)}</span>
                      </div>
                      <div class="stream-stat">
                        <span class="stream-stat-label">Deaths/hr</span>
                        <span class="stream-stat-value" style={{ color: stats.deaths_per_hour > 2 ? "#f87171" : undefined }}>
                          {stats.deaths_per_hour.toFixed(1)}
                        </span>
                      </div>
                    </div>

                    {/* Current map info */}
                    <Show when={stats.current_map}>
                      {(map) => (
                        <div class="stream-death-map">
                          <div class="stream-death-map-header">
                            <span>{map().zone_name}</span>
                            <Show when={map().area_level}>
                              <span class="stream-death-level">Lv{map().area_level}</span>
                            </Show>
                            <span class="stream-death-duration">{map().duration}</span>
                            <Show when={map().deaths > 0}>
                              <span class="stream-death-count">{map().deaths} death{map().deaths !== 1 ? "s" : ""}</span>
                            </Show>
                          </div>
                          <Show when={map().death_recaps.length > 0}>
                            <div class="stream-death-recaps">
                              <For each={map().death_recaps}>
                                {(recap) => (
                                  <div class="stream-death-recap-entry">
                                    <span class="stream-death-skull">&#x1F480;</span>
                                    <span class="stream-death-killer">{recap.killer}</span>
                                    <span class="stream-death-time">{recap.timestamp}</span>
                                  </div>
                                )}
                              </For>
                            </div>
                          </Show>
                        </div>
                      )}
                    </Show>

                    {/* Last death */}
                    <Show when={stats.last_death && !stats.current_map}>
                      <div class="stream-death-last">
                        <span class="stream-death-skull">&#x1F480;</span>
                        Last death: <strong>{stats.last_death!.character}</strong> slain by{" "}
                        <strong style={{ color: "#f87171" }}>{stats.last_death!.killer}</strong>
                        {" "}in {stats.last_death!.zone}
                      </div>
                    </Show>
                  </>
                );
              })()}
            </Show>
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
