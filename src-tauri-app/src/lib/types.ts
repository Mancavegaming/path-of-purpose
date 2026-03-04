/**
 * TypeScript interfaces matching the Python Pydantic models.
 * These define the shape of data returned by Tauri invoke() calls.
 */

// --- Build Parser models (src-python/pop/build_parser/models.py) ---

export interface ItemMod {
  text: string;
  is_implicit: boolean;
  is_crafted: boolean;
}

export interface Item {
  id: number;
  slot: string;
  name: string;
  base_type: string;
  rarity: string;
  level: number;
  quality: number;
  sockets: string;
  implicits: ItemMod[];
  explicits: ItemMod[];
  raw_text: string;
  icon_url?: string;
}

export interface PassiveSpec {
  title: string;
  tree_version: string;
  class_id: number;
  ascendancy_id: number;
  nodes: number[];
  overrides: Record<number, number>;
  url: string;
}

export interface Gem {
  name: string;
  gem_id: string;
  level: number;
  quality: number;
  is_support: boolean;
  is_enabled: boolean;
  icon_url?: string;
}

export interface SkillGroup {
  slot: string;
  label: string;
  is_enabled: boolean;
  gems: Gem[];
}

export interface SkillSet {
  title: string;
  skills: SkillGroup[];
}

export interface ItemSet {
  title: string;
  slot_map: Record<string, number>;
}

export interface BuildConfig {
  entries: Record<string, string>;
}

export interface Build {
  class_name: string;
  ascendancy_name: string;
  level: number;
  main_socket_group: number;
  passive_specs: PassiveSpec[];
  skill_groups: SkillGroup[];
  items: Item[];
  config: BuildConfig;
  skill_sets: SkillSet[];
  item_sets: ItemSet[];
  active_skill_set: number;
  active_item_set: number;
  pob_version: string;
  build_name: string;
}

// --- Delta Engine models (src-python/pop/delta/models.py) ---

export type Severity = "critical" | "high" | "medium" | "low";
export type GapCategory = "passive" | "gear" | "gem";

export interface PassiveDelta {
  missing_nodes: number[];
  extra_nodes: number[];
  missing_count: number;
  extra_count: number;
  guide_total: number;
  character_total: number;
  match_pct: number;
}

export interface ModGap {
  mod_text: string;
  is_implicit: boolean;
  importance: number;
}

export interface SlotDelta {
  slot: string;
  guide_item_name: string;
  character_item_name: string;
  has_item: boolean;
  missing_mods: ModGap[];
  matched_mods: number;
  total_guide_mods: number;
  match_pct: number;
  priority_score: number;
}

export interface GearDelta {
  slot_deltas: SlotDelta[];
  overall_match_pct: number;
}

export interface GemGap {
  gem_name: string;
  issue: string;
  guide_level: number;
  character_level: number;
  slot: string;
}

export interface SkillGroupDelta {
  skill_name: string;
  slot: string;
  missing_supports: string[];
  extra_supports: string[];
  level_gaps: GemGap[];
  is_missing_entirely: boolean;
  match_pct: number;
}

export interface GemDelta {
  group_deltas: SkillGroupDelta[];
  total_missing_supports: number;
  total_level_gaps: number;
}

export interface DeltaGap {
  rank: number;
  category: GapCategory;
  severity: Severity;
  title: string;
  detail: string;
  score: number;
}

export interface DeltaReport {
  passive_delta: PassiveDelta;
  gear_delta: GearDelta;
  gem_delta: GemDelta;
  top_gaps: DeltaGap[];
  guide_build_name: string;
  character_name: string;
}

// --- Build Guide models (scraped from mobalytics.gg) ---

export interface GuideGem {
  name: string;
  icon_url: string;
  is_support: boolean;
}

export interface GuideGemGroup {
  slot: string;
  gems: GuideGem[];
}

export interface GuideItem {
  slot: string;
  name: string;
  base_type: string;
  icon_url: string;
}

export interface LevelBracket {
  title: string;
  gem_groups: GuideGemGroup[];
  items: GuideItem[];
}

export interface BuildGuide {
  url: string;
  title: string;
  class_name: string;
  ascendancy_name: string;
  brackets: LevelBracket[];
}

// Placeholder response from analyze_delta while OAuth is pending
export interface DeltaPendingResponse {
  status: "oauth_pending";
  message: string;
  guide_decoded: boolean;
}
