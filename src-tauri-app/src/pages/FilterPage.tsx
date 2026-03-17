import { createSignal, For, Show, type Accessor } from "solid-js";
import type { AccountFilter, Build, FilterStrictness } from "../lib/types";
import {
  generateFilter,
  saveFilterFile,
  uploadFilterToAccount,
  listAccountFilters,
  deleteAccountFilter,
} from "../lib/commands";

interface FilterPageProps {
  loadedBuild?: Accessor<Build | null>;
}

const BEAMS = ["", "Red", "Green", "Blue", "Yellow", "White", "Orange", "Cyan", "Purple", "Pink", "Brown", "Grey"];
const SOUNDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];

/** Play a PoE alert sound preview. Sounds are short sine-wave tones at different pitches. */
function playAlertSound(soundId: number) {
  if (soundId === 0) return;
  try {
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    // Each sound ID gets a distinct frequency
    const baseFreq = 220;
    const freq = baseFreq + (soundId - 1) * 80;
    osc.type = soundId <= 8 ? "sine" : "square";
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.4);
    osc.onended = () => ctx.close();
  } catch {
    // AudioContext not available
  }
}

export default function FilterPage(props: FilterPageProps) {
  // Strictness
  const [strictness, setStrictness] = createSignal<FilterStrictness>("mapping");

  // Currency
  const [t1Sound, setT1Sound] = createSignal(1);
  const [t1Beam, setT1Beam] = createSignal("Red");
  const [t2Sound, setT2Sound] = createSignal(2);
  const [t2Beam, setT2Beam] = createSignal("Yellow");
  const [t3Sound, setT3Sound] = createSignal(0);
  const [showT4, setShowT4] = createSignal(true);
  const [showT5, setShowT5] = createSignal(false);
  const [showEssences, setShowEssences] = createSignal(true);
  const [showFossils, setShowFossils] = createSignal(true);
  const [showCatalysts, setShowCatalysts] = createSignal(true);
  const [showOils, setShowOils] = createSignal(true);
  const [showDeliriumOrbs, setShowDeliriumOrbs] = createSignal(true);
  const [showFragments, setShowFragments] = createSignal(true);

  // Equipment
  const [showRareJewellery, setShowRareJewellery] = createSignal(true);
  const [showRareWeapons, setShowRareWeapons] = createSignal(true);
  const [showSixLinks, setShowSixLinks] = createSignal(true);
  const [sixLinkSound, setSixLinkSound] = createSignal(1);
  const [showFiveLinks, setShowFiveLinks] = createSignal(true);
  const [showRgb, setShowRgb] = createSignal(false);

  // Maps
  const [mapMinTier, setMapMinTier] = createSignal(1);
  const [mapSound, setMapSound] = createSignal(4);
  const [showUniqueMaps, setShowUniqueMaps] = createSignal(true);

  // Gems
  const [gemMinQual, setGemMinQual] = createSignal(0);
  const [gemMinLevel, setGemMinLevel] = createSignal(1);

  // Flasks
  const [showUtilFlasks, setShowUtilFlasks] = createSignal(true);
  const [showLifeMana, setShowLifeMana] = createSignal(false);

  // Sounds
  const [uniqueSound, setUniqueSound] = createSignal(3);
  const [buildGearSound, setBuildGearSound] = createSignal(6);

  // Build tailored
  const [buildEnabled, setBuildEnabled] = createSignal(false);
  const [hlWeapons, setHlWeapons] = createSignal(true);
  const [hlGems, setHlGems] = createSignal(true);
  const [hlResists, setHlResists] = createSignal(true);
  const [hlClusters, setHlClusters] = createSignal(true);

  // Output
  const [loading, setLoading] = createSignal(false);
  const [filterText, setFilterText] = createSignal("");
  const [error, setError] = createSignal("");
  const [savedPath, setSavedPath] = createSignal("");

  // Upload to account
  const [showUploadModal, setShowUploadModal] = createSignal(false);
  const [uploadName, setUploadName] = createSignal("PathOfPurpose");
  const [uploadDesc, setUploadDesc] = createSignal("");
  const [uploading, setUploading] = createSignal(false);
  const [uploadMsg, setUploadMsg] = createSignal("");

  // Manage account filters
  const [showManage, setShowManage] = createSignal(false);
  const [accountFilters, setAccountFilters] = createSignal<AccountFilter[]>([]);
  const [loadingFilters, setLoadingFilters] = createSignal(false);
  const [manageError, setManageError] = createSignal("");
  const [deletingId, setDeletingId] = createSignal("");

  const build = () => props.loadedBuild?.() ?? null;

  function buildConfig() {
    return {
      strictness: strictness(),
      currency: {
        tier1: { show: true, sound: t1Sound(), volume: 300, beam: t1Beam(), icon: "0 Red Star", font_size: 45 },
        tier2: { show: true, sound: t2Sound(), volume: 300, beam: t2Beam(), icon: "1 Yellow Circle", font_size: 38 },
        tier3: { show: true, sound: t3Sound(), volume: 200, beam: "", icon: "", font_size: 32 },
        tier4: { show: showT4(), sound: 0, volume: 0, beam: "", icon: "", font_size: 26 },
        tier5: { show: showT5(), sound: 0, volume: 0, beam: "", icon: "", font_size: 20 },
        show_essences: showEssences(), show_fossils: showFossils(),
        show_catalysts: showCatalysts(), show_oils: showOils(),
        show_delirium_orbs: showDeliriumOrbs(), show_fragments: showFragments(),
      },
      equipment: {
        show_rare_jewellery: showRareJewellery(), rare_jewellery_ilvl: 75,
        show_rare_weapons: showRareWeapons(), rare_weapon_ilvl: 82,
        show_six_links: showSixLinks(), six_link_sound: sixLinkSound(), six_link_beam: "Red",
        show_five_links: showFiveLinks(), show_rgb_items: showRgb(),
      },
      maps: { min_tier: mapMinTier(), show_unique_maps: showUniqueMaps(), sound: mapSound(), beam: "White" },
      gems: { min_quality: gemMinQual(), min_level: gemMinLevel() },
      flasks: { show_utility: showUtilFlasks(), show_life_mana: showLifeMana() },
      sounds: {
        unique_drop: uniqueSound(), unique_volume: 200,
        map_drop: mapSound(), map_volume: 200,
        build_gear: buildGearSound(), build_gear_volume: 200,
      },
      build_tailored: {
        enabled: buildEnabled(),
        highlight_weapon_bases: hlWeapons(),
        highlight_build_gems: hlGems(),
        highlight_resist_fillers: hlResists(),
        highlight_cluster_jewels: hlClusters(),
      },
      filter_name: "PathOfPurpose",
    };
  }

  async function handleGenerate() {
    setLoading(true);
    setError("");
    setSavedPath("");
    try {
      const b = buildEnabled() ? build() : null;
      const result = await generateFilter(b, buildConfig());
      setFilterText(result.filter_text);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleInstall() {
    if (!filterText()) return;
    try {
      const path = await saveFilterFile(filterText(), "PathOfPurpose");
      setSavedPath(path);
    } catch (e) {
      setError(String(e));
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

  async function handleCopy() {
    if (!filterText()) return;
    await navigator.clipboard.writeText(filterText()).catch(() => {});
  }

  async function handleUpload() {
    if (!filterText() || !uploadName().trim()) return;
    setUploading(true);
    setUploadMsg("");
    try {
      await uploadFilterToAccount(uploadName().trim(), filterText(), uploadDesc());
      setUploadMsg(`Filter "${uploadName()}" uploaded to your PoE account.`);
      setShowUploadModal(false);
    } catch (e) {
      setUploadMsg(`Upload failed: ${String(e)}`);
    } finally {
      setUploading(false);
    }
  }

  async function loadAccountFilters() {
    setLoadingFilters(true);
    setManageError("");
    try {
      const res = await listAccountFilters();
      setAccountFilters(res.filters || []);
    } catch (e) {
      setManageError(String(e));
    } finally {
      setLoadingFilters(false);
    }
  }

  async function handleDeleteFilter(id: string) {
    setDeletingId(id);
    try {
      await deleteAccountFilter(id);
      setAccountFilters((prev) => prev.filter((f) => f.id !== id));
    } catch (e) {
      setManageError(`Delete failed: ${String(e)}`);
    } finally {
      setDeletingId("");
    }
  }

  function toggleManage() {
    const next = !showManage();
    setShowManage(next);
    if (next) loadAccountFilters();
  }

  const SoundSelect = (p: { value: number; onChange: (v: number) => void }) => (
    <span class="filter-sound-select-wrap">
      <select class="filter-select" value={p.value} onChange={(e) => p.onChange(Number(e.currentTarget.value))}>
        {SOUNDS.map((s) => <option value={s}>{s === 0 ? "Off" : `Sound ${s}`}</option>)}
      </select>
      <Show when={p.value > 0}>
        <button
          class="filter-sound-preview-btn"
          title={`Preview Sound ${p.value}`}
          onClick={() => playAlertSound(p.value)}
        >&#9654;</button>
      </Show>
    </span>
  );

  const BeamSelect = (p: { value: string; onChange: (v: string) => void }) => (
    <select class="filter-select" value={p.value} onChange={(e) => p.onChange(e.currentTarget.value)}>
      {BEAMS.map((b) => <option value={b}>{b || "None"}</option>)}
    </select>
  );

  return (
    <div class="filter-page">
      <h2>Loot Filter Generator</h2>
      <p class="filter-page-desc">Create a customized PoE loot filter. Optionally tailor it to your loaded build.</p>

      {/* Strictness */}
      <div class="filter-section">
        <h3>Strictness</h3>
        <div class="filter-strictness-grid">
          {(["leveling", "mapping", "endgame", "ultra_strict"] as FilterStrictness[]).map((s) => (
            <button class={`filter-strictness-btn ${strictness() === s ? "active" : ""}`} onClick={() => setStrictness(s)}>
              <div class="filter-strictness-label">{s.replace("_", " ")}</div>
              <div class="filter-strictness-desc">
                {s === "leveling" && "Show almost everything"}
                {s === "mapping" && "Hide low currency & normals"}
                {s === "endgame" && "Only relevant drops"}
                {s === "ultra_strict" && "Absolute minimum"}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Currency */}
      <div class="filter-section">
        <h3>Currency</h3>
        <div class="filter-grid-rows">
          <div class="filter-row-item">
            <span class="filter-row-label">T1 — Mirror, Divine, Exalt</span>
            <span class="filter-row-controls">Sound: <SoundSelect value={t1Sound()} onChange={setT1Sound} /> Beam: <BeamSelect value={t1Beam()} onChange={setT1Beam} /></span>
          </div>
          <div class="filter-row-item">
            <span class="filter-row-label">T2 — Chaos, Vaal, Regal, GCP</span>
            <span class="filter-row-controls">Sound: <SoundSelect value={t2Sound()} onChange={setT2Sound} /> Beam: <BeamSelect value={t2Beam()} onChange={setT2Beam} /></span>
          </div>
          <div class="filter-row-item">
            <span class="filter-row-label">T3 — Alchemy, Chisel, Jeweller</span>
            <span class="filter-row-controls">Sound: <SoundSelect value={t3Sound()} onChange={setT3Sound} /></span>
          </div>
          <div class="filter-row-item">
            <span class="filter-row-label">T4 — Alteration, Augmentation</span>
            <label class="filter-toggle-label"><input type="checkbox" checked={showT4()} onChange={(e) => setShowT4(e.currentTarget.checked)} /> Show</label>
          </div>
          <div class="filter-row-item">
            <span class="filter-row-label">T5 — Scrolls, Scraps</span>
            <label class="filter-toggle-label"><input type="checkbox" checked={showT5()} onChange={(e) => setShowT5(e.currentTarget.checked)} /> Show</label>
          </div>
        </div>
        <div class="filter-checkbox-row">
          <label><input type="checkbox" checked={showEssences()} onChange={(e) => setShowEssences(e.currentTarget.checked)} /> Essences</label>
          <label><input type="checkbox" checked={showFossils()} onChange={(e) => setShowFossils(e.currentTarget.checked)} /> Fossils</label>
          <label><input type="checkbox" checked={showCatalysts()} onChange={(e) => setShowCatalysts(e.currentTarget.checked)} /> Catalysts</label>
          <label><input type="checkbox" checked={showOils()} onChange={(e) => setShowOils(e.currentTarget.checked)} /> Oils</label>
          <label><input type="checkbox" checked={showDeliriumOrbs()} onChange={(e) => setShowDeliriumOrbs(e.currentTarget.checked)} /> Delirium Orbs</label>
          <label><input type="checkbox" checked={showFragments()} onChange={(e) => setShowFragments(e.currentTarget.checked)} /> Fragments</label>
        </div>
      </div>

      {/* Equipment */}
      <div class="filter-section">
        <h3>Equipment</h3>
        <div class="filter-checkbox-row">
          <label><input type="checkbox" checked={showRareJewellery()} onChange={(e) => setShowRareJewellery(e.currentTarget.checked)} /> Rare Jewellery (75+)</label>
          <label><input type="checkbox" checked={showRareWeapons()} onChange={(e) => setShowRareWeapons(e.currentTarget.checked)} /> Rare Weapons (82+)</label>
          <label><input type="checkbox" checked={showFiveLinks()} onChange={(e) => setShowFiveLinks(e.currentTarget.checked)} /> 5-Links</label>
          <label><input type="checkbox" checked={showRgb()} onChange={(e) => setShowRgb(e.currentTarget.checked)} /> RGB Items</label>
        </div>
        <div class="filter-row-item">
          <span class="filter-row-label">6-Link Sound</span>
          <span class="filter-row-controls"><SoundSelect value={sixLinkSound()} onChange={setSixLinkSound} /></span>
        </div>
      </div>

      {/* Maps */}
      <div class="filter-section">
        <h3>Maps</h3>
        <div class="filter-row-item">
          <span class="filter-row-label">Show tiers</span>
          <select class="filter-select" value={mapMinTier()} onChange={(e) => setMapMinTier(Number(e.currentTarget.value))}>
            <option value={1}>All</option>
            <option value={6}>T6+</option>
            <option value={11}>T11+</option>
            <option value={14}>T14+</option>
            <option value={16}>T16 only</option>
          </select>
          <span class="filter-row-label" style="margin-left: 12px">Drop sound</span>
          <SoundSelect value={mapSound()} onChange={setMapSound} />
        </div>
        <label class="filter-checkbox-inline"><input type="checkbox" checked={showUniqueMaps()} onChange={(e) => setShowUniqueMaps(e.currentTarget.checked)} /> Show Unique Maps</label>
      </div>

      {/* Gems */}
      <div class="filter-section">
        <h3>Gems</h3>
        <div class="filter-row-item">
          <span class="filter-row-label">Min quality</span>
          <select class="filter-select" value={gemMinQual()} onChange={(e) => setGemMinQual(Number(e.currentTarget.value))}>
            <option value={0}>All</option>
            <option value={10}>10%+</option>
            <option value={15}>15%+</option>
            <option value={20}>20% only</option>
          </select>
          <span class="filter-row-label" style="margin-left: 12px">Min level</span>
          <select class="filter-select" value={gemMinLevel()} onChange={(e) => setGemMinLevel(Number(e.currentTarget.value))}>
            <option value={1}>All</option>
            <option value={19}>19+</option>
            <option value={20}>20+</option>
            <option value={21}>21 only</option>
          </select>
        </div>
      </div>

      {/* Flasks */}
      <div class="filter-section">
        <h3>Flasks</h3>
        <div class="filter-checkbox-row">
          <label><input type="checkbox" checked={showUtilFlasks()} onChange={(e) => setShowUtilFlasks(e.currentTarget.checked)} /> Utility Flasks</label>
          <label><input type="checkbox" checked={showLifeMana()} onChange={(e) => setShowLifeMana(e.currentTarget.checked)} /> Life/Mana Flasks</label>
        </div>
      </div>

      {/* Sounds */}
      <div class="filter-section">
        <h3>Sounds</h3>
        <div class="filter-grid-rows">
          <div class="filter-row-item">
            <span class="filter-row-label">Unique drops</span>
            <SoundSelect value={uniqueSound()} onChange={setUniqueSound} />
          </div>
        </div>
      </div>

      {/* Build Tailored */}
      <div class="filter-section filter-build-section">
        <h3>
          <label>
            <input type="checkbox" checked={buildEnabled()} onChange={(e) => setBuildEnabled(e.currentTarget.checked)} />
            {" "}Build-Tailored Mode
          </label>
        </h3>
        <Show when={buildEnabled()}>
          <Show
            when={build()}
            fallback={<div class="filter-no-build">No build loaded. Go to Build Viewer and load a PoB code first.</div>}
          >
            <div class="filter-build-info">
              Build: <strong>{build()!.ascendancy_name || build()!.class_name}</strong> — Level {build()!.level}
            </div>
            <div class="filter-checkbox-row">
              <label><input type="checkbox" checked={hlWeapons()} onChange={(e) => setHlWeapons(e.currentTarget.checked)} /> Highlight weapon bases</label>
              <label><input type="checkbox" checked={hlGems()} onChange={(e) => setHlGems(e.currentTarget.checked)} /> Highlight build gems</label>
              <label><input type="checkbox" checked={hlResists()} onChange={(e) => setHlResists(e.currentTarget.checked)} /> Highlight resist fillers</label>
              <label><input type="checkbox" checked={hlClusters()} onChange={(e) => setHlClusters(e.currentTarget.checked)} /> Highlight cluster jewels</label>
            </div>
            <div class="filter-row-item">
              <span class="filter-row-label">Build gear sound</span>
              <SoundSelect value={buildGearSound()} onChange={setBuildGearSound} />
            </div>
          </Show>
        </Show>
      </div>

      {/* Actions */}
      <div class="filter-section">
        <div class="filter-main-actions">
          <button class="filter-generate-main-btn" onClick={handleGenerate} disabled={loading()}>
            {loading() ? "Generating..." : "Generate Filter"}
          </button>
          <Show when={filterText()}>
            <button class="filter-install-main-btn" onClick={handleInstall}>Install to PoE</button>
            <button class="filter-upload-btn" onClick={() => { setShowUploadModal(true); setUploadMsg(""); }}>Upload to Account</button>
            <button class="filter-download-btn" onClick={handleDownload}>Download .filter</button>
            <button class="filter-copy-main-btn" onClick={handleCopy}>Copy</button>
          </Show>
        </div>
        <Show when={error()}><div class="filter-error">{error()}</div></Show>
        <Show when={savedPath()}>
          <div class="filter-success">Installed to: {savedPath()}<br />In-game: Options &gt; UI &gt; Item Filter &gt; select "PathOfPurpose"</div>
        </Show>
        <Show when={uploadMsg()}>
          <div class={uploadMsg().startsWith("Upload failed") ? "filter-error" : "filter-success"}>{uploadMsg()}</div>
        </Show>
      </div>

      {/* Upload Modal */}
      <Show when={showUploadModal()}>
        <div class="filter-upload-modal">
          <h3>Upload Filter to PoE Account</h3>
          <p class="filter-upload-hint">This uploads the filter directly to your PoE account via the API. Available in-game on any machine (including GeForce Now). If a filter with the same name exists, it will be overwritten.</p>
          <div class="filter-upload-field">
            <label>Filter Name</label>
            <input type="text" value={uploadName()} onInput={(e) => setUploadName(e.currentTarget.value)} placeholder="PathOfPurpose" />
          </div>
          <div class="filter-upload-field">
            <label>Description (optional)</label>
            <input type="text" value={uploadDesc()} onInput={(e) => setUploadDesc(e.currentTarget.value)} placeholder="Generated by Path of Purpose" />
          </div>
          <div class="filter-upload-actions">
            <button class="filter-upload-confirm-btn" onClick={handleUpload} disabled={uploading() || !uploadName().trim()}>
              {uploading() ? "Uploading..." : "Upload"}
            </button>
            <button class="filter-upload-cancel-btn" onClick={() => setShowUploadModal(false)}>Cancel</button>
          </div>
        </div>
      </Show>

      {/* Manage Account Filters */}
      <div class="filter-section">
        <button class="filter-manage-toggle" onClick={toggleManage}>
          {showManage() ? "Hide" : "Manage"} Account Filters
        </button>
        <Show when={showManage()}>
          <div class="filter-manage-panel">
            <Show when={loadingFilters()}>
              <div class="filter-manage-loading">Loading filters...</div>
            </Show>
            <Show when={manageError()}>
              <div class="filter-error">{manageError()}</div>
            </Show>
            <Show when={!loadingFilters() && accountFilters().length === 0 && !manageError()}>
              <div class="filter-manage-empty">No filters found on your account.</div>
            </Show>
            <Show when={accountFilters().length > 0}>
              <table class="filter-manage-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Realm</th>
                    <th>Public</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <For each={accountFilters()}>
                    {(f) => (
                      <tr>
                        <td>{f.filter_name}</td>
                        <td>{f.realm}</td>
                        <td>{f.public ? "Yes" : "No"}</td>
                        <td>
                          <button
                            class="filter-manage-delete-btn"
                            disabled={deletingId() === f.id}
                            onClick={() => {
                              if (confirm(`Delete filter "${f.filter_name}"?`)) {
                                handleDeleteFilter(f.id);
                              }
                            }}
                          >
                            {deletingId() === f.id ? "..." : "Delete"}
                          </button>
                        </td>
                      </tr>
                    )}
                  </For>
                </tbody>
              </table>
            </Show>
            <button class="filter-manage-refresh-btn" onClick={loadAccountFilters} disabled={loadingFilters()}>
              Refresh
            </button>
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
    </div>
  );
}
