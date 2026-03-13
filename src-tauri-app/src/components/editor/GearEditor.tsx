import { createMemo, For, Show } from "solid-js";
import type { Item } from "../../lib/types";
import ItemEditorCard from "./ItemEditorCard";

interface GearEditorProps {
  items: Item[];
  onUpdate: (items: Item[]) => void;
  nextId: () => number;
}

const SLOT_CATEGORIES: { label: string; slots: string[] }[] = [
  { label: "Weapons", slots: ["Weapon 1", "Weapon 2"] },
  { label: "Armour", slots: ["Helmet", "Body Armour", "Gloves", "Boots"] },
  { label: "Jewelry", slots: ["Amulet", "Ring 1", "Ring 2", "Belt"] },
  { label: "Flasks", slots: ["Flask 1", "Flask 2", "Flask 3", "Flask 4", "Flask 5"] },
];

function emptyItem(slot: string, id: number): Item {
  return {
    id,
    slot,
    name: "",
    base_type: "",
    rarity: "RARE",
    level: 1,
    quality: 0,
    sockets: "",
    implicits: [],
    explicits: [],
    raw_text: "",
  };
}

export default function GearEditor(props: GearEditorProps) {
  const bySlot = createMemo(() => {
    const map = new Map<string, Item>();
    for (const item of props.items) {
      map.set(item.slot, item);
    }
    return map;
  });

  function updateItem(item: Item) {
    const items = props.items.map((it) => (it.id === item.id ? item : it));
    props.onUpdate(items);
  }

  function removeItem(id: number) {
    const items = props.items.filter((it) => it.id !== id);
    props.onUpdate(items);
  }

  function addItem(slot: string) {
    const items = [...props.items, emptyItem(slot, props.nextId())];
    props.onUpdate(items);
  }

  return (
    <div class="editor-gear">
      <For each={SLOT_CATEGORIES}>
        {(cat) => (
          <div class="editor-gear-category">
            <h4 class="editor-gear-category-title">{cat.label}</h4>
            <div class="editor-gear-grid">
              <For each={cat.slots}>
                {(slot) => {
                  const item = () => bySlot().get(slot);
                  return (
                    <Show
                      when={item()}
                      fallback={
                        <button
                          class="editor-item-empty"
                          onClick={() => addItem(slot)}
                        >
                          + {slot}
                        </button>
                      }
                    >
                      {(it) => (
                        <ItemEditorCard
                          item={it()}
                          onUpdate={updateItem}
                          onRemove={() => removeItem(it().id)}
                        />
                      )}
                    </Show>
                  );
                }}
              </For>
            </div>
          </div>
        )}
      </For>
    </div>
  );
}
