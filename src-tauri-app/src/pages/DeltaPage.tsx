import { createSignal, For, Show, type Accessor } from "solid-js";
import { analyzeDelta, compareItems, decodeBuild } from "../lib/commands";
import type { Build, DeltaReport, Item, ItemComparison, TradeListing } from "../lib/types";
import type { SavedBuildEntry } from "../lib/commands";
import { loadSavedBuild } from "../lib/commands";
import { guideToBuild } from "../lib/buildUtils";
import type { BuildGuide } from "../lib/types";
import GapCard from "../components/GapCard";
import TradePanel from "../components/TradePanel";
import ItemComparisonPanel from "../components/ItemComparisonPanel";
import AiAdvisorPanel from "../components/AiAdvisorPanel";

/** Strip PoB internal tags and resolve ranges from mod text. */
function cleanMod(text: string): string {
  let clean = text.replace(/\{[^}]*\}/g, "").trim();
  clean = clean.replace(/\((\d+)-(\d+)\)/g, (_m, _a, b) => b);
  return clean || text;
}

interface DeltaPageProps {
  loadedBuild?: Accessor<Build | null>;
  characterBuild?: Accessor<Build | null>;
  savedBuilds?: Accessor<SavedBuildEntry[]>;
}

export default function DeltaPage(props: DeltaPageProps) {
  const [report, setReport] = createSignal<DeltaReport | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");

  // Local guide build (can come from props or local paste/load)
  const [localGuide, setLocalGuide] = createSignal<Build | null>(null);
  const [pobCode, setPobCode] = createSignal("");
  const [decodeLoading, setDecodeLoading] = createSignal(false);
  const [decodeError, setDecodeError] = createSignal("");

  // Trade search for guide target items
  const [selectedItem, setSelectedItem] = createSignal<Item | null>(null);
  const [selectedSlot, setSelectedSlot] = createSignal<string | null>(null);

  const guideBuild = () => localGuide() ?? props.loadedBuild?.() ?? null;
  const charBuild = () => props.characterBuild?.() ?? null;
  const canAnalyze = () => !!guideBuild() && !!charBuild();

  async function handleDecodePob() {
    const code = pobCode().trim();
    if (!code) return;
    setDecodeLoading(true);
    setDecodeError("");
    try {
      const build = await decodeBuild(code);
      setLocalGuide(build as Build);
    } catch (e) {
      setDecodeError(String(e));
    } finally {
      setDecodeLoading(false);
    }
  }

  async function handleLoadSaved(name: string) {
    try {
      const result = await loadSavedBuild(name);
      if (result.kind === "build") {
        setLocalGuide(result.data as Build);
      } else {
        setLocalGuide(await guideToBuild(result.data as BuildGuide));
      }
    } catch (e) {
      setDecodeError(String(e));
    }
  }

  async function handleAnalyze() {
    const guide = guideBuild();
    const character = charBuild();
    if (!guide || !character) return;

    setLoading(true);
    setError("");
    setReport(null);

    try {
      const result = await analyzeDelta(guide, character);
      setReport(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  // The character's current item in the selected slot (for DPS comparison baseline)
  const [charSlotItem, setCharSlotItem] = createSignal<Item | null>(null);
  const [slotComparison, setSlotComparison] = createSignal<ItemComparison | null>(null);

  // Trade listing comparison
  const [selectedTradeListing, setSelectedTradeListing] = createSignal<TradeListing | null>(null);

  function handleSlotClick(slotName: string) {
    const guide = guideBuild();
    if (!guide) return;

    // Toggle off if clicking same slot
    if (selectedSlot() === slotName) {
      setSelectedSlot(null);
      setSelectedItem(null);
      setCharSlotItem(null);
      setSlotComparison(null);
      setSelectedTradeListing(null);
      return;
    }

    // Find the guide item for this slot (what the user is aiming for)
    const guideItem = guide.items?.find((i: Item) => i.slot === slotName);
    if (guideItem) {
      setSelectedSlot(slotName);
      setSelectedItem(guideItem);
      setSlotComparison(null);
      setSelectedTradeListing(null);

      // Find the character's current item for this slot (DPS comparison baseline)
      const char = charBuild();
      const charItem = char?.items?.find((i: Item) => i.slot === slotName) ?? null;
      setCharSlotItem(charItem);

      // Calculate DPS comparison between equipped and guide target
      if (charItem) {
        compareItems(
          charItem as unknown as Record<string, unknown>,
          guideItem as unknown as Record<string, unknown>,
          slotName,
          0,
        ).then((cmp) => setSlotComparison(cmp)).catch(() => {});
      }
    }
  }

  // Determine league from character build
  const league = () => "Mirage"; // Current league

  function severityClass(pct: number): string {
    if (pct >= 95) return "delta-good";
    if (pct >= 70) return "delta-ok";
    if (pct >= 40) return "delta-warn";
    return "delta-bad";
  }

  return (
    <div class="decode-page">
      <div class="main-content">
        <div class="decode-input-area">
          <h2>Delta Report</h2>
          <p class="decode-hint">
            Compare your imported character against a guide build to see exactly what to upgrade next.
          </p>

          <div class="delta-build-cards">
            <div class="delta-build-card">
              <div class="delta-build-label">Guide Build</div>
              <Show when={guideBuild()} fallback={
                <div class="delta-guide-input">
                  <div class="delta-guide-row">
                    <input
                      type="text"
                      class="decode-input"
                      placeholder="Paste PoB export code..."
                      value={pobCode()}
                      onInput={(e) => setPobCode(e.currentTarget.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") handleDecodePob(); }}
                    />
                    <button
                      class="btn-primary"
                      onClick={handleDecodePob}
                      disabled={decodeLoading() || !pobCode().trim()}
                    >
                      {decodeLoading() ? "Loading..." : "Load"}
                    </button>
                  </div>
                  <Show when={(props.savedBuilds?.()?.length ?? 0) > 0}>
                    <select
                      class="delta-saved-select"
                      onChange={(e) => {
                        const val = e.currentTarget.value;
                        if (val) handleLoadSaved(val);
                        e.currentTarget.value = "";
                      }}
                    >
                      <option value="">— or load a saved build —</option>
                      <For each={props.savedBuilds!()}>
                        {(entry) => <option value={entry.name}>{entry.name}</option>}
                      </For>
                    </select>
                  </Show>
                  <Show when={decodeError()}>
                    <div class="error-toast" style={{ "margin-top": "6px", "font-size": "12px" }}>{decodeError()}</div>
                  </Show>
                </div>
              }>
                <div class="delta-build-info">
                  <span class="delta-build-name">
                    {guideBuild()!.build_name || guideBuild()!.ascendancy_name || "Guide"}
                  </span>
                  <span class="delta-build-detail">
                    Level {guideBuild()!.level} {guideBuild()!.ascendancy_name || guideBuild()!.class_name}
                  </span>
                  <button
                    class="delta-change-btn"
                    onClick={() => { setLocalGuide(null); setReport(null); }}
                  >
                    Change
                  </button>
                </div>
              </Show>
            </div>

            <div class="delta-vs">vs</div>

            <div class="delta-build-card">
              <div class="delta-build-label">Your Character</div>
              <Show when={charBuild()} fallback={
                <div class="delta-build-empty">
                  Import your character from the Character Import tab first.
                </div>
              }>
                <div class="delta-build-info">
                  <span class="delta-build-name">
                    {charBuild()!.build_name || charBuild()!.ascendancy_name || "Character"}
                  </span>
                  <span class="delta-build-detail">
                    Level {charBuild()!.level} {charBuild()!.ascendancy_name || charBuild()!.class_name}
                  </span>
                </div>
              </Show>
            </div>
          </div>

          <button
            class="btn-primary"
            onClick={handleAnalyze}
            disabled={loading() || !canAnalyze()}
            style={{ "margin-top": "12px" }}
          >
            <Show when={loading()} fallback="Analyze Delta">
              <span class="spinner" />
              Analyzing...
            </Show>
          </button>
        </div>

        <Show when={error()}>
          <div class="error-toast">{error()}</div>
        </Show>

        <Show when={report()}>
          {/* Top Gaps */}
          <div class="delta-section">
            <h3 class="delta-section-title">
              Top Priorities: {report()!.character_name} vs {report()!.guide_build_name}
            </h3>
            <div class="delta-top-gaps">
              <For each={report()!.top_gaps}>
                {(gap) => <GapCard gap={gap} />}
              </For>
            </div>
          </div>

          {/* Passive Tree */}
          <div class="delta-section">
            <h3 class="delta-section-title">
              Passive Tree
              <span class={`delta-pct ${severityClass(report()!.passive_delta.match_pct)}`}>
                {report()!.passive_delta.match_pct.toFixed(0)}%
              </span>
            </h3>
            <div class="delta-passive-summary">
              <div class="delta-stat">
                <span class="delta-stat-value">{report()!.passive_delta.guide_total}</span>
                <span class="delta-stat-label">Guide nodes</span>
              </div>
              <div class="delta-stat">
                <span class="delta-stat-value">{report()!.passive_delta.character_total}</span>
                <span class="delta-stat-label">Your nodes</span>
              </div>
              <div class="delta-stat">
                <span class="delta-stat-value delta-bad">{report()!.passive_delta.missing_count}</span>
                <span class="delta-stat-label">Missing</span>
              </div>
              <div class="delta-stat">
                <span class="delta-stat-value delta-warn">{report()!.passive_delta.extra_count}</span>
                <span class="delta-stat-label">Extra</span>
              </div>
            </div>
          </div>

          {/* Gear */}
          <div class="delta-section">
            <h3 class="delta-section-title">
              Gear
              <span class={`delta-pct ${severityClass(report()!.gear_delta.overall_match_pct)}`}>
                {report()!.gear_delta.overall_match_pct.toFixed(0)}%
              </span>
            </h3>
            <div class="delta-gear-grid">
              <For each={report()!.gear_delta.slot_deltas}>
                {(slot) => (
                  <div
                    class={`delta-slot-card delta-slot-clickable ${slot.match_pct >= 95 ? "delta-slot-good" : ""} ${selectedSlot() === slot.slot ? "delta-slot-selected" : ""}`}
                    onClick={() => handleSlotClick(slot.slot)}
                  >
                    <div class="delta-slot-header">
                      <span class="delta-slot-name">{slot.slot}</span>
                      <span class={`delta-pct-badge ${severityClass(slot.match_pct)}`}>
                        {slot.match_pct.toFixed(0)}%
                      </span>
                    </div>
                    <div class="delta-slot-items">
                      <span class="delta-slot-guide" title={slot.guide_item_name}>
                        {slot.guide_item_name || "—"}
                      </span>
                      <span class="delta-slot-arrow">→</span>
                      <span class="delta-slot-char" title={slot.character_item_name}>
                        {slot.character_item_name || "—"}
                      </span>
                    </div>
                    <Show when={slot.missing_mods.length > 0}>
                      <ul class="delta-missing-mods">
                        <For each={slot.missing_mods.slice(0, 4)}>
                          {(mod) => (
                            <li class="delta-missing-mod">
                              <span class="delta-mod-importance" style={{
                                opacity: String(0.4 + mod.importance * 0.6),
                              }}>
                                {cleanMod(mod.mod_text)}
                              </span>
                            </li>
                          )}
                        </For>
                        <Show when={slot.missing_mods.length > 4}>
                          <li class="delta-missing-mod delta-more">
                            +{slot.missing_mods.length - 4} more
                          </li>
                        </Show>
                      </ul>
                    </Show>
                  </div>
                )}
              </For>
            </div>
            <Show when={selectedItem()}>
              <div class="delta-trade-panel">
                <div class="delta-trade-header">
                  <h4 class="delta-trade-title">
                    Upgrade: {selectedSlot()}
                    <button class="delta-change-btn" onClick={() => { setSelectedItem(null); setSelectedSlot(null); setCharSlotItem(null); setSlotComparison(null); setSelectedTradeListing(null); }}>
                      Close
                    </button>
                  </h4>

                  {/* Side-by-side: what you have vs what you want */}
                  <div class="delta-compare-cards">
                    <div class="delta-compare-card delta-compare-current">
                      <div class="delta-compare-label">You Have</div>
                      <div class="delta-compare-name">
                        {charSlotItem()?.name || charSlotItem()?.base_type || "Empty"}
                      </div>
                      <Show when={charSlotItem()?.base_type && charSlotItem()?.name}>
                        <div class="delta-compare-base">{charSlotItem()!.base_type}</div>
                      </Show>
                      <Show when={charSlotItem()}>
                        <ul class="delta-compare-mods">
                          <For each={charSlotItem()!.implicits}>
                            {(mod) => <li class="mod-implicit">{cleanMod(mod.text)}</li>}
                          </For>
                          <For each={charSlotItem()!.explicits.slice(0, 5)}>
                            {(mod) => <li>{cleanMod(mod.text)}</li>}
                          </For>
                          <Show when={(charSlotItem()!.explicits.length) > 5}>
                            <li class="delta-more">+{charSlotItem()!.explicits.length - 5} more</li>
                          </Show>
                        </ul>
                      </Show>
                      <Show when={slotComparison()}>
                        <div class="delta-compare-dps">
                          <Show when={slotComparison()!.is_weapon && slotComparison()!.equipped_dps}>
                            <span class="delta-dps-value">{slotComparison()!.equipped_dps!.total_dps.toFixed(1)} DPS</span>
                            <span class="delta-dps-detail">
                              {slotComparison()!.equipped_dps!.physical_dps.toFixed(0)} phys / {slotComparison()!.equipped_dps!.elemental_dps.toFixed(0)} ele
                            </span>
                          </Show>
                          <Show when={!slotComparison()!.is_weapon && slotComparison()!.equipped_flat_dps > 0}>
                            <span class="delta-dps-value">+{slotComparison()!.equipped_flat_dps.toFixed(1)} flat DPS</span>
                          </Show>
                        </div>
                      </Show>
                    </div>

                    <div class="delta-compare-arrow">→</div>

                    <div class="delta-compare-card delta-compare-target">
                      <div class="delta-compare-label">Guide Target</div>
                      <div class="delta-compare-name">
                        {selectedItem()!.name !== "New Item" ? selectedItem()!.name : selectedItem()!.base_type}
                      </div>
                      <Show when={selectedItem()!.base_type && selectedItem()!.name && selectedItem()!.name !== "New Item"}>
                        <div class="delta-compare-base">{selectedItem()!.base_type}</div>
                      </Show>
                      <ul class="delta-compare-mods">
                        <For each={selectedItem()!.implicits}>
                          {(mod) => <li class="mod-implicit">{cleanMod(mod.text)}</li>}
                        </For>
                        <For each={selectedItem()!.explicits.slice(0, 5)}>
                          {(mod) => <li>{cleanMod(mod.text)}</li>}
                        </For>
                        <Show when={(selectedItem()!.explicits.length) > 5}>
                          <li class="delta-more">+{selectedItem()!.explicits.length - 5} more</li>
                        </Show>
                      </ul>
                      <Show when={slotComparison()}>
                        <div class="delta-compare-dps">
                          <Show when={slotComparison()!.is_weapon && slotComparison()!.trade_dps}>
                            <span class="delta-dps-value">{slotComparison()!.trade_dps!.total_dps.toFixed(1)} DPS</span>
                            <span class="delta-dps-detail">
                              {slotComparison()!.trade_dps!.physical_dps.toFixed(0)} phys / {slotComparison()!.trade_dps!.elemental_dps.toFixed(0)} ele
                            </span>
                          </Show>
                          <Show when={!slotComparison()!.is_weapon && slotComparison()!.trade_flat_dps > 0}>
                            <span class="delta-dps-value">+{slotComparison()!.trade_flat_dps.toFixed(1)} flat DPS</span>
                          </Show>
                          <Show when={slotComparison()!.dps_change_pct !== 0}>
                            <span class={`delta-dps-change ${slotComparison()!.dps_change_pct > 0 ? "delta-dps-up" : "delta-dps-down"}`}>
                              {slotComparison()!.dps_change_pct > 0 ? "+" : ""}{slotComparison()!.dps_change_pct.toFixed(1)}%
                            </span>
                          </Show>
                        </div>
                      </Show>
                    </div>
                  </div>
                </div>

                <TradePanel
                  selectedItem={selectedItem()}
                  equippedItem={charSlotItem()}
                  league={league()}
                  onListingSelect={setSelectedTradeListing}
                />

                <Show when={(charSlotItem() || selectedItem()) && selectedTradeListing()}>
                  <ItemComparisonPanel
                    equippedItem={(charSlotItem() ?? selectedItem())!}
                    tradeListing={selectedTradeListing()!}
                    build={guideBuild()}
                  />
                </Show>
              </div>
            </Show>
          </div>

          {/* Gems */}
          <div class="delta-section">
            <h3 class="delta-section-title">
              Skill Gems
              <Show when={report()!.gem_delta.total_missing_supports > 0}>
                <span class="delta-pct delta-warn">
                  {report()!.gem_delta.total_missing_supports} missing supports
                </span>
              </Show>
            </h3>
            <div class="delta-gem-grid">
              <For each={report()!.gem_delta.group_deltas}>
                {(group) => (
                  <div class={`delta-gem-card ${group.is_missing_entirely ? "delta-gem-missing" : group.match_pct >= 100 ? "delta-gem-good" : ""}`}>
                    <div class="delta-gem-header">
                      <span class="delta-gem-name">{group.skill_name}</span>
                      <span class={`delta-pct-badge ${severityClass(group.match_pct)}`}>
                        {group.is_missing_entirely ? "MISSING" : `${group.match_pct.toFixed(0)}%`}
                      </span>
                    </div>
                    <Show when={group.missing_supports.length > 0}>
                      <div class="delta-gem-missing-list">
                        <span class="delta-gem-label">Missing:</span>
                        <For each={group.missing_supports}>
                          {(name) => <span class="delta-gem-tag delta-gem-tag-missing">{name}</span>}
                        </For>
                      </div>
                    </Show>
                    <Show when={group.extra_supports.length > 0}>
                      <div class="delta-gem-extra-list">
                        <span class="delta-gem-label">Extra:</span>
                        <For each={group.extra_supports}>
                          {(name) => <span class="delta-gem-tag delta-gem-tag-extra">{name}</span>}
                        </For>
                      </div>
                    </Show>
                  </div>
                )}
              </For>
            </div>
          </div>
        </Show>

        {/* AI Advisor — available when delta report is loaded */}
        <Show when={report()}>
          <div class="delta-section">
            <h3 class="delta-section-title">AI Advisor</h3>
            <AiAdvisorPanel
              build={guideBuild()}
              selectedItem={selectedItem()}
              selectedListing={selectedTradeListing()}
              deltaReport={report()}
            />
          </div>
        </Show>
      </div>
    </div>
  );
}
