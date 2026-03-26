import { createSignal, Show, onCleanup, type Accessor } from "solid-js";
import type { Build, FilterStrictness, HotItemsResult } from "../lib/types";
import {
  generateFilter,
  saveFilterFile,
  fetchHotItems,
  fetchLeagues,
} from "../lib/commands";

interface FilterPageProps {
  loadedBuild?: Accessor<Build | null>;
}

const BEAMS = ["", "Red", "Green", "Blue", "Yellow", "White", "Orange", "Cyan", "Purple", "Pink", "Brown", "Grey"];
const SOUNDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];
const MINIMAP_ICONS = ["", "0 Red Star", "0 Yellow Star", "0 Green Star", "0 Blue Star", "0 White Star", "1 Red Circle", "1 Yellow Circle", "1 Green Circle", "1 Blue Circle", "1 White Circle", "2 Red Diamond", "2 Yellow Diamond", "2 White Diamond"];

function poeToHex(poe: string): string {
  const p = poe.split(" ").map(Number);
  return "#" + [p[0] ?? 0, p[1] ?? 0, p[2] ?? 0].map((v) => v.toString(16).padStart(2, "0")).join("");
}

function hexToPoe(hex: string, alpha?: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return alpha !== undefined ? `${r} ${g} ${b} ${alpha}` : `${r} ${g} ${b}`;
}

