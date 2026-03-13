import { createSignal, For, Show } from "solid-js";
import type { Build, BudgetRecommendation } from "../lib/types";
import { budgetOptimize, type BudgetOptimizeResult } from "../lib/commands";

interface BudgetOptimizerProps {
  build: Build;
  league: string;
  config?: Record<string, unknown>;
}

const GEAR_SLOTS = [
  "Weapon 1", "Body Armour", "Helmet", "Gloves", "Boots",
  "Belt", "Ring 1", "Ring 2", "Amulet",
];

function formatDps(v: number): string {
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + "M";
  if (v >= 1_000) return (v / 1_000).toFixed(0) + "K";
  return Math.round(v).toString();
}

export default function BudgetOptimizer(props: BudgetOptimizerProps) {
  const [expanded, setExpanded] = createSignal(false);
  const [budget, setBudget] = createSignal(50);
  const [divineRatio, setDivineRatio] = createSignal(200);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");
  const [result, setResult] = createSignal<BudgetOptimizeResult | null>(null);
  const [selectedSlots, setSelectedSlots] = createSignal<Set<string>>(
    new Set(["Weapon 1", "Body Armour", "Helmet", "Gloves", "Boots"]),
  );

  // Which slots have equipped items
  const equippedSlots = () => {
    const slots = new Set<string>();
    for (const item of props.build.items) {
      if (item.slot) slots.add(item.slot);
    }
    return slots;
  };

  function toggleSlot(slot: string) {
    setSelectedSlots((prev) => {
      const next = new Set(prev);
      if (next.has(slot)) next.delete(slot);
      else next.add(slot);
      return next;
    });
  }

  async function handleOptimize() {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const slots = Array.from(selectedSlots());
      const res = await budgetOptimize(
        props.build as unknown as Record<string, unknown>,
        budget(),
        props.league,
        divineRatio(),
        slots,
        5,
        props.config,
      );
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function copyWhisper(whisper: string) {
    await navigator.clipboard.writeText(whisper);
  }

  const topThreeCost = () => {
    const r = result();
    if (!r) return { cost: 0, gain: 0 };
    const top = r.recommendations.slice(0, 3);
    return {
      cost: top.reduce((s, t) => s + t.price_chaos, 0),
      gain: top.reduce((s, t) => s + t.dps_gain_pct, 0),
    };
  };

  return (
    <div class="budget-optimizer">
      <button
        class="boss-readiness-toggle"
        onClick={() => setExpanded(!expanded())}
      >
        <span class="boss-readiness-title">Budget Optimizer</span>
        <Show when={result() && !loading()}>
          <span class="boss-readiness-summary">
            <span class="boss-summary-pass">
              {result()!.recommendations.length} upgrades found
            </span>
            <span class="boss-summary-warn">
              {result()!.slots_searched} slots searched
            </span>
          </span>
        </Show>
        <span class="boss-readiness-chevron">
          {expanded() ? "\u25B2" : "\u25BC"}
        </span>
      </button>

      <Show when={expanded()}>
        <div class="budget-controls">
          <div class="budget-inputs">
            <div class="budget-field">
              <label>Budget (chaos)</label>
              <input
                type="number"
                min={1}
                max={100000}
                value={budget()}
                onInput={(e) => setBudget(Number(e.currentTarget.value))}
                class="budget-input"
              />
            </div>
            <div class="budget-field">
              <label>Divine:Chaos ratio</label>
              <input
                type="number"
                min={1}
                max={1000}
                value={divineRatio()}
                onInput={(e) => setDivineRatio(Number(e.currentTarget.value))}
                class="budget-input"
              />
            </div>
          </div>

          <div class="budget-slots">
            <span class="budget-slots-label">Search slots:</span>
            <div class="budget-slot-pills">
              <For each={GEAR_SLOTS}>
                {(slot) => {
                  const hasItem = () => equippedSlots().has(slot);
                  const isSelected = () => selectedSlots().has(slot);
                  return (
                    <button
                      class={`budget-slot-pill ${isSelected() ? "budget-slot-active" : ""} ${!hasItem() ? "budget-slot-empty" : ""}`}
                      onClick={() => hasItem() && toggleSlot(slot)}
                      disabled={!hasItem()}
                      title={hasItem() ? `Toggle ${slot}` : `No item in ${slot}`}
                    >
                      {slot}
                    </button>
                  );
                }}
              </For>
            </div>
          </div>

          <button
            class="dps-calc-btn"
            onClick={handleOptimize}
            disabled={loading() || selectedSlots().size === 0}
          >
            <Show when={loading()} fallback="Find Upgrades">
              <span class="spinner" /> Searching trade... (this may take 30-60s)
            </Show>
          </button>
        </div>

        <Show when={error()}>
          <div class="error-toast">{error()}</div>
        </Show>

        <Show when={result() && result()!.recommendations.length > 0}>
          <div class="budget-summary-bar">
            <span>
              Baseline: <strong>{formatDps(result()!.baseline_dps)} DPS</strong>
              {" "}({result()!.skill_name})
            </span>
            <Show when={result()!.recommendations.length >= 3}>
              <span class="budget-summary-top3">
                Top 3 upgrades: {topThreeCost().cost.toFixed(0)}c total for +{topThreeCost().gain.toFixed(1)}% DPS
              </span>
            </Show>
          </div>

          <div class="budget-results">
            <div class="budget-results-header">
              <span class="budget-col-rank">#</span>
              <span class="budget-col-slot">Slot</span>
              <span class="budget-col-item">Item</span>
              <span class="budget-col-price">Price</span>
              <span class="budget-col-dps">DPS Gain</span>
              <span class="budget-col-eff">DPS/c</span>
              <span class="budget-col-action"></span>
            </div>
            <For each={result()!.recommendations}>
              {(rec, i) => (
                <BudgetRow rec={rec} rank={i() + 1} onCopyWhisper={copyWhisper} />
              )}
            </For>
          </div>
        </Show>

        <Show when={result() && result()!.recommendations.length === 0 && !loading()}>
          <div class="panel-empty">
            No upgrades found within budget. Try increasing the budget or selecting more slots.
          </div>
        </Show>
      </Show>
    </div>
  );
}

function BudgetRow(props: {
  rec: BudgetRecommendation;
  rank: number;
  onCopyWhisper: (w: string) => void;
}) {
  const [showMods, setShowMods] = createSignal(false);
  const r = () => props.rec;

  const effClass = () => {
    const eff = r().efficiency;
    if (eff >= 200) return "budget-eff-high";
    if (eff >= 50) return "budget-eff-mid";
    return "budget-eff-low";
  };

  return (
    <div class="budget-row">
      <div class="budget-row-main" onClick={() => setShowMods(!showMods())}>
        <span class="budget-col-rank">{props.rank}</span>
        <span class="budget-col-slot">{r().slot}</span>
        <span class="budget-col-item">
          <Show when={r().icon_url}>
            <img src={r().icon_url} alt="" class="budget-item-icon" loading="lazy" />
          </Show>
          <span class="budget-item-name">{r().item_name}</span>
        </span>
        <span class="budget-col-price">
          {r().price_amount}{r().price_currency === "divine" ? " div" : "c"}
        </span>
        <span class="budget-col-dps dps-up">
          +{formatDps(r().dps_gain)} ({r().dps_gain_pct.toFixed(1)}%)
        </span>
        <span class={`budget-col-eff ${effClass()}`}>
          {r().efficiency.toFixed(0)}
        </span>
        <span class="budget-col-action">
          <Show when={r().whisper}>
            <button
              class="trade-whisper-btn"
              onClick={(e) => {
                e.stopPropagation();
                props.onCopyWhisper(r().whisper);
              }}
            >
              Whisper
            </button>
          </Show>
        </span>
      </div>
      <Show when={showMods()}>
        <div class="budget-row-mods">
          <For each={r().implicit_mods}>
            {(mod) => <div class="mod-implicit">{mod}</div>}
          </For>
          <For each={r().explicit_mods}>
            {(mod) => <div>{mod}</div>}
          </For>
        </div>
      </Show>
    </div>
  );
}
