import { createSignal, createMemo, createEffect, untrack, onMount, Show, For, type Accessor, type Setter } from "solid-js";
import { decodeBuild, scrapeBuildGuide, resolveTreeUrls, saveBuildData, calculateDps, fetchLeagues } from "../lib/commands";
import type { Build, BuildGuide, CalcResult, Item } from "../lib/types";
import { guideToBuild, resolveVariantForCalc } from "../lib/buildUtils";
import BuildSummary from "../components/BuildSummary";
import RightPanel from "../components/RightPanel";
import DpsBanner from "../components/DpsBanner";
import DpsBreakdown from "../components/DpsBreakdown";
import DefenceSummary from "../components/DefenceSummary";
import BossReadiness from "../components/BossReadiness";
import BudgetOptimizer from "../components/BudgetOptimizer";
import SkillSelector from "../components/SkillSelector";
import { setStreamBuild } from "../lib/streamStore";
import ConfigBar, { type CalcConfigState, DEFAULT_CONFIG } from "../components/ConfigBar";

function isMobalyticsUrl(input: string): boolean {
  return /mobalytics\.gg/i.test(input);
}

interface DecodePageProps {
  loadedBuild?: Accessor<Build | null>;
  setLoadedBuild?: Setter<Build | null>;
  onSave?: () => void;
}

