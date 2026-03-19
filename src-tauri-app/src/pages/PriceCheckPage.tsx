import { createSignal, onMount, For } from "solid-js";
import {
  settings,
  updateSetting,
  loadPriceCheckSettings,
  settingsLoaded,
} from "../lib/priceCheckStore";
import { fetchLeagues } from "../lib/commands";

export default function PriceCheckPage() {
  const [leagues, setLeagues] = createSignal<string[]>(["Standard"]);
  const [leagueLoading, setLeagueLoading] = createSignal(false);

  onMount(async () => {
    if (!settingsLoaded()) {
      await loadPriceCheckSettings();
    }
    // Fetch available leagues
    setLeagueLoading(true);
    try {
      const result = await fetchLeagues();
      if (result.length > 0) {
        setLeagues(result);
      }
    } catch {
      // Keep default
    } finally {
      setLeagueLoading(false);
    }
  });

  return (
    <div class="page-content">
      <h2 class="page-title">Price Check Settings</h2>
      <p class="page-subtitle">
        Hover over an item in PoE and press the hotkey to price check without alt-tabbing.
      </p>

      {/* Hotkey */}
      <section class="settings-section">
        <h3 class="settings-heading">Hotkey</h3>
        <div class="settings-row">
          <label class="settings-label">Price check trigger</label>
          <span style={{ color: "#e8c56d", "font-weight": "bold", "font-size": "0.95rem" }}>Alt + D</span>
        </div>
        <div class="settings-hint">
          Press this key while hovering an item in PoE (borderless windowed mode).
        </div>
      </section>

      {/* Trade Search */}
      <section class="settings-section">
        <h3 class="settings-heading">Trade Search</h3>
        <div class="settings-row">
          <label class="settings-label">League</label>
          <select
            class="settings-select"
            value={settings().league}
            onChange={(e) => updateSetting("league", e.currentTarget.value)}
            disabled={leagueLoading()}
          >
            <For each={leagues()}>
              {(league) => <option value={league}>{league}</option>}
            </For>
          </select>
        </div>
        <div class="settings-row">
          <label class="settings-label">Max listings shown</label>
          <select
            class="settings-select"
            value={settings().maxListings}
            onChange={(e) => updateSetting("maxListings", parseInt(e.currentTarget.value))}
          >
            <option value="5">5</option>
            <option value="8">8</option>
            <option value="10">10</option>
            <option value="15">15</option>
          </select>
        </div>
      </section>

      {/* Overlay Behavior */}
      <section class="settings-section">
        <h3 class="settings-heading">Overlay Behavior</h3>
        <div class="settings-row">
          <label class="settings-label">
            Overlay opacity: {settings().overlayOpacity}%
          </label>
          <input
            type="range"
            class="settings-range"
            min="50"
            max="100"
            step="5"
            value={settings().overlayOpacity}
            onInput={(e) => updateSetting("overlayOpacity", parseInt(e.currentTarget.value))}
          />
        </div>
        <div class="settings-row">
          <label class="settings-label">Auto-dismiss (seconds)</label>
          <select
            class="settings-select"
            value={settings().overlayAutoDismiss}
            onChange={(e) => updateSetting("overlayAutoDismiss", parseInt(e.currentTarget.value))}
          >
            <option value="0">Off (manual close)</option>
            <option value="15">15 seconds</option>
            <option value="30">30 seconds</option>
            <option value="60">60 seconds</option>
          </select>
        </div>
        <div class="settings-row">
          <label class="settings-label">Position</label>
          <select
            class="settings-select"
            value={settings().overlayPosition}
            onChange={(e) => updateSetting("overlayPosition", e.currentTarget.value as "cursor" | "top-left" | "top-right")}
          >
            <option value="cursor">Follow cursor</option>
            <option value="top-left">Fixed — Top Left</option>
            <option value="top-right">Fixed — Top Right</option>
          </select>
        </div>
      </section>

      {/* Death Recap */}
      <section class="settings-section">
        <h3 class="settings-heading">Death Recap</h3>
        <div class="settings-row">
          <label class="settings-label">Enable death recap overlay</label>
          <label class="settings-toggle">
            <input
              type="checkbox"
              checked={settings().deathRecapEnabled}
              onChange={(e) => updateSetting("deathRecapEnabled", e.currentTarget.checked)}
            />
            <span class="toggle-slider" />
          </label>
        </div>
        <div class="settings-row">
          <label class="settings-label">Auto-dismiss (seconds)</label>
          <select
            class="settings-select"
            value={settings().deathRecapDismiss}
            onChange={(e) => updateSetting("deathRecapDismiss", parseInt(e.currentTarget.value))}
            disabled={!settings().deathRecapEnabled}
          >
            <option value="0">Off (manual close)</option>
            <option value="5">5 seconds</option>
            <option value="10">10 seconds</option>
            <option value="15">15 seconds</option>
          </select>
        </div>
        <div class="settings-row">
          <label class="settings-label">Show grace verses on death</label>
          <label class="settings-toggle">
            <input
              type="checkbox"
              checked={settings().showGraceVerses}
              onChange={(e) => updateSetting("showGraceVerses", e.currentTarget.checked)}
            />
            <span class="toggle-slider" />
          </label>
        </div>
      </section>
    </div>
  );
}
