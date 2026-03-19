/**
 * Price Check Store — persisted settings for the price check overlay.
 *
 * Settings are saved to app data directory as JSON and loaded on startup.
 */
import { createSignal } from "solid-js";
import { invoke } from "@tauri-apps/api/core";

export interface PriceCheckSettings {
  hotkey: string;
  league: string;
  maxListings: number;
  overlayOpacity: number;
  overlayAutoDismiss: number; // seconds, 0 = off
  overlayPosition: "cursor" | "top-left" | "top-right";
  deathRecapEnabled: boolean;
  deathRecapDismiss: number; // seconds, 0 = off
  showGraceVerses: boolean;
}

const DEFAULT_SETTINGS: PriceCheckSettings = {
  hotkey: "Alt+D",
  league: "Standard",
  maxListings: 8,
  overlayOpacity: 94,
  overlayAutoDismiss: 0,
  overlayPosition: "cursor",
  deathRecapEnabled: false,
  deathRecapDismiss: 10,
  showGraceVerses: true,
};

const [settings, setSettingsSignal] = createSignal<PriceCheckSettings>({ ...DEFAULT_SETTINGS });
const [settingsLoaded, setSettingsLoaded] = createSignal(false);

export { settings, settingsLoaded };

export async function loadPriceCheckSettings(): Promise<void> {
  try {
    const result = await invoke<PriceCheckSettings | null>("load_price_check_settings");
    if (result) {
      setSettingsSignal({ ...DEFAULT_SETTINGS, ...result });
    }
    setSettingsLoaded(true);
  } catch {
    setSettingsLoaded(true);
  }
}

export async function savePriceCheckSettings(newSettings: Partial<PriceCheckSettings>): Promise<void> {
  const merged = { ...settings(), ...newSettings };
  setSettingsSignal(merged);
  try {
    await invoke("save_price_check_settings", { settings: merged });
  } catch (e) {
    console.error("Failed to save price check settings:", e);
  }
}

export function updateSetting<K extends keyof PriceCheckSettings>(
  key: K,
  value: PriceCheckSettings[K],
): void {
  savePriceCheckSettings({ [key]: value });
}
