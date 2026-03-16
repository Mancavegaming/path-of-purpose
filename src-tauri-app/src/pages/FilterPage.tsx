import { createSignal, Show, type Accessor } from "solid-js";
import type { Build, FilterStrictness } from "../lib/types";
import { generateFilter, saveFilterFile } from "../lib/commands";

interface FilterPageProps {
  loadedBuild?: Accessor<Build | null>;
}

export default function FilterPage(props: FilterPageProps) {
  const [strictness, setStrictness] = createSignal<FilterStrictness>("mapping");
  const [showResists, setShowResists] = createSignal(true);
  const [showClusters, setShowClusters] = createSignal(true);
  const [showLevelGems, setShowLevelGems] = createSignal(true);
  const [loading, setLoading] = createSignal(false);
  const [filterText, setFilterText] = createSignal("");
  const [error, setError] = createSignal("");
  const [savedPath, setSavedPath] = createSignal("");

  const build = () => props.loadedBuild?.() ?? null;

  async function handleGenerate() {
    const b = build();
    if (!b) return;
    setLoading(true);
    setError("");
    setSavedPath("");
    try {
      const result = await generateFilter(b, {
        strictness: strictness(),
        show_resist_fillers: showResists(),
        show_cluster_jewels: showClusters(),
        show_leveling_gems: showLevelGems(),
        filter_name: "PathOfPurpose",
      });
      setFilterText(result.filter_text);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleInstall() {
    if (!filterText()) return;
    setError("");
    try {
      const path = await saveFilterFile(filterText(), "PathOfPurpose");
      setSavedPath(path);
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleCopy() {
    if (!filterText()) return;
    try {
      await navigator.clipboard.writeText(filterText());
    } catch {
      // fallback
    }
  }

  function handleDownload() {
    if (!filterText()) return;
    const blob = new Blob([filterText()], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "PathOfPurpose.filter";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div class="filter-page">
      <h2>Loot Filter Generator</h2>
      <p class="filter-page-desc">
        Generate a personalized loot filter based on your build. Load a build from the Build Viewer first, then customize and generate.
      </p>

      <Show
        when={build()}
        fallback={
          <div class="filter-no-build">
            No build loaded. Go to <strong>Build Viewer</strong> and paste a PoB code first, then come back here.
          </div>
        }
      >
        <div class="filter-build-info">
          Build: <strong>{build()!.ascendancy_name || build()!.class_name}</strong> — Level {build()!.level}
        </div>

        {/* Strictness */}
        <div class="filter-section">
          <h3>Strictness</h3>
          <div class="filter-strictness-grid">
            {(["leveling", "mapping", "endgame", "ultra_strict"] as FilterStrictness[]).map((s) => (
              <button
                class={`filter-strictness-btn ${strictness() === s ? "active" : ""}`}
                onClick={() => setStrictness(s)}
              >
                <div class="filter-strictness-label">{s.replace("_", " ")}</div>
                <div class="filter-strictness-desc">
                  {s === "leveling" && "Show almost everything"}
                  {s === "mapping" && "Hide low currency & normals"}
                  {s === "endgame" && "Only build-relevant drops"}
                  {s === "ultra_strict" && "Absolute minimum"}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Options */}
        <div class="filter-section">
          <h3>Options</h3>
          <div class="filter-options-grid">
            <label class="filter-option">
              <input type="checkbox" checked={showResists()} onChange={(e) => setShowResists(e.currentTarget.checked)} />
              <div>
                <div class="filter-option-title">Resist Gap Fillers</div>
                <div class="filter-option-desc">Highlight rares with resists your build needs</div>
              </div>
            </label>
            <label class="filter-option">
              <input type="checkbox" checked={showClusters()} onChange={(e) => setShowClusters(e.currentTarget.checked)} />
              <div>
                <div class="filter-option-title">Cluster Jewels</div>
                <div class="filter-option-desc">Show cluster jewels matching your damage type</div>
              </div>
            </label>
            <label class="filter-option">
              <input type="checkbox" checked={showLevelGems()} onChange={(e) => setShowLevelGems(e.currentTarget.checked)} />
              <div>
                <div class="filter-option-title">Leveling Gems</div>
                <div class="filter-option-desc">Show all gem drops (not just build gems)</div>
              </div>
            </label>
          </div>
        </div>

        {/* Actions */}
        <div class="filter-section">
          <div class="filter-main-actions">
            <button
              class="filter-generate-main-btn"
              onClick={handleGenerate}
              disabled={loading()}
            >
              {loading() ? "Generating..." : "Generate Filter"}
            </button>

            <Show when={filterText()}>
              <button class="filter-install-main-btn" onClick={handleInstall}>
                Install to PoE Folder
              </button>
              <button class="filter-download-btn" onClick={handleDownload}>
                Download .filter
              </button>
              <button class="filter-copy-main-btn" onClick={handleCopy}>
                Copy to Clipboard
              </button>
            </Show>
          </div>

          <Show when={error()}>
            <div class="filter-error">{error()}</div>
          </Show>
          <Show when={savedPath()}>
            <div class="filter-success">
              Installed to: {savedPath()}
              <br />
              In-game: Options &gt; UI &gt; Item Filter &gt; select "PathOfPurpose"
            </div>
          </Show>
        </div>

        {/* Preview */}
        <Show when={filterText()}>
          <div class="filter-section">
            <h3>Filter Preview ({filterText().split("\n").length} lines)</h3>
            <pre class="filter-preview-full">{filterText()}</pre>
          </div>
        </Show>
      </Show>
    </div>
  );
}
