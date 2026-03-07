import { createSignal, For, Show } from "solid-js";
import type { Accessor, Setter } from "solid-js";
import type { SavedBuildEntry } from "../lib/commands";
import {
  user,
  isLoggedIn,
  isSubscribed,
  discordLogin,
  openCheckout,
  logoutUser,
  refreshUserStatus,
} from "../lib/auth";
import { check } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";

const DISCORD_CLIENT_ID = "1479135178650554510";

export type Page = "build" | "delta" | "generator";

interface SidebarProps {
  page: Accessor<Page>;
  setPage: Setter<Page>;
  savedBuilds: Accessor<SavedBuildEntry[]>;
  onLoadBuild: (name: string) => void;
  onDeleteBuild: (name: string) => void;
}

export default function Sidebar(props: SidebarProps) {
  const [updateStatus, setUpdateStatus] = createSignal("");
  const [updating, setUpdating] = createSignal(false);
  const [loginError, setLoginError] = createSignal<string | null>(null);

  async function handleCheckForUpdates() {
    setUpdating(true);
    setUpdateStatus("Checking...");
    try {
      const update = await check();
      if (update) {
        setUpdateStatus(`Downloading v${update.version}...`);
        let downloaded = 0;
        let total = 0;
        await update.downloadAndInstall((event) => {
          if (event.event === "Started" && event.data.contentLength) {
            total = event.data.contentLength;
          } else if (event.event === "Progress") {
            downloaded += event.data.chunkLength;
            if (total > 0) {
              const pct = Math.round((downloaded / total) * 100);
              setUpdateStatus(`Downloading... ${pct}%`);
            }
          } else if (event.event === "Finished") {
            setUpdateStatus("Restarting...");
          }
        });
        await relaunch();
      } else {
        setUpdateStatus("You're up to date!");
        setTimeout(() => setUpdateStatus(""), 3000);
      }
    } catch (e) {
      setUpdateStatus(`Update failed: ${String(e)}`);
      setTimeout(() => setUpdateStatus(""), 5000);
    } finally {
      setUpdating(false);
    }
  }

  function formatDate(iso: string): string {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      });
    } catch {
      return "";
    }
  }

  function avatarUrl(): string {
    const u = user();
    if (!u || !u.discord_avatar) return "";
    return `https://cdn.discordapp.com/avatars/${u.discord_id}/${u.discord_avatar}.png?size=64`;
  }

  async function handleLogin() {
    setLoginError(null);
    const error = await discordLogin(DISCORD_CLIENT_ID);
    if (error) {
      setLoginError(error);
    }
  }

  async function openDiscordInvite() {
    const { open } = await import("@tauri-apps/plugin-shell");
    await open("https://discord.gg/uSnAMzsTGP");
  }

  async function handleSubscribe() {
    await openCheckout();
  }

  async function handleRefresh() {
    await refreshUserStatus();
  }

  return (
    <aside class="sidebar">
      <div class="sidebar-brand">
        <h1>Path of Purpose</h1>
        <p>Build mentor for exiles</p>
      </div>
      <nav class="sidebar-nav">
        <button
          class={`nav-item ${props.page() === "build" ? "active" : ""}`}
          onClick={() => props.setPage("build")}
        >
          <span class="nav-icon">{"\u{1F4DC}"}</span>
          Build Viewer
        </button>
        <button
          class={`nav-item ${props.page() === "generator" ? "active" : ""}`}
          onClick={() => props.setPage("generator")}
        >
          <span class="nav-icon">{"\u{2728}"}</span>
          Build Generator
        </button>
        <button
          class={`nav-item ${props.page() === "delta" ? "active" : ""}`}
          onClick={() => props.setPage("delta")}
        >
          <span class="nav-icon">{"\u{1F50D}"}</span>
          Delta Report
        </button>
      </nav>

      <Show when={props.savedBuilds().length > 0}>
        <div class="saved-builds-section">
          <div class="saved-builds-title">Saved Builds</div>
          <div class="saved-builds-list">
            <For each={props.savedBuilds()}>
              {(entry) => (
                <div class="saved-build-item">
                  <button
                    class="saved-build-link"
                    onClick={() => props.onLoadBuild(entry.name)}
                    title={entry.name}
                  >
                    <span class="saved-build-name">{entry.name}</span>
                    <span class="saved-build-date">
                      {formatDate(entry.saved_at)}
                    </span>
                  </button>
                  <button
                    class="saved-build-delete"
                    onClick={(e) => {
                      e.stopPropagation();
                      props.onDeleteBuild(entry.name);
                    }}
                    title="Delete"
                  >
                    x
                  </button>
                </div>
              )}
            </For>
          </div>
        </div>
      </Show>

      {/* Update section */}
      <div class="sidebar-update-section">
        <button
          class="sidebar-update-btn"
          onClick={handleCheckForUpdates}
          disabled={updating()}
        >
          {updating() ? "Updating..." : "Check for Updates"}
        </button>
        <Show when={updateStatus()}>
          <span class="sidebar-update-status">{updateStatus()}</span>
        </Show>
      </div>

      {/* User section at bottom */}
      <div class="sidebar-user-section">
        <Show
          when={isLoggedIn()}
          fallback={
            <div class="sidebar-login-section">
              <button class="discord-login-btn sidebar-login" onClick={handleLogin}>
                Login with Discord
              </button>
              <Show when={loginError()}>
                <div class="login-error">
                  <Show
                    when={loginError() === "discord_not_member"}
                    fallback={<span class="login-error-text">Login failed: {loginError()}</span>}
                  >
                    <span class="login-error-text">
                      You must join the Path of Purpose Discord server first.
                    </span>
                    <button class="discord-join-btn" onClick={openDiscordInvite}>
                      Join Discord Server
                    </button>
                  </Show>
                </div>
              </Show>
            </div>
          }
        >
          <div class="sidebar-user-info">
            <Show when={avatarUrl()}>
              <img class="sidebar-avatar" src={avatarUrl()} alt="avatar" />
            </Show>
            <div class="sidebar-user-details">
              <span class="sidebar-username">{user()?.discord_username}</span>
              <span
                class="sidebar-sub-badge"
                classList={{
                  active: isSubscribed(),
                  inactive: !isSubscribed(),
                }}
              >
                {isSubscribed() ? "Subscribed" : "Free"}
              </span>
            </div>
          </div>
          <div class="sidebar-user-actions">
            <Show when={!isSubscribed()}>
              <button class="subscribe-btn sidebar-subscribe" onClick={handleSubscribe}>
                Subscribe — $4.99/mo
              </button>
              <button class="refresh-status-btn" onClick={handleRefresh}>
                Refresh status
              </button>
            </Show>
            <button class="sidebar-logout-btn" onClick={logoutUser}>
              Logout
            </button>
          </div>
        </Show>
      </div>
    </aside>
  );
}
