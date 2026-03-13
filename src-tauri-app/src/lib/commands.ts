/**
 * Type-safe wrappers around Tauri invoke() calls.
 */
import { invoke } from "@tauri-apps/api/core";
import type {
  Build,
  BuildGuide,
  BuildPreferences,
  CalcResult,
  ChatMessage,
  ChatResponse,
  DeltaReport,
  Item,
  ItemComparison,
  TradeSearchResult,
} from "./types";

export async function decodeBuild(code: string): Promise<Build> {
  return await invoke<Build>("decode_build", { code });
}

export async function calculateDps(
  build: Build,
  skillIndex?: number,
  config?: Record<string, unknown>,
): Promise<CalcResult> {
  return await invoke<CalcResult>("calculate_dps", {
    build,
    skillIndex: skillIndex ?? null,
    config: config ?? null,
  });
}

export async function calculateAllDps(
  build: Build,
  config?: Record<string, unknown>,
): Promise<CalcResult[]> {
  return await invoke<CalcResult[]>("calculate_all_dps", {
    build,
    config: config ?? null,
  });
}

export async function openPassiveTree(url: string): Promise<void> {
  return await invoke<void>("open_passive_tree", { url });
}

export async function scrapeBuildGuide(url: string): Promise<BuildGuide> {
  return await invoke<BuildGuide>("scrape_build_guide", { url });
}

export async function resolveTreeUrls(guide: BuildGuide): Promise<BuildGuide> {
  return await invoke<BuildGuide>("resolve_tree_urls", { guide });
}

export async function resolveTreeUrlsRemote(
  token: string,
  guide: BuildGuide,
): Promise<BuildGuide> {
  return await invoke<BuildGuide>("resolve_tree_urls_remote", { token, guide });
}

export async function analyzeDelta(
  guideBuild: Build,
  characterBuild: Build,
): Promise<DeltaReport> {
  return await invoke<DeltaReport>("analyze_delta", {
    guideBuild,
    characterBuild,
  });
}

export async function tradeSearch(
  item: Item,
  league: string,
  equippedItem?: Item,
  enabledMods?: string[],
  minLinks?: number,
  minSockets?: number,
  socketColours?: Record<string, Record<string, number>>,
): Promise<TradeSearchResult> {
  return await invoke<TradeSearchResult>("trade_search", {
    item,
    league,
    equippedItem: equippedItem ?? null,
    enabledMods: enabledMods ?? null,
    minLinks: minLinks && minLinks > 0 ? minLinks : null,
    minSockets: minSockets && minSockets > 0 ? minSockets : null,
    socketColours: socketColours ?? null,
  });
}

export async function synthesizeItems(
  items: import("./types").GuideItem[],
  tier: "basic" | "max" = "basic",
): Promise<Item[]> {
  return await invoke<Item[]>("synthesize_items", { items, tier });
}

export interface GemNameList {
  active: string[];
  support: string[];
}

export async function listGemNames(): Promise<GemNameList> {
  return await invoke<GemNameList>("list_gem_names");
}

// --- Character Import (public profile API) ---

export interface CharacterEntry {
  name: string;
  class_name: string;
  level: number;
  league: string;
}

export async function listPublicCharacters(
  accountName: string,
): Promise<CharacterEntry[] | { error: string; private?: boolean }> {
  return await invoke<CharacterEntry[] | { error: string; private?: boolean }>(
    "list_public_characters",
    { accountName },
  );
}

export async function importCharacter(
  accountName: string,
  characterName: string,
): Promise<Build | { error: string; private?: boolean }> {
  return await invoke<Build | { error: string; private?: boolean }>(
    "import_character",
    { accountName, characterName },
  );
}

export async function compareItems(
  equippedItem: Record<string, unknown>,
  tradeListing: Record<string, unknown>,
  slot: string,
  weaponAps: number = 0,
): Promise<ItemComparison> {
  return await invoke<ItemComparison>("compare_items", {
    equippedItem,
    tradeListing,
    slot,
    weaponAps,
  });
}

