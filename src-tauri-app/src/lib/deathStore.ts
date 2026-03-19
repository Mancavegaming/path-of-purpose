/**
 * Death Store — session-only reactive state for the Death tab.
 *
 * Polls Client.txt for death events when the Death tab is active.
 * No persistence — history resets each app session.
 */
import { createSignal, createEffect } from "solid-js";
import type { DeathAnalysis } from "./types";
import {
  logSnapshot,
  analyzeDeath,
} from "./commands";
import {
  streamDpsResult,
  logWatcherOffset,
  logWatcherPath,
  updateLogWatcherStats,
} from "./streamStore";

export interface DeathEntry {
  id: number;
  timestamp: number;
  killer: string;
  zone: string;
  element: string;
  analysis: DeathAnalysis | null;
}

// --- Signals ---
const [deathHistory, setDeathHistory] = createSignal<DeathEntry[]>([]);
const [selectedDeath, setSelectedDeath] = createSignal<DeathEntry | null>(null);
const [isActive, setIsActive] = createSignal(false);
const [deathLogError, setDeathLogError] = createSignal("");
const [showGraceVerses, setShowGraceVerses] = createSignal(true);

export {
  deathHistory,
  selectedDeath,
  setSelectedDeath,
  deathLogError,
  showGraceVerses,
  setShowGraceVerses,
};

export function setDeathTabActive(active: boolean): void {
  setIsActive(active);
}

// --- Polling ---
let logTimer: ReturnType<typeof setInterval> | null = null;
let isPolling = false;
let isFirstPoll = true;
let nextId = 1;

async function pollLogSnapshot(): Promise<void> {
  if (isPolling) return;
  isPolling = true;
  try {
    const offset = logWatcherOffset();
    const path = logWatcherPath() || undefined;
    const snap = await logSnapshot(path, offset || undefined);
    if (snap.error) {
      setDeathLogError(snap.error);
    } else {
      setDeathLogError("");

      const newDeaths = snap.stats?.total_deaths ?? 0;
      if (!isFirstPoll && newDeaths > 0 && snap.stats?.last_death) {
        const death = snap.stats.last_death as Record<string, unknown>;
        const entry: DeathEntry = {
          id: nextId++,
          timestamp: Date.now(),
          killer: (death.killer as string) || "Unknown",
          zone: (death.zone as string) || "Unknown",
          element: (death.damage_element as string) || "",
          analysis: null,
        };

        // Try to analyze death against player defences
        const dps = streamDpsResult();
        const defence = dps?.defence;
        if (defence) {
          try {
            const analysis = await analyzeDeath(
              death,
              defence as unknown as Record<string, unknown>,
            );
            entry.analysis = analysis;
            entry.element = analysis.damage_element || entry.element;
          } catch {
            // Analysis is non-critical
          }
        }

        setDeathHistory((prev) => [entry, ...prev].slice(0, 50));
      }
      isFirstPoll = false;

      updateLogWatcherStats(snap);
    }
  } catch (e) {
    setDeathLogError(String(e));
  } finally {
    isPolling = false;
  }
}

// Reactive polling — starts/stops based on tab visibility
createEffect(() => {
  if (logTimer) {
    clearInterval(logTimer);
    logTimer = null;
  }
  if (isActive()) {
    isFirstPoll = true; // Reset so first poll after activation is a baseline
    pollLogSnapshot();
    logTimer = setInterval(pollLogSnapshot, 5000);
  }
});
