import { createSignal, createMemo, createEffect, onCleanup, untrack, Show, type Accessor, type Setter } from "solid-js";
import type { Build, CalcResult, Item, PassiveSpec, SkillGroup } from "../lib/types";
import { calculateDps, saveBuildData } from "../lib/commands";
import { resolveVariantForCalc } from "../lib/buildUtils";
import BuildHeaderEditor from "../components/editor/BuildHeaderEditor";
import SkillsEditor from "../components/editor/SkillsEditor";
import GearEditor from "../components/editor/GearEditor";
import TreeEditor from "../components/editor/TreeEditor";
import AtlasEditor from "../components/editor/AtlasEditor";
import VariantTabs from "../components/VariantTabs";
import DpsBanner from "../components/DpsBanner";
import DpsBreakdown from "../components/DpsBreakdown";
import DefenceSummary from "../components/DefenceSummary";
import BossReadiness from "../components/BossReadiness";
import SkillSelector from "../components/SkillSelector";
import ConfigBar, { type CalcConfigState, DEFAULT_CONFIG } from "../components/ConfigBar";
import EditorAiPanel, { type BuildAction } from "../components/editor/EditorAiPanel";

type EditorTab = "gear" | "skills" | "tree" | "atlas";

function createEmptyBuild(): Build {
  return {
    class_name: "Marauder",
    ascendancy_name: "",
    level: 1,
    main_socket_group: 1,
    passive_specs: [{
      title: "Default",
      tree_version: "",
      class_id: 0,
      ascendancy_id: 0,
      nodes: [],
      overrides: {},
      url: "",
      key_nodes: [],
      total_points: 0,
      priority: "",
    }],
    skill_groups: [],
    items: [],
    config: { entries: {} },
    skill_sets: [],
    item_sets: [],
    active_skill_set: 0,
    active_item_set: 0,
    pob_version: "",
    build_name: "New Build",
  };
}

interface EditorPageProps {
  loadedBuild?: Accessor<Build | null>;
  setLoadedBuild?: Setter<Build | null>;
  onSave?: () => void;
}

