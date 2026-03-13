import { Show } from "solid-js";
import type { CalcResult } from "../lib/types";

interface DpsBannerProps {
  result: CalcResult | null;
  loading: boolean;
  error: string;
  expanded: boolean;
  onToggle: () => void;
}

function formatDps(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(0);
}

function skillTag(r: CalcResult): string {
  if (r.is_totem) return `Totem (x${r.num_totems})`;
  if (r.is_trap) return "Trap";
  if (r.is_mine) return "Mine";
  if (r.is_minion) return "Minion";
  return "";
}

/** Persistent DPS banner with combined number, click to expand. */
export default function DpsBanner(props: DpsBannerProps) {
  const showResult = () => !props.loading && !props.error ? props.result : null;

  return (
    <div class="dps-banner" classList={{ "dps-banner-expanded": props.expanded }}>
      <Show when={props.loading}>
        <div class="dps-banner-content">
          <span class="spinner" /> Calculating...
        </div>
      </Show>

      <Show when={props.error && !props.loading}>
        <div class="dps-banner-content dps-banner-error">
          {props.error}
        </div>
      </Show>

      <Show when={showResult()}>
        {(r) => (
          <div class="dps-banner-content" onClick={props.onToggle}>
            <div class="dps-banner-main">
              <span class="dps-banner-label">
                {r().skill_name || "DPS"}
                <Show when={skillTag(r())}>
                  <span class="dps-banner-tag">{skillTag(r())}</span>
                </Show>
              </span>
              <span class="dps-banner-value">
                {formatDps(r().combined_dps)}
              </span>
            </div>
            <div class="dps-banner-sub">
              <Show when={r().total_dps > 0}>
                <span class="dps-sub-item">
                  Hit: {formatDps(r().total_dps)}
                </span>
              </Show>
              <Show when={r().total_dot_dps > 0}>
                <span class="dps-sub-item">
                  DoT: {formatDps(r().total_dot_dps)}
                </span>
              </Show>
              <Show when={r().impale_dps > 0}>
                <span class="dps-sub-item">
                  Impale: {formatDps(r().impale_dps)}
                </span>
              </Show>
            </div>
            <span class="dps-banner-toggle">
              {props.expanded ? "\u25B2" : "\u25BC"}
            </span>
          </div>
        )}
      </Show>

      <Show when={props.result && props.result!.warnings.length > 0}>
        <div class="dps-warnings">
          {props.result!.warnings.map((w) => (
            <div class="dps-warning">{w}</div>
          ))}
        </div>
      </Show>
    </div>
  );
}
