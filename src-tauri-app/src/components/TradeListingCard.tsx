import { For, Show } from "solid-js";
import type { TradeListing, TradeSocket } from "../lib/types";

/** Colour map for socket display. */
const SOCKET_COLOURS: Record<string, string> = {
  R: "#c44", G: "#4a4", B: "#46c", W: "#ccc", A: "#b8b8b8", D: "#666",
};

/** Group sockets by link group and render as colored dots. */
function SocketDisplay(props: { sockets: TradeSocket[] }) {
  const groups = () => {
    const map = new Map<number, TradeSocket[]>();
    for (const s of props.sockets) {
      const g = map.get(s.group) || [];
      g.push(s);
      map.set(s.group, g);
    }
    return Array.from(map.values());
  };

  return (
    <div class="trade-sockets">
      <For each={groups()}>
        {(group, gi) => (
          <>
            <Show when={gi() > 0}>
              <span class="socket-gap" />
            </Show>
            <For each={group}>
              {(s, si) => (
                <>
                  <Show when={si() > 0}>
                    <span class="socket-link">-</span>
                  </Show>
                  <span
                    class="socket-dot"
                    style={{ background: SOCKET_COLOURS[s.colour] || "#888" }}
                    title={s.colour}
                  />
                </>
              )}
            </For>
          </>
        )}
      </For>
    </div>
  );
}

interface TradeListingCardProps {
  listing: TradeListing;
  selected?: boolean;
  onSelect?: (listing: TradeListing) => void;
  onModClick?: (modText: string) => void;
  focusStat?: string | null;
  focusStatValue?: number;
  priorities?: string[];
  priorityMatches?: number;
}

/** Check if a mod text matches any of the given stat_priority keywords. */
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

/** Check if a mod line is the currently focused stat. */
function isModFocused(modText: string, focusStat: string | null | undefined): boolean {
  if (!focusStat) return false;
  return modText.toLowerCase().includes(focusStat.toLowerCase().replace(/[+\-\d.%]+/g, "").trim())
    || focusStat.toLowerCase().includes(modText.toLowerCase().replace(/[+\-\d.%]+/g, "").trim());
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

  function handleModClick(e: MouseEvent, modText: string) {
    e.stopPropagation();
    props.onModClick?.(modText);
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
          <Show when={l().sockets && l().sockets.length > 0}>
            <SocketDisplay sockets={l().sockets} />
          </Show>
        </div>
        <div class="trade-price-dps">
          <div class="trade-price">{priceText()}</div>
          <Show when={l().dps_change != null}>
            <div class={`trade-dps-change ${l().dps_change! > 0 ? "dps-up" : l().dps_change! < 0 ? "dps-down" : ""}`}>
              {l().dps_change! > 0 ? "+" : ""}{typeof l().dps_change === "number" && Math.abs(l().dps_change!) < 100
                ? `${l().dps_change!.toFixed(1)}% DPS`
                : `${l().dps_change! > 0 ? "+" : ""}${l().dps_change!.toFixed(0)} DPS`}
            </div>
          </Show>
        </div>
      </div>

      <Show when={props.focusStatValue}>
        <div class="trade-focus-value-badge">
          {props.focusStatValue}
        </div>
      </Show>

      <Show when={(props.priorityMatches ?? 0) > 0}>
        <div class="trade-priority-badge">
          {props.priorityMatches}/{props.priorities!.length} priority mods
        </div>
      </Show>

      <Show when={l().implicit_mods.length > 0 || l().explicit_mods.length > 0}>
        <ul class="mod-list">
          <For each={l().implicit_mods}>
            {(mod) => (
              <li
                class={`mod-implicit mod-clickable ${(props.priorities?.length && modMatchesPriority(mod, props.priorities!)) ? "mod-priority" : ""} ${isModFocused(mod, props.focusStat) ? "mod-focused" : ""}`}
                onClick={(e) => handleModClick(e, mod)}
                title="Click to search for highest value of this stat"
              >
                {mod}
              </li>
            )}
          </For>
          <For each={l().explicit_mods}>
            {(mod) => (
              <li
                class={`mod-clickable ${(props.priorities?.length && modMatchesPriority(mod, props.priorities!)) ? "mod-priority" : ""} ${isModFocused(mod, props.focusStat) ? "mod-focused" : ""}`}
                onClick={(e) => handleModClick(e, mod)}
                title="Click to search for highest value of this stat"
              >
                {mod}
              </li>
            )}
          </For>
          <For each={l().crafted_mods}>
            {(mod) => (
              <li
                class={`mod-crafted mod-clickable ${(props.priorities?.length && modMatchesPriority(mod, props.priorities!)) ? "mod-priority" : ""} ${isModFocused(mod, props.focusStat) ? "mod-focused" : ""}`}
                onClick={(e) => handleModClick(e, mod)}
                title="Click to search for highest value of this stat"
              >
                {mod}
              </li>
            )}
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
