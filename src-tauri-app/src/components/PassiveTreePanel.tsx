import { For, Show } from "solid-js";
import type { PassiveSpec } from "../lib/types";
import { openPassiveTree } from "../lib/commands";

interface PassiveTreePanelProps {
  spec: PassiveSpec;
}

export default function PassiveTreePanel(props: PassiveTreePanelProps) {
  const spec = () => props.spec;

  const hasTreeData = () =>
    spec().nodes.length > 0 ||
    (spec().key_nodes && spec().key_nodes!.length > 0) ||
    spec().total_points;

  function handleOpenTree() {
    const url = spec().url;
    if (url) {
      openPassiveTree(url);
    }
  }

  return (
    <div class="passive-panel">
      <div class="passive-panel-header">
        <h4 class="card-title">{spec().title || "Passive Tree"}</h4>
      </div>

      <Show when={hasTreeData()}>
        <div class="stat-grid" style={{ "margin-top": "var(--space-sm)" }}>
          <Show when={spec().nodes.length > 0}>
            <div class="stat-box">
              <div class="stat-label">Nodes</div>
              <div class="stat-value">{spec().nodes.length}</div>
            </div>
          </Show>
          <Show when={spec().total_points}>
            <div class="stat-box">
              <div class="stat-label">Points</div>
              <div class="stat-value">{spec().total_points}</div>
            </div>
          </Show>
          <Show when={spec().tree_version}>
            <div class="stat-box">
              <div class="stat-label">Tree Version</div>
              <div class="stat-value">{spec().tree_version.replace(/_/g, ".")}</div>
            </div>
          </Show>
        </div>
      </Show>

      <Show when={spec().priority}>
        <div class="passive-priority">
          <span class="passive-priority-label">Priority:</span> {spec().priority}
        </div>
      </Show>

      <Show when={spec().key_nodes && spec().key_nodes!.length > 0}>
        <div class="passive-key-nodes">
          <div class="passive-key-nodes-label">Key Nodes:</div>
          <div class="passive-key-nodes-list">
            <For each={spec().key_nodes}>
              {(node) => <span class="passive-key-node">{node}</span>}
            </For>
          </div>
        </div>
      </Show>

      <Show when={spec().url}>
        <button class="tree-toggle-btn" onClick={handleOpenTree}>
          View Passive Tree
        </button>
      </Show>
    </div>
  );
}
