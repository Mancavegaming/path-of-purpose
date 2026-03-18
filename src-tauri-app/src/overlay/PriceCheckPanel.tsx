import { createSignal, For, Show } from "solid-js";
import { invoke } from "@tauri-apps/api/core";
import type { PriceCheckResult } from "../lib/types";

interface Props {
  result: PriceCheckResult;
  onClose: () => void;
  maxListings: number;
  opacity: number;
}

const RARITY_COLORS: Record<string, string> = {
  Normal: "#c8c8c8",
  Magic: "#8888ff",
  Rare: "#ffd700",
  Unique: "#af6025",
  Gem: "#1ba29b",
  Currency: "#aa9e82",
};

export default function PriceCheckPanel(props: Props) {
  const [modToggles, setModToggles] = createSignal<boolean[]>([]);
  const [loading, setLoading] = createSignal(false);
  const [result, setResult] = createSignal(props.result);

  const item = () => result().item;
  const allMods = () => [...(item()?.explicits || []), ...(item()?.crafted_mods || [])];

  if (modToggles().length === 0 && allMods().length > 0) {
    setModToggles(allMods().map(() => true));
  }

  async function handleModToggle(index: number) {
    const current = [...modToggles()];
    current[index] = !current[index];
    setModToggles(current);

    const enabledIndices = current
      .map((enabled, i) => (enabled ? i : -1))
      .filter((i) => i >= 0);

    setLoading(true);
    try {
      const newResult = await invoke<PriceCheckResult>("price_check_refine", {
        clipboardText: result().clipboard_text,
        league: "Standard",
        enabledModIndices: enabledIndices,
      });
      setResult(newResult);
    } catch (e) {
      console.error("Price check refine failed:", e);
    } finally {
      setLoading(false);
    }
  }

  const summary = () => result().price_summary;
  const listings = () => result().results?.listings || [];
  const rarityColor = () => RARITY_COLORS[item()?.rarity || "Normal"] || "#c8c8c8";

  return (
    <div
      class="price-panel"
      style={{ opacity: props.opacity }}
      onClick={(e) => e.stopPropagation()}
    >
      <div class="price-header">
        <div class="price-item-name" style={{ color: rarityColor() }}>
          {item()?.name || item()?.base_type || "Unknown Item"}
        </div>
        <Show when={item()?.name && item()?.base_type && item()?.name !== item()?.base_type}>
          <div class="price-base-type">{item()?.base_type}</div>
        </Show>
        <Show when={item()?.ilvl}>
          <div class="price-ilvl">ilvl {item()?.ilvl}</div>
        </Show>
        <button class="price-close" onClick={props.onClose}>x</button>
      </div>

      <Show when={summary()}>
        <div class="price-bar">
          <span class="price-min">{summary()!.min}</span>
          <span class="price-median">{summary()!.median}</span>
          <span class="price-max">{summary()!.max}</span>
          <span class="price-currency">{summary()!.currency}</span>
          <span class="price-count">({summary()!.count} listed)</span>
        </div>
      </Show>

      <Show when={result().error}>
        <div class="price-error">{result().error}</div>
      </Show>

      <Show when={allMods().length > 0 && item()?.rarity !== "Unique"}>
        <div class="price-mods">
          <div class="price-mods-header">Search Filters {loading() && "(searching...)"}</div>
          <For each={allMods()}>
            {(mod, i) => (
              <label class="price-mod-toggle">
                <input
                  type="checkbox"
                  checked={modToggles()[i()] ?? true}
                  onChange={() => handleModToggle(i())}
                />
                <span class={mod.endsWith("(crafted)") ? "crafted-mod" : ""}>
                  {mod}
                </span>
              </label>
            )}
          </For>
        </div>
      </Show>

      <Show when={listings().length > 0}>
        <div class="price-listings">
          <For each={listings().slice(0, props.maxListings)}>
            {(listing) => (
              <div class="price-listing">
                <span class="listing-price">
                  {listing.price?.amount} {listing.price?.currency}
                </span>
                <span class="listing-account">{listing.account_name}</span>
              </div>
            )}
          </For>
        </div>
      </Show>

      <Show when={result().results?.trade_url}>
        <a
          class="price-trade-link"
          href={result().results!.trade_url}
          target="_blank"
          rel="noopener"
        >
          Open on Trade Site
        </a>
      </Show>
    </div>
  );
}
