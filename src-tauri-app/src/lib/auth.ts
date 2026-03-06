/**
 * Auth state management — Discord login + subscription status.
 *
 * Stores JWT + user info via Tauri commands (persisted in app data dir).
 * Provides reactive signals for use across the app.
 */
import { createSignal } from "solid-js";
import { invoke } from "@tauri-apps/api/core";

export interface UserInfo {
  id: number;
  discord_id: string;
  discord_username: string;
  discord_avatar: string;
  subscription_status: string;
}

const [token, setToken] = createSignal<string | null>(null);
const [user, setUser] = createSignal<UserInfo | null>(null);

export { token, user };

export function isLoggedIn(): boolean {
  return !!token();
}

export function isSubscribed(): boolean {
  const u = user();
  return !!u && (u.subscription_status === "active" || u.subscription_status === "trialing");
}

/** Load stored token from disk on app start. */
export async function initAuth(): Promise<void> {
  try {
    const stored = await invoke<{ token: string | null; user: UserInfo | null }>("load_token");
    if (stored.token && stored.user) {
      setToken(stored.token);
      setUser(stored.user);
      // Refresh subscription status from server
      try {
        const fresh = await invoke<UserInfo>("get_user_status", { token: stored.token });
        setUser(fresh);
        // Re-persist with updated user info
        await invoke("store_token", { token: stored.token, user: fresh });
      } catch {
        // Server unreachable — use cached data
      }
    }
  } catch {
    // No stored token
  }
}

/** Start the Discord login flow. Returns true on success. */
export async function discordLogin(clientId: string): Promise<boolean> {
  try {
    // Get the auth URL
    const authUrl = await invoke<string>("get_discord_auth_url", { clientId });

    // Start listening BEFORE opening the browser so we don't miss the callback
    const codePromise = invoke<string>("listen_for_oauth_callback");

    // Open browser (use shell plugin)
    const { open } = await import("@tauri-apps/plugin-shell");
    await open(authUrl);

    // Wait for the callback
    const code = await codePromise;

    // Exchange code for JWT
    const result = await invoke<{ access_token: string; user: UserInfo }>(
      "exchange_discord_code",
      { code }
    );

    setToken(result.access_token);
    setUser(result.user);

    // Persist
    const app = await import("@tauri-apps/api/core");
    await app.invoke("store_token", {
      token: result.access_token,
      user: result.user,
    });

    return true;
  } catch (e) {
    console.error("Discord login failed:", e);
    return false;
  }
}

/** Logout: clear stored token and signals. */
export async function logoutUser(): Promise<void> {
  await invoke("logout");
  setToken(null);
  setUser(null);
}

/** Open Stripe checkout for subscription, then poll for activation. */
export async function openCheckout(): Promise<void> {
  const t = token();
  if (!t) throw new Error("Not logged in");

  const url = await invoke<string>("open_checkout", { token: t });
  const { open } = await import("@tauri-apps/plugin-shell");
  await open(url);

  // Poll for subscription activation after checkout opens
  pollForSubscription();
}

/** Poll the server every 5s for up to 5 minutes to detect subscription activation. */
function pollForSubscription(): void {
  let attempts = 0;
  const maxAttempts = 60; // 5 minutes
  const interval = setInterval(async () => {
    attempts++;
    if (attempts >= maxAttempts || isSubscribed()) {
      clearInterval(interval);
      return;
    }
    try {
      await refreshUserStatus();
      if (isSubscribed()) {
        clearInterval(interval);
      }
    } catch {
      // Server unreachable, keep trying
    }
  }, 5000);
}

/** Refresh user status from server (e.g., after payment). */
export async function refreshUserStatus(): Promise<void> {
  const t = token();
  if (!t) return;

  const fresh = await invoke<UserInfo>("get_user_status", { token: t });
  setUser(fresh);
  await invoke("store_token", { token: t, user: fresh });
}
