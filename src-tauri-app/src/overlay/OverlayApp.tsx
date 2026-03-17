import { createSignal, onMount, onCleanup, Show } from "solid-js";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import PriceCheckPanel from "./PriceCheckPanel";
import DeathRecapToast from "./DeathRecapToast";
import type { PriceCheckResult, DeathAnalysis } from "../lib/types";

/** Hide the overlay at the OS level — window becomes invisible and click-through. */
async function dismissOverlay() {
  try {
    await invoke("hide_overlay");
  } catch {
    // fallback: at least the content is hidden via signals
  }
}

export default function OverlayApp() {
  const [priceResult, setPriceResult] = createSignal<PriceCheckResult | null>(null);
  const [deathRecap, setDeathRecap] = createSignal<DeathAnalysis | null>(null);
  const [showPrice, setShowPrice] = createSignal(false);
  const [showDeath, setShowDeath] = createSignal(false);

  function closePrice() {
    setShowPrice(false);
    // If nothing else is shown, fully hide the window
    if (!showDeath()) {
      dismissOverlay();
    }
  }

  function closeDeath() {
    setShowDeath(false);
    // If nothing else is shown, fully hide the window
    if (!showPrice()) {
      dismissOverlay();
    }
  }

  function closeAll() {
    setShowPrice(false);
    setShowDeath(false);
    dismissOverlay();
  }

  const unlisteners: UnlistenFn[] = [];

  onMount(async () => {
    // Listen for price check results from main window
    unlisteners.push(
      await listen<PriceCheckResult>("price-check-result", (event) => {
        setPriceResult(event.payload);
        setShowPrice(true);
      })
    );

    // Listen for death recap events
    unlisteners.push(
      await listen<DeathAnalysis>("death-recap", (event) => {
        setDeathRecap(event.payload);
        setShowDeath(true);
        // Auto-dismiss after 10 seconds
        setTimeout(() => closeDeath(), 10000);
      })
    );

    // Listen for hide-overlay event
    unlisteners.push(
      await listen("hide-overlay", () => {
        closeAll();
      })
    );

    // Escape key hides overlay
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        closeAll();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    unlisteners.push(() => document.removeEventListener("keydown", handleKeyDown));
  });

  onCleanup(() => {
    for (const unlisten of unlisteners) {
      unlisten();
    }
  });

  return (
    <div class="overlay-root">
      <Show when={showPrice() && priceResult()}>
        <PriceCheckPanel
          result={priceResult()!}
          onClose={closePrice}
        />
      </Show>
      <Show when={showDeath() && deathRecap()}>
        <DeathRecapToast
          analysis={deathRecap()!}
          onDismiss={closeDeath}
        />
      </Show>
    </div>
  );
}
