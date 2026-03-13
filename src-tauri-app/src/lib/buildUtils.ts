/**
 * Shared utility to convert a BuildGuide into a Build for the Build Viewer.
 * Used by both DecodePage (scraped guides) and GeneratorPage (AI-generated guides).
 */
import type { Build, BuildGuide, Item } from "./types";
import { synthesizeItems } from "./commands";

/**
 * Convert a BuildGuide (scraped or AI-generated) into a Build so BuildSummary can render it.
 * Calls the Python synthesize_items engine to produce real Item objects with mods.
 *
 * @param guide - The BuildGuide to convert
 * @param tier - "basic" for budget rolls, "max" for endgame rolls
 */
export async function guideToBuild(
  guide: BuildGuide,
  tier: "basic" | "max" = "basic",
): Promise<Build> {
  const skillSets = guide.brackets.map((bracket) => ({
    title: bracket.title,
    skills: bracket.gem_groups.map((gg) => ({
      slot: gg.slot,
      label: "",
      is_enabled: true,
      gems: gg.gems.map((g) => ({
        name: g.name,
        gem_id: "",
        level: 20,
        quality: 0,
        is_support: g.is_support,
        is_enabled: true,
        icon_url: g.icon_url,
      })),
    })),
  }));

  // Build bracket_notes map from bracket title → notes
  const bracketNotes: Record<string, string> = {};
  const bracketAtlas: Record<string, string> = {};
  const bracketMapWarnings: Record<string, string[]> = {};
  for (const bracket of guide.brackets) {
    if (bracket.notes) {
      bracketNotes[bracket.title] = bracket.notes;
    }
    if (bracket.atlas_strategy) {
      bracketAtlas[bracket.title] = bracket.atlas_strategy;
    }
    if (bracket.map_warnings?.length) {
      bracketMapWarnings[bracket.title] = bracket.map_warnings;
    }
  }

  // Build flat item list with unique IDs, and item sets mapping slots to IDs
  // Synthesize real items with mods from stat priorities via Python engine
  let nextId = 1;
  const allItems: Build["items"] = [];
  const itemSets: Build["item_sets"] = [];

  for (const bracket of guide.brackets) {
    const guideItems = bracket.items;
    const startId = nextId;

    // Use "max" tier for endgame brackets (maps+), "basic" for leveling
    const bracketTier = tier === "max" ? "max"
      : /maps|endgame|8[0-9]|9[0-9]|100/i.test(bracket.title) ? "max" : "basic";

    // Synthesize real items (with mods, base types, rarity) from guide items
    let synthesized: Item[] = [];
    if (guideItems.length > 0) {
      try {
        synthesized = await synthesizeItems(guideItems, bracketTier);
      } catch {
        // Fall back to stub items if synthesis fails (e.g. Python not available)
      }
    }

    const slotMap: Record<string, number> = {};
    for (let i = 0; i < guideItems.length; i++) {
      const gi = guideItems[i];
      const id = startId + i;
      const synth = synthesized[i];

      if (synth) {
        // Use synthesized item, preserving guide-specific fields
        allItems.push({
          ...synth,
          id,
          icon_url: gi.icon_url || synth.icon_url,
          stat_priority: gi.stat_priority,
          notes: gi.notes,
        });
      } else {
        // Fallback: stub item with no mods
        allItems.push({
          id,
          slot: gi.slot,
          name: gi.name,
          base_type: "",
          rarity: "NORMAL",
          level: 0,
          quality: 0,
          sockets: "",
          implicits: [],
          explicits: [],
          raw_text: "",
          icon_url: gi.icon_url,
          stat_priority: gi.stat_priority,
          notes: gi.notes,
        });
      }
      slotMap[gi.slot] = id;
    }
    nextId = startId + guideItems.length;
    itemSets.push({ title: bracket.title, slot_map: slotMap });
  }

  // For the flat skill_groups / items, use the first bracket
  const firstBracket = guide.brackets[0];
  const skillGroups = firstBracket
    ? firstBracket.gem_groups.map((gg) => ({
        slot: gg.slot,
        label: "",
        is_enabled: true,
        gems: gg.gems.map((g) => ({
          name: g.name,
          gem_id: "",
          level: 20,
          quality: 0,
          is_support: g.is_support,
          is_enabled: true,
          icon_url: g.icon_url,
        })),
      }))
    : [];

  return {
    class_name: guide.class_name,
    ascendancy_name: guide.ascendancy_name,
    level: 1,
    main_socket_group: 1,
    passive_specs: guide.brackets.map((b) => ({
      title: b.title,
      tree_version: "",
      class_id: 0,
      ascendancy_id: 0,
      nodes: [],
      overrides: {},
      url: b.passive_tree?.url || "",
      key_nodes: b.passive_tree?.key_nodes || [],
      total_points: b.passive_tree?.total_points || 0,
      priority: b.passive_tree?.priority || "",
    })),
    skill_groups: skillGroups,
    items: allItems,
    config: { entries: {} },
    skill_sets: skillSets,
    item_sets: itemSets,
    active_skill_set: 0,
    active_item_set: 0,
    pob_version: "",
    build_name: guide.title,
    bracket_notes: bracketNotes,
    bracket_atlas: bracketAtlas,
    bracket_map_warnings: bracketMapWarnings,
  };
}

/**
 * Resolve a Build's active variant into a flat Build suitable for the DPS calculator.
 *
 * The DPS engine only reads `skill_groups` and `items` (flat arrays).
 * For variant builds (AI-generated with brackets), the real data lives in
 * `skill_sets[idx]` and `item_sets[idx]`. This function flattens the active
 * variant so Python gets the correct skills and items.
 *
 * @param build - The full Build with variant data
 * @param variantIndex - Which variant/bracket to resolve (default: active_skill_set)
 * @param skillIndex - Which skill group within the variant to calc (0-based)
 */
export function resolveVariantForCalc(
  build: Build,
  variantIndex?: number,
  skillIndex?: number,
): Build {
  const idx = variantIndex ?? build.active_skill_set;

  // Resolve skill groups from the active variant's skill set
  let skills = build.skill_groups;
  if (build.skill_sets.length > 0 && idx < build.skill_sets.length) {
    skills = build.skill_sets[idx].skills;
  }

  // Resolve items from the active variant's item set
  let items = build.items;
  if (build.item_sets.length > 0 && idx < build.item_sets.length) {
    const slotMap = build.item_sets[idx].slot_map;
    const byId = new Map(build.items.map((it) => [it.id, it]));
    items = [];
    for (const [slot, itemId] of Object.entries(slotMap)) {
      const item = byId.get(itemId);
      if (item) {
        items.push({ ...item, slot });
      }
    }
  }

  // Resolve passive spec for the active variant
  // AI builds have one passive_spec per bracket — pick the matching one
  let passiveSpecs = build.passive_specs;
  if (passiveSpecs.length > 1 && idx < passiveSpecs.length) {
    passiveSpecs = [passiveSpecs[idx]];
  }

  return {
    ...build,
    skill_groups: skills,
    items,
    passive_specs: passiveSpecs,
    main_socket_group: (skillIndex ?? 0) + 1, // 1-based for Python
  };
}

/**
 * Re-synthesize items in an existing Build at a different tier.
 * Only affects items that have stat_priority (guide-sourced items).
 */
export async function resynthesizeBuildItems(
  guide: BuildGuide,
  tier: "basic" | "max",
): Promise<Build> {
  return await guideToBuild(guide, tier);
}
