import { createMemo, createSignal, For, Show } from "solid-js";
import type { Build, Item, SkillGroup, PassiveSpec } from "../lib/types";
import ItemCard from "./ItemCard";
import SkillGroupCard from "./SkillGroupCard";
import VariantTabs from "./VariantTabs";
import PassiveTreePanel from "./PassiveTreePanel";

interface BuildSummaryProps {
  build: Build;
  onItemClick?: (item: Item) => void;
  selectedItem?: Item | null;
  onVariantChange?: (index: number) => void;
}

const SLOT_CATEGORIES: { label: string; slots: string[] }[] = [
  {
    label: "Weapons",
    slots: ["Weapon 1", "Weapon 2", "Weapon 1 Swap", "Weapon 2 Swap"],
  },
  {
    label: "Armour",
    slots: ["Helmet", "Body Armour", "Gloves", "Boots"],
  },
  {
    label: "Jewelry",
    slots: ["Amulet", "Ring 1", "Ring 2", "Belt"],
  },
  {
    label: "Flasks",
    slots: ["Flask 1", "Flask 2", "Flask 3", "Flask 4", "Flask 5"],
  },
];

/** Known PoE 1 keystones for visual tagging in the tree progression. */
const KEYSTONES = new Set([
  "Resolute Technique", "Iron Reflexes", "Acrobatics", "Phase Acrobatics",
  "Mind Over Matter", "Elemental Overload", "Avatar of Fire", "Point Blank",
  "Ancestral Bond", "Unwavering Stance", "Zealot's Oath", "Vaal Pact",
  "Iron Will", "Ghost Reaver", "Chaos Inoculation", "Pain Attunement",
  "Eldritch Battery", "Blood Magic", "Crimson Dance", "Perfect Agony",
  "Elemental Equilibrium", "Necromantic Aegis", "Runebinder",
  "Glancing Blows", "Wind Dancer", "The Agnostic", "Imbalanced Guard",
  "Supreme Ego", "Divine Shield", "Magebane", "Precise Technique",
  "Eternal Youth", "Lethe Shade", "Wicked Ward", "Arrow Dancing",
  "Call to Arms", "Mortal Conviction",
]);

/** Known ascendancy notable prefixes/names. */
const ASCENDANCY_KEYWORDS = [
  "Augury", "Inevitable Judgement", "Righteous Providence", "Instruments of Virtue",
  "Sanctuary", "Pious Path", "Conviction of Power", "Pursuit of Faith",
  "Ritual of Awakening", "Illuminated Devotion", "Arcane Blessing",
  "Pendulum of Destruction", "Mastermind of Discord", "Shaper of Desolation",
  "Beacon of Ruin", "Paragon of Calamity", "Liege of the Primordial",
  "Elemancer", "Bastion of Elements", "Heart of Destruction",
  "Profane Bloom", "Malediction", "Void Beacon", "Withering Presence",
  "Frigid Wake", "Forbidden Power", "Vile Bastion",
  "Mistress of Sacrifice", "Spirit Offering", "Bone Barrier", "Plaguebringer",
  "Corpse Pact", "Essence Glutton", "Commander of Darkness", "Unnatural Strength",
  "Mindless Aggression",
  "Bane of Legends", "Headsman", "Brutal Fervour", "Endless Hunger",
  "Impact", "Overwhelm", "Masterful Form", "Arena Challenger",
  "Gratuitous Violence", "Blood in the Eyes", "Outmatch and Outlast", "Versatile Combatant",
  "Pain Reaver", "Crave the Slaughter", "Aspect of Carnage", "War Bringer",
  "Blitz", "Rite of Ruin", "Flawless Savagery",
  "Gathering Winds", "Far Shot", "Endless Munitions", "Ricochet",
  "Focal Point", "Mirage Archer", "Occupying Force", "Rupture",
  "Nature's Reprisal", "Master Toxicist", "Nature's Adrenaline", "Master Surgeon",
  "Nature's Boon", "Master Alchemist", "Veteran Bowyer",
  "Master of the Arena", "Conqueror", "Worthy Foe", "Inspirational",
  "Fortitude", "Unstoppable Hero", "First to Strike, Last to Fall",
  "Adrenaline",
  "Noxious Strike", "Toxic Delivery", "Mistwalker", "Opportunistic",
  "Ambush and Assassinate", "Unstable Infusion", "Deadly Infusion",
  "Harness the Void", "Escape Artist", "Ghost Dance", "Prolonged Pain",
  "Patient Reaper", "Swift Killer", "Weave the Arcane",
  "Ramako", "Hinekora", "Tawhoa", "Valako", "Ngamahu", "Arohongui",
  "Tukohama", "Tasalio",
];

