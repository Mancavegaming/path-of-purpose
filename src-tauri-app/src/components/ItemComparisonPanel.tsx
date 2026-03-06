import { createEffect, createSignal, For, Show } from "solid-js";
import type { Build, Item, ItemComparison, TradeListing } from "../lib/types";
import { compareItems } from "../lib/commands";

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
  // Look for APS in raw_text (PoB format: "Attacks per Second: 1.50")
  const match = weapon.raw_text?.match(/Attacks per Second:\s*([\d.]+)/i);
  if (match) return parseFloat(match[1]);
  // Fallback: check explicits for attack speed mod and estimate
  return 1.2; // reasonable default if not found
}

export default function ItemComparisonPanel(props: ItemComparisonPanelProps) {
  const [comparison, setComparison] = createSignal<ItemComparison | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");

  createEffect(() => {
    const item = props.equippedItem;
    const listing = props.tradeListing;
    if (!item || !listing) return;

    setLoading(true);
    setError("");
    setComparison(null);

    const weaponAps = getWeaponAps(props.build);

    compareItems(
      item as unknown as Record<string, unknown>,
      listing as unknown as Record<string, unknown>,
      item.slot,
      weaponAps,
    )
      .then((result) => setComparison(result))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  });

  const dpsChangeClass = () => {
    const c = comparison();
    if (!c || !c.is_weapon) return "";
    return c.dps_change_pct > 0 ? "stat-better" : c.dps_change_pct < 0 ? "stat-worse" : "";
  };

  const flatDpsChangeClass = () => {
    const c = comparison();
    if (!c) return "";
    return c.flat_dps_change > 0 ? "stat-better" : c.flat_dps_change < 0 ? "stat-worse" : "";
  };

  return (
    <div class="comparison-panel">
      <Show when={loading()}>
        <div class="panel-loading">
          <span class="spinner" />
          Comparing items...
        </div>
      </Show>

      <Show when={error()}>
        <div class="error-toast">{error()}</div>
      </Show>

      <Show when={comparison()}>
        {(comp) => (
          <>
            <div class="comparison-header">
              <span class="comparison-label">
                {comp().equipped_name} vs {comp().trade_name}
              </span>
            </div>

            {/* Weapon DPS comparison — only for actual weapons */}
            <Show when={comp().is_weapon && comp().equipped_dps && comp().trade_dps
              && (comp().equipped_dps!.total_dps > 0 || comp().trade_dps!.total_dps > 0)}>
              <div class="comparison-dps">
                <div class="comparison-dps-row">
                  <span class="comparison-dps-label">Equipped DPS</span>
                  <span class="comparison-dps-value">{comp().equipped_dps!.total_dps}</span>
                </div>
                <div class="comparison-dps-row">
                  <span class="comparison-dps-label">Trade DPS</span>
                  <span class="comparison-dps-value">{comp().trade_dps!.total_dps}</span>
                </div>
                <div class={`comparison-dps-change ${dpsChangeClass()}`}>
                  {comp().dps_change_pct > 0 ? "+" : ""}{comp().dps_change_pct}% DPS
                </div>
              </div>
            </Show>

            {/* Flat DPS contribution — for non-weapon items (rings, amulets, etc.) */}
            <Show when={!comp().is_weapon
              && (comp().equipped_flat_dps > 0 || comp().trade_flat_dps > 0)}>
              <div class="comparison-dps">
                <div class="comparison-dps-row">
                  <span class="comparison-dps-label">Equipped DPS Contrib.</span>
                  <span class="comparison-dps-value">{comp().equipped_flat_dps}</span>
                </div>
                <div class="comparison-dps-row">
                  <span class="comparison-dps-label">Trade DPS Contrib.</span>
                  <span class="comparison-dps-value">{comp().trade_flat_dps}</span>
                </div>
                <div class={`comparison-dps-change ${flatDpsChangeClass()}`}>
                  {comp().flat_dps_change > 0 ? "+" : ""}{comp().flat_dps_change} DPS
                </div>
              </div>
            </Show>

            {/* Stat deltas */}
            <Show when={comp().stat_deltas.length > 0}>
              <div class="comparison-stats">
                <For each={comp().stat_deltas}>
                  {(delta) => (
                    <div class={`comparison-stat-row ${delta.difference > 0 ? "stat-better" : delta.difference < 0 ? "stat-worse" : ""}`}>
                      <span class="comparison-stat-name">{delta.stat_name}</span>
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
