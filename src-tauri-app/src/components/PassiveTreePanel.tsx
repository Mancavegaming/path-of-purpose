import { Show } from "solid-js";
import type { PassiveSpec } from "../lib/types";

interface PassiveTreePanelProps {
  spec: PassiveSpec;
}

export default function PassiveTreePanel(props: PassiveTreePanelProps) {
  const spec = () => props.spec;

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
        <a
          class="passive-link"
          href={spec().url}
          target="_blank"
          rel="noopener noreferrer"
        >
          View on pathofexile.com
        </a>
      </Show>
    </div>
  );
}
