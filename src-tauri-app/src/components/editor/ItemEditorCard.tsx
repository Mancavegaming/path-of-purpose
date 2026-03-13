import { For, Show } from "solid-js";
import type { Item } from "../../lib/types";

interface ItemEditorCardProps {
  item: Item;
  onUpdate: (item: Item) => void;
  onRemove: () => void;
}

const RARITY_OPTIONS = ["NORMAL", "MAGIC", "RARE", "UNIQUE"];

export default function ItemEditorCard(props: ItemEditorCardProps) {
  function updateField<K extends keyof Item>(key: K, value: Item[K]) {
    props.onUpdate({ ...props.item, [key]: value });
  }

  function updateExplicit(idx: number, text: string) {
    const explicits = [...props.item.explicits];
    explicits[idx] = { ...explicits[idx], text };
    props.onUpdate({ ...props.item, explicits });
  }

  function removeExplicit(idx: number) {
    const explicits = props.item.explicits.filter((_, i) => i !== idx);
    props.onUpdate({ ...props.item, explicits });
  }

  function addExplicit() {
    const explicits = [...props.item.explicits, { text: "", is_implicit: false, is_crafted: false }];
    props.onUpdate({ ...props.item, explicits });
  }

  function updateImplicit(idx: number, text: string) {
    const implicits = [...props.item.implicits];
    implicits[idx] = { ...implicits[idx], text };
    props.onUpdate({ ...props.item, implicits });
  }

  function removeImplicit(idx: number) {
    const implicits = props.item.implicits.filter((_, i) => i !== idx);
    props.onUpdate({ ...props.item, implicits });
  }

  function addImplicit() {
    const implicits = [...props.item.implicits, { text: "", is_implicit: true, is_crafted: false }];
    props.onUpdate({ ...props.item, implicits });
  }

  function updateStatPriority(value: string) {
    const priorities = value.split(",").map((s) => s.trim()).filter(Boolean);
    updateField("stat_priority", priorities);
  }

  return (
    <div class="editor-item-card">
      <div class="editor-item-header">
        <span class="editor-item-slot">{props.item.slot}</span>
        <button class="editor-btn-sm editor-btn-danger" onClick={props.onRemove}>
          Remove
        </button>
      </div>

      <div class="editor-item-fields">
        <div class="editor-item-row">
          <input
            type="text"
            class="editor-input"
            value={props.item.name}
            placeholder="Item name..."
            onInput={(e) => updateField("name", e.currentTarget.value)}
          />
          <select
            class="editor-select editor-select-sm"
            value={props.item.rarity}
            onChange={(e) => updateField("rarity", e.currentTarget.value)}
          >
            <For each={RARITY_OPTIONS}>
              {(r) => <option value={r}>{r.charAt(0) + r.slice(1).toLowerCase()}</option>}
            </For>
          </select>
        </div>

        <input
          type="text"
          class="editor-input"
          value={props.item.base_type}
          placeholder="Base type (e.g. Jewelled Foil, Astral Plate)..."
          onInput={(e) => updateField("base_type", e.currentTarget.value)}
        />

        {/* Implicits */}
        <Show when={props.item.implicits.length > 0 || true}>
          <div class="editor-mods-section">
            <span class="editor-mods-label">Implicits</span>
            <For each={props.item.implicits}>
              {(mod, i) => (
                <div class="editor-mod-row">
                  <input
                    type="text"
                    class="editor-input editor-mod-input"
                    value={mod.text}
                    placeholder="Implicit mod..."
                    onInput={(e) => updateImplicit(i(), e.currentTarget.value)}
                  />
                  <button class="editor-btn-sm editor-btn-danger" onClick={() => removeImplicit(i())}>
                    x
                  </button>
                </div>
              )}
            </For>
            <button class="editor-btn-sm" onClick={addImplicit}>+ Implicit</button>
          </div>
        </Show>

        {/* Explicits */}
        <div class="editor-mods-section">
          <span class="editor-mods-label">Mods</span>
          <For each={props.item.explicits}>
            {(mod, i) => (
              <div class="editor-mod-row">
                <input
                  type="text"
                  class="editor-input editor-mod-input"
                  value={mod.text}
                  placeholder="e.g. +80 to Maximum Life"
                  onInput={(e) => updateExplicit(i(), e.currentTarget.value)}
                />
                <button class="editor-btn-sm editor-btn-danger" onClick={() => removeExplicit(i())}>
                  x
                </button>
              </div>
            )}
          </For>
          <button class="editor-btn-sm" onClick={addExplicit}>+ Mod</button>
        </div>

        {/* Stat Priority */}
        <label class="editor-field">
          <span class="editor-label">Stat Priority (comma-separated)</span>
          <input
            type="text"
            class="editor-input"
            value={(props.item.stat_priority ?? []).join(", ")}
            placeholder="life, elemental resistances, attack speed"
            onInput={(e) => updateStatPriority(e.currentTarget.value)}
          />
        </label>

        {/* Notes */}
        <label class="editor-field">
          <span class="editor-label">Notes</span>
          <input
            type="text"
            class="editor-input"
            value={props.item.notes ?? ""}
            placeholder="Brief item notes..."
            onInput={(e) => updateField("notes", e.currentTarget.value)}
          />
        </label>
      </div>
    </div>
  );
}
