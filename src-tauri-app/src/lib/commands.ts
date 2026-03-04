/**
 * Type-safe wrappers around Tauri invoke() calls.
 */
import { invoke } from "@tauri-apps/api/core";
import type { Build, DeltaPendingResponse, DeltaReport } from "./types";

export async function decodeBuild(code: string): Promise<Build> {
  return await invoke<Build>("decode_build", { code });
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
