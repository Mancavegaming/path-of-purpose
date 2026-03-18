import { For, Show } from "solid-js";
import type { DeathAnalysis } from "../lib/types";

interface Props {
  analysis: DeathAnalysis;
  onDismiss: () => void;
  showGraceVerse: boolean;
  opacity: number;
}

export default function DeathRecapToast(props: Props) {
  return (
    <div
      class="death-toast"
      style={{ opacity: props.opacity }}
      onClick={(e) => e.stopPropagation()}
    >
      <div class="death-header">
        <span class="death-skull">Slain by {props.analysis.killer}</span>
        <Show when={props.analysis.zone}>
          <span class="death-zone">in {props.analysis.zone}</span>
        </Show>
        <button class="death-dismiss" onClick={props.onDismiss}>x</button>
      </div>

      <Show when={props.analysis.weaknesses.length > 0}>
        <div class="death-weaknesses">
          <For each={props.analysis.weaknesses}>
            {(weakness) => (
              <div class={`death-weakness ${weakness.severity}`}>
                <span class="weakness-stat">{weakness.stat}:</span>
                <span class="weakness-current">{Math.round(weakness.current)}</span>
                <span class="weakness-arrow">-&gt;</span>
                <span class="weakness-target">{weakness.target}</span>
              </div>
            )}
          </For>
        </div>
      </Show>

      <Show when={props.analysis.suggestions.length > 0}>
        <div class="death-suggestions">
          <For each={props.analysis.suggestions}>
            {(suggestion) => (
              <div class="death-suggestion">{suggestion}</div>
            )}
          </For>
        </div>
      </Show>

      <Show when={props.showGraceVerse && props.analysis.grace_verse}>
        <div class="death-grace">
          <em>"{props.analysis.grace_verse}"</em>
          <span class="grace-ref"> — {props.analysis.grace_ref}</span>
        </div>
      </Show>
    </div>
  );
}
