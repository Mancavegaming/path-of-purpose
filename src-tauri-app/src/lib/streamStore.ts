/**
 * Stream Store — shared reactive state for the Streaming tab.
 *
 * Pages that compute DPS (DecodePage, CharacterPage) publish their
 * build + CalcResult here. The streaming tab, chat bot, and overlay
 * all read from this store.
 */
import { createSignal } from "solid-js";
import type { Build, CalcResult } from "./types";

// --- Types ---

export interface ViewerSuggestion {
  user: string;
  text: string;
  timestamp: number;
}

export interface ChatLogEntry {
  timestamp: number;
  user: string;
  command: string;
  response: string;
}

// --- Signals ---

const [streamBuild, setStreamBuildSignal] = createSignal<Build | null>(null);
const [streamDpsResult, setStreamDpsResultSignal] = createSignal<CalcResult | null>(null);
const [viewerSuggestions, setViewerSuggestions] = createSignal<ViewerSuggestion[]>([]);
const [chatLog, setChatLog] = createSignal<ChatLogEntry[]>([]);
const [sessionStartTime, setSessionStartTime] = createSignal<number | null>(null);
const [commandsHandled, setCommandsHandled] = createSignal(0);

export {
  streamBuild,
  streamDpsResult,
  viewerSuggestions,
  chatLog,
  sessionStartTime,
  commandsHandled,
};

/** Called by DecodePage / CharacterPage when DPS is calculated. */
export function setStreamBuild(build: Build | null, dpsResult: CalcResult | null): void {
  setStreamBuildSignal(build);
  setStreamDpsResultSignal(dpsResult);
}

export function addViewerSuggestion(user: string, text: string): void {
  setViewerSuggestions((prev) => [
    ...prev.slice(-19), // keep last 20
    { user, text, timestamp: Date.now() },
  ]);
}

export function dismissSuggestion(timestamp: number): void {
  setViewerSuggestions((prev) => prev.filter((s) => s.timestamp !== timestamp));
}

export function addChatLogEntry(entry: ChatLogEntry): void {
  setChatLog((prev) => [...prev.slice(-99), entry]); // keep last 100
  setCommandsHandled((c) => c + 1);
}

export function startSession(): void {
  setSessionStartTime(Date.now());
  setCommandsHandled(0);
  setChatLog([]);
  setViewerSuggestions([]);
}

export function stopSession(): void {
  setSessionStartTime(null);
}

/** Build the JSON payload for the overlay server. */
export function getOverlayPayload(): Record<string, unknown> {
  const build = streamBuild();
  const dps = streamDpsResult();
  const def = dps?.defence;

  // Boss readiness summary
  const bossReadiness: { name: string; status: string }[] = [];
  if (dps && def) {
    const bosses = [
      { name: "Shaper", dps: 2_000_000, life: 5500, res: 75 },
      { name: "Sirus A8", dps: 2_000_000, life: 5500, res: 75 },
      { name: "Maven", dps: 3_000_000, life: 5500, res: 75 },
      { name: "Uber Elder", dps: 3_000_000, life: 6000, res: 75 },
      { name: "The Feared", dps: 5_000_000, life: 6000, res: 75 },
    ];
    for (const b of bosses) {
      const minRes = Math.min(
        def.elemental_resistances?.fire ?? 0,
        def.elemental_resistances?.cold ?? 0,
        def.elemental_resistances?.lightning ?? 0,
      );
      const dpsPasses = dps.combined_dps >= b.dps;
      const lifePasses = def.life >= b.life;
      const resPasses = minRes >= b.res;
      const status = dpsPasses && lifePasses && resPasses
        ? "pass"
        : (dpsPasses || lifePasses) && resPasses
          ? "warn"
          : "fail";
      bossReadiness.push({ name: b.name, status });
    }
  }

  return {
    build_name: build?.build_name || build?.ascendancy_name || "",
    ascendancy: build?.ascendancy_name || "",
    level: build?.level || 0,
    combined_dps: dps?.combined_dps || 0,
    skill_name: dps?.skill_name || "",
    hit_dps: dps?.total_dps || 0,
    dot_dps: dps?.total_dot_dps || 0,
    impale_dps: dps?.impale_dps || 0,
    life: def?.life || 0,
    energy_shield: def?.energy_shield || 0,
    resistances: {
      fire: def?.elemental_resistances?.fire || 0,
      cold: def?.elemental_resistances?.cold || 0,
      lightning: def?.elemental_resistances?.lightning || 0,
      chaos: def?.chaos_resistance || 0,
    },
    boss_readiness: bossReadiness,
    viewer_suggestions: viewerSuggestions().slice(-5),
    session_start: sessionStartTime(),
    commands_handled: commandsHandled(),
  };
}
