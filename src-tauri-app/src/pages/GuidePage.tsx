import { createSignal, Show } from "solid-js";
import { decodeBuild, scrapeBuildGuide } from "../lib/commands";
import type { Build, BuildGuide } from "../lib/types";
import BuildSummary from "../components/BuildSummary";

/** Convert a scraped BuildGuide into a Build so BuildSummary can render it. */
function guideToBuild(guide: BuildGuide): Build {
  const skillSets = guide.brackets.map((bracket) => ({
    title: bracket.title,
    skills: bracket.gem_groups.map((gg) => ({
      slot: gg.slot,
      label: "",
      is_enabled: true,
      gems: gg.gems.map((g) => ({
        name: g.name,
        gem_id: "",
        level: 20,
        quality: 0,
        is_support: g.is_support,
        is_enabled: true,
        icon_url: g.icon_url,
      })),
    })),
  }));

  // Build flat item list with unique IDs, and item sets mapping slots to IDs
  let nextId = 1;
  const allItems: Build["items"] = [];
  const itemSets: Build["item_sets"] = [];

  for (const bracket of guide.brackets) {
    const slotMap: Record<string, number> = {};
    for (const gi of bracket.items) {
      const id = nextId++;
      allItems.push({
        id,
        slot: gi.slot,
        name: gi.name,
        base_type: "",
        rarity: "NORMAL",
        level: 0,
        quality: 0,
        sockets: "",
        implicits: [],
        explicits: [],
        raw_text: "",
        icon_url: gi.icon_url,
      });
      slotMap[gi.slot] = id;
    }
    itemSets.push({ title: bracket.title, slot_map: slotMap });
  }

  // For the flat skill_groups / items, use the first bracket
  const firstBracket = guide.brackets[0];
  const skillGroups = firstBracket
    ? firstBracket.gem_groups.map((gg) => ({
        slot: gg.slot,
        label: "",
        is_enabled: true,
        gems: gg.gems.map((g) => ({
          name: g.name,
          gem_id: "",
          level: 20,
          quality: 0,
          is_support: g.is_support,
          is_enabled: true,
          icon_url: g.icon_url,
        })),
      }))
    : [];

  return {
    class_name: guide.class_name,
    ascendancy_name: guide.ascendancy_name,
    level: 1,
    main_socket_group: 1,
    passive_specs: guide.brackets.map((b) => ({
      title: b.title,
      tree_version: "",
      class_id: 0,
      ascendancy_id: 0,
      nodes: [],
      overrides: {},
      url: "",
    })),
    skill_groups: skillGroups,
    items: allItems,
    config: { entries: {} },
    skill_sets: skillSets,
    item_sets: itemSets,
    active_skill_set: 0,
    active_item_set: 0,
    pob_version: "",
    build_name: guide.title,
  };
}

function isUrl(input: string): boolean {
  return /^https?:\/\//i.test(input);
}

export default function GuidePage() {
  const [input, setInput] = createSignal("");
  const [build, setBuild] = createSignal<Build | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");

  async function handleLoad() {
    const raw = input().trim();
    if (!raw) return;

    setLoading(true);
    setError("");
    setBuild(null);

    try {
      if (isUrl(raw)) {
        const guide: BuildGuide = await scrapeBuildGuide(raw);
        setBuild(guideToBuild(guide));
      } else {
        const result: Build = await decodeBuild(raw);
        setBuild(result);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 class="page-title">Build Guide</h1>
      <p class="page-subtitle">
        Paste a mobalytics.gg URL or a PoB export code to view gem setups and
        gear.
      </p>

      <div class="input-group">
        <label for="guide-input">Guide URL or PoB Code</label>
        <textarea
          id="guide-input"
          placeholder="https://mobalytics.gg/poe-2/builds/... or paste PoB export code"
          value={input()}
          onInput={(e) => setInput(e.currentTarget.value)}
          rows={3}
        />
      </div>

      <button onClick={handleLoad} disabled={loading() || !input().trim()}>
        <Show when={loading()} fallback="Load Guide">
          <span class="spinner" />
          Loading...
        </Show>
      </button>

      <Show when={error()}>
        <div class="error-toast" style={{ "margin-top": "16px" }}>
          {error()}
        </div>
      </Show>

      <Show when={build()}>
        <div style={{ "margin-top": "24px" }}>
          <BuildSummary build={build()!} />
        </div>
      </Show>
    </div>
  );
}
