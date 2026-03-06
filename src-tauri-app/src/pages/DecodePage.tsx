import { createSignal, Show, type Accessor, type Setter } from "solid-js";
import { decodeBuild, scrapeBuildGuide, saveBuildData } from "../lib/commands";
import type { Build, BuildGuide, Item } from "../lib/types";
import { guideToBuild } from "../lib/buildUtils";
import BuildSummary from "../components/BuildSummary";
import RightPanel from "../components/RightPanel";

function isMobalyticsUrl(input: string): boolean {
  return /mobalytics\.gg/i.test(input);
}

interface DecodePageProps {
  loadedBuild?: Accessor<Build | null>;
  setLoadedBuild?: Setter<Build | null>;
  onSave?: () => void;
}

export default function DecodePage(props: DecodePageProps) {
  const [input, setInput] = createSignal("");
  const [build, setBuild] = createSignal<Build | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");
  const [selectedItem, setSelectedItem] = createSignal<Item | null>(null);
  const [league, setLeague] = createSignal("Mirage");
  const [showSaveInput, setShowSaveInput] = createSignal(false);
  const [saveName, setSaveName] = createSignal("");
  const [saveStatus, setSaveStatus] = createSignal("");

  // If a saved build was loaded externally (e.g. from sidebar), display it
  const displayBuild = () => props.loadedBuild?.() ?? build();

  async function handleLoad() {
    const raw = input().trim();
    if (!raw) return;

    setLoading(true);
    setError("");
    setBuild(null);
    setSelectedItem(null);
    props.setLoadedBuild?.(null);

    try {
      if (isMobalyticsUrl(raw)) {
        // Mobalytics guide URL → scrape then convert
        const guide: BuildGuide = await scrapeBuildGuide(raw);
        setBuild(guideToBuild(guide));
      } else {
        // PoB code, pobb.in URL, or any other URL → decodeBuild handles all
        const result: Build = await decodeBuild(raw);
        setBuild(result);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  function handleItemClick(item: Item) {
    // Toggle selection
    const current = selectedItem();
    if (current && current.id === item.id && current.slot === item.slot) {
      setSelectedItem(null);
    } else {
      setSelectedItem(item);
    }
  }

  function handleStartSave() {
    const b = displayBuild();
    if (b) {
      setSaveName(b.build_name || b.ascendancy_name || b.class_name || "My Build");
      setShowSaveInput(true);
      setSaveStatus("");
    }
  }

  async function handleConfirmSave() {
    const b = displayBuild();
    const name = saveName().trim();
    if (!b || !name) return;

    try {
      await saveBuildData(name, b);
      setSaveStatus("Saved!");
      setShowSaveInput(false);
      props.onSave?.();
    } catch (e) {
      setSaveStatus(`Error: ${String(e)}`);
    }
  }

  return (
    <div>
      <h1 class="page-title">Build Viewer</h1>
      <p class="page-subtitle">
        Paste a PoB code, pobb.in link, or mobalytics guide URL
      </p>

      <div class="input-group">
        <label for="build-input">PoB Code or URL</label>
        <textarea
          id="build-input"
          placeholder="Paste a PoB export code, pobb.in link, or mobalytics.gg URL..."
          value={input()}
          onInput={(e) => setInput(e.currentTarget.value)}
          rows={4}
        />
      </div>

      <div class="decode-actions">
        <button onClick={handleLoad} disabled={loading() || !input().trim()}>
          <Show when={loading()} fallback="Load Build">
            <span class="spinner" />
            Loading...
          </Show>
        </button>

        <Show when={displayBuild()}>
          <div class="league-selector">
            <label for="league-select">League:</label>
            <select
              id="league-select"
              value={league()}
              onChange={(e) => setLeague(e.currentTarget.value)}
            >
              <option value="Mirage">Mirage</option>
              <option value="Hardcore Mirage">HC Mirage</option>
              <option value="Standard">Standard</option>
              <option value="Hardcore">Hardcore</option>
            </select>
          </div>
          <Show when={!showSaveInput()}>
            <button class="generator-save-btn" onClick={handleStartSave}>
              Save Build
            </button>
          </Show>
        </Show>
      </div>

      <Show when={showSaveInput()}>
        <div class="save-build-row" style={{ "margin-top": "8px" }}>
          <input
            type="text"
            value={saveName()}
            onInput={(e) => setSaveName(e.currentTarget.value)}
            placeholder="Build name..."
            class="save-build-input"
          />
          <button onClick={handleConfirmSave} disabled={!saveName().trim()}>
            Confirm
          </button>
          <button
            class="generator-reset-btn"
            onClick={() => setShowSaveInput(false)}
          >
            Cancel
          </button>
        </div>
      </Show>
      <Show when={saveStatus()}>
        <div
          class={saveStatus().startsWith("Error") ? "error-toast" : "info-box"}
          style={{ "margin-top": "8px" }}
        >
          {saveStatus()}
        </div>
      </Show>

      <Show when={error()}>
        <div class="error-toast" style={{ "margin-top": "16px" }}>
          {error()}
        </div>
      </Show>

      <Show when={displayBuild()}>
        <div class="decode-layout">
          <div class="decode-main">
            <BuildSummary
              build={displayBuild()!}
              onItemClick={handleItemClick}
              selectedItem={selectedItem()}
            />
          </div>
          <RightPanel
            selectedItem={selectedItem()}
            league={league()}
            build={displayBuild()!}
          />
        </div>
      </Show>
    </div>
  );
}
