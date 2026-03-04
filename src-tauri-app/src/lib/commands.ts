/**
 * Type-safe wrappers around Tauri invoke() calls.
 */
import { invoke } from "@tauri-apps/api/core";
import type { Build, BuildGuide, DeltaPendingResponse, DeltaReport } from "./types";

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
