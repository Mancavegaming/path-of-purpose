import { createSignal, onMount, onCleanup, Show } from "solid-js";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import PriceCheckPanel from "./PriceCheckPanel";
import type { PriceCheckResult } from "../lib/types";

interface OverlaySettings {
  maxListings: number;
  overlayOpacity: number;
  overlayAutoDismiss: number;
}

const DEFAULT_SETTINGS: OverlaySettings = {
  maxListings: 8,
  overlayOpacity: 94,
  overlayAutoDismiss: 0,
};

async function dismissOverlay() {
  try {
    await invoke("hide_overlay");
  } catch {
    // fallback
  }
}

export default function OverlayApp() {
  const [priceResult, setPriceResult] = createSignal<PriceCheckResult | null>(null);
  const [showPrice, setShowPrice] = createSignal(false);
  const [settings, setSettings] = createSignal<OverlaySettings>(DEFAULT_SETTINGS);

  let priceTimer: ReturnType<typeof setTimeout> | null = null;

  async function loadSettings() {
    try {
      const result = await invoke<OverlaySettings | null>("load_price_check_settings");
      if (result) {
        setSettings({ ...DEFAULT_SETTINGS, ...result });
      }
    } catch {
      // use defaults
    }
  }

  function closePrice() {
    setShowPrice(false);
    if (priceTimer) { clearTimeout(priceTimer); priceTimer = null; }
    dismissOverlay();
  }

  function closeAll() {
    setShowPrice(false);
    if (priceTimer) { clearTimeout(priceTimer); priceTimer = null; }
    dismissOverlay();
  }

  const unlisteners: UnlistenFn[] = [];

  onMount(async () => {
    await loadSettings();

    unlisteners.push(
      await listen<PriceCheckResult>("price-check-result", async (event) => {
        await loadSettings(); // refresh settings each time
        setPriceResult(event.payload);
        setShowPrice(true);

        // Auto-dismiss timer for price check
        if (priceTimer) clearTimeout(priceTimer);
        const dismiss = settings().overlayAutoDismiss;
        if (dismiss > 0) {
          priceTimer = setTimeout(() => closePrice(), dismiss * 1000);
        }
      })
    );

    unlisteners.push(
      await listen("hide-overlay", () => closeAll())
    );

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeAll();
    };
    document.addEventListener("keydown", handleKeyDown);
    unlisteners.push(() => document.removeEventListener("keydown", handleKeyDown));
  });

  onCleanup(() => {
    for (const unlisten of unlisteners) unlisten();
  });

  const opacity = () => Math.max(0.2, settings().overlayOpacity / 100);

  return (
    <div class="overlay-root">
      <Show when={showPrice() && priceResult()}>
        <PriceCheckPanel
          result={priceResult()!}
          onClose={closePrice}
          maxListings={settings().maxListings}
          opacity={opacity()}
        />
      </Show>
    </div>
  );
}
