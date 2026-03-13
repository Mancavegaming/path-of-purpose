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
  stat_priority?: string[];
  notes?: string;
}

export interface PassiveSpec {
  title: string;
  tree_version: string;
  class_id: number;
  ascendancy_id: number;
  nodes: number[];
  overrides: Record<number, number>;
  url: string;
  key_nodes?: string[];
  total_points?: number;
  priority?: string;
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
  bracket_notes?: Record<string, string>;
  bracket_atlas?: Record<string, string>;
  bracket_map_warnings?: Record<string, string[]>;
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
  stat_priority?: string[];
  notes?: string;
}

export interface PassiveTreeSpec {
  total_points: number;
  key_nodes: string[];
  priority: string;
  url: string;
}

export interface LevelBracket {
  title: string;
  gem_groups: GuideGemGroup[];
  items: GuideItem[];
  passive_tree?: PassiveTreeSpec | null;
  notes?: string;
  atlas_strategy?: string;
  map_warnings?: string[];
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

// --- Trade models (src-python/pop/trade/models.py) ---

export interface TradePrice {
  amount: number;
  currency: string;
  type: string;
}

export interface TradeSocket {
  group: number;
  colour: string;  // R, G, B, W, A, D
}

export interface TradeListing {
  id: string;
  item_name: string;
  type_line: string;
  ilvl: number;
  corrupted: boolean;
  price: TradePrice | null;
  explicit_mods: string[];
  implicit_mods: string[];
  crafted_mods: string[];
  account_name: string;
  whisper: string;
  icon_url: string;
  attacks_per_second: number;
  dps_change: number | null;
  sockets: TradeSocket[];
  socket_count: number;
  max_links: number;
}

export interface TradeSearchResult {
  total: number;
  listings: TradeListing[];
  query_id: string;
  trade_url: string;
  relaxed_level: number;
  dropped_stats: string[];
}

// --- Item Comparison models (src-python/pop/trade/dps_estimator.py) ---

export interface WeaponDps {
  physical_dps: number;
  elemental_dps: number;
  total_dps: number;
  attacks_per_second: number;
}

export interface StatDelta {
  stat_name: string;
  equipped_value: number;
  trade_value: number;
  difference: number;
  pct_change: number;
}

export interface ItemComparison {
  equipped_name: string;
  trade_name: string;
  slot: string;
  is_weapon: boolean;
  equipped_dps: WeaponDps | null;
  trade_dps: WeaponDps | null;
  dps_change_pct: number;
  equipped_flat_dps: number;
  trade_flat_dps: number;
  flat_dps_change: number;
  stat_deltas: StatDelta[];
  summary: string;
}

// --- Damage Calc models (src-python/pop/calc/models.py) ---

export interface TypeDamage {
  damage_type: string;
  base: number;
  after_flat: number;
  after_conversion: number;
  after_increased: number;
  after_more: number;
  final_hit: number;
  after_mitigation: number;
}

export interface DefenceResult {
  armour: number;
  evasion: number;
  energy_shield: number;
  life: number;
  block_chance: number;
  spell_block_chance: number;
  dodge_chance: number;
  spell_suppression: number;
  phys_damage_reduction: number;
  elemental_resistances: Record<string, number>;
  chaos_resistance: number;
}

export interface CalcResult {
  total_dps: number;
  hit_damage: number;
  hits_per_second: number;
  effective_crit_multi: number;
  crit_chance: number;
  hit_chance: number;
  type_breakdown: TypeDamage[];
  ignite_dps: number;
  bleed_dps: number;
  poison_dps: number;
  total_dot_dps: number;
  impale_dps: number;
  combined_dps: number;
  enemy_damage_taken_multi: number;
  skill_name: string;
  is_attack: boolean;
  is_totem: boolean;
  is_trap: boolean;
  is_mine: boolean;
  is_minion: boolean;
  num_totems: number;
  defence: DefenceResult | null;
  warnings: string[];
}

// --- Budget Optimizer models ---

export interface BudgetRecommendation {
  slot: string;
  item_name: string;
  type_line: string;
  icon_url: string;
  price_chaos: number;
  price_currency: string;
  price_amount: number;
  dps_gain: number;
  dps_gain_pct: number;
  efficiency: number;
  new_total_dps: number;
  whisper: string;
  account_name: string;
  explicit_mods: string[];
  implicit_mods: string[];
}

export interface BudgetOptimizeResult {
  baseline_dps: number;
  skill_name: string;
  slots_searched: number;
  total_listings_evaluated: number;
  recommendations: BudgetRecommendation[];
}

// --- Build Generator models (src-python/pop/ai/models.py) ---

export interface BuildPreferences {
  main_skill: string;
  weapon_type: string;
  class_name: string;
  ascendancy_name: string;
  budget_chaos: number;
  league: string;
  playstyle: string;
}

// --- AI Advisor models (src-python/pop/ai/models.py) ---

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  message: string;
  conversation_id: string;
  tokens_used: number;
}
