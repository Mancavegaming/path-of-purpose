import { createSignal, Show } from "solid-js";
import type { Build, FilterStrictness } from "../lib/types";
import { generateFilter, saveFilterFile } from "../lib/commands";

interface FilterGeneratorProps {
  build: Build;
}

export default function FilterGenerator(props: FilterGeneratorProps) {
  const [expanded, setExpanded] = createSignal(false);
  const [strictness, setStrictness] = createSignal<FilterStrictness>("mapping");
  const [showResists, setShowResists] = createSignal(true);
  const [showClusters, setShowClusters] = createSignal(true);
  const [showLevelGems, setShowLevelGems] = createSignal(true);
  const [loading, setLoading] = createSignal(false);
  const [filterText, setFilterText] = createSignal("");
  const [error, setError] = createSignal("");
  const [savedPath, setSavedPath] = createSignal("");

  async function handleGenerate() {
    setLoading(true);
    setError("");
    setSavedPath("");
    try {
      const result = await generateFilter(props.build, {
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
      // Fallback
    }
  }

  return (
    <div class="filter-generator">
      <button
        class="filter-generator-header"
        onClick={() => setExpanded(!expanded())}
      >
        <span>Loot Filter Generator</span>
        <span class="filter-toggle">{expanded() ? "\u25BC" : "\u25B6"}</span>
      </button>

      <Show when={expanded()}>
        <div class="filter-generator-body">
          {/* Strictness */}
          <div class="filter-row">
            <label class="filter-label">Strictness:</label>
            <div class="filter-radio-group">
              {(["leveling", "mapping", "endgame", "ultra_strict"] as FilterStrictness[]).map((s) => (
                <label class="filter-radio">
                  <input
                    type="radio"
                    name="strictness"
                    value={s}
                    checked={strictness() === s}
                    onChange={() => setStrictness(s)}
                  />
                  {s.replace("_", " ")}
                </label>
              ))}
            </div>
          </div>

          {/* Options */}
          <div class="filter-row">
            <label class="filter-checkbox">
              <input type="checkbox" checked={showResists()} onChange={(e) => setShowResists(e.currentTarget.checked)} />
              Highlight resist gap fillers
            </label>
            <label class="filter-checkbox">
              <input type="checkbox" checked={showClusters()} onChange={(e) => setShowClusters(e.currentTarget.checked)} />
              Show cluster jewels
            </label>
            <label class="filter-checkbox">
              <input type="checkbox" checked={showLevelGems()} onChange={(e) => setShowLevelGems(e.currentTarget.checked)} />
              Show leveling gems
            </label>
          </div>

          {/* Generate button */}
          <div class="filter-actions">
            <button
              class="filter-generate-btn"
              onClick={handleGenerate}
              disabled={loading()}
            >
              {loading() ? "Generating..." : "Generate Filter"}
            </button>

            <Show when={filterText()}>
              <button class="filter-install-btn" onClick={handleInstall}>
                Install to PoE
              </button>
              <button class="filter-copy-btn" onClick={handleCopy}>
                Copy
              </button>
            </Show>
          </div>

          <Show when={error()}>
            <div class="filter-error">{error()}</div>
          </Show>

          <Show when={savedPath()}>
            <div class="filter-success">
              Saved to: {savedPath()}
            </div>
          </Show>

          {/* Preview */}
          <Show when={filterText()}>
            <div class="filter-preview-label">Preview:</div>
            <pre class="filter-preview">
              {filterText().split("\n").slice(0, 30).join("\n")}
              {filterText().split("\n").length > 30 ? "\n..." : ""}
            </pre>
          </Show>
        </div>
      </Show>
    </div>
  );
}
