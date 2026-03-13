import { createSignal, For, Show } from "solid-js";
import type { Build, PassiveSpec } from "../lib/types";
import { openPassiveTree, suggestPassiveNodes, type PassiveNodeSuggestion } from "../lib/commands";
import PassiveTreeCanvas from "./PassiveTreeCanvas";

interface PassiveTreePanelProps {
  spec: PassiveSpec;
  build?: Build | null;
}

export default function PassiveTreePanel(props: PassiveTreePanelProps) {
  const spec = () => props.spec;
  const [treeOpen, setTreeOpen] = createSignal(false);
  const [suggestions, setSuggestions] = createSignal<PassiveNodeSuggestion[]>([]);
  const [suggestLoading, setSuggestLoading] = createSignal(false);
  const [suggestError, setSuggestError] = createSignal("");
  const [suggestSkill, setSuggestSkill] = createSignal("");

  const hasTreeData = () =>
    spec().nodes.length > 0 ||
    (spec().key_nodes && spec().key_nodes!.length > 0) ||
    spec().total_points;

  function handleOpenExternal() {
    const url = spec().url;
    if (url) {
      openPassiveTree(url);
    }
  }

  async function handleSuggestNodes() {
    const build = props.build;
    if (!build || !spec().nodes.length) return;

    setSuggestLoading(true);
    setSuggestError("");
    setSuggestions([]);

    try {
      const result = await suggestPassiveNodes(
        build as unknown as Record<string, unknown>,
        undefined,
        10,
      );
      if (result.error) {
        setSuggestError(result.error);
      } else {
        setSuggestions(result.suggestions);
        setSuggestSkill(result.skill_name);
      }
    } catch (e) {
      setSuggestError(String(e));
    } finally {
      setSuggestLoading(false);
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
        <div class="passive-tree-actions">
          <button
            class="tree-toggle-btn"
            onClick={() => setTreeOpen(!treeOpen())}
          >
            {treeOpen() ? "Hide Tree" : "Show Passive Tree"}
          </button>
          <button
            class="tree-external-btn"
            onClick={handleOpenExternal}
            title="Open on pathofexile.com"
          >
            &#8599;
          </button>
        </div>

        <Show when={treeOpen()}>
          <div class="passive-tree-viewer">
            <PassiveTreeCanvas
              url={spec().url}
              height={550}
              highlightNodes={suggestions().map((s) => s.node_id)}
            />
          </div>
        </Show>
      </Show>

      {/* Node Suggestions */}
      <Show when={props.build && spec().nodes.length > 0}>
        <div class="passive-suggest-section">
          <button
            class="btn-secondary passive-suggest-btn"
            onClick={handleSuggestNodes}
            disabled={suggestLoading()}
          >
            {suggestLoading() ? (
              <><span class="spinner" /> Analyzing nodes...</>
            ) : (
              "Suggest Next Nodes"
            )}
          </button>

          <Show when={suggestError()}>
            <div class="error-toast" style={{ "margin-top": "8px" }}>{suggestError()}</div>
          </Show>

          <Show when={suggestions().length > 0}>
            <div class="passive-suggestions">
              <div class="passive-suggestions-header">
                Top nodes for <strong>{suggestSkill()}</strong> DPS:
              </div>
              <For each={suggestions()}>
                {(s) => (
                  <div class={`passive-suggestion ${s.dps_change > 0 ? "suggestion-positive" : s.dps_change < 0 ? "suggestion-negative" : ""}`}>
                    <div class="passive-suggestion-header">
                      <span class={`suggestion-name ${s.is_keystone ? "suggestion-keystone" : s.is_notable ? "suggestion-notable" : ""}`}>
                        {s.name || `Node ${s.node_id}`}
                      </span>
                      <span class={`suggestion-dps ${s.dps_change > 0 ? "dps-up" : s.dps_change < 0 ? "dps-down" : ""}`}>
                        {s.dps_change > 0 ? "+" : ""}{s.dps_change.toFixed(1)} DPS
                        <span class="suggestion-pct">({s.dps_change_pct > 0 ? "+" : ""}{s.dps_change_pct.toFixed(1)}%)</span>
                      </span>
                    </div>
                    <Show when={s.stats.length > 0}>
                      <div class="suggestion-stats">
                        <For each={s.stats}>
                          {(stat) => <div class="suggestion-stat">{stat}</div>}
                        </For>
                      </div>
                    </Show>
                  </div>
                )}
              </For>
            </div>
          </Show>
        </div>
      </Show>
    </div>
  );
}
