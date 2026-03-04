import { Show } from "solid-js";
import type { PassiveSpec } from "../lib/types";
import { openPassiveTree } from "../lib/commands";

interface PassiveTreePanelProps {
  spec: PassiveSpec;
}

export default function PassiveTreePanel(props: PassiveTreePanelProps) {
  const spec = () => props.spec;

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

      <div class="stat-grid" style={{ "margin-top": "var(--space-sm)" }}>
        <div class="stat-box">
          <div class="stat-label">Nodes</div>
          <div class="stat-value">{spec().nodes.length}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Tree Version</div>
          <div class="stat-value">{spec().tree_version.replace(/_/g, ".")}</div>
        </div>
      </div>

      <Show when={spec().url}>
        <button class="tree-toggle-btn" onClick={handleOpenTree}>
          View Passive Tree
        </button>
      </Show>
    </div>
  );
}
