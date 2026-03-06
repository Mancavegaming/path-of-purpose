import { For, Show } from "solid-js";
import type { TradeListing } from "../lib/types";

interface TradeListingCardProps {
  listing: TradeListing;
  selected?: boolean;
  onSelect?: (listing: TradeListing) => void;
}

export default function TradeListingCard(props: TradeListingCardProps) {
  const l = () => props.listing;

  const displayName = () => l().item_name || l().type_line || "Unknown Item";

  const priceText = () => {
    const p = l().price;
    if (!p) return "No price";
    return `${p.amount} ${p.currency}`;
  };

  async function copyWhisper() {
    const whisper = l().whisper;
    if (whisper) {
      await navigator.clipboard.writeText(whisper);
    }
  }

  function handleCompare() {
    props.onSelect?.(l());
  }

  return (
    <div class={`trade-listing-card ${props.selected ? "trade-listing-selected" : ""}`}>
      <div class="trade-listing-header">
        <Show when={l().icon_url}>
          <img
            class="trade-listing-icon"
            src={l().icon_url}
            alt={displayName()}
            loading="lazy"
          />
        </Show>
        <div class="trade-listing-info">
          <div class="trade-listing-name">{displayName()}</div>
          <Show when={l().item_name && l().type_line}>
            <div class="trade-listing-base">{l().type_line}</div>
          </Show>
          <Show when={l().ilvl > 0}>
            <span class="trade-listing-ilvl">iLvl {l().ilvl}</span>
          </Show>
        </div>
        <div class="trade-price">{priceText()}</div>
      </div>

      <Show when={l().implicit_mods.length > 0 || l().explicit_mods.length > 0}>
        <ul class="mod-list">
          <For each={l().implicit_mods}>
            {(mod) => <li class="mod-implicit">{mod}</li>}
          </For>
          <For each={l().explicit_mods}>
            {(mod) => <li>{mod}</li>}
          </For>
          <For each={l().crafted_mods}>
            {(mod) => <li class="mod-crafted">{mod}</li>}
          </For>
        </ul>
      </Show>

      <div class="trade-listing-footer">
        <span class="trade-listing-account">{l().account_name}</span>
        <div class="trade-listing-actions">
          <Show when={props.onSelect}>
            <button
              class={`trade-compare-btn ${props.selected ? "trade-compare-active" : ""}`}
              onClick={handleCompare}
            >
              {props.selected ? "Comparing" : "Compare"}
            </button>
          </Show>
          <Show when={l().whisper}>
            <button class="trade-whisper-btn" onClick={copyWhisper}>
              Copy Whisper
            </button>
          </Show>
        </div>
      </div>
    </div>
  );
}
