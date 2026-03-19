import { For, Show } from "solid-js";
import type { DeathAnalysis } from "../lib/types";
import {
  deathHistory,
  selectedDeath,
  setSelectedDeath,
  deathLogError,
  detectedLogPath,
  showGraceVerses,
  setShowGraceVerses,
} from "../lib/deathStore";

const ELEMENT_COLORS: Record<string, string> = {
  Fire: "#f97316",
  Cold: "#38bdf8",
  Lightning: "#facc15",
  Chaos: "#c084fc",
  Physical: "#a1a1aa",
};

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function DeathPage() {
  return (
    <div class="page-content">
      <h2 class="page-title">Death Log</h2>
      <p class="page-subtitle">
        Review your deaths, understand what killed you, and learn how to survive.
      </p>

      <Show when={deathLogError()}>
        <div style={{ color: "#f88", "font-size": "0.85rem", "margin-bottom": "8px" }}>
          {deathLogError()}
        </div>
      </Show>
      <Show when={detectedLogPath()}>
        <div style={{ color: "#666", "font-size": "0.8rem", "margin-bottom": "8px" }}>
          Monitoring: {detectedLogPath()}
        </div>
      </Show>

      <div class="death-layout">
        {/* Left: Death log list */}
        <div class="death-log-panel">
          <h3 class="settings-heading">
            Deaths ({deathHistory().length})
          </h3>
          <Show
            when={deathHistory().length > 0}
            fallback={
              <div class="death-empty">No deaths this session. Stay safe, exile.</div>
            }
          >
            <div class="death-log-list">
              <For each={deathHistory()}>
                {(entry) => {
                  const color = ELEMENT_COLORS[entry.element] || "#a1a1aa";
                  return (
                    <button
                      class={`death-log-entry ${selectedDeath()?.id === entry.id ? "selected" : ""}`}
                      onClick={() => setSelectedDeath(entry)}
                    >
                      <span class="death-entry-time">{formatTime(entry.timestamp)}</span>
                      <span class="death-entry-dot" style={{ background: color }} />
                      <span class="death-entry-killer">{entry.killer}</span>
                      <span class="death-entry-zone">{entry.zone}</span>
                    </button>
                  );
                }}
              </For>
            </div>
          </Show>
        </div>

        {/* Right: Death detail */}
        <div class="death-detail-panel">
          <Show
            when={selectedDeath()}
            fallback={
              <div class="death-empty">Select a death to see details and survival tips.</div>
            }
          >
            {(death) => <DeathDetail death={death()} />}
          </Show>
        </div>
      </div>
    </div>
  );
}

function DeathDetail(props: { death: { killer: string; zone: string; element: string; timestamp: number; analysis: DeathAnalysis | null } }) {
  const elementColor = () => ELEMENT_COLORS[props.death.element] || "";

  return (
    <div>
      {/* Header */}
      <div class="death-detail-header">
        <span class="death-detail-skull">Slain by {props.death.killer}</span>
        <Show when={props.death.element}>
          <span style={{ color: elementColor(), "font-weight": "bold", "margin-left": "6px" }}>
            ({props.death.element})
          </span>
        </Show>
      </div>
      <div class="death-detail-meta">
        <span>Zone: {props.death.zone}</span>
        <span style={{ "margin-left": "16px" }}>Time: {formatTime(props.death.timestamp)}</span>
      </div>

      <Show
        when={props.death.analysis}
        fallback={
          <div class="death-empty" style={{ "margin-top": "16px" }}>
            Load a build to see survival analysis.
          </div>
        }
      >
        {(analysis) => (
          <>
            {/* Weaknesses */}
            <Show when={analysis().weaknesses.length > 0}>
              <h4 class="death-section-title">Weaknesses</h4>
              <div class="death-weakness-list">
                <For each={analysis().weaknesses}>
                  {(w) => (
                    <div class={`death-weakness-row ${w.severity}`}>
                      <span class="death-w-stat">{w.stat}</span>
                      <span class="death-w-current">{Math.round(w.current)}</span>
                      <span class="death-w-arrow">&rarr;</span>
                      <span class="death-w-target">{w.target}</span>
                    </div>
                  )}
                </For>
              </div>
            </Show>

            {/* Suggestions */}
            <Show when={analysis().suggestions.length > 0}>
              <h4 class="death-section-title">Survival Tips</h4>
              <div class="death-suggestion-list">
                <For each={analysis().suggestions}>
                  {(s) => <div class="death-suggestion-item">{s}</div>}
                </For>
              </div>
            </Show>

            {/* Grace verse */}
            <Show when={showGraceVerses() && analysis().grace_verse}>
              <div class="death-grace-card">
                <em>"{analysis().grace_verse}"</em>
                <span class="death-grace-ref"> — {analysis().grace_ref}</span>
              </div>
            </Show>
          </>
        )}
      </Show>

      {/* Verse toggle */}
      <div class="death-verse-toggle">
        <label class="settings-toggle">
          <input
            type="checkbox"
            checked={showGraceVerses()}
            onChange={(e) => setShowGraceVerses(e.currentTarget.checked)}
          />
          <span class="toggle-slider" />
        </label>
        <span style={{ "margin-left": "8px", "font-size": "0.85rem", color: "#999" }}>
          Show grace verses
        </span>
      </div>
    </div>
  );
}
