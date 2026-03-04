import { createSignal } from "solid-js";
import Sidebar, { type Page } from "./components/Sidebar";
import DecodePage from "./pages/DecodePage";
import DeltaPage from "./pages/DeltaPage";
import GuidePage from "./pages/GuidePage";
import type { Build } from "./lib/types";
import "./styles.css";

function App() {
  const [page, setPage] = createSignal<Page>("decode");
  const [loadedBuild, setLoadedBuild] = createSignal<Build | null>(null);

  function onLoadSavedBuild(build: Build) {
    setLoadedBuild(build);
    setPage("decode");
  }

  return (
    <div class="app-layout">
      <Sidebar page={page} setPage={setPage} onLoadSavedBuild={onLoadSavedBuild} />
      <main class="content">
        <div style={{ display: page() === "decode" ? "block" : "none" }}>
          <DecodePage loadedBuild={loadedBuild} setLoadedBuild={setLoadedBuild} />
        </div>
        <div style={{ display: page() === "delta" ? "block" : "none" }}>
          <DeltaPage />
        </div>
        <div style={{ display: page() === "guide" ? "block" : "none" }}>
          <GuidePage />
        </div>
      </main>
    </div>
  );
}

export default App;
