import { createEffect, createSignal, For, Show } from "solid-js";
import type { Item, TradeListing, TradeSearchResult } from "../lib/types";
import { tradeSearch } from "../lib/commands";
import TradeListingCard from "./TradeListingCard";

interface TradePanelProps {
  selectedItem: Item | null;
  league: string;
  onListingSelect?: (listing: TradeListing | null) => void;
}

export default function TradePanel(props: TradePanelProps) {
  const [result, setResult] = createSignal<TradeSearchResult | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");
  const [selectedListingId, setSelectedListingId] = createSignal<string | null>(null);

  // Auto-search when selected item changes
  createEffect(() => {
    const item = props.selectedItem;
    if (!item) {
      setResult(null);
      setSelectedListingId(null);
      props.onListingSelect?.(null);
      return;
    }
    // Clear selection when item changes
    setSelectedListingId(null);
    props.onListingSelect?.(null);
    doSearch(item);
  });

  async function doSearch(item: Item) {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await tradeSearch(item, props.league);
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  function handleListingSelect(listing: TradeListing) {
    if (selectedListingId() === listing.id) {
      // Deselect
      setSelectedListingId(null);
      props.onListingSelect?.(null);
    } else {
      setSelectedListingId(listing.id);
      props.onListingSelect?.(listing);
    }
  }

  return (
    <div class="trade-panel">
      <Show when={!props.selectedItem}>
        <div class="panel-empty">
          Click an item in the build to search for similar items on the trade site.
        </div>
      </Show>

      <Show when={props.selectedItem}>
        <div class="trade-results-header">
          <span class="trade-search-item">
            {props.selectedItem!.name || props.selectedItem!.base_type}
          </span>
          <Show when={result()}>
            <span class="trade-results-count">
              {result()!.total} results
            </span>
            <a
              class="trade-site-link"
              href={result()!.trade_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open on Trade Site
            </a>
          </Show>
        </div>
      </Show>

      <Show when={loading()}>
        <div class="panel-loading">
          <span class="spinner" />
          Searching trade...
        </div>
      </Show>

      <Show when={error()}>
        <div class="error-toast">{error()}</div>
      </Show>

      <Show when={result() && result()!.listings.length > 0}>
        <div class="trade-listings">
          <For each={result()!.listings}>
            {(listing) => (
              <TradeListingCard
                listing={listing}
                selected={selectedListingId() === listing.id}
                onSelect={handleListingSelect}
              />
            )}
          </For>
        </div>
      </Show>

      <Show when={result() && result()!.listings.length === 0 && !loading()}>
        <div class="panel-empty">No listings found for this item.</div>
      </Show>
    </div>
  );
}
