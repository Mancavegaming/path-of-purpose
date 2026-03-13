import { createEffect, createSignal, For, Show } from "solid-js";
import type { Build, Item, ItemComparison, TradeListing } from "../lib/types";
import { compareItems, compareBuildDps, type BuildDpsComparison } from "../lib/commands";

interface ItemComparisonPanelProps {
  equippedItem: Item;
  tradeListing: TradeListing;
  build: Build | null;
}

/** Extract the main-hand weapon's APS from the build, or 0 if not found. */
function getWeaponAps(build: Build | null): number {
  if (!build) return 0;
  const weapon = build.items.find(
    (i) => i.slot === "Weapon 1" || i.slot === "Weapon 1 Swap",
  );
  if (!weapon) return 0;
  const match = weapon.raw_text?.match(/Attacks per Second:\s*([\d.]+)/i);
  if (match) return parseFloat(match[1]);
  return 1.2;
}

function formatDps(value: number): string {
  if (value >= 1_000_000) return (value / 1_000_000).toFixed(2) + "M";
  if (value >= 1_000) return (value / 1_000).toFixed(1) + "K";
  return value.toFixed(0);
}

export default function ItemComparisonPanel(props: ItemComparisonPanelProps) {
  const [comparison, setComparison] = createSignal<ItemComparison | null>(null);
  const [buildDps, setBuildDps] = createSignal<BuildDpsComparison | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");

  createEffect(() => {
    const item = props.equippedItem;
    const listing = props.tradeListing;
    if (!item || !listing) return;

    setLoading(true);
    setError("");
    setComparison(null);
    setBuildDps(null);

    const weaponAps = getWeaponAps(props.build);

    // Run both comparisons in parallel
    const itemPromise = compareItems(
      item as unknown as Record<string, unknown>,
      listing as unknown as Record<string, unknown>,
      item.slot,
      weaponAps,
    );

    const buildPromise = props.build
      ? compareBuildDps(
          props.build as unknown as Record<string, unknown>,
          listing as unknown as Record<string, unknown>,
          item.slot,
        )
      : Promise.resolve(null);

    Promise.all([itemPromise, buildPromise])
      .then(([itemResult, dpsResult]) => {
        setComparison(itemResult);
        setBuildDps(dpsResult);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  });

  const buildDpsChangeClass = () => {
    const d = buildDps();
    if (!d) return "";
    return d.dps_change > 0 ? "stat-better" : d.dps_change < 0 ? "stat-worse" : "";
  };

  /** Check if a stat_name relates to a guide priority keyword. */
  const isGuidePriority = (statName: string): boolean => {
    const priorities = props.equippedItem.stat_priority;
    if (!priorities?.length) return false;
    const lower = statName.toLowerCase();
    return priorities.some((p) => {
      const pl = p.toLowerCase();
      return lower.includes(pl) || pl.includes(lower)
        || (pl === "life" && lower.includes("life"))
        || (pl.includes("resistance") && lower.includes("resistance"))
        || (pl.includes("res") && lower.includes("resistance"))
        || (pl.includes("attack speed") && lower.includes("attack speed"))
        || (pl.includes("cast speed") && lower.includes("cast speed"))
        || (pl.includes("crit") && lower.includes("critical"))
        || (pl.includes("movement") && lower.includes("movement"))
        || (pl.includes("energy shield") && (lower.includes("energy shield") || lower.includes("es")))
        || (pl.includes("armour") && lower.includes("armour"))
        || (pl.includes("evasion") && lower.includes("evasion"));
    });
  };

  const hasGuidePriorities = () => !!props.equippedItem.stat_priority?.length;

  return (
    <div class="comparison-panel">
      <Show when={loading()}>
        <div class="panel-loading">
          <span class="spinner" />
          Calculating build DPS...
        </div>
      </Show>

      <Show when={error()}>
        <div class="error-toast">{error()}</div>
      </Show>

      {/* Full Build DPS comparison — the main attraction */}
      <Show when={buildDps()}>
        {(dps) => (
          <div class="comparison-build-dps">
            <div class="comparison-build-dps-title">
              Build DPS — {dps().skill_name}
            </div>
            <div class="comparison-build-dps-grid">
              <div class="comparison-build-dps-cell">
                <span class="comparison-build-dps-label">Current</span>
                <span class="comparison-build-dps-value">{formatDps(dps().baseline_dps)}</span>
              </div>
              <div class="comparison-build-dps-cell">
                <span class="comparison-build-dps-label">With Trade Item</span>
                <span class="comparison-build-dps-value">{formatDps(dps().swapped_dps)}</span>
              </div>
            </div>
            <div class={`comparison-build-dps-change ${buildDpsChangeClass()}`}>
              {dps().dps_change > 0 ? "+" : ""}{formatDps(dps().dps_change)} DPS
              ({dps().dps_change_pct > 0 ? "+" : ""}{dps().dps_change_pct}%)
            </div>
          </div>
        )}
      </Show>

      <Show when={comparison()}>
        {(comp) => (
          <>
            <div class="comparison-header">
              <span class="comparison-label">
                {comp().equipped_name} vs {comp().trade_name}
              </span>
            </div>

            {/* Stat deltas */}
            <Show when={comp().stat_deltas.length > 0}>
              <div class="comparison-stats">
                <Show when={hasGuidePriorities()}>
                  <div class="comparison-priority-legend">
                    <span class="priority-dot" /> = guide priority
                  </div>
                </Show>
                <For each={comp().stat_deltas}>
                  {(delta) => (
                    <div class={`comparison-stat-row ${delta.difference > 0 ? "stat-better" : delta.difference < 0 ? "stat-worse" : ""} ${isGuidePriority(delta.stat_name) ? "stat-priority" : ""}`}>
                      <span class="comparison-stat-name">
                        <Show when={isGuidePriority(delta.stat_name)}>
                          <span class="priority-dot" />
                        </Show>
                        {delta.stat_name}
                      </span>
                      <span class="comparison-stat-equipped">{delta.equipped_value}</span>
                      <span class="comparison-stat-diff">
                        {delta.difference > 0 ? "+" : ""}{delta.difference}
                      </span>
                      <span class="comparison-stat-trade">{delta.trade_value}</span>
                    </div>
                  )}
                </For>
              </div>
            </Show>

            <div class="comparison-summary">{comp().summary}</div>
          </>
        )}
      </Show>
    </div>
  );
}
