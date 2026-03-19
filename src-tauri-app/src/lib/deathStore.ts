/**
 * Death Store — session-only reactive state for the Death tab.
 *
 * Polls Client.txt continuously in the background (with overlap guard).
 * The Death tab just displays data — polling is not tied to tab visibility.
 * No persistence — history resets each app session.
 */
import { createSignal } from "solid-js";
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
  graceVerse: string;
  graceRef: string;
  analysis: DeathAnalysis | null;
}

// --- Signals ---
const [deathHistory, setDeathHistory] = createSignal<DeathEntry[]>([]);
const [selectedDeath, setSelectedDeath] = createSignal<DeathEntry | null>(null);
const [deathLogError, setDeathLogError] = createSignal("");
const [detectedLogPath, setDetectedLogPath] = createSignal("");
const [showGraceVerses, setShowGraceVerses] = createSignal(true);

export {
  deathHistory,
  selectedDeath,
  setSelectedDeath,
  deathLogError,
  detectedLogPath,
  showGraceVerses,
  setShowGraceVerses,
};

// --- Polling (runs continuously from app start) ---
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
      if (snap.log_path) setDetectedLogPath(snap.log_path);

      const newDeaths = snap.stats?.total_deaths ?? 0;
      if (!isFirstPoll && newDeaths > 0 && snap.stats?.last_death) {
        const death = snap.stats.last_death as Record<string, unknown>;
        const entry: DeathEntry = {
          id: nextId++,
          timestamp: Date.now(),
          killer: (death.killer as string) || "Unknown",
          zone: (death.zone as string) || "Unknown",
          element: (death.damage_element as string) || "",
          graceVerse: (death.grace_verse as string) || "",
          graceRef: (death.grace_ref as string) || "",
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

        // If the last death was "Unknown" and this one has a real killer,
        // replace it instead of adding a duplicate (split poll boundary)
        setDeathHistory((prev) => {
          if (
            prev.length > 0 &&
            prev[0].killer === "Unknown" &&
            entry.killer !== "Unknown" &&
            entry.timestamp - prev[0].timestamp < 10000
          ) {
            return [entry, ...prev.slice(1)].slice(0, 50);
          }
          return [entry, ...prev].slice(0, 50);
        });
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

// Start polling immediately on import — runs for the lifetime of the app.
// The isPolling guard ensures at most one Python process at a time.
pollLogSnapshot();
setInterval(pollLogSnapshot, 5000);
