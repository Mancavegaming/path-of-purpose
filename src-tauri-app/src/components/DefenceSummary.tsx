import { Show } from "solid-js";
import type { DefenceResult } from "../lib/types";

interface DefenceSummaryProps {
  defence: DefenceResult | null;
}

function formatNum(v: number): string {
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + "M";
  if (v >= 10_000) return (v / 1_000).toFixed(1) + "K";
  if (v >= 1_000) return (v / 1_000).toFixed(1) + "K";
  return Math.round(v).toLocaleString();
}

function resClass(value: number, cap: number = 75): string {
  if (value >= cap) return "def-capped";
  if (value >= cap - 10) return "def-close";
  return "def-low";
}

export default function DefenceSummary(props: DefenceSummaryProps) {
  return (
    <Show when={props.defence}>
      {(def) => {
        const d = def();
        const fireRes = d.elemental_resistances?.fire ?? 0;
        const coldRes = d.elemental_resistances?.cold ?? 0;
        const lightRes = d.elemental_resistances?.lightning ?? 0;
        const chaosRes = d.chaos_resistance ?? 0;

        return (
          <div class="defence-summary">
            <div class="defence-summary-title">Defences</div>
            <div class="defence-grid">
              {/* Pool stats */}
              <Show when={d.life > 0}>
                <div class="defence-stat">
                  <span class="defence-label">Life</span>
                  <span class="defence-value def-life">{formatNum(d.life)}</span>
                </div>
              </Show>
              <Show when={d.energy_shield > 0}>
                <div class="defence-stat">
                  <span class="defence-label">ES</span>
                  <span class="defence-value def-es">{formatNum(d.energy_shield)}</span>
                </div>
              </Show>

              {/* Mitigation */}
              <Show when={d.armour > 0}>
                <div class="defence-stat">
                  <span class="defence-label">Armour</span>
                  <span class="defence-value">{formatNum(d.armour)}</span>
                </div>
              </Show>
              <Show when={d.evasion > 0}>
                <div class="defence-stat">
                  <span class="defence-label">Evasion</span>
                  <span class="defence-value">{formatNum(d.evasion)}</span>
                </div>
              </Show>

              {/* Block */}
              <Show when={d.block_chance > 0}>
                <div class="defence-stat">
                  <span class="defence-label">Block</span>
                  <span class={`defence-value ${resClass(d.block_chance)}`}>
                    {d.block_chance.toFixed(0)}%
                  </span>
                </div>
              </Show>
              <Show when={d.spell_block_chance > 0}>
                <div class="defence-stat">
                  <span class="defence-label">Spell Block</span>
                  <span class={`defence-value ${resClass(d.spell_block_chance)}`}>
                    {d.spell_block_chance.toFixed(0)}%
                  </span>
                </div>
              </Show>

              {/* Spell Suppression */}
              <Show when={d.spell_suppression > 0}>
                <div class="defence-stat">
                  <span class="defence-label">Spell Supp</span>
                  <span class={`defence-value ${resClass(d.spell_suppression, 100)}`}>
                    {d.spell_suppression.toFixed(0)}%
                  </span>
                </div>
              </Show>

              {/* Phys DR */}
              <Show when={d.phys_damage_reduction > 0}>
                <div class="defence-stat">
                  <span class="defence-label">Phys DR</span>
                  <span class="defence-value">{d.phys_damage_reduction.toFixed(0)}%</span>
                </div>
              </Show>
            </div>

            {/* Resistances — always show */}
            <div class="defence-res-row">
              <div class={`defence-res ${resClass(fireRes)}`}>
                <span class="defence-res-icon def-fire">F</span>
                <span class="defence-res-val">{fireRes.toFixed(0)}%</span>
              </div>
              <div class={`defence-res ${resClass(coldRes)}`}>
                <span class="defence-res-icon def-cold">C</span>
                <span class="defence-res-val">{coldRes.toFixed(0)}%</span>
              </div>
              <div class={`defence-res ${resClass(lightRes)}`}>
                <span class="defence-res-icon def-light">L</span>
                <span class="defence-res-val">{lightRes.toFixed(0)}%</span>
              </div>
              <div class={`defence-res ${resClass(chaosRes, 0)}`}>
                <span class="defence-res-icon def-chaos">Ch</span>
                <span class="defence-res-val">{chaosRes.toFixed(0)}%</span>
              </div>
            </div>
          </div>
        );
      }}
    </Show>
  );
}