export interface BuildDpsComparison {
  baseline_dps: number;
  swapped_dps: number;
  dps_change: number;
  dps_change_pct: number;
  baseline_hit_dps: number;
  swapped_hit_dps: number;
  baseline_dot_dps: number;
  swapped_dot_dps: number;
  skill_name: string;
}

export interface BatchDpsResult {
  listing_index: number;
  dps_change: number | null;
  dps_change_pct: number | null;
}

export interface BatchDpsResponse {
  baseline_dps: number;
  skill_name: string;
  results: BatchDpsResult[];
}

export async function batchCompareBuildDps(
  build: Record<string, unknown>,
  listings: Record<string, unknown>[],
  slot: string,
  config?: Record<string, unknown>,
): Promise<BatchDpsResponse> {
  return await invoke<BatchDpsResponse>("batch_compare_build_dps", {
    build,
    listings,
    slot,
    config: config ?? null,
  });
}

export interface PassiveNodeSuggestion {
  node_id: number;
  name: string;
  stats: string[];
  is_notable: boolean;
  is_keystone: boolean;
  dps_change: number;
  dps_change_pct: number;
}

export interface PassiveSuggestionResult {
  baseline_dps: number;
  skill_name: string;
  candidates_evaluated: number;
  suggestions: PassiveNodeSuggestion[];
  error?: string;
}

export async function suggestPassiveNodes(
  build: Record<string, unknown>,
  config?: Record<string, unknown>,
  maxSuggestions?: number,
): Promise<PassiveSuggestionResult> {
  return await invoke<PassiveSuggestionResult>("suggest_passive_nodes", {
    build,
    config: config ?? null,
    maxSuggestions: maxSuggestions ?? 5,
  });
}

export interface BudgetOptimizeResult {
  baseline_dps: number;
  skill_name: string;
  slots_searched: number;
  total_listings_evaluated: number;
  recommendations: import("./types").BudgetRecommendation[];
}

export async function budgetOptimize(
  build: Record<string, unknown>,
  budgetChaos: number,
  league: string,
  divineRatio?: number,
  slots?: string[],
  maxListingsPerSlot?: number,
  config?: Record<string, unknown>,
): Promise<BudgetOptimizeResult> {
  return await invoke<BudgetOptimizeResult>("budget_optimize", {
    build,
    budgetChaos,
    league,
    divineRatio: divineRatio ?? null,
    slots: slots ?? null,
    maxListingsPerSlot: maxListingsPerSlot ?? null,
    config: config ?? null,
  });
}

export async function compareBuildDps(
  build: Record<string, unknown>,
  tradeListing: Record<string, unknown>,
  slot: string,
): Promise<BuildDpsComparison> {
  return await invoke<BuildDpsComparison>("compare_build_dps", {
    build,
    tradeListing,
    slot,
  });
}

export async function aiChat(
  message: string,
  history: ChatMessage[],
  buildContext: Record<string, unknown> | null,
  apiKey: string,
  provider: string = "gemini",
): Promise<ChatResponse> {
  return await invoke<ChatResponse>("ai_chat", {
    message,
    history,
    buildContext,
    apiKey,
    provider,
  });
}

export async function generatorChat(
  message: string,
  history: ChatMessage[],
  apiKey: string,
  provider: string = "gemini",
): Promise<ChatResponse> {
  return await invoke<ChatResponse>("generator_chat", {
    message,
    history,
    apiKey,
    provider,
  });
}

export async function generateBuild(
  apiKey: string,
  preferences: BuildPreferences,
  history: ChatMessage[],
  provider: string = "gemini",
): Promise<BuildGuide> {
  return await invoke<BuildGuide>("generate_build", {
    apiKey,
    preferences,
    history,
    provider,
  });
}

