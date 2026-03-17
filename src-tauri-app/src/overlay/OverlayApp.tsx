import { createSignal, onMount, onCleanup, Show } from "solid-js";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import PriceCheckPanel from "./PriceCheckPanel";
import DeathRecapToast from "./DeathRecapToast";
import type { PriceCheckResult, DeathAnalysis } from "../lib/types";

export default function OverlayApp() {
  const [priceResult, setPriceResult] = createSignal<PriceCheckResult | null>(null);
  const [deathRecap, setDeathRecap] = createSignal<DeathAnalysis | null>(null);
  const [showPrice, setShowPrice] = createSignal(false);
  const [showDeath, setShowDeath] = createSignal(false);

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
        setTimeout(() => setShowDeath(false), 10000);
      })
    );

    // Listen for hide-overlay event
    unlisteners.push(
      await listen("hide-overlay", () => {
        setShowPrice(false);
        setShowDeath(false);
      })
    );

    // Escape key hides overlay
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setShowPrice(false);
        setShowDeath(false);
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
          onClose={() => setShowPrice(false)}
        />
      </Show>
      <Show when={showDeath() && deathRecap()}>
        <DeathRecapToast
          analysis={deathRecap()!}
          onDismiss={() => setShowDeath(false)}
        />
      </Show>
    </div>
  );
}