export default function EditorPage(props: EditorPageProps) {
  const [build, setBuild] = createSignal<Build>(createEmptyBuild());
  const [activeTab, setActiveTab] = createSignal<EditorTab>("skills");
  const [activeVariant, setActiveVariant] = createSignal(0);
  const [saveName, setSaveName] = createSignal("");
  const [saveStatus, setSaveStatus] = createSignal("");
  // DPS state
  const [dpsResult, setDpsResult] = createSignal<CalcResult | null>(null);
  const [dpsLoading, setDpsLoading] = createSignal(false);
  const [dpsError, setDpsError] = createSignal("");
  const [dpsExpanded, setDpsExpanded] = createSignal(false);
  const [selectedSkillIndex, setSelectedSkillIndex] = createSignal(0);
  const [calcConfig, setCalcConfig] = createSignal<CalcConfigState>({ ...DEFAULT_CONFIG });

  // Next item ID counter
  let nextItemId = 1000;
  function getNextId(): number {
    return ++nextItemId;
  }

  // Variant titles
  const variantTitles = createMemo(() =>
    build().passive_specs.map((s) => s.title),
  );

  // Active variant's data
  const activeSpec = createMemo(() => {
    const idx = activeVariant();
    const specs = build().passive_specs;
    return idx < specs.length ? specs[idx] : specs[0];
  });

  const activeSkillGroups = createMemo(() => {
    const b = build();
    const idx = activeVariant();
    if (b.skill_sets.length > 0 && idx < b.skill_sets.length) {
      return b.skill_sets[idx].skills;
    }
    return b.skill_groups;
  });

  const activeItems = createMemo(() => {
    const b = build();
    const idx = activeVariant();
    if (b.item_sets.length > 0 && idx < b.item_sets.length) {
      const slotMap = b.item_sets[idx].slot_map;
      const byId = new Map(b.items.map((it) => [it.id, it]));
      const items: Item[] = [];
      for (const [slot, itemId] of Object.entries(slotMap)) {
        const item = byId.get(itemId);
        if (item) items.push({ ...item, slot });
      }
      return items;
    }
    return b.items;
  });

  const activeBracketTitle = createMemo(() => variantTitles()[activeVariant()] ?? "Default");
  const activeNotes = createMemo(() => build().bracket_notes?.[activeBracketTitle()] ?? "");
  const activeAtlas = createMemo(() => build().bracket_atlas?.[activeBracketTitle()] ?? "");
  const activeMapWarnings = createMemo(() => build().bracket_map_warnings?.[activeBracketTitle()] ?? []);

  // ---- Updaters ----

  function updateBuild(partial: Partial<Build>) {
    setBuild((prev) => ({ ...prev, ...partial }));
  }

  function updateSkillGroups(groups: SkillGroup[]) {
    const b = build();
    const idx = activeVariant();
    if (b.skill_sets.length > 0 && idx < b.skill_sets.length) {
      const sets = [...b.skill_sets];
      sets[idx] = { ...sets[idx], skills: groups };
      updateBuild({ skill_sets: sets });
    } else {
      updateBuild({ skill_groups: groups });
    }
  }

  function updateItems(items: Item[]) {
    const b = build();
    const idx = activeVariant();
    if (b.item_sets.length > 0 && idx < b.item_sets.length) {
      // Update the flat items array and the slot map
      const existingIds = new Set(items.map((it) => it.id));
      const otherItems = b.items.filter((it) => !existingIds.has(it.id));
      const allItems = [...otherItems, ...items];
      const slotMap: Record<string, number> = {};
      for (const it of items) {
        slotMap[it.slot] = it.id;
      }
      const sets = [...b.item_sets];
      sets[idx] = { ...sets[idx], slot_map: slotMap };
      updateBuild({ items: allItems, item_sets: sets });
    } else {
      updateBuild({ items });
    }
  }

  function updateSpec(spec: PassiveSpec) {
    const specs = [...build().passive_specs];
    const idx = activeVariant();
    if (idx < specs.length) {
      specs[idx] = spec;
      updateBuild({ passive_specs: specs });
    }
  }

  function updateBracketNotes(notes: string) {
    const title = activeBracketTitle();
    updateBuild({
      bracket_notes: { ...(build().bracket_notes ?? {}), [title]: notes },
    });
  }

  function updateBracketAtlas(atlas: string) {
    const title = activeBracketTitle();
    updateBuild({
      bracket_atlas: { ...(build().bracket_atlas ?? {}), [title]: atlas },
    });
  }

  function updateBracketMapWarnings(warnings: string[]) {
    const title = activeBracketTitle();
    updateBuild({
      bracket_map_warnings: { ...(build().bracket_map_warnings ?? {}), [title]: warnings },
    });
  }

  // ---- Variant management ----

  function addVariant() {
    const b = build();
    const title = `Variant ${b.passive_specs.length + 1}`;
    const newSpec: PassiveSpec = {
      title,
      tree_version: "",
      class_id: 0,
      ascendancy_id: 0,
      nodes: [],
      overrides: {},
      url: "",
      key_nodes: [],
      total_points: 0,
      priority: "",
    };

    // If this is the first time adding variants, migrate flat data to sets
    if (b.skill_sets.length === 0 && b.passive_specs.length === 1) {
      const currentTitle = b.passive_specs[0].title;
      const slotMap: Record<string, number> = {};
      for (const it of b.items) {
        slotMap[it.slot] = it.id;
      }
      updateBuild({
        passive_specs: [...b.passive_specs, newSpec],
        skill_sets: [
          { title: currentTitle, skills: [...b.skill_groups] },
          { title, skills: [] },
        ],
        item_sets: [
          { title: currentTitle, slot_map: slotMap },
          { title, slot_map: {} },
        ],
      });
    } else {
      updateBuild({
        passive_specs: [...b.passive_specs, newSpec],
        skill_sets: [...b.skill_sets, { title, skills: [] }],
        item_sets: [...b.item_sets, { title, slot_map: {} }],
      });
    }
  }

  function removeVariant(idx: number) {
    const b = build();
    if (b.passive_specs.length <= 1) return;
    const specs = b.passive_specs.filter((_, i) => i !== idx);
    const skillSets = b.skill_sets.filter((_, i) => i !== idx);
    const itemSets = b.item_sets.filter((_, i) => i !== idx);
    updateBuild({ passive_specs: specs, skill_sets: skillSets, item_sets: itemSets });
    if (activeVariant() >= specs.length) {
      setActiveVariant(specs.length - 1);
    }
  }

  function renameVariant(idx: number) {
    const current = build().passive_specs[idx]?.title ?? "";
    const name = prompt("Variant name:", current);
    if (name && name !== current) {
      const specs = [...build().passive_specs];
      specs[idx] = { ...specs[idx], title: name };
      // Also rename in skill_sets and item_sets
      const skillSets = [...build().skill_sets];
      if (idx < skillSets.length) skillSets[idx] = { ...skillSets[idx], title: name };
      const itemSets = [...build().item_sets];
      if (idx < itemSets.length) itemSets[idx] = { ...itemSets[idx], title: name };
      updateBuild({ passive_specs: specs, skill_sets: skillSets, item_sets: itemSets });
    }
  }

  // ---- Actions ----

  function handleNew() {
    setBuild(createEmptyBuild());
    setSaveName("");
    setSaveStatus("");
    setDpsResult(null);
    setActiveVariant(0);
  }

  function handleLoadFromViewer() {
    const loaded = props.loadedBuild?.();
    if (loaded) {
      setBuild({ ...loaded });
      setSaveName(loaded.build_name || "");
      // Sync next ID
      const maxId = Math.max(...loaded.items.map((it) => it.id), 0);
      nextItemId = maxId + 1;
    }
  }

  async function handleSave() {
    const name = saveName().trim();
    if (!name) {
      setSaveStatus("Enter a name first.");
      return;
    }
    try {
      await saveBuildData(name, build());
      setSaveStatus("Saved!");
      props.onSave?.();
      setTimeout(() => setSaveStatus(""), 2000);
    } catch (e) {
      setSaveStatus(`Error: ${String(e)}`);
    }
  }

  function handleAiAction(action: BuildAction) {
    if (action.type === "add_skill_group") {
      // Create a new empty skill group
      const slot = action.slot || "Body Armour";
      const groups = [...activeSkillGroups(), {
        slot,
        label: "",
        is_enabled: true,
        gems: [],
      }];
      updateSkillGroups(groups);
      // Set as main if it's the first group
      if (groups.length === 1) {
        updateBuild({ main_socket_group: 1 });
      }
    } else if (action.type === "add_item" && action.item) {
      const item = { ...action.item };
      const slot = action.slot || item.slot;
      item.slot = slot;
      // Replace existing item in slot, or add new
      const current = activeItems();
      const filtered = current.filter((it) => it.slot !== slot);
      updateItems([...filtered, item]);
    } else if (action.type === "remove_item" && action.slot) {
      const current = activeItems();
      updateItems(current.filter((it) => it.slot !== action.slot));
    } else if (action.type === "add_gem" && action.gem) {
      let groups = [...activeSkillGroups()];
      // Auto-create a skill group if none exist
      if (groups.length === 0) {
        groups = [{
          slot: "Body Armour",
          label: "",
          is_enabled: true,
          gems: [],
        }];
        updateBuild({ main_socket_group: 1 });
      }
      const idx = action.groupIndex ?? (build().main_socket_group - 1);
      const targetIdx = (idx >= 0 && idx < groups.length) ? idx : 0;
      groups[targetIdx] = {
        ...groups[targetIdx],
        gems: [...groups[targetIdx].gems, action.gem],
      };
      updateSkillGroups(groups);
    } else if (action.type === "remove_gem" && action.gem) {
      const groups = [...activeSkillGroups()];
      const idx = action.groupIndex ?? (build().main_socket_group - 1);
      if (idx >= 0 && idx < groups.length) {
        groups[idx] = {
          ...groups[idx],
          gems: groups[idx].gems.filter((g) => g.name !== action.gem!.name),
        };
        updateSkillGroups(groups);
      }
    }
  }

  async function handleCalcDps() {
    setDpsLoading(true);
    setDpsError("");
    try {
      const resolved = resolveVariantForCalc(build(), activeVariant(), selectedSkillIndex());
      const result = await calculateDps(resolved, undefined, calcConfig() as unknown as Record<string, unknown>);
      setDpsResult(result);
    } catch (e) {
      setDpsError(String(e));
    } finally {
      setDpsLoading(false);
    }
  }

  // Auto-recalculate DPS when config changes (only if DPS was already calculated)
  createEffect(() => {
    void calcConfig();
    if (untrack(() => dpsResult() && build() && !dpsLoading())) {
      handleCalcDps();
    }
  });

  // Auto-recalculate DPS when gems or items change (debounced)
  let dpsTimer: ReturnType<typeof setTimeout> | null = null;
  onCleanup(() => { if (dpsTimer) clearTimeout(dpsTimer); });

  createEffect(() => {
    void activeSkillGroups();
    void activeItems();
    if (untrack(() => dpsResult() && !dpsLoading())) {
      if (dpsTimer) clearTimeout(dpsTimer);
      dpsTimer = setTimeout(() => {
        if (dpsResult() && !dpsLoading()) handleCalcDps();
      }, 500);
    }
  });

  return (
    <div class="editor-page">
      {/* Top bar */}
      <div class="editor-top-bar">
        <button class="editor-btn" onClick={handleNew}>New Build</button>
        <Show when={props.loadedBuild?.()}>
          <button class="editor-btn editor-btn-accent" onClick={handleLoadFromViewer}>
            Edit Current Build
          </button>
        </Show>
        <div class="editor-save-group">
          <input
            type="text"
            class="editor-input"
            value={saveName()}
            placeholder="Build name to save..."
            onInput={(e) => setSaveName(e.currentTarget.value)}
          />
          <button class="editor-btn editor-btn-accent" onClick={handleSave}>
            Save
          </button>
          <Show when={saveStatus()}>
            <span class="editor-save-status">{saveStatus()}</span>
          </Show>
        </div>
      </div>

      <div class="editor-layout">
        {/* Main editor area */}
        <div class="editor-main">
          <BuildHeaderEditor
            buildName={build().build_name}
            className={build().class_name}
            ascendancyName={build().ascendancy_name}
            level={build().level}
            onBuildNameChange={(v) => updateBuild({ build_name: v })}
            onClassChange={(v) => updateBuild({ class_name: v })}
            onAscendancyChange={(v) => updateBuild({ ascendancy_name: v })}
            onLevelChange={(v) => updateBuild({ level: v })}
          />

          {/* Variant tabs */}
          <div class="editor-variant-bar">
            <VariantTabs
              titles={variantTitles()}
              active={activeVariant()}
              onSelect={setActiveVariant}
            />
            <div class="editor-variant-actions">
              <button class="editor-btn-sm" onClick={addVariant}>+ Variant</button>
              <Show when={build().passive_specs.length > 1}>
                <button
                  class="editor-btn-sm"
                  onClick={() => renameVariant(activeVariant())}
                >
                  Rename
                </button>
                <button
                  class="editor-btn-sm editor-btn-danger"
                  onClick={() => removeVariant(activeVariant())}
                >
                  Remove
                </button>
              </Show>
            </div>
          </div>

          {/* Content tabs */}
          <div class="editor-tabs">
            <button
              class="editor-tab"
              classList={{ active: activeTab() === "skills" }}
              onClick={() => setActiveTab("skills")}
            >
              Skills
            </button>
            <button
              class="editor-tab"
              classList={{ active: activeTab() === "gear" }}
              onClick={() => setActiveTab("gear")}
            >
              Gear
            </button>
            <button
              class="editor-tab"
              classList={{ active: activeTab() === "tree" }}
              onClick={() => setActiveTab("tree")}
            >
              Passive Tree
            </button>
            <button
              class="editor-tab"
              classList={{ active: activeTab() === "atlas" }}
              onClick={() => setActiveTab("atlas")}
            >
              Atlas & Notes
            </button>
          </div>

          {/* Tab content */}
          <div class="editor-content">
            <Show when={activeTab() === "skills"}>
              <SkillsEditor
                skillGroups={activeSkillGroups()}
                mainSocketGroup={build().main_socket_group}
                onUpdate={(groups) => updateSkillGroups(groups)}
                onSetMain={(idx) => updateBuild({ main_socket_group: idx + 1 })}
              />
            </Show>
            <Show when={activeTab() === "gear"}>
              <GearEditor
                items={activeItems()}
                onUpdate={updateItems}
                nextId={getNextId}
              />
            </Show>
            <Show when={activeTab() === "tree"}>
              <Show when={activeSpec()}>
                {(spec) => (
                  <TreeEditor spec={spec()} onUpdate={updateSpec} />
                )}
              </Show>
            </Show>
            <Show when={activeTab() === "atlas"}>
              <AtlasEditor
                notes={activeNotes()}
                atlasStrategy={activeAtlas()}
                mapWarnings={activeMapWarnings()}
                onNotesChange={updateBracketNotes}
                onAtlasChange={updateBracketAtlas}
                onMapWarningsChange={updateBracketMapWarnings}
              />
            </Show>
          </div>

          {/* DPS calculator */}
          <div class="editor-dps-section">
            <div class="editor-dps-controls">
              <SkillSelector
                skills={activeSkillGroups()}
                selectedIndex={selectedSkillIndex()}
                onSelect={setSelectedSkillIndex}
              />
              <button class="editor-btn editor-btn-accent" onClick={handleCalcDps}>
                Calculate DPS
              </button>
            </div>
            <ConfigBar config={calcConfig()} onChange={setCalcConfig} />
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
          </div>
        </div>

        {/* Right panel: AI advisor */}
        <div class="editor-sidebar">
          <div class="editor-sidebar-title">AI Advisor</div>
          <EditorAiPanel
            build={build()}
            dpsResult={dpsResult()}
            onAction={handleAiAction}
            nextId={getNextId}
          />
        </div>
      </div>
    </div>
  );
}
