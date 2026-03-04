import { For, Show } from "solid-js";
import type { Item } from "../lib/types";

interface ItemCardProps {
  item: Item;
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

  return (
    <div class="card">
      <div class="card-header">
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
