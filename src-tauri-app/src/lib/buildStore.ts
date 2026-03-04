import { createSignal } from "solid-js";
import type { Build } from "./types";

export interface SavedBuild {
  id: string;
  name: string;
  build: Build;
  savedAt: string;
}

const STORAGE_KEY = "pop-saved-builds";

function loadFromStorage(): SavedBuild[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function writeToStorage(builds: SavedBuild[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(builds));
}

const [savedBuilds, setSavedBuilds] = createSignal<SavedBuild[]>(loadFromStorage());

export function saveBuild(name: string, build: Build) {
  const entry: SavedBuild = {
    id: crypto.randomUUID(),
    name,
    build,
    savedAt: new Date().toISOString(),
  };
  const next = [...savedBuilds(), entry];
  setSavedBuilds(next);
  writeToStorage(next);
}

export function removeBuild(id: string) {
  const next = savedBuilds().filter((b) => b.id !== id);
  setSavedBuilds(next);
  writeToStorage(next);
}

export { savedBuilds };