export async function refineBuild(
  apiKey: string,
  guide: BuildGuide,
  tradePrices: Array<{ name: string; price_chaos: number }>,
  budgetChaos: number,
  history: ChatMessage[],
  message: string,
  provider: string = "gemini",
): Promise<BuildGuide> {
  return await invoke<BuildGuide>("refine_build", {
    apiKey,
    guide,
    tradePrices,
    budgetChaos,
    history,
    message,
    provider,
  });
}

export interface KnowledgeRefreshResult {
  status: string;
  gems: number;
  uniques: number;
  patch_notes: number;
  version: string;
  last_updated: string;
}

export async function refreshKnowledge(): Promise<KnowledgeRefreshResult> {
  return await invoke<KnowledgeRefreshResult>("refresh_knowledge");
}

export async function checkKnowledge(): Promise<KnowledgeRefreshResult> {
  return await invoke<KnowledgeRefreshResult>("check_knowledge");
}

export async function aiSetKey(key: string, provider: string = "anthropic"): Promise<void> {
  await invoke("ai_set_key", { key, provider });
}

export async function aiCheckKey(provider: string = "gemini"): Promise<{ has_key: boolean; provider: string }> {
  return await invoke<{ has_key: boolean; provider: string }>("ai_check_key", { provider });
}

// --- Saved Builds ---

export interface SavedBuildEntry {
  name: string;
  saved_at: string;
  kind: "guide" | "build";
}

export async function saveBuildGuide(
  name: string,
  guide: BuildGuide,
): Promise<void> {
  await invoke("save_build", { name, data: guide, kind: "guide" });
}

export async function saveBuildData(
  name: string,
  build: Build,
): Promise<void> {
  await invoke("save_build", { name, data: build, kind: "build" });
}

export interface SavedBuildResult {
  kind: "guide" | "build";
  data: unknown;
}

export async function listSavedBuilds(): Promise<SavedBuildEntry[]> {
  return await invoke<SavedBuildEntry[]>("list_saved_builds");
}

export async function loadSavedBuild(name: string): Promise<SavedBuildResult> {
  return await invoke<SavedBuildResult>("load_saved_build", { name });
}

export async function deleteSavedBuild(name: string): Promise<void> {
  await invoke("delete_saved_build", { name });
}

// --- Remote AI commands (server-side, no API key needed) ---

export async function aiChatRemote(
  token: string,
  message: string,
  history: ChatMessage[],
  buildContext: Record<string, unknown> | null,
): Promise<ChatResponse> {
  return await invoke<ChatResponse>("ai_chat_remote", {
    token,
    message,
    history,
    buildContext,
  });
}

export async function generatorChatRemote(
  token: string,
  message: string,
  history: ChatMessage[],
): Promise<ChatResponse> {
  return await invoke<ChatResponse>("generator_chat_remote", {
    token,
    message,
    history,
  });
}

export async function generateBuildRemote(
  token: string,
  preferences: BuildPreferences,
  history: ChatMessage[],
): Promise<BuildGuide> {
  return await invoke<BuildGuide>("generate_build_remote", {
    token,
    preferences,
    history,
  });
}

// --- Tree Layout ---

export interface TreeLayoutNode {
  id: number;
  x: number;
  y: number;
  type: number; // 0=normal, 1=notable, 2=keystone, 3=mastery, 4=jewel, 5=start
  name: string;
  ascendancy: string;
}

export interface TreeLayout {
  nodes: TreeLayoutNode[];
  edges: [number, number][];
  bounds: [number, number, number, number];
  version: string;
}

export async function getTreeLayout(): Promise<TreeLayout> {
  const raw = await invoke<{
    nodes: [number, number, number, number, string, string][];
    edges: [number, number][];
    bounds: [number, number, number, number];
    version: string;
  }>("get_tree_layout");

  // Convert compact arrays to named objects
  const nodes = raw.nodes.map(([id, x, y, type, name, ascendancy]) => ({
    id, x, y, type, name, ascendancy,
  }));

  return { nodes, edges: raw.edges, bounds: raw.bounds, version: raw.version };
}

