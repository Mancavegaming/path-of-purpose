import { createEffect, createMemo, createSignal, For, Show } from "solid-js";
import type { Build, Item, ItemMod, TradeListing, TradeSearchResult } from "../lib/types";
import { tradeSearch, batchCompareBuildDps } from "../lib/commands";
import TradeListingCard from "./TradeListingCard";

type SortMode = "price" | "dps" | "priority" | "stat";

interface TradePanelProps {
  selectedItem: Item | null;
  equippedItem?: Item | null;
  league: string;
  build?: Build | null;
  onListingSelect?: (listing: TradeListing | null) => void;
}

/** Compute max link group from PoB socket string (e.g. "R-R-R-R-B-G"). */
function getMaxLinks(sockets: string): number {
  if (!sockets) return 0;
  const groups = sockets.split(/\s+/);
  return Math.max(...groups.map((g) => {
    return g.split("").filter((c) => "RGBWAD".includes(c.toUpperCase())).length;
  }), 0);
}


/** Strip PoB internal tags from mod text. */
function cleanModText(text: string): string {
  let clean = text.replace(/\{[^}]*\}/g, "").trim();
  clean = clean.replace(/\((\d+)-(\d+)\)/g, (_m, _a, b) => b);
  return clean || text;
}

/** Check if a mod text matches a stat_priority keyword. */
function modMatchesPriority(modText: string, priorities: string[]): boolean {
  if (!priorities.length) return false;
  const lower = modText.toLowerCase();
  return priorities.some((p) => {
    const pl = p.toLowerCase();
    return lower.includes(pl) || pl.includes(lower)
      || (pl === "life" && lower.includes("life"))
      || (pl.includes("resistance") && lower.includes("resistance"))
      || (pl.includes("res") && lower.includes("resistance"))
      || (pl.includes("attack speed") && lower.includes("attack speed"))
      || (pl.includes("cast speed") && lower.includes("cast speed"))
      || (pl.includes("crit") && lower.includes("critical"))
      || (pl.includes("movement") && lower.includes("movement"))
      || (pl.includes("energy shield") && (lower.includes("energy shield") || lower.includes("es")))
      || (pl.includes("armour") && lower.includes("armour"))
      || (pl.includes("evasion") && lower.includes("evasion"))
      || (pl.includes("physical damage") && lower.includes("physical damage"))
      || (pl.includes("elemental damage") && lower.includes("elemental damage"))
      || (pl.includes("spell damage") && lower.includes("spell damage"));
  });
}

function countPriorityMatches(listing: TradeListing, priorities: string[]): number {
  if (!priorities.length) return 0;
  const allMods = [...listing.implicit_mods, ...listing.explicit_mods, ...listing.crafted_mods];
  return allMods.filter((m) => modMatchesPriority(m, priorities)).length;
}

function extractModValue(modText: string): number {
  const nums = modText.match(/[\d.]+/g);
  if (!nums) return 0;
  return Math.max(...nums.map(Number));
}

function normalizeMod(text: string): string {
  return text.toLowerCase().replace(/[\d.]+/g, "#").replace(/\s+/g, " ").trim();
}