function poeAlpha(poe: string): number {
  const p = poe.split(" ");
  return p.length >= 4 ? Number(p[3]) : 255;
}

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
  // Currency colors (PoE format "R G B" / "R G B A")
  const [t1Colors, setT1Colors] = createSignal({ text: "255 0 0", bg: "255 255 255 255", border: "255 0 0" });
  const [t2Colors, setT2Colors] = createSignal({ text: "255 170 0", bg: "0 0 0 220", border: "255 170 0" });
  const [t3Colors, setT3Colors] = createSignal({ text: "200 200 100", bg: "0 0 0 200", border: "200 200 100" });
  const [t1Icon, setT1Icon] = createSignal("0 Red Star");
  const [t2Icon, setT2Icon] = createSignal("1 Yellow Circle");

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

  // Filter name
  const [filterName, setFilterName] = createSignal("PathOfPurpose");

  // Hot Items (poe.ninja)
  const [hotEnabled, setHotEnabled] = createSignal(false);
  const [hotItems, setHotItems] = createSignal<HotItemsResult | null>(null);
  const [hotLoading, setHotLoading] = createSignal(false);
  const [hotError, setHotError] = createSignal("");
  const [hotToast, setHotToast] = createSignal("");
  const [hotLeague, setHotLeague] = createSignal("Standard");
  const [hotLeagues, setHotLeagues] = createSignal<string[]>(["Standard"]);
  let hotTimer: ReturnType<typeof setInterval> | null = null;

  // Load leagues for hot items
  fetchLeagues().then((r) => { if (r.length > 0) setHotLeagues(r); }).catch(() => {});

  async function refreshHotPrices() {
    setHotLoading(true);
    setHotError("");
    try {
      const result = await fetchHotItems(hotLeague());
      setHotItems(result);
      setHotToast(`${result.total_count} hot items loaded`);
      setTimeout(() => setHotToast(""), 4000);
    } catch (e) {
      setHotError(String(e));
    } finally {
      setHotLoading(false);
    }
  }

  function toggleHot(enabled: boolean) {
    setHotEnabled(enabled);
    if (enabled) {
      refreshHotPrices();
      hotTimer = setInterval(refreshHotPrices, 6 * 60 * 60 * 1000); // 6 hours
    } else {
      if (hotTimer) { clearInterval(hotTimer); hotTimer = null; }
    }
  }

  onCleanup(() => { if (hotTimer) clearInterval(hotTimer); });

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
        tier1: { show: true, sound: t1Sound(), volume: 300, beam: t1Beam(), icon: t1Icon(), font_size: 45, text_color: t1Colors().text, bg_color: t1Colors().bg, border_color: t1Colors().border },
        tier2: { show: true, sound: t2Sound(), volume: 300, beam: t2Beam(), icon: t2Icon(), font_size: 38, text_color: t2Colors().text, bg_color: t2Colors().bg, border_color: t2Colors().border },
        tier3: { show: true, sound: t3Sound(), volume: 200, beam: "", icon: "", font_size: 32, text_color: t3Colors().text, bg_color: t3Colors().bg, border_color: t3Colors().border },
        tier4: { show: showT4(), sound: 0, volume: 0, beam: "", icon: "", font_size: 26, text_color: "170 158 130", bg_color: "", border_color: "" },
        tier5: { show: showT5(), sound: 0, volume: 0, beam: "", icon: "", font_size: 20, text_color: "120 120 120", bg_color: "", border_color: "" },
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
      hot_items: {
        enabled: hotEnabled(),
        tier1: hotItems()?.tier1 ?? [],
        tier2: hotItems()?.tier2 ?? [],
        tier3: hotItems()?.tier3 ?? [],
        tier4: hotItems()?.tier4 ?? [],
      },
      filter_name: filterName() || "PathOfPurpose",
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
      const name = filterName() || "PathOfPurpose";
      const path = await saveFilterFile(filterText(), name);
      setSavedPath(path);
    } catch (e) {
      setError(String(e));
    }
  }

  function handleDownload() {
    if (!filterText()) return;
    const name = filterName() || "PathOfPurpose";
    const blob = new Blob([filterText()], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${name}.filter`;
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

  const IconSelect = (p: { value: string; onChange: (v: string) => void }) => (
    <select class="filter-select" value={p.value} onChange={(e) => p.onChange(e.currentTarget.value)}>
      {MINIMAP_ICONS.map((i) => <option value={i}>{i || "None"}</option>)}
    </select>
  );

  const ColorRow = (p: {
    colors: { text: string; bg: string; border: string };
    onChange: (c: { text: string; bg: string; border: string }) => void;
  }) => {
    const [open, setOpen] = createSignal(false);
    return (
      <div>
        <button class="filter-color-toggle" onClick={() => setOpen(!open())}>
          {open() ? "Hide" : "Appearance"}
          <span class="filter-color-swatches-inline">
            <span class="filter-swatch-dot" style={{ background: poeToHex(p.colors.text) }} />
            <span class="filter-swatch-dot" style={{ background: p.colors.bg ? poeToHex(p.colors.bg) : "#000" }} />
            <span class="filter-swatch-dot" style={{ background: p.colors.border ? poeToHex(p.colors.border) : "transparent" }} />
          </span>
        </button>
        <Show when={open()}>
          <div class="filter-color-row">
            <label class="filter-color-item">
              <span class="filter-color-label">Text</span>
              <input type="color" value={poeToHex(p.colors.text)} onChange={(e) => p.onChange({ ...p.colors, text: hexToPoe(e.currentTarget.value) })} />
            </label>
            <label class="filter-color-item">
              <span class="filter-color-label">Background</span>
              <input type="color" value={p.colors.bg ? poeToHex(p.colors.bg) : "#000000"} onChange={(e) => p.onChange({ ...p.colors, bg: hexToPoe(e.currentTarget.value, poeAlpha(p.colors.bg)) })} />
            </label>
            <label class="filter-color-item">
              <span class="filter-color-label">Opacity</span>
              <input type="range" min="0" max="255" value={poeAlpha(p.colors.bg)} class="filter-opacity-slider" onChange={(e) => {
                const hex = p.colors.bg ? poeToHex(p.colors.bg) : "#000000";
                p.onChange({ ...p.colors, bg: hexToPoe(hex, Number(e.currentTarget.value)) });
              }} />
            </label>
            <label class="filter-color-item">
              <span class="filter-color-label">Border</span>
              <input type="color" value={p.colors.border ? poeToHex(p.colors.border) : "#000000"} onChange={(e) => p.onChange({ ...p.colors, border: hexToPoe(e.currentTarget.value) })} />
            </label>
          </div>
        </Show>
      </div>
    );
  };

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
            <span class="filter-row-controls">Sound: <SoundSelect value={t1Sound()} onChange={setT1Sound} /> Beam: <BeamSelect value={t1Beam()} onChange={setT1Beam} /> Icon: <IconSelect value={t1Icon()} onChange={setT1Icon} /></span>
            <ColorRow colors={t1Colors()} onChange={setT1Colors} />
          </div>
          <div class="filter-row-item">
            <span class="filter-row-label">T2 — Chaos, Vaal, Regal, GCP</span>
            <span class="filter-row-controls">Sound: <SoundSelect value={t2Sound()} onChange={setT2Sound} /> Beam: <BeamSelect value={t2Beam()} onChange={setT2Beam} /> Icon: <IconSelect value={t2Icon()} onChange={setT2Icon} /></span>
            <ColorRow colors={t2Colors()} onChange={setT2Colors} />
          </div>
          <div class="filter-row-item">
            <span class="filter-row-label">T3 — Alchemy, Chisel, Jeweller</span>
            <span class="filter-row-controls">Sound: <SoundSelect value={t3Sound()} onChange={setT3Sound} /></span>
            <ColorRow colors={t3Colors()} onChange={setT3Colors} />
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

      {/* Hot Items (poe.ninja) */}
      <div class="filter-section">
        <h3>
          <label>
            <input type="checkbox" checked={hotEnabled()} onChange={(e) => toggleHot(e.currentTarget.checked)} />
            {" "}Hot Items — poe.ninja Prices
          </label>
        </h3>
        <Show when={hotEnabled()}>
          <div class="filter-row-item" style={{ "margin-bottom": "8px" }}>
            <span class="filter-row-label">League</span>
            <select class="filter-select" value={hotLeague()} onChange={(e) => setHotLeague(e.currentTarget.value)}>
              {hotLeagues().map((l) => <option value={l}>{l}</option>)}
            </select>
            <button style={{ "font-size": "12px", padding: "4px 12px", "margin-left": "8px" }} onClick={refreshHotPrices} disabled={hotLoading()}>
              {hotLoading() ? "Fetching..." : "Refresh Prices"}
            </button>
          </div>
          <Show when={hotError()}><div class="filter-error">{hotError()}</div></Show>
          <Show when={hotToast()}><div class="filter-success">{hotToast()}</div></Show>
          <Show when={hotItems()}>
            <div style={{ "font-size": "12px", color: "var(--text-secondary)", display: "flex", gap: "16px", "flex-wrap": "wrap", padding: "4px 0" }}>
              <span style={{ color: "#ff00c8", "font-weight": "600" }}>T1 Jackpot: {hotItems()!.tier1.length}</span>
              <span style={{ color: "#00dcdc", "font-weight": "600" }}>T2 Valuable: {hotItems()!.tier2.length}</span>
              <span style={{ color: "#78ff78", "font-weight": "600" }}>T3 Notable: {hotItems()!.tier3.length}</span>
              <span style={{ color: "#ff9632", "font-weight": "600" }}>T4 Check: {hotItems()!.tier4.length}</span>
            </div>
            <div style={{ "font-size": "11px", color: "var(--text-muted)", "margin-top": "4px" }}>
              Last updated: {new Date(hotItems()!.fetched_at).toLocaleTimeString()} | Divine: {Math.round(hotItems()!.divine_ratio)}c
            </div>
          </Show>
        </Show>
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

      {/* Filter Name + Actions */}
      <div class="filter-section">
        <div class="filter-row-item" style={{ "margin-bottom": "12px" }}>
          <span class="filter-row-label">Filter Name</span>
          <input
            type="text"
            value={filterName()}
            onInput={(e) => setFilterName(e.currentTarget.value.replace(/[^a-zA-Z0-9_\- ]/g, ""))}
            placeholder="PathOfPurpose"
            style={{
              background: "var(--bg-input)", border: "1px solid var(--border)",
              "border-radius": "var(--radius)", color: "var(--text-primary)",
              padding: "6px 12px", "font-size": "13px", width: "200px",
            }}
          />
        </div>
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
          <div class="filter-success">Installed to: {savedPath()}<br />In-game: Options &gt; UI &gt; Item Filter &gt; select "{filterName() || "PathOfPurpose"}"</div>
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
