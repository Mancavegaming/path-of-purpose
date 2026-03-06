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

export default function BuildSummary(props: BuildSummaryProps) {
  const b = () => props.build;

  // Variant support: use passive spec titles as tab labels
  const hasVariants = () => b().passive_specs.length > 1;
  const [activeVariant, setActiveVariant] = createSignal(0);

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
          // Clone with this variant's slot assignment
          result.push({ ...item, slot });
        }
      }
      return result;
    }

    // Simple build — use items with slots already assigned
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
    return spec ? spec.nodes.length : 0;
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

      {/* Passive tree panel — hidden for generated builds with no real tree data */}
      <Show when={(() => {
        const spec = variantSpec();
        return spec && (spec.nodes.length > 0 || spec.url) ? spec : false;
      })()}>
        {(spec) => <PassiveTreePanel spec={spec()} />}
      </Show>

      {/* Skill groups */}
      <Show when={variantSkills().length > 0}>
        <h3 class="section-title">Skill Groups</h3>
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

      {/* Items grouped by slot category */}
      <Show when={variantItems().length > 0}>
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
    </div>
  );
}
