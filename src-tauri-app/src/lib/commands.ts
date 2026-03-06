/**
 * Type-safe wrappers around Tauri invoke() calls.
 */
import { invoke } from "@tauri-apps/api/core";
import type {
  Build,
  BuildGuide,
  BuildPreferences,
  ChatMessage,
  ChatResponse,
  DeltaPendingResponse,
  DeltaReport,
  Item,
  ItemComparison,
  TradeSearchResult,
} from "./types";

export async function decodeBuild(code: string): Promise<Build> {
  return await invoke<Build>("decode_build", { code });
}

export async function openPassiveTree(url: string): Promise<void> {
  return await invoke<void>("open_passive_tree", { url });
}

export async function scrapeBuildGuide(url: string): Promise<BuildGuide> {
  return await invoke<BuildGuide>("scrape_build_guide", { url });
}

export async function analyzeDelta(
  pobCode: string,
  characterName: string,
): Promise<DeltaReport | DeltaPendingResponse> {
  return await invoke<DeltaReport | DeltaPendingResponse>("analyze_delta", {
    pobCode,
    characterName,
  });
}

export async function tradeSearch(
  item: Item,
  league: string,
): Promise<TradeSearchResult> {
  return await invoke<TradeSearchResult>("trade_search", { item, league });
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