function isKeystone(node: string): boolean {
  return KEYSTONES.has(node);
}

function isAscendancy(node: string): boolean {
  return ASCENDANCY_KEYWORDS.some((kw) => node.includes(kw));
}

/** Map bracket titles to lab progression milestones. */
function labForBracket(title: string): string {
  const t = title.toLowerCase();
  if (t.includes("36") || t.includes("33") || t.includes("40")) return "Normal Lab (Ascendancy 1-2)";
  if (t.includes("50") || t.includes("55")) return "Cruel Lab (Ascendancy 3-4)";
  if (t.includes("60") || t.includes("68")) return "Merciless Lab (Ascendancy 5-6)";
  if (t.includes("75") || t.includes("80-85") || t.includes("80")) return "Uber Lab (Ascendancy 7-8)";
  return "";
}

/** Check if a bracket title indicates a mapping-tier bracket (maps, T1+, endgame). */
function isMapBracket(title: string): boolean {
  const t = title.toLowerCase();
  return (
    /\bt\d+/i.test(t) ||
    t.includes("map") ||
    t.includes("atlas") ||
    t.includes("endgame") ||
    t.includes("late") ||
    t.includes("90") ||
    t.includes("92") ||
    t.includes("94") ||
    t.includes("95") ||
    t.includes("100")
  );
}

/** Voidstone progression milestones. */
const VOIDSTONE_STEPS = [
  { label: "Voidstone 1", detail: "Defeat The Eater of Worlds / The Searing Exarch" },
  { label: "Voidstone 2", detail: "Defeat the other Eldritch horror" },
  { label: "Voidstone 3", detail: "Defeat The Maven" },
  { label: "Voidstone 4", detail: "Defeat Uber Elder" },
];

type ContentTab = "gear" | "skills" | "tree" | "atlas";

const CONTENT_TABS: { id: ContentTab; label: string }[] = [
  { id: "gear", label: "Gear" },
  { id: "skills", label: "Skills" },
  { id: "tree", label: "Passive Tree" },
  { id: "atlas", label: "Atlas & Maps" },
];

