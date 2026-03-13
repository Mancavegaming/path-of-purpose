import { createSignal, createMemo, createEffect, untrack, For, Show, type Accessor, type Setter } from "solid-js";
import {
  listPublicCharacters,
  importCharacter,
  calculateDps,
  saveBuildData,
} from "../lib/commands";
import type { CharacterEntry } from "../lib/commands";
import type { Build, CalcResult, Item } from "../lib/types";
import { resolveVariantForCalc } from "../lib/buildUtils";
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

interface CharacterPageProps {
  loadedBuild?: Accessor<Build | null>;
  setLoadedBuild?: Setter<Build | null>;
  onSave?: () => void;
  onCharacterImported?: (build: Build) => void;
}

export default function CharacterPage(props: CharacterPageProps) {
  // Account lookup state
  const [accountName, setAccountName] = createSignal(
    localStorage.getItem("pop_poe_account") || "",
  );
  const [characters, setCharacters] = createSignal<CharacterEntry[]>([]);
  const [lookupLoading, setLookupLoading] = createSignal(false);
  const [lookupError, setLookupError] = createSignal("");

  // Character import state
  const [build, setBuild] = createSignal<Build | null>(null);
  const [importLoading, setImportLoading] = createSignal(false);
  const [importError, setImportError] = createSignal("");
  const [importedCharName, setImportedCharName] = createSignal("");

  // Build display state
  const [selectedItem, setSelectedItem] = createSignal<Item | null>(null);
  const [league, setLeague] = createSignal("Mirage");

  // DPS calc state
  const [dpsResult, setDpsResult] = createSignal<CalcResult | null>(null);
  const [dpsLoading, setDpsLoading] = createSignal(false);
  const [dpsError, setDpsError] = createSignal("");
  const [dpsExpanded, setDpsExpanded] = createSignal(false);
  const [selectedSkillIndex, setSelectedSkillIndex] = createSignal(0);
  const [calcConfig, setCalcConfig] = createSignal<CalcConfigState>({ ...DEFAULT_CONFIG });

  // Save state
  const [showSaveInput, setShowSaveInput] = createSignal(false);
  const [saveName, setSaveName] = createSignal("");
  const [saveStatus, setSaveStatus] = createSignal("");

  const displayBuild = () => props.loadedBuild?.() ?? build();

  const skillGroups = createMemo(() => {
    const b = displayBuild();
    if (!b) return [];
    return b.skill_groups;
  });

  async function handleLookup() {
    const name = accountName().trim();
    if (!name) return;

    setLookupLoading(true);
    setLookupError("");
    setCharacters([]);
    setBuild(null);

    try {
      localStorage.setItem("pop_poe_account", name);
      const result = await listPublicCharacters(name);

      if (!Array.isArray(result)) {
        if ((result as { private?: boolean }).private) {
          setLookupError(
            "This profile is private. The player needs to uncheck 'Hide Characters' " +
            "in their PoE account privacy settings at pathofexile.com/account/privacy",
          );
        } else {
          setLookupError((result as { error: string }).error);
        }
        return;
      }
      if (result.length === 0) {
        setLookupError("No characters found. Check the account name (case-sensitive).");
        return;
      }
      setCharacters(result);
    } catch (e) {
      setLookupError(String(e));
    } finally {
      setLookupLoading(false);
    }
  }

  async function handleImport(char: CharacterEntry) {
    setImportLoading(true);
    setImportError("");
    setBuild(null);
    setDpsResult(null);
    setSelectedItem(null);
    setImportedCharName(char.name);

    try {
      const result = await importCharacter(accountName().trim(), char.name);

      if ("error" in result) {
        setImportError((result as { error: string }).error);
        return;
      }

      const b = result as Build;
      setBuild(b);
      props.onCharacterImported?.(b);
      if (char.league) setLeague(char.league);
      // Auto-select main skill
      if (b.main_socket_group > 0) {
        setSelectedSkillIndex(b.main_socket_group - 1);
      }
    } catch (e) {
      setImportError(String(e));
    } finally {
      setImportLoading(false);
    }
  }

  async function handleCalcDps() {
    const b = displayBuild();
    if (!b) return;

    setDpsLoading(true);
    setDpsError("");

    try {
      const resolved = resolveVariantForCalc(b, 0, selectedSkillIndex());
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
    void calcConfig();
    if (untrack(() => dpsResult() && displayBuild() && !dpsLoading())) {
      handleCalcDps();
    }
  });

  function handleItemClick(item: Item) {
    setSelectedItem(item);
  }

  async function handleSave() {
    const b = displayBuild();
    if (!b || !saveName().trim()) return;
    try {
      await saveBuildData(saveName().trim(), b);
      setSaveStatus("Saved!");
      setShowSaveInput(false);
      props.onSave?.();
      setTimeout(() => setSaveStatus(""), 2000);
    } catch (e) {
      setSaveStatus(`Error: ${e}`);
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter") handleLookup();
  }

  return (
    <div class="decode-page">
      <div class="main-content">
        {/* Account Name Input */}
        <div class="decode-input-area">
          <h2>Character Import</h2>
          <p class="decode-hint">
            Enter a PoE account name to load their characters. Profile must be public.
          </p>
          <div class="decode-input-row">
            <input
              type="text"
              class="decode-input"
              placeholder="PoE account name..."
              value={accountName()}
              onInput={(e) => setAccountName(e.currentTarget.value)}
              onKeyDown={handleKeyDown}
            />
            <button
              class="btn-primary"
              onClick={handleLookup}
              disabled={lookupLoading() || !accountName().trim()}
            >
              {lookupLoading() ? "Looking up..." : "Look Up"}
            </button>
          </div>
        </div>

        <Show when={lookupError()}>
          <div class="error-toast">{lookupError()}</div>
        </Show>

        {/* Character List */}
        <Show when={characters().length > 0 && !displayBuild()}>
          <div class="character-list">
            <h3>Select a Character</h3>
            <div class="character-grid">
              <For each={characters()}>
                {(char) => (
                  <button
                    class="character-card"
                    onClick={() => handleImport(char)}
                    disabled={importLoading()}
                  >
                    <span class="character-name">{char.name}</span>
                    <span class="character-details">
                      Level {char.level} {char.class_name}
                    </span>
                    <span class="character-league">{char.league}</span>
                  </button>
                )}
              </For>
            </div>
          </div>
        </Show>

        <Show when={importLoading()}>
          <div class="panel-loading">
            <span class="spinner" />
            Importing {importedCharName()}...
          </div>
        </Show>

        <Show when={importError()}>
          <div class="error-toast">{importError()}</div>
        </Show>

        {/* Build Display */}
        <Show when={displayBuild()}>
          <div class="decode-toolbar">
            <div class="decode-toolbar-left">
              <Show when={skillGroups().length > 0}>
                <SkillSelector
                  skills={skillGroups()}
                  selectedIndex={selectedSkillIndex()}
                  onSelect={setSelectedSkillIndex}
                />
              </Show>
              <button
                class="btn-primary"
                onClick={handleCalcDps}
                disabled={dpsLoading()}
              >
                {dpsLoading() ? "Calculating..." : "Calculate DPS"}
              </button>
            </div>
            <div class="decode-toolbar-right">
              <Show when={!showSaveInput()}>
                <button class="btn-secondary" onClick={() => {
                  setSaveName(importedCharName() || "Imported Character");
                  setShowSaveInput(true);
                }}>
                  Save Build
                </button>
              </Show>
              <Show when={showSaveInput()}>
                <input
                  type="text"
                  class="save-name-input"
                  value={saveName()}
                  onInput={(e) => setSaveName(e.currentTarget.value)}
                  placeholder="Build name..."
                />
                <button class="btn-primary" onClick={handleSave}>Save</button>
                <button class="btn-secondary" onClick={() => setShowSaveInput(false)}>Cancel</button>
              </Show>
              <Show when={saveStatus()}>
                <span class="save-status">{saveStatus()}</span>
              </Show>
              <button
                class="btn-secondary"
                onClick={() => {
                  setBuild(null);
                  setDpsResult(null);
                  setSelectedItem(null);
                }}
              >
                Back to Characters
              </button>
            </div>
          </div>
          <ConfigBar config={calcConfig()} onChange={setCalcConfig} />

          <Show when={dpsError()}>
            <div class="error-toast">{dpsError()}</div>
          </Show>

          <Show when={dpsResult()}>
            <DpsBanner
              result={dpsResult()}
              loading={dpsLoading()}
              error={dpsError()}
              expanded={dpsExpanded()}
              onToggle={() => setDpsExpanded(!dpsExpanded())}
            />
            <Show when={dpsExpanded()}>
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

          <div class="build-layout">
            <div class="build-main">
              <BuildSummary
                build={displayBuild()!}
                onItemClick={handleItemClick}
              />
            </div>
            <RightPanel
              selectedItem={selectedItem()}
              league={league()}
              build={displayBuild()!}
            />
          </div>
        </Show>
      </div>
    </div>
  );
}
