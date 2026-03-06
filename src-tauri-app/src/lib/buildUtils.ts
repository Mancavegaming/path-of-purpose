/**
 * Shared utility to convert a BuildGuide into a Build for the Build Viewer.
 * Used by both DecodePage (scraped guides) and GeneratorPage (AI-generated guides).
 */
import type { Build, BuildGuide } from "./types";

/** Convert a BuildGuide (scraped or AI-generated) into a Build so BuildSummary can render it. */
export function guideToBuild(guide: BuildGuide): Build {
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
  for (const bracket of guide.brackets) {
    if (bracket.notes) {
      bracketNotes[bracket.title] = bracket.notes;
    }
  }

  // Build flat item list with unique IDs, and item sets mapping slots to IDs
  let nextId = 1;
  const allItems: Build["items"] = [];
  const itemSets: Build["item_sets"] = [];

  for (const bracket of guide.brackets) {
    const slotMap: Record<string, number> = {};
    for (const gi of bracket.items) {
      const id = nextId++;
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
      slotMap[gi.slot] = id;
    }
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
  };
}
