import { Show } from "solid-js";
import type { PassiveSpec } from "../../lib/types";

interface TreeEditorProps {
  spec: PassiveSpec;
  onUpdate: (spec: PassiveSpec) => void;
}

export default function TreeEditor(props: TreeEditorProps) {
  function update<K extends keyof PassiveSpec>(key: K, value: PassiveSpec[K]) {
    props.onUpdate({ ...props.spec, [key]: value });
  }

  function updateKeyNodes(value: string) {
    const nodes = value.split(",").map((s) => s.trim()).filter(Boolean);
    update("key_nodes", nodes);
  }

  return (
    <div class="editor-tree">
      <div class="editor-tree-row">
        <label class="editor-field">
          <span class="editor-label">Passive Tree URL</span>
          <input
            type="text"
            class="editor-input"
            value={props.spec.url}
            placeholder="https://www.pathofexile.com/passive-skill-tree/..."
            onInput={(e) => update("url", e.currentTarget.value)}
          />
        </label>
      </div>

      <div class="editor-tree-row">
        <label class="editor-field editor-field-sm">
          <span class="editor-label">Total Points</span>
          <input
            type="number"
            class="editor-input"
            value={props.spec.total_points ?? 0}
            min={0}
            max={130}
            onInput={(e) => update("total_points", parseInt(e.currentTarget.value) || 0)}
          />
        </label>
        <label class="editor-field">
          <span class="editor-label">Priority</span>
          <input
            type="text"
            class="editor-input"
            value={props.spec.priority ?? ""}
            placeholder="Life > Sword damage > Crit multi"
            onInput={(e) => update("priority", e.currentTarget.value)}
          />
        </label>
      </div>

      <label class="editor-field">
        <span class="editor-label">Key Nodes (comma-separated)</span>
        <input
          type="text"
          class="editor-input"
          value={(props.spec.key_nodes ?? []).join(", ")}
          placeholder="Resolute Technique, Iron Grip, Master of the Arena"
          onInput={(e) => updateKeyNodes(e.currentTarget.value)}
        />
      </label>

      <Show when={props.spec.url}>
        <a
          class="editor-btn editor-btn-accent"
          href={props.spec.url}
          target="_blank"
          rel="noopener"
          style={{ "text-align": "center", "text-decoration": "none", display: "block", "margin-top": "8px" }}
        >
          Open Tree in Browser
        </a>
      </Show>
    </div>
  );
}
