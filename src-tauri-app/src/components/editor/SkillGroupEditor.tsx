import { For, Show } from "solid-js";
import type { SkillGroup, Gem } from "../../lib/types";

interface SkillGroupEditorProps {
  group: SkillGroup;
  index: number;
  isMain: boolean;
  onUpdate: (group: SkillGroup) => void;
  onRemove: () => void;
  onSetMain: () => void;
}

const SLOT_OPTIONS = [
  "Body Armour", "Helmet", "Gloves", "Boots",
  "Weapon 1", "Weapon 2", "Amulet", "Ring 1", "Ring 2",
];

function emptyGem(isSupport: boolean): Gem {
  return {
    name: "",
    gem_id: "",
    level: 20,
    quality: 0,
    is_support: isSupport,
    is_enabled: true,
  };
}

export default function SkillGroupEditor(props: SkillGroupEditorProps) {
  function updateGem(gemIdx: number, updates: Partial<Gem>) {
    const gems = [...props.group.gems];
    gems[gemIdx] = { ...gems[gemIdx], ...updates };
    props.onUpdate({ ...props.group, gems });
  }

  function removeGem(gemIdx: number) {
    const gems = props.group.gems.filter((_, i) => i !== gemIdx);
    props.onUpdate({ ...props.group, gems });
  }

  function addGem(isSupport: boolean) {
    const gems = [...props.group.gems, emptyGem(isSupport)];
    props.onUpdate({ ...props.group, gems });
  }

  return (
    <div class="editor-skill-group" classList={{ "editor-skill-main": props.isMain }}>
      <div class="editor-skill-header">
        <select
          class="editor-select editor-select-sm"
          value={props.group.slot}
          onChange={(e) => props.onUpdate({ ...props.group, slot: e.currentTarget.value })}
        >
          <For each={SLOT_OPTIONS}>
            {(s) => <option value={s}>{s}</option>}
          </For>
        </select>
        <Show when={!props.isMain}>
          <button class="editor-btn-sm editor-btn-accent" onClick={props.onSetMain}>
            Set Main
          </button>
        </Show>
        <Show when={props.isMain}>
          <span class="editor-badge">Main Skill</span>
        </Show>
        <button class="editor-btn-sm editor-btn-danger" onClick={props.onRemove}>
          Remove
        </button>
      </div>

      <div class="editor-gem-list">
        <For each={props.group.gems}>
          {(gem, i) => (
            <div class="editor-gem-row">
              <input
                type="text"
                class="editor-input editor-gem-name"
                value={gem.name}
                placeholder={gem.is_support ? "Support gem name..." : "Active gem name..."}
                onInput={(e) => updateGem(i(), { name: e.currentTarget.value })}
              />
              <label class="editor-gem-type">
                <input
                  type="checkbox"
                  checked={gem.is_support}
                  onChange={(e) => updateGem(i(), { is_support: e.currentTarget.checked })}
                />
                Sup
              </label>
              <input
                type="number"
                class="editor-input editor-gem-num"
                value={gem.level}
                min={1}
                max={21}
                title="Level"
                onInput={(e) => updateGem(i(), { level: parseInt(e.currentTarget.value) || 1 })}
              />
              <input
                type="number"
                class="editor-input editor-gem-num"
                value={gem.quality}
                min={0}
                max={30}
                title="Quality"
                onInput={(e) => updateGem(i(), { quality: parseInt(e.currentTarget.value) || 0 })}
              />
              <button class="editor-btn-sm editor-btn-danger" onClick={() => removeGem(i())}>
                x
              </button>
            </div>
          )}
        </For>
      </div>

      <div class="editor-gem-actions">
        <button class="editor-btn-sm" onClick={() => addGem(false)}>+ Active Gem</button>
        <button class="editor-btn-sm" onClick={() => addGem(true)}>+ Support Gem</button>
      </div>
    </div>
  );
}