export function decodeTreeUrl(url: string): Set<number> {
  const nodeIds = new Set<number>();
  try {
    const parts = url.split("/");
    const encoded = parts[parts.length - 1];
    // Restore Base64 padding
    let b64 = encoded.replace(/-/g, "+").replace(/_/g, "/");
    while (b64.length % 4 !== 0) b64 += "=";

    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

    // Header: 4 bytes version + 1 class + 1 ascendancy + 1 fullscreen = 7 bytes
    for (let i = 7; i + 1 < bytes.length; i += 2) {
      const nodeId = (bytes[i] << 8) | bytes[i + 1];
      if (nodeId > 0) nodeIds.add(nodeId);
    }
  } catch {
    // Invalid URL, return empty set
  }
  return nodeIds;
}

// --- Streaming / Overlay ---

export async function storeTwitchToken(
  token: string,
  username: string,
  channel: string,
): Promise<void> {
  await invoke("store_twitch_token", { token, username, channel });
}

export async function loadTwitchToken(): Promise<{
  token: string | null;
  username: string | null;
  channel: string | null;
}> {
  return await invoke("load_twitch_token");
}

export async function clearTwitchToken(): Promise<void> {
  await invoke("clear_twitch_token");
}

export async function updateOverlayState(
  payload: Record<string, unknown>,
): Promise<void> {
  await invoke("update_overlay_state", { payload });
}

export async function startOverlayServer(): Promise<string> {
  return await invoke<string>("start_overlay_server");
}

export async function stopOverlayServer(): Promise<void> {
  await invoke("stop_overlay_server");
}

export interface MapHistoryEntry {
  zone_name: string;
  area_level: number;
  duration: string;
  duration_seconds: number;
  deaths: number;
}

export interface TradeWhisper {
  timestamp: string;
  player: string;
  item: string;
  price: string;
  currency: string;
  league: string;
}

export interface LogSnapshot {
  log_path: string;
  offset: number;
  stats: {
    maps_completed: number;
    total_deaths: number;
    levels_gained: number;
    maps_per_hour: number;
    avg_map_time: string;
    deaths_per_hour: number;
    current_zone: string;
    current_map: {
      zone_name: string;
      area_level: number;
      duration: string;
      deaths: number;
      death_recaps: Array<{ killer: string; timestamp: string; grace_verse: string; grace_ref: string }>;
    } | null;
    last_death: {
      character: string;
      killer: string;
      zone: string;
      timestamp: string;
      grace_verse: string;
      grace_ref: string;
    } | null;
    map_history: MapHistoryEntry[];
    fastest_map: { zone_name: string; area_level: number; duration: string; duration_seconds: number } | null;
    deadliest_map: { zone_name: string; area_level: number; deaths: number } | null;
    trade_whispers: TradeWhisper[];
    trades_completed: number;
    current_boss: {
      boss_name: string;
      zone_name: string;
      duration: string;
      duration_seconds: number;
      deaths: number;
    } | null;
    boss_kills: number;
    boss_history: Array<{
      boss_name: string;
      zone_name: string;
      duration: string;
      duration_seconds: number;
      deaths: number;
      killed: boolean;
    }>;
    time_played: string;
  };
  error?: string;
}

export async function logSnapshot(
  logPath?: string,
  offset?: number,
  characterName?: string,
): Promise<LogSnapshot> {
  return await invoke<LogSnapshot>("log_snapshot", {
    logPath: logPath || null,
    offset: offset || null,
    characterName: characterName || null,
  });
}

export async function fetchLeagues(): Promise<string[]> {
  const result = await invoke<{ leagues: string[] }>("fetch_leagues");
  return result.leagues;
}

export async function refineBuildRemote(
  token: string,
  guide: BuildGuide,
  tradePrices: Array<{ name: string; price_chaos: number }>,
  budgetChaos: number,
  history: ChatMessage[],
  message: string,
): Promise<BuildGuide> {
  return await invoke<BuildGuide>("refine_build_remote", {
    token,
    guide,
    tradePrices,
    budgetChaos,
    history,
    message,
  });
}
