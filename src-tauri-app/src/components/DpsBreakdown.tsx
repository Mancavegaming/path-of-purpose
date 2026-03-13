import { For, Show } from "solid-js";
import type { CalcResult, TypeDamage } from "../lib/types";

interface DpsBreakdownProps {
  result: CalcResult;
}

function formatDps(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(0);
}

function formatNum(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

const TYPE_COLORS: Record<string, string> = {
  physical: "#c8c8c8",
  fire: "#e25822",
  cold: "#36b5d8",
  lightning: "#ffd700",
  chaos: "#8844cc",
};

/** Expandable detailed DPS breakdown panel. */
export default function DpsBreakdown(props: DpsBreakdownProps) {
  const r = () => props.result;

  const activeTypes = () =>
    r().type_breakdown.filter((t) => t.after_mitigation > 0);

  const hasDefence = () => r().defence != null;
  const def = () => r().defence!;

  return (
    <div class="dps-breakdown">
      {/* Summary row */}
      <div class="dps-summary-grid">
        <div class="dps-summary-item">
          <div class="dps-summary-label">Hit Damage</div>
          <div class="dps-summary-value">{formatNum(r().hit_damage)}</div>
        </div>
        <div class="dps-summary-item">
          <div class="dps-summary-label">Hits/sec</div>
          <div class="dps-summary-value">{r().hits_per_second}</div>
        </div>
        <div class="dps-summary-item">
          <div class="dps-summary-label">Crit Chance</div>
          <div class="dps-summary-value">{r().crit_chance}%</div>
        </div>
        <div class="dps-summary-item">
          <div class="dps-summary-label">Crit Multi</div>
          <div class="dps-summary-value">{r().effective_crit_multi}x</div>
        </div>
        <Show when={r().is_attack}>
          <div class="dps-summary-item">
            <div class="dps-summary-label">Hit Chance</div>
            <div class="dps-summary-value">{r().hit_chance}%</div>
          </div>
        </Show>
      </div>

      {/* Enemy damage taken multiplier */}
      <Show when={r().enemy_damage_taken_multi > 1.001}>
        <div class="dps-enemy-taken">
          Enemy takes {((r().enemy_damage_taken_multi - 1) * 100).toFixed(1)}% more damage
          <span class="dps-enemy-taken-sources">
            (shock, curses, wither, intimidate)
          </span>
        </div>
      </Show>

      {/* Impale DPS */}
      <Show when={r().impale_dps > 0}>
        <div class="dps-impale-section">
          <div class="dps-dot-title">Impale</div>
          <div class="dps-dot-grid">
            <div class="dps-dot-item">
              <span class="dps-dot-label" style={{ color: TYPE_COLORS.physical }}>Impale DPS</span>
              <span class="dps-dot-value">{formatDps(r().impale_dps)}</span>
            </div>
          </div>
        </div>
      </Show>

      {/* DoT summary if present */}
      <Show when={r().total_dot_dps > 0}>
        <div class="dps-dot-section">
          <div class="dps-dot-title">Damage over Time</div>
          <div class="dps-dot-grid">
            <Show when={r().ignite_dps > 0}>
              <div class="dps-dot-item">
                <span class="dps-dot-label" style={{ color: TYPE_COLORS.fire }}>Ignite</span>
                <span class="dps-dot-value">{formatDps(r().ignite_dps)}</span>
              </div>
            </Show>
            <Show when={r().bleed_dps > 0}>
              <div class="dps-dot-item">
                <span class="dps-dot-label" style={{ color: TYPE_COLORS.physical }}>Bleed</span>
                <span class="dps-dot-value">{formatDps(r().bleed_dps)}</span>
              </div>
            </Show>
            <Show when={r().poison_dps > 0}>
              <div class="dps-dot-item">
                <span class="dps-dot-label" style={{ color: TYPE_COLORS.chaos }}>Poison</span>
                <span class="dps-dot-value">{formatDps(r().poison_dps)}</span>
              </div>
            </Show>
          </div>
        </div>
      </Show>

      {/* Per-type breakdown */}
      <Show when={activeTypes().length > 0}>
        <div class="dps-type-section">
          <div class="dps-type-title">Damage by Type</div>
          <For each={activeTypes()}>
            {(td: TypeDamage) => {
              const color = TYPE_COLORS[td.damage_type] || "#aaa";
              const total = r().hit_damage || 1;
              const pct = (td.after_mitigation / total) * 100;
              return (
                <div class="dps-type-row">
                  <span class="dps-type-name" style={{ color }}>
                    {td.damage_type}
                  </span>
                  <div class="dps-type-bar-wrap">
                    <div
                      class="dps-type-bar"
                      style={{ width: `${Math.min(pct, 100)}%`, background: color }}
                    />
                  </div>
                  <span class="dps-type-amount">{formatNum(td.after_mitigation)}</span>
                </div>
              );
            }}
          </For>
        </div>
      </Show>

      {/* Defence section */}
      <Show when={hasDefence()}>
        <div class="dps-defence-section">
          <div class="dps-type-title">Defences</div>
          <div class="dps-defence-grid">
            <Show when={def().armour > 0}>
              <div class="dps-defence-item">
                <span class="dps-defence-label">Armour</span>
                <span class="dps-defence-value">{formatNum(def().armour)}</span>
              </div>
            </Show>
            <Show when={def().evasion > 0}>
              <div class="dps-defence-item">
                <span class="dps-defence-label">Evasion</span>
                <span class="dps-defence-value">{formatNum(def().evasion)}</span>
              </div>
            </Show>
            <Show when={def().energy_shield > 0}>
              <div class="dps-defence-item">
                <span class="dps-defence-label">Energy Shield</span>
                <span class="dps-defence-value">{formatNum(def().energy_shield)}</span>
              </div>
            </Show>
            <Show when={def().phys_damage_reduction > 0}>
              <div class="dps-defence-item">
                <span class="dps-defence-label">Phys Reduction</span>
                <span class="dps-defence-value">{def().phys_damage_reduction.toFixed(0)}%</span>
              </div>
            </Show>
            <Show when={def().block_chance > 0}>
              <div class="dps-defence-item">
                <span class="dps-defence-label">Block</span>
                <span class="dps-defence-value">{def().block_chance.toFixed(0)}%</span>
              </div>
            </Show>
            <Show when={def().spell_block_chance > 0}>
              <div class="dps-defence-item">
                <span class="dps-defence-label">Spell Block</span>
                <span class="dps-defence-value">{def().spell_block_chance.toFixed(0)}%</span>
              </div>
            </Show>
            <Show when={(def().elemental_resistances?.fire ?? 0) > 0}>
              <div class="dps-defence-item">
                <span class="dps-defence-label" style={{ color: TYPE_COLORS.fire }}>Fire Res</span>
                <span class="dps-defence-value">{def().elemental_resistances.fire.toFixed(0)}%</span>
              </div>
            </Show>
            <Show when={(def().elemental_resistances?.cold ?? 0) > 0}>
              <div class="dps-defence-item">
                <span class="dps-defence-label" style={{ color: TYPE_COLORS.cold }}>Cold Res</span>
                <span class="dps-defence-value">{def().elemental_resistances.cold.toFixed(0)}%</span>
              </div>
            </Show>
            <Show when={(def().elemental_resistances?.lightning ?? 0) > 0}>
              <div class="dps-defence-item">
                <span class="dps-defence-label" style={{ color: TYPE_COLORS.lightning }}>Light Res</span>
                <span class="dps-defence-value">{def().elemental_resistances.lightning.toFixed(0)}%</span>
              </div>
            </Show>
          </div>
        </div>
      </Show>
    </div>
  );
}
