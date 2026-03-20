import { createSignal, Show, type Accessor } from "solid-js";
import type { Build, FilterStrictness } from "../lib/types";
import {
  generateFilter,
  saveFilterFile,
} from "../lib/commands";

interface FilterPageProps {
  loadedBuild?: Accessor<Build | null>;
}

const BEAMS = ["", "Red", "Green", "Blue", "Yellow", "White", "Orange", "Cyan", "Purple", "Pink", "Brown", "Grey"];
const SOUNDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];

/** Create a convolver node that simulates a reverb tail. */
function createReverb(ctx: AudioContext, duration: number, decay: number): ConvolverNode {
  const rate = ctx.sampleRate;
  const len = rate * duration;
  const buf = ctx.createBuffer(2, len, rate);
  for (let ch = 0; ch < 2; ch++) {
    const data = buf.getChannelData(ch);
    for (let i = 0; i < len; i++) {
      data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
    }
  }
  const conv = ctx.createConvolver();
  conv.buffer = buf;
  return conv;
}

/** Add an oscillator with envelope to the audio graph. */
function addTone(
  ctx: AudioContext, dest: AudioNode,
  type: OscillatorType, freq: number, vol: number,
  attack: number, sustain: number, release: number, delay: number = 0,
) {
  const osc = ctx.createOscillator();
  const env = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, ctx.currentTime);
  const t = ctx.currentTime + delay;
  env.gain.setValueAtTime(0, t);
  env.gain.linearRampToValueAtTime(vol, t + attack);
  env.gain.setValueAtTime(vol, t + attack + sustain);
  env.gain.exponentialRampToValueAtTime(0.001, t + attack + sustain + release);
  osc.connect(env);
  env.connect(dest);
  osc.start(t);
  osc.stop(t + attack + sustain + release + 0.05);
  return osc;
}

/** Play a vibrant loot filter alert sound (3-5s). Each ID has a distinct character. */
function playAlertSound(soundId: number) {
  if (soundId === 0) return;
  try {
    const ctx = new AudioContext();
    const master = ctx.createGain();
    master.gain.setValueAtTime(0.35, ctx.currentTime);
    const reverb = createReverb(ctx, 3, 2.5);
    const dry = ctx.createGain();
    const wet = ctx.createGain();
    dry.gain.setValueAtTime(0.6, ctx.currentTime);
    wet.gain.setValueAtTime(0.4, ctx.currentTime);
    dry.connect(master);
    reverb.connect(wet);
    wet.connect(master);
    master.connect(ctx.destination);

    const allOsc: OscillatorNode[] = [];
    const track = (o: OscillatorNode) => { allOsc.push(o); return o; };

    if (soundId >= 1 && soundId <= 4) {
      // Warm chimes — ascending arpeggio with soft sine layers
      const roots = [262, 294, 330, 392]; // C4, D4, E4, G4
      const root = roots[soundId - 1];
      const notes = [root, root * 1.25, root * 1.5, root * 2];
      notes.forEach((f, i) => {
        track(addTone(ctx, dry, "sine", f, 0.25, 0.05, 0.6, 1.8, i * 0.35));
        track(addTone(ctx, reverb, "sine", f * 2, 0.08, 0.03, 0.3, 1.5, i * 0.35 + 0.05));
      });
      // Soft pad underneath
      track(addTone(ctx, reverb, "sine", root / 2, 0.12, 0.3, 1.5, 1.2));
    } else if (soundId >= 5 && soundId <= 8) {
      // Bright bells — metallic shimmer with harmonics
      const roots = [523, 587, 659, 784]; // C5, D5, E5, G5
      const root = roots[soundId - 5];
      // Bell fundamental + inharmonic partials
      track(addTone(ctx, dry, "sine", root, 0.22, 0.01, 0.8, 2.5));
      track(addTone(ctx, dry, "sine", root * 2.76, 0.1, 0.01, 0.4, 2.0));
      track(addTone(ctx, reverb, "sine", root * 5.4, 0.05, 0.01, 0.2, 1.5));
      track(addTone(ctx, dry, "triangle", root * 1.5, 0.08, 0.01, 0.5, 2.2));
      // Sparkle arpeggios
      for (let i = 0; i < 3; i++) {
        track(addTone(ctx, reverb, "sine", root * (1 + i * 0.5), 0.06, 0.02, 0.15, 1.0, 0.8 + i * 0.25));
      }
    } else if (soundId >= 9 && soundId <= 12) {
      // Epic power tones — deep layered fifths with rising swell
      const roots = [131, 147, 165, 175]; // C3, D3, E3, F3
      const root = roots[soundId - 9];
      // Deep foundation
      track(addTone(ctx, dry, "sawtooth", root, 0.12, 0.4, 1.5, 2.0));
      track(addTone(ctx, dry, "sawtooth", root * 1.5, 0.1, 0.4, 1.2, 1.8));
      // Octave layer
      track(addTone(ctx, dry, "square", root * 2, 0.07, 0.3, 1.0, 1.5));
      // Bright overtone swell
      track(addTone(ctx, reverb, "sine", root * 4, 0.08, 0.8, 0.8, 1.5));
      track(addTone(ctx, reverb, "sine", root * 3, 0.06, 0.6, 1.0, 1.8));
      // Sub bass hit
      track(addTone(ctx, dry, "sine", root / 2, 0.15, 0.05, 0.5, 2.5));
    } else {
      // Celestial shimmer — ethereal choir-like tones with slow bloom
      const roots = [392, 440, 494, 523]; // G4, A4, B4, C5
      const root = roots[soundId - 13];
      // Slow-blooming pad voices
      track(addTone(ctx, reverb, "sine", root, 0.18, 1.2, 1.5, 2.0));
      track(addTone(ctx, reverb, "sine", root * 1.5, 0.12, 1.0, 1.2, 2.0, 0.3));
      track(addTone(ctx, reverb, "sine", root * 2, 0.08, 0.8, 1.0, 2.0, 0.6));
      // Detuned shimmer (chorus effect)
      track(addTone(ctx, reverb, "sine", root * 1.003, 0.1, 1.0, 1.2, 2.2));
      track(addTone(ctx, reverb, "sine", root * 0.997, 0.1, 1.0, 1.2, 2.2));
      // Gentle high sparkle
      for (let i = 0; i < 4; i++) {
        track(addTone(ctx, reverb, "sine", root * 3 + i * 50, 0.03, 0.05, 0.2, 1.5, 1.0 + i * 0.6));
      }
      // Sub warmth
      track(addTone(ctx, dry, "sine", root / 2, 0.08, 0.8, 2.0, 2.0));
    }

    // Close context after the longest sound finishes
    const maxDur = soundId >= 13 ? 5.5 : soundId >= 9 ? 4.5 : soundId >= 5 ? 4.0 : 3.5;
    setTimeout(() => ctx.close().catch(() => {}), maxDur * 1000);
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
  const [showSixLinks, _setShowSixLinks] = createSignal(true);
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
            <button class="filter-download-btn" onClick={handleDownload}>Download .filter</button>
            <button class="filter-copy-main-btn" onClick={handleCopy}>Copy</button>
          </Show>
        </div>
        <Show when={error()}><div class="filter-error">{error()}</div></Show>
        <Show when={savedPath()}>
          <div class="filter-success">Installed to: {savedPath()}<br />In-game: Options &gt; UI &gt; Item Filter &gt; select "PathOfPurpose"</div>
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
