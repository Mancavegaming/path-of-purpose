import { createSignal, onMount, onCleanup, Show } from "solid-js";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { emitTo } from "@tauri-apps/api/event";
import Sidebar, { type Page } from "./components/Sidebar";
import DecodePage from "./pages/DecodePage";
import DeltaPage from "./pages/DeltaPage";
import GeneratorPage from "./pages/GeneratorPage";
import EditorPage from "./pages/EditorPage";
import CharacterPage from "./pages/CharacterPage";
import StreamingPage from "./pages/StreamingPage";
import FilterPage from "./pages/FilterPage";
import PriceCheckPage from "./pages/PriceCheckPage";
import type { Build, BuildGuide } from "./lib/types";
import {
  createOverlayWindow,
  getCursorPosition,
  priceCheckTrigger,
  showOverlayAt,
  listSavedBuilds,
  loadSavedBuild,
  deleteSavedBuild,
  type SavedBuildEntry,
} from "./lib/commands";
import { guideToBuild } from "./lib/buildUtils";
import { initAuth } from "./lib/auth";
import { loadPriceCheckSettings, settings } from "./lib/priceCheckStore";
import "./styles.css";

function App() {
  const [page, setPage] = createSignal<Page>("build");
  const [loadedBuild, setLoadedBuild] = createSignal<Build | null>(null);
  const [characterBuild, setCharacterBuild] = createSignal<Build | null>(null);
  const [savedBuilds, setSavedBuilds] = createSignal<SavedBuildEntry[]>([]);
  const [priceCheckStatus, setPriceCheckStatus] = createSignal("");

  async function refreshSavedBuilds() {
    try {
      const builds = await listSavedBuilds();
      setSavedBuilds(builds);
    } catch {
      // Ignore — saved builds are non-critical
    }
  }

  onMount(async () => {
    initAuth();
    refreshSavedBuilds();
    await loadPriceCheckSettings();

    // Pre-create overlay window (hidden)
    try {
      await createOverlayWindow();
    } catch (e) {
      console.warn("Overlay window creation failed:", e);
    }

    // Listen for price check hotkey trigger from Rust global shortcut
    const unlisten = await listen("price-check-triggered", async () => {
      setPriceCheckStatus("Checking price...");
      try {
        const [x, y] = await getCursorPosition();
        const league = settings().league || "Standard";
        const result = await priceCheckTrigger(league);
        // Emit to overlay window specifically
        await emitTo("price-overlay", "price-check-result", result);

        // Position based on settings
        const pos = settings().overlayPosition;
        if (pos === "top-left") {
          await showOverlayAt(20, 20);
        } else if (pos === "top-right") {
          await showOverlayAt(1400, 20);
        } else {
          await showOverlayAt(x + 20, y + 20);
        }
        setPriceCheckStatus("");
      } catch (e) {
        const msg = String(e);
        setPriceCheckStatus(msg);
        console.error("Price check failed:", e);
        // Clear error after 4 seconds
        setTimeout(() => setPriceCheckStatus(""), 4000);
      }
    });
    unlistenRef = unlisten;
  });

  let unlistenRef: UnlistenFn | null = null;
  onCleanup(() => { unlistenRef?.(); });

  function handleGeneratorComplete(build: Build) {
    setLoadedBuild(build);
    setPage("build");
  }

  async function handleLoadSavedBuild(name: string) {
    try {
      const result = await loadSavedBuild(name);
      if (result.kind === "build") {
        setLoadedBuild(result.data as Build);
      } else {
        setLoadedBuild(await guideToBuild(result.data as BuildGuide));
      }
      setPage("build");
    } catch (e) {
      console.error("Failed to load saved build:", e);
    }
  }

  async function handleDeleteSavedBuild(name: string) {
    try {
      await deleteSavedBuild(name);
      await refreshSavedBuilds();
    } catch (e) {
      console.error("Failed to delete saved build:", e);
    }
  }

  return (
    <div class="app-layout">
      <Sidebar
        page={page}
        setPage={setPage}
        savedBuilds={savedBuilds}
        onLoadBuild={handleLoadSavedBuild}
        onDeleteBuild={handleDeleteSavedBuild}
      />
      <main class="content">
        <div style={{ display: page() === "build" ? "block" : "none" }}>
          <DecodePage loadedBuild={loadedBuild} setLoadedBuild={setLoadedBuild} onSave={refreshSavedBuilds} />
        </div>
        <div style={{ display: page() === "generator" ? "block" : "none" }}>
          <GeneratorPage
            onComplete={handleGeneratorComplete}
            onSave={refreshSavedBuilds}
          />
        </div>
        <div style={{ display: page() === "editor" ? "block" : "none" }}>
          <EditorPage
            loadedBuild={loadedBuild}
            setLoadedBuild={setLoadedBuild}
            onSave={refreshSavedBuilds}
          />
        </div>
        <div style={{ display: page() === "character" ? "block" : "none" }}>
          <CharacterPage
            loadedBuild={loadedBuild}
            setLoadedBuild={setLoadedBuild}
            onSave={refreshSavedBuilds}
            onCharacterImported={setCharacterBuild}
          />
        </div>
        <div style={{ display: page() === "delta" ? "block" : "none" }}>
          <DeltaPage
            loadedBuild={loadedBuild}
            characterBuild={characterBuild}
            savedBuilds={savedBuilds}
          />
        </div>
        <div style={{ display: page() === "filter" ? "block" : "none" }}>
          <FilterPage loadedBuild={loadedBuild} />
        </div>
        <div style={{ display: page() === "pricecheck" ? "block" : "none" }}>
          <PriceCheckPage />
        </div>
        <div style={{ display: page() === "streaming" ? "block" : "none" }}>
          <StreamingPage />
        </div>
      </main>
      <Show when={priceCheckStatus()}>
        <div style={{
          position: "fixed",
          bottom: "12px",
          right: "12px",
          padding: "8px 14px",
          background: "rgba(30, 30, 50, 0.95)",
          border: "1px solid rgba(100, 100, 140, 0.4)",
          "border-radius": "6px",
          color: priceCheckStatus().startsWith("Checking") ? "#aaa" : "#f88",
          "font-size": "13px",
          "z-index": "9999",
          "pointer-events": "none",
        }}>
          {priceCheckStatus()}
        </div>
      </Show>
    </div>
  );
}

export default App;