export default function BuildSummary(props: BuildSummaryProps) {
  const b = () => props.build;
  const [activeTab, setActiveTab] = createSignal<ContentTab>("gear");

  // Variant support: use passive spec titles as tab labels
  const hasVariants = () => b().passive_specs.length > 1;
  const [activeVariant, _setActiveVariant] = createSignal(0);
  const setActiveVariant = (idx: number) => {
    _setActiveVariant(idx);
    props.onVariantChange?.(idx);
  };

  const variantTitles = createMemo(() =>
    b().passive_specs.map((s) => s.title || "Default"),
  );

  // Resolve items for the active variant
  const variantItems = createMemo((): Item[] => {
    const build = b();
    const idx = activeVariant();

    if (build.item_sets.length > 0 && idx < build.item_sets.length) {
      const slotMap = build.item_sets[idx].slot_map;
      const byId = new Map(build.items.map((it) => [it.id, it]));
      const result: Item[] = [];
      for (const [slot, itemId] of Object.entries(slotMap)) {
        const item = byId.get(itemId);
        if (item) {
          result.push({ ...item, slot });
        }
      }
      return result;
    }

    return build.items.filter((it) => it.slot);
  });

  // Resolve skill groups for the active variant
  const variantSkills = createMemo((): SkillGroup[] => {
    const build = b();
    const idx = activeVariant();

    if (build.skill_sets.length > 0 && idx < build.skill_sets.length) {
      return build.skill_sets[idx].skills;
    }

    return build.skill_groups;
  });

  // Active passive spec for the active variant
  const variantSpec = createMemo((): PassiveSpec | null => {
    const specs = b().passive_specs;
    const idx = activeVariant();
    return idx < specs.length ? specs[idx] : specs[0] ?? null;
  });

  const mainSkill = () => {
    const idx = b().main_socket_group - 1;
    const skills = variantSkills();
    const group = skills[idx];
    if (!group) return null;
    const active = group.gems.find((g) => !g.is_support && g.is_enabled);
    return active ?? null;
  };

  const passiveCount = () => {
    const spec = variantSpec();
    if (!spec) return 0;
    return spec.nodes.length > 0 ? spec.nodes.length : (spec.total_points ?? 0);
  };

  // Group items by slot category
  const groupedItems = createMemo(() => {
    const items = variantItems();
    const bySlot = new Map(items.map((it) => [it.slot, it]));

    return SLOT_CATEGORIES.map((cat) => ({
      label: cat.label,
      items: cat.slots
        .map((s) => bySlot.get(s))
        .filter((it): it is Item => it != null),
    })).filter((cat) => cat.items.length > 0);
  });

  // Atlas data from active variant/bracket
  const currentBracketTitle = () => variantTitles()[activeVariant()] ?? "";
  const atlasStrategy = () => b().bracket_atlas?.[currentBracketTitle()] ?? "";
  const mapWarnings = () => b().bracket_map_warnings?.[currentBracketTitle()] ?? [];
  const hasAtlasData = () => atlasStrategy() || mapWarnings().length > 0;

  // Check if ANY bracket has atlas data
  const hasAnyAtlasData = () => {
    const atlas = b().bracket_atlas ?? {};
    const warnings = b().bracket_map_warnings ?? {};
    return Object.keys(atlas).length > 0 || Object.keys(warnings).length > 0;
  };

  // Collect all map-tier brackets with their atlas/warning data
  const mapBrackets = createMemo(() => {
    const atlas = b().bracket_atlas ?? {};
    const warnings = b().bracket_map_warnings ?? {};
    const notes = b().bracket_notes ?? {};
    const mapTitles = variantTitles().filter((t) => isMapBracket(t));
    return mapTitles.map((title) => ({
      title,
      atlas: atlas[title] ?? "",
      warnings: warnings[title] ?? [],
      notes: notes[title] ?? "",
    }));
  });

  // Estimate Voidstone progress based on bracket level
  const voidstoneProgress = createMemo(() => {
    const title = currentBracketTitle().toLowerCase();
    if (title.includes("endgame") || title.includes("100")) return 4;
    if (title.includes("late") || title.includes("t12") || title.includes("t16") || title.includes("94")) return 3;
    if (title.includes("mid") || title.includes("t6") || title.includes("t11") || title.includes("92")) return 2;
    if (title.includes("early") || title.includes("t1") || title.includes("t5") || title.includes("90")) return 1;
    if (title.includes("85") || title.includes("80")) return 0;
    return 0;
  });

  return (
    <div>
      {/* Header */}
      <div class="build-header">
        <h2 class="build-class">
          {b().ascendancy_name || b().class_name}
        </h2>
        <Show when={b().build_name}>
          <span class="build-meta">{b().build_name}</span>
        </Show>
      </div>

      {/* Variant tabs */}
      <Show when={hasVariants()}>
        <VariantTabs
          titles={variantTitles()}
          active={activeVariant()}
          onSelect={setActiveVariant}
        />
      </Show>

      {/* Bracket notes */}
      <Show when={b().bracket_notes}>
        {(notes) => {
          const currentTitle = () => variantTitles()[activeVariant()] ?? "";
          const currentNotes = () => notes()[currentTitle()];
          return (
            <Show when={currentNotes()}>
              {(n) => (
                <div class="bracket-notes">
                  <div class="bracket-notes-title">Notes — {currentTitle()}</div>
                  <div class="bracket-notes-body">{n()}</div>
                </div>
              )}
            </Show>
          );
        }}
      </Show>

      {/* Stats grid */}
      <div class="stat-grid">
        <div class="stat-box">
          <div class="stat-label">Level</div>
          <div class="stat-value">{b().level}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Class</div>
          <div class="stat-value">{b().class_name}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Passives</div>
          <div class="stat-value">{passiveCount()}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Main Skill</div>
          <div class="stat-value">{mainSkill()?.name ?? "—"}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Items</div>
          <div class="stat-value">{variantItems().length}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Skill Groups</div>
          <div class="stat-value">{variantSkills().length}</div>
        </div>
      </div>

      {/* Content tabs */}
      <div class="build-content-tabs">
        <For each={CONTENT_TABS}>
          {(tab) => (
            <button
              class={`build-content-tab ${activeTab() === tab.id ? "build-content-tab-active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
              <Show when={tab.id === "atlas" && hasAtlasData()}>
                <span class="tab-badge" />
              </Show>
            </button>
          )}
        </For>
      </div>

      {/* Tab content */}
      <div class="build-tab-content">
        {/* Gear tab */}
        <Show when={activeTab() === "gear"}>
          <Show when={variantItems().length > 0} fallback={
            <div class="panel-empty">No items in this build.</div>
          }>
            <For each={groupedItems()}>
              {(category) => (
                <>
                  <h3 class="section-title slot-category">{category.label}</h3>
                  <div class="card-grid">
                    <For each={category.items}>
                      {(item) => (
                        <ItemCard
                          item={item}
                          onClick={props.onItemClick}
                          selected={props.selectedItem?.id === item.id && props.selectedItem?.slot === item.slot}
                        />
                      )}
                    </For>
                  </div>
                </>
              )}
            </For>
          </Show>
        </Show>

        {/* Skills tab */}
        <Show when={activeTab() === "skills"}>
          <Show when={variantSkills().length > 0} fallback={
            <div class="panel-empty">No skill groups in this build.</div>
          }>
            <div class="card-grid">
              <For each={variantSkills()}>
                {(group, i) => (
                  <SkillGroupCard
                    group={group}
                    isMain={i() === b().main_socket_group - 1}
                  />
                )}
              </For>
            </div>
          </Show>
        </Show>

        {/* Passive Tree tab */}
        <Show when={activeTab() === "tree"}>
          <Show when={b().passive_specs.length > 0}
            fallback={<div class="panel-empty">No passive tree data available.</div>}
          >
            {/* Active bracket's tree — expanded with viewer */}
            <Show when={variantSpec()}>
              {(spec) => <PassiveTreePanel spec={spec()} build={props.build} />}
            </Show>

            {/* Full bracket progression timeline */}
            <Show when={b().passive_specs.length > 1}>
              <h4 class="tree-progression-title">Passive Progression by Bracket</h4>
              <div class="tree-progression-timeline">
                <For each={b().passive_specs}>
                  {(spec, i) => {
                    const isActive = () => i() === activeVariant();
                    const hasData = () =>
                      spec.total_points || spec.nodes.length > 0 ||
                      (spec.key_nodes && spec.key_nodes.length > 0);
                    const prevPoints = () => {
                      const prev = b().passive_specs[i() - 1];
                      return prev?.total_points ?? 0;
                    };
                    const newPoints = () =>
                      (spec.total_points ?? 0) - prevPoints();

                    return (
                      <Show when={hasData()}>
                        <div
                          class={`tree-progression-step ${isActive() ? "tree-step-active" : ""}`}
                          onClick={() => setActiveVariant(i())}
                        >
                          <div class="tree-step-header">
                            <span class="tree-step-title">{spec.title}</span>
                            <span class="tree-step-points">
                              {spec.total_points ?? spec.nodes.length} pts
                              <Show when={newPoints() > 0}>
                                <span class="tree-step-new">+{newPoints()}</span>
                              </Show>
                            </span>
                          </div>

                          <Show when={spec.priority}>
                            <div class="tree-step-priority">{spec.priority}</div>
                          </Show>

                          <Show when={spec.key_nodes && spec.key_nodes.length > 0}>
                            <div class="tree-step-nodes">
                              <For each={spec.key_nodes}>
                                {(node) => (
                                  <span class={`tree-step-node ${isKeystone(node) ? "tree-node-keystone" : isAscendancy(node) ? "tree-node-ascendancy" : ""}`}>
                                    {node}
                                  </span>
                                )}
                              </For>
                            </div>
                          </Show>

                          <Show when={labForBracket(spec.title)}>
                            <div class="tree-step-lab">
                              {labForBracket(spec.title)}
                            </div>
                          </Show>
                        </div>
                      </Show>
                    );
                  }}
                </For>
              </div>
            </Show>
          </Show>
        </Show>

        {/* Atlas & Maps tab */}
        <Show when={activeTab() === "atlas"}>
          <div class="atlas-tab-content">
            {/* Active bracket's atlas strategy */}
            <Show when={atlasStrategy()}>
              <div class="atlas-strategy-section">
                <h4 class="atlas-section-title">Atlas Strategy — {currentBracketTitle()}</h4>
                <div class="atlas-strategy-text">{atlasStrategy()}</div>
              </div>
            </Show>

            {/* Map mod warnings for active bracket */}
            <Show when={mapWarnings().length > 0}>
              <div class="map-warnings-section">
                <h4 class="atlas-section-title">Map Mod Warnings</h4>
                <p class="map-warnings-intro">Avoid or reroll these map mods for this build:</p>
                <div class="map-warnings-list">
                  <For each={mapWarnings()}>
                    {(warning) => (
                      <span class="map-warning-tag">{warning}</span>
                    )}
                  </For>
                </div>
              </div>
            </Show>

            {/* Voidstone progression tracker */}
            <Show when={hasAnyAtlasData()}>
              <div class="voidstone-section">
                <h4 class="atlas-section-title">Voidstone Progression</h4>
                <div class="voidstone-track">
                  <For each={VOIDSTONE_STEPS}>
                    {(step, i) => {
                      const reached = () => voidstoneProgress() > i();
                      return (
                        <div class={`voidstone-step ${reached() ? "voidstone-reached" : ""}`}>
                          <div class="voidstone-icon">{reached() ? "\u2B22" : "\u2B21"}</div>
                          <div class="voidstone-info">
                            <div class="voidstone-label">{step.label}</div>
                            <div class="voidstone-detail">{step.detail}</div>
                          </div>
                        </div>
                      );
                    }}
                  </For>
                </div>
              </div>
            </Show>

            {/* Map bracket progression — atlas strategy across all map brackets */}
            <Show when={mapBrackets().length > 0}>
              <h4 class="atlas-section-title" style={{ "margin-top": "var(--space-lg)" }}>
                Mapping Progression
              </h4>
              <div class="atlas-progression">
                <For each={mapBrackets()}>
                  {(mb) => {
                    const isActive = () => mb.title === currentBracketTitle();
                    return (
                      <div
                        class={`atlas-bracket-card ${isActive() ? "atlas-bracket-active" : ""}`}
                        onClick={() => {
                          const idx = b().passive_specs.findIndex((s) => s.title === mb.title);
                          if (idx >= 0) setActiveVariant(idx);
                        }}
                      >
                        <div class="atlas-bracket-header">
                          <span class="atlas-bracket-title">{mb.title}</span>
                          <Show when={mb.warnings.length > 0}>
                            <span class="atlas-bracket-warn-count">
                              {mb.warnings.length} warnings
                            </span>
                          </Show>
                        </div>
                        <Show when={mb.atlas}>
                          <div class="atlas-bracket-strategy">{mb.atlas}</div>
                        </Show>
                        <Show when={mb.notes}>
                          <div class="atlas-bracket-notes">{mb.notes}</div>
                        </Show>
                      </div>
                    );
                  }}
                </For>
              </div>
            </Show>

            {/* Empty state when no atlas data at all */}
            <Show when={!hasAnyAtlasData()}>
              <div class="panel-empty">
                Atlas strategy and map mod warnings appear for mapping brackets (T1+).
                Select a map-tier bracket or generate a build to see recommendations.
              </div>
            </Show>
          </div>
        </Show>
      </div>
    </div>
  );
}