export default function DecodePage(props: DecodePageProps) {
  const [input, setInput] = createSignal("");
  const [build, setBuild] = createSignal<Build | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");
  const [selectedItem, setSelectedItem] = createSignal<Item | null>(null);
  const [league, setLeague] = createSignal("Mirage");
  const [showSaveInput, setShowSaveInput] = createSignal(false);
  const [saveName, setSaveName] = createSignal("");
  const [saveStatus, setSaveStatus] = createSignal("");

  // Dynamic league list from trade API
  const [availableLeagues, setAvailableLeagues] = createSignal<string[]>([
    "Mirage", "Hardcore Mirage", "Standard", "Hardcore",
  ]);
  onMount(async () => {
    try {
      const leagues = await fetchLeagues();
      if (leagues.length > 0) {
        setAvailableLeagues(leagues);
        // If current selection isn't in the list, default to first
        if (!leagues.includes(league())) {
          setLeague(leagues[0]);
        }
      }
    } catch {
      // Keep fallback defaults
    }
  });

  // Guide + tier state for item synthesis
  const [sourceGuide, setSourceGuide] = createSignal<BuildGuide | null>(null);
  const [itemTier, setItemTier] = createSignal<"basic" | "max">("basic");
  const [tierLoading, setTierLoading] = createSignal(false);

  // DPS calc state
  const [dpsResult, setDpsResult] = createSignal<CalcResult | null>(null);
  const [dpsLoading, setDpsLoading] = createSignal(false);
  const [dpsError, setDpsError] = createSignal("");
  const [dpsExpanded, setDpsExpanded] = createSignal(false);
  const [selectedSkillIndex, setSelectedSkillIndex] = createSignal(0);
  const [activeVariant, setActiveVariant] = createSignal(0);
  const [calcConfig, setCalcConfig] = createSignal<CalcConfigState>({ ...DEFAULT_CONFIG });

  // If a saved build was loaded externally (e.g. from sidebar), display it
  const displayBuild = () => props.loadedBuild?.() ?? build();

  // Skill groups for the skill selector — uses the active variant
  const skillGroups = createMemo(() => {
    const b = displayBuild();
    if (!b) return [];
    const idx = activeVariant();
    if (b.skill_sets.length > 0 && idx < b.skill_sets.length) {
      return b.skill_sets[idx].skills;
    }
    return b.skill_groups;
  });

  // Initialize skill selector to main skill
  const initSkillIndex = () => {
    const b = displayBuild();
    if (b && b.main_socket_group > 0) {
      setSelectedSkillIndex(b.main_socket_group - 1);
    }
  };

  async function handleCalcDps() {
    const b = displayBuild();
    if (!b) return;

    setDpsLoading(true);
    setDpsError("");

    try {
      const resolved = resolveVariantForCalc(b, activeVariant(), selectedSkillIndex());
      const result = await calculateDps(resolved, undefined, calcConfig() as unknown as Record<string, unknown>);
      setDpsResult(result);
      setStreamBuild(displayBuild(), result);
    } catch (e) {
      setDpsError(String(e));
    } finally {
      setDpsLoading(false);
    }
  }

  // Auto-recalculate DPS when config changes (only if DPS was already calculated)
  createEffect(() => {
    void calcConfig(); // track config changes
    if (untrack(() => dpsResult() && displayBuild() && !dpsLoading())) {
      handleCalcDps();
    }
  });

  async function handleLoad() {
    const raw = input().trim();
    if (!raw) return;

    setLoading(true);
    setError("");
    setBuild(null);
    setSelectedItem(null);
    setDpsResult(null);
    setDpsError("");
    setDpsExpanded(false);
    setSourceGuide(null);
    setItemTier("basic");
    props.setLoadedBuild?.(null);

    try {
      if (isMobalyticsUrl(raw)) {
        // Mobalytics guide URL → scrape then convert
        let guide: BuildGuide = await scrapeBuildGuide(raw);
        try {
          guide = await resolveTreeUrls(guide);
        } catch {
          // Non-critical — guide still works without tree URLs
        }
        setSourceGuide(guide);
        setBuild(await guideToBuild(guide));
      } else {
        // PoB code, pobb.in URL, or any other URL → decodeBuild handles all
        const result: Build = await decodeBuild(raw);
        setBuild(result);
      }
      // Initialize skill selector to main skill after decode
      setTimeout(initSkillIndex, 0);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleTierChange(newTier: "basic" | "max") {
    const guide = sourceGuide();
    if (!guide || newTier === itemTier()) return;

    setTierLoading(true);
    setItemTier(newTier);
    try {
      const rebuilt = await guideToBuild(guide, newTier);
      setBuild(rebuilt);
    } catch (e) {
      setError(`Tier change failed: ${String(e)}`);
    } finally {
      setTierLoading(false);
    }
  }

  function handleItemClick(item: Item) {
    // Toggle selection
    const current = selectedItem();
    if (current && current.id === item.id && current.slot === item.slot) {
      setSelectedItem(null);
    } else {
      setSelectedItem(item);
    }
  }

  function handleStartSave() {
    const b = displayBuild();
    if (b) {
      setSaveName(b.build_name || b.ascendancy_name || b.class_name || "My Build");
      setShowSaveInput(true);
      setSaveStatus("");
    }
  }

  async function handleConfirmSave() {
    const b = displayBuild();
    const name = saveName().trim();
    if (!b || !name) return;

    try {
      await saveBuildData(name, b);
      setSaveStatus("Saved!");
      setShowSaveInput(false);
      props.onSave?.();
    } catch (e) {
      setSaveStatus(`Error: ${String(e)}`);
    }
  }

  return (
    <div>
      <h1 class="page-title">Build Viewer</h1>
      <p class="page-subtitle">
        Paste a PoB code, pobb.in link, or mobalytics guide URL
      </p>

      <div class="input-group">
        <label for="build-input">PoB Code or URL</label>
        <textarea
          id="build-input"
          placeholder="Paste a PoB export code, pobb.in link, or mobalytics.gg URL..."
          value={input()}
          onInput={(e) => setInput(e.currentTarget.value)}
          rows={4}
        />
      </div>

      <div class="decode-actions">
        <button onClick={handleLoad} disabled={loading() || !input().trim()}>
          <Show when={loading()} fallback="Load Build">
            <span class="spinner" />
            Loading...
          </Show>
        </button>

        <Show when={displayBuild()}>
          <div class="league-selector">
            <label for="league-select">League:</label>
            <select
              id="league-select"
              value={league()}
              onChange={(e) => setLeague(e.currentTarget.value)}
            >
              <For each={availableLeagues()}>
                {(l) => <option value={l}>{l}</option>}
              </For>
            </select>
          </div>
          <Show when={sourceGuide()}>
            <div class="tier-selector">
              <label>Item Tier:</label>
              <button
                class={`tier-btn ${itemTier() === "basic" ? "tier-active" : ""}`}
                onClick={() => handleTierChange("basic")}
                disabled={tierLoading()}
              >
                Budget
              </button>
              <button
                class={`tier-btn ${itemTier() === "max" ? "tier-active" : ""}`}
                onClick={() => handleTierChange("max")}
                disabled={tierLoading()}
              >
                Endgame
              </button>
              <Show when={tierLoading()}>
                <span class="spinner" />
              </Show>
            </div>
          </Show>
          <Show when={!showSaveInput()}>
            <button class="generator-save-btn" onClick={handleStartSave}>
              Save Build
            </button>
          </Show>
        </Show>
      </div>

      <Show when={showSaveInput()}>
        <div class="save-build-row" style={{ "margin-top": "8px" }}>
          <input
            type="text"
            value={saveName()}
            onInput={(e) => setSaveName(e.currentTarget.value)}
            placeholder="Build name..."
            class="save-build-input"
          />
          <button onClick={handleConfirmSave} disabled={!saveName().trim()}>
            Confirm
          </button>
          <button
            class="generator-reset-btn"
            onClick={() => setShowSaveInput(false)}
          >
            Cancel
          </button>
        </div>
      </Show>
      <Show when={saveStatus()}>
        <div
          class={saveStatus().startsWith("Error") ? "error-toast" : "info-box"}
          style={{ "margin-top": "8px" }}
        >
          {saveStatus()}
        </div>
      </Show>

      <Show when={error()}>
        <div class="error-toast" style={{ "margin-top": "16px" }}>
          {error()}
        </div>
      </Show>

      {/* DPS Calculator */}
      <Show when={displayBuild()}>
        <div class="dps-calc-row">
          <Show when={skillGroups().length > 0}>
            <SkillSelector
              skills={skillGroups()}
              selectedIndex={selectedSkillIndex()}
              onSelect={setSelectedSkillIndex}
            />
          </Show>
          <button
            class="dps-calc-btn"
            onClick={handleCalcDps}
            disabled={dpsLoading()}
          >
            <Show when={dpsLoading()} fallback="Calculate DPS">
              <span class="spinner" /> Calculating...
            </Show>
          </button>
        </div>
        <ConfigBar config={calcConfig()} onChange={setCalcConfig} />
      </Show>

      <Show when={dpsResult() || dpsLoading() || dpsError()}>
        <DpsBanner
          result={dpsResult()}
          loading={dpsLoading()}
          error={dpsError()}
          expanded={dpsExpanded()}
          onToggle={() => setDpsExpanded(!dpsExpanded())}
        />
        <Show when={dpsExpanded() && dpsResult()}>
          <DpsBreakdown result={dpsResult()!} />
        </Show>
        <DefenceSummary defence={dpsResult()?.defence ?? null} />
        <BossReadiness dpsResult={dpsResult()} />
        <Show when={displayBuild()}>
          <BudgetOptimizer
            build={displayBuild()!}
            league={league()}
            config={calcConfig() as unknown as Record<string, unknown>}
          />
        </Show>
      </Show>

      <Show when={displayBuild()}>
        <div class="decode-layout">
          <div class="decode-main">
            <BuildSummary
              build={displayBuild()!}
              onItemClick={handleItemClick}
              selectedItem={selectedItem()}
              onVariantChange={setActiveVariant}
            />
          </div>
          <RightPanel
            selectedItem={selectedItem()}
            league={league()}
            build={displayBuild()!}
            dpsResult={dpsResult()}
          />
        </div>
      </Show>
    </div>
  );
}