function getStatValue(listing: TradeListing, statPattern: string): number {
  const patternNorm = normalizeMod(statPattern);
  const patternKeywords = patternNorm.replace(/#/g, "").replace(/\s+/g, " ").trim();
  const allMods = [...listing.implicit_mods, ...listing.explicit_mods, ...listing.crafted_mods];
  for (const mod of allMods) {
    const modNorm = normalizeMod(mod);
    const modKeywords = modNorm.replace(/#/g, "").replace(/\s+/g, " ").trim();
    if (
      modNorm === patternNorm
      || modKeywords === patternKeywords
      || (patternKeywords.length > 4 && modKeywords.includes(patternKeywords))
      || (modKeywords.length > 4 && patternKeywords.includes(modKeywords))
    ) {
      return extractModValue(mod);
    }
  }
  return 0;
}

interface StatFilter {
  mod: ItemMod;
  cleanText: string;
  enabled: boolean;
}

export default function TradePanel(props: TradePanelProps) {
  const [result, setResult] = createSignal<TradeSearchResult | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");
  const [selectedListingId, setSelectedListingId] = createSignal<string | null>(null);
  const [sortMode, setSortMode] = createSignal<SortMode>("price");
  const [focusStat, setFocusStat] = createSignal<string | null>(null);
  const [statFilters, setStatFilters] = createSignal<StatFilter[]>([]);
  const [hasSearched, setHasSearched] = createSignal(false);
  const [minLinks, setMinLinks] = createSignal(0);
  const [minSockets, setMinSockets] = createSignal(0);
  // Socket colour filters: {r, g, b, w} counts for sockets and links
  const [socketR, setSocketR] = createSignal(0);
  const [socketG, setSocketG] = createSignal(0);
  const [socketB, setSocketB] = createSignal(0);
  const [socketW, setSocketW] = createSignal(0);
  const [linkR, setLinkR] = createSignal(0);
  const [linkG, setLinkG] = createSignal(0);
  const [linkB, setLinkB] = createSignal(0);
  const [linkW, setLinkW] = createSignal(0);
  const [dpsEnriching, setDpsEnriching] = createSignal(false);

  /** Enrich listings with DPS deltas via batch calculation. */
  async function enrichListingsWithDps(listings: TradeListing[], item: Item) {
    const build = props.build;
    if (!build || listings.length === 0) return;

    setDpsEnriching(true);
    try {
      const listingData = listings.map((l) => ({
        item_name: l.item_name,
        type_line: l.type_line,
        ilvl: l.ilvl,
        rarity: "RARE",
        implicit_mods: l.implicit_mods,
        explicit_mods: l.explicit_mods,
        crafted_mods: l.crafted_mods,
      }));

      const resp = await batchCompareBuildDps(
        build as unknown as Record<string, unknown>,
        listingData,
        item.slot,
      );

      // Merge dps_change into listings
      setResult((prev) => {
        if (!prev) return prev;
        const updated = [...prev.listings];
        for (const r of resp.results) {
          if (r.listing_index < updated.length && r.dps_change != null) {
            updated[r.listing_index] = { ...updated[r.listing_index], dps_change: r.dps_change };
          }
        }
        return { ...prev, listings: updated };
      });
    } catch (e) {
      console.warn("DPS enrichment failed:", e);
    } finally {
      setDpsEnriching(false);
    }
  }

  /** Build stat filters from the selected item's mods. */
  function buildStatFilters(item: Item): StatFilter[] {
    const filters: StatFilter[] = [];
    for (const mod of item.implicits) {
      filters.push({ mod, cleanText: cleanModText(mod.text), enabled: true });
    }
    for (const mod of item.explicits) {
      filters.push({ mod, cleanText: cleanModText(mod.text), enabled: true });
    }
    return filters;
  }

  const sortedListings = createMemo(() => {
    const r = result();
    if (!r) return [];
    const listings = [...r.listings];
    const focus = focusStat();
    const mode = sortMode();

    if (focus && mode === "stat") {
      listings.sort((a, b) => {
        const va = getStatValue(a, focus);
        const vb = getStatValue(b, focus);
        if (va === 0 && vb === 0) return 0;
        if (va === 0) return 1;
        if (vb === 0) return -1;
        return vb - va;
      });
    } else if (mode === "dps") {
      listings.sort((a, b) => (b.dps_change ?? -Infinity) - (a.dps_change ?? -Infinity));
    } else if (mode === "priority") {
      const prios = props.selectedItem?.stat_priority ?? [];
      listings.sort((a, b) => countPriorityMatches(b, prios) - countPriorityMatches(a, prios));
    }
    return listings;
  });

  // When selected item changes, rebuild filters and auto-search
  createEffect(() => {
    const item = props.selectedItem;
    if (!item) {
      setResult(null);
      setSelectedListingId(null);
      setFocusStat(null);
      setSortMode("price");
      setStatFilters([]);
      setHasSearched(false);
      props.onListingSelect?.(null);
      return;
    }
    setSelectedListingId(null);
    setFocusStat(null);
    setSortMode("price");
    setHasSearched(false);
    props.onListingSelect?.(null);

    // Auto-detect socket/link requirements from the item
    const itemLinks = getMaxLinks(item.sockets);
    // Only auto-set link filter for items with 4+ links (meaningful filter)
    setMinLinks(itemLinks >= 4 ? itemLinks : 0);
    setMinSockets(0);
    // Reset colour filters on item change
    setSocketR(0); setSocketG(0); setSocketB(0); setSocketW(0);
    setLinkR(0); setLinkG(0); setLinkB(0); setLinkW(0);

    const filters = buildStatFilters(item);
    setStatFilters(filters);
    doSearch(item, filters, itemLinks >= 4 ? itemLinks : 0, 0);
  });

  /** Build socket colour filter object (only includes non-zero values). */
  function buildSocketColourFilter(): Record<string, Record<string, number>> | undefined {
    const sc: Record<string, number> = {};
    const lc: Record<string, number> = {};
    if (socketR() > 0) sc.r = socketR();
    if (socketG() > 0) sc.g = socketG();
    if (socketB() > 0) sc.b = socketB();
    if (socketW() > 0) sc.w = socketW();
    if (linkR() > 0) lc.r = linkR();
    if (linkG() > 0) lc.g = linkG();
    if (linkB() > 0) lc.b = linkB();
    if (linkW() > 0) lc.w = linkW();
    if (Object.keys(sc).length === 0 && Object.keys(lc).length === 0) return undefined;
    const result: Record<string, Record<string, number>> = {};
    if (Object.keys(sc).length > 0) result.sockets = sc;
    if (Object.keys(lc).length > 0) result.links = lc;
    return result;
  }

  async function doSearch(
    item: Item,
    filters?: StatFilter[],
    links?: number,
    sockets?: number,
  ) {
    setLoading(true);
    setError("");
    setResult(null);
    setHasSearched(true);
    try {
      const equipped = props.equippedItem ?? undefined;
      // Build list of enabled mod texts to send as the search filter
      const activeFilters = (filters ?? statFilters()).filter((f) => f.enabled);
      const enabledMods = activeFilters.map((f) => f.cleanText);
      const res = await tradeSearch(
        item,
        props.league,
        equipped,
        enabledMods,
        links ?? minLinks(),
        sockets ?? minSockets(),
        buildSocketColourFilter(),
      );
      setResult(res);
      // Auto-enrich with DPS deltas if build is available
      if (props.build && res.listings.length > 0 && item) {
        enrichListingsWithDps(res.listings, item);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  function handleSearchClick() {
    const item = props.selectedItem;
    if (!item) return;
    doSearch(item);
  }

  function toggleStatFilter(index: number) {
    setStatFilters((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], enabled: !next[index].enabled };
      return next;
    });
  }

  function handleStatClick(cleanText: string) {
    if (focusStat() === cleanText) {
      setFocusStat(null);
      setSortMode("price");
    } else {
      setFocusStat(cleanText);
      setSortMode("stat");
    }
  }

  function handleModClickFromListing(modText: string) {
    if (focusStat() === modText) {
      setFocusStat(null);
      setSortMode("price");
    } else {
      setFocusStat(modText);
      setSortMode("stat");
    }
  }

  function handleSortChange(mode: SortMode) {
    setSortMode(mode);
    if (mode !== "stat") {
      setFocusStat(null);
    }
  }

  function handleListingSelect(listing: TradeListing) {
    if (selectedListingId() === listing.id) {
      setSelectedListingId(null);
      props.onListingSelect?.(null);
    } else {
      setSelectedListingId(listing.id);
      props.onListingSelect?.(listing);
    }
  }

  function focusStatLabel(): string {
    const stat = focusStat();
    if (!stat) return "";
    return stat.replace(/[\d.]+/g, "#").trim();
  }

  const enabledCount = () => statFilters().filter((f) => f.enabled).length;
  const totalCount = () => statFilters().length;
  const noResults = () => hasSearched() && result() && sortedListings().length === 0 && !loading();

  return (
    <div class="trade-panel">
      <Show when={!props.selectedItem}>
        <div class="panel-empty">
          Click an item in the build to search for similar items on the trade site.
        </div>
      </Show>

      <Show when={props.selectedItem}>
        {/* Stat filter pills */}
        <Show when={statFilters().length > 0}>
          <div class="trade-filter-section">
            <div class="trade-filter-header">
              <span class="trade-filter-title">
                {props.selectedItem!.name || props.selectedItem!.base_type}
              </span>
              <span class="trade-filter-count">
                {enabledCount()}/{totalCount()} stats
              </span>
            </div>
            <div class="trade-filter-pills">
              <For each={statFilters()}>
                {(filter, i) => (
                  <div
                    class={`trade-filter-pill ${filter.enabled ? "pill-enabled" : "pill-disabled"} ${focusStat() === filter.cleanText ? "pill-sorting" : ""}`}
                  >
                    <label class="pill-checkbox" title="Include in search">
                      <input
                        type="checkbox"
                        checked={filter.enabled}
                        onChange={() => toggleStatFilter(i())}
                      />
                    </label>
                    <span
                      class="pill-text"
                      onClick={() => handleStatClick(filter.cleanText)}
                      title="Click to sort by highest value"
                    >
                      {filter.cleanText}
                    </span>
                    <Show when={focusStat() === filter.cleanText}>
                      <span class="pill-sort-indicator" title="Sorting by this stat">▲</span>
                    </Show>
                  </div>
                )}
              </For>
            </div>
            {/* Socket / Link filters */}
            <div class="trade-socket-section">
              <div class="trade-socket-row">
                <span class="trade-socket-row-label">Sockets</span>
                <div class="trade-socket-filters">
                  <div class="trade-socket-filter">
                    <label class="trade-socket-label">Min</label>
                    <select class="trade-socket-select" value={minSockets()} onChange={(e) => setMinSockets(Number(e.currentTarget.value))}>
                      <option value="0">-</option>
                      <option value="1">1</option><option value="2">2</option><option value="3">3</option>
                      <option value="4">4</option><option value="5">5</option><option value="6">6</option>
                    </select>
                  </div>
                  <div class="trade-socket-filter">
                    <span class="socket-dot-label" style={{ background: "#c44" }} />
                    <select class="trade-socket-select trade-socket-colour" value={socketR()} onChange={(e) => setSocketR(Number(e.currentTarget.value))}>
                      <option value="0">-</option>
                      <option value="1">1</option><option value="2">2</option><option value="3">3</option>
                      <option value="4">4</option><option value="5">5</option><option value="6">6</option>
                    </select>
                  </div>
                  <div class="trade-socket-filter">
                    <span class="socket-dot-label" style={{ background: "#4a4" }} />
                    <select class="trade-socket-select trade-socket-colour" value={socketG()} onChange={(e) => setSocketG(Number(e.currentTarget.value))}>
                      <option value="0">-</option>
                      <option value="1">1</option><option value="2">2</option><option value="3">3</option>
                      <option value="4">4</option><option value="5">5</option><option value="6">6</option>
                    </select>
                  </div>
                  <div class="trade-socket-filter">
                    <span class="socket-dot-label" style={{ background: "#46c" }} />
                    <select class="trade-socket-select trade-socket-colour" value={socketB()} onChange={(e) => setSocketB(Number(e.currentTarget.value))}>
                      <option value="0">-</option>
                      <option value="1">1</option><option value="2">2</option><option value="3">3</option>
                      <option value="4">4</option><option value="5">5</option><option value="6">6</option>
                    </select>
                  </div>
                  <div class="trade-socket-filter">
                    <span class="socket-dot-label" style={{ background: "#ccc" }} />
                    <select class="trade-socket-select trade-socket-colour" value={socketW()} onChange={(e) => setSocketW(Number(e.currentTarget.value))}>
                      <option value="0">-</option>
                      <option value="1">1</option><option value="2">2</option><option value="3">3</option>
                      <option value="4">4</option><option value="5">5</option><option value="6">6</option>
                    </select>
                  </div>
                </div>
              </div>
              <div class="trade-socket-row">
                <span class="trade-socket-row-label">Links</span>
                <div class="trade-socket-filters">
                  <div class="trade-socket-filter">
                    <label class="trade-socket-label">Min</label>
                    <select class="trade-socket-select" value={minLinks()} onChange={(e) => setMinLinks(Number(e.currentTarget.value))}>
                      <option value="0">-</option>
                      <option value="2">2</option><option value="3">3</option>
                      <option value="4">4</option><option value="5">5</option><option value="6">6</option>
                    </select>
                  </div>
                  <div class="trade-socket-filter">
                    <span class="socket-dot-label" style={{ background: "#c44" }} />
                    <select class="trade-socket-select trade-socket-colour" value={linkR()} onChange={(e) => setLinkR(Number(e.currentTarget.value))}>
                      <option value="0">-</option>
                      <option value="1">1</option><option value="2">2</option><option value="3">3</option>
                      <option value="4">4</option><option value="5">5</option><option value="6">6</option>
                    </select>
                  </div>
                  <div class="trade-socket-filter">
                    <span class="socket-dot-label" style={{ background: "#4a4" }} />
                    <select class="trade-socket-select trade-socket-colour" value={linkG()} onChange={(e) => setLinkG(Number(e.currentTarget.value))}>
                      <option value="0">-</option>
                      <option value="1">1</option><option value="2">2</option><option value="3">3</option>
                      <option value="4">4</option><option value="5">5</option><option value="6">6</option>
                    </select>
                  </div>
                  <div class="trade-socket-filter">
                    <span class="socket-dot-label" style={{ background: "#46c" }} />
                    <select class="trade-socket-select trade-socket-colour" value={linkB()} onChange={(e) => setLinkB(Number(e.currentTarget.value))}>
                      <option value="0">-</option>
                      <option value="1">1</option><option value="2">2</option><option value="3">3</option>
                      <option value="4">4</option><option value="5">5</option><option value="6">6</option>
                    </select>
                  </div>
                  <div class="trade-socket-filter">
                    <span class="socket-dot-label" style={{ background: "#ccc" }} />
                    <select class="trade-socket-select trade-socket-colour" value={linkW()} onChange={(e) => setLinkW(Number(e.currentTarget.value))}>
                      <option value="0">-</option>
                      <option value="1">1</option><option value="2">2</option><option value="3">3</option>
                      <option value="4">4</option><option value="5">5</option><option value="6">6</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            <div class="trade-filter-actions">
              <button
                class="trade-search-btn"
                onClick={handleSearchClick}
                disabled={loading()}
              >
                {loading() ? "Searching..." : "Search"}
              </button>
              <Show when={noResults()}>
                <span class="trade-filter-hint">
                  No results — try unchecking some stats or lowering socket requirements
                </span>
              </Show>
            </div>
          </div>
        </Show>

        {/* Results header */}
        <Show when={result() && sortedListings().length > 0}>
          <div class="trade-results-header">
            <span class="trade-results-count">
              {result()!.total} results
            </span>
            <select
              class="trade-sort-select"
              value={sortMode()}
              onChange={(e) => handleSortChange(e.currentTarget.value as SortMode)}
            >
              <option value="price">Sort: Price</option>
              <option value="dps">Sort: DPS Change</option>
              <option value="priority">Sort: Priority</option>
              <Show when={focusStat()}>
                <option value="stat">Sort: {focusStatLabel()}</option>
              </Show>
            </select>
            <a
              class="trade-site-link"
              href={result()!.trade_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open on Trade Site
            </a>
            <Show when={dpsEnriching()}>
              <span class="trade-dps-enriching"><span class="spinner" /> Calculating DPS...</span>
            </Show>
          </div>
        </Show>

        <Show when={focusStat() && sortedListings().length > 0}>
          <div class="trade-focus-banner">
            <span>Sorted by highest: <strong>{focusStatLabel()}</strong></span>
            <button class="trade-focus-clear" onClick={() => { setFocusStat(null); setSortMode("price"); }}>Clear</button>
          </div>
        </Show>
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

      <Show when={result() && result()!.relaxed_level > 0}>
        <div class="trade-relaxed-notice">
          <span class="trade-relaxed-icon">~</span>
          <span>Broadened search</span>
          <Show when={result()!.dropped_stats.length > 0}>
            <span class="trade-relaxed-details">
              {result()!.dropped_stats.join("; ")}
            </span>
          </Show>
        </div>
      </Show>

      <Show when={result() && sortedListings().length > 0}>
        <div class="trade-listings">
          <For each={sortedListings()}>
            {(listing) => {
              const statVal = () => {
                const focus = focusStat();
                return focus ? getStatValue(listing, focus) : 0;
              };
              return (
                <TradeListingCard
                  listing={listing}
                  selected={selectedListingId() === listing.id}
                  onSelect={handleListingSelect}
                  onModClick={handleModClickFromListing}
                  focusStat={focusStat()}
                  focusStatValue={statVal() > 0 ? statVal() : undefined}
                  priorities={props.selectedItem?.stat_priority ?? []}
                  priorityMatches={countPriorityMatches(listing, props.selectedItem?.stat_priority ?? [])}
                />
              );
            }}
          </For>
        </div>
      </Show>

      <Show when={noResults()}>
        <div class="panel-empty">
          No listings found. Try unchecking some stats above and searching again.
        </div>
      </Show>
    </div>
  );
}
