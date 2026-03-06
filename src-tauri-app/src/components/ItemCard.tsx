import { For, Show } from "solid-js";
import type { Item } from "../lib/types";

interface ItemCardProps {
  item: Item;
  onClick?: (item: Item) => void;
  selected?: boolean;
}

export default function ItemCard(props: ItemCardProps) {
  const item = () => props.item;

  const rarityClass = () => {
    const r = item().rarity.toLowerCase();
    if (r === "unique") return "rarity-unique";
    if (r === "rare") return "rarity-rare";
    if (r === "magic") return "rarity-magic";
    return "rarity-normal";
  };

  const cardClass = () => {
    let cls = "card";
    if (props.onClick) cls += " item-selectable";
    if (props.selected) cls += " item-selected";
    return cls;
  };

  return (
    <div class={cardClass()} onClick={() => props.onClick?.(item())}>
      <div class="card-header">
        <Show when={item().icon_url}>
          <img
            class="item-card-icon"
            src={item().icon_url}
            alt={item().name || item().base_type}
            loading="lazy"
          />
        </Show>
        <div>
          <span class={`item-name ${rarityClass()}`}>
            {item().name || item().base_type}
          </span>
          <Show when={item().name && item().base_type}>
            <div class="item-base">{item().base_type}</div>
          </Show>
        </div>
        <Show when={item().slot}>
          <span class="build-meta">{item().slot}</span>
        </Show>
      </div>

      <Show when={item().stat_priority && item().stat_priority!.length > 0}>
        <div class="item-stat-tags">
          <For each={item().stat_priority!}>
            {(stat) => <span class="item-stat-tag">{stat}</span>}
          </For>
        </div>
      </Show>

      <Show when={item().notes}>
        <div class="item-notes">{item().notes}</div>
      </Show>

      <Show when={item().implicits.length > 0 || item().explicits.length > 0}>
        <ul class="mod-list">
          <For each={item().implicits}>
            {(mod) => <li class="mod-implicit">{mod.text}</li>}
          </For>
          <For each={item().explicits}>
            {(mod) => (
              <li class={mod.is_crafted ? "mod-crafted" : ""}>
                {mod.text}
              </li>
            )}
          </For>
        </ul>
      </Show>
    </div>
  );
}
