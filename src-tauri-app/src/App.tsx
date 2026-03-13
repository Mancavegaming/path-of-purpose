import { createSignal, onMount } from "solid-js";
import Sidebar, { type Page } from "./components/Sidebar";
import DecodePage from "./pages/DecodePage";
import DeltaPage from "./pages/DeltaPage";
import GeneratorPage from "./pages/GeneratorPage";
import EditorPage from "./pages/EditorPage";
import CharacterPage from "./pages/CharacterPage";
import StreamingPage from "./pages/StreamingPage";
import type { Build, BuildGuide } from "./lib/types";
import {
  listSavedBuilds,
  loadSavedBuild,
  deleteSavedBuild,
  type SavedBuildEntry,
} from "./lib/commands";
import { guideToBuild } from "./lib/buildUtils";
import { initAuth } from "./lib/auth";
import "./styles.css";

function App() {
  const [page, setPage] = createSignal<Page>("build");
  const [loadedBuild, setLoadedBuild] = createSignal<Build | null>(null);
  const [characterBuild, setCharacterBuild] = createSignal<Build | null>(null);
  const [savedBuilds, setSavedBuilds] = createSignal<SavedBuildEntry[]>([]);

  async function refreshSavedBuilds() {
    try {
      const builds = await listSavedBuilds();
      setSavedBuilds(builds);
    } catch {
      // Ignore — saved builds are non-critical
    }
  }

  onMount(() => {
    initAuth();
    refreshSavedBuilds();
  });

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
        <div style={{ display: page() === "streaming" ? "block" : "none" }}>
          <StreamingPage />
        </div>
      </main>
    </div>
  );
}

export default App;
