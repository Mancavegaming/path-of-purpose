import { createMemo, createSignal, For, Show } from "solid-js";
import type { CalcResult, DefenceResult } from "../lib/types";

interface BossReadinessProps {
  dpsResult: CalcResult | null;
}

type Status = "pass" | "warn" | "fail";

interface Check {
  label: string;
  value: string;
  need: string;
  status: Status;
}

interface BossThresholds {
  name: string;
  category: string;
  dps: number;
  life: number;
  eleRes: number;
  chaosRes?: number;
  spellSupp?: number;
  notes?: string;
}

const BOSSES: BossThresholds[] = [
  // Map progression
  { name: "White Maps (T1-T5)", category: "Maps", dps: 200_000, life: 4000, eleRes: 75 },
  { name: "Yellow Maps (T6-T10)", category: "Maps", dps: 500_000, life: 4500, eleRes: 75 },
  { name: "Red Maps (T11-T13)", category: "Maps", dps: 1_000_000, life: 5000, eleRes: 75 },
  { name: "T14-T16 Maps", category: "Maps", dps: 2_000_000, life: 5500, eleRes: 75 },
  // Pinnacle
  { name: "The Elder", category: "Pinnacle", dps: 1_500_000, life: 5000, eleRes: 75 },
  { name: "The Shaper", category: "Pinnacle", dps: 2_000_000, life: 5500, eleRes: 75 },
  { name: "Sirus (A8)", category: "Pinnacle", dps: 2_000_000, life: 5500, eleRes: 75, chaosRes: 0, notes: "Chaos res helps vs storms" },
  { name: "The Maven", category: "Pinnacle", dps: 3_000_000, life: 5500, eleRes: 75 },
  { name: "Uber Elder", category: "Pinnacle", dps: 3_000_000, life: 6000, eleRes: 75 },
  { name: "Cortex", category: "Pinnacle", dps: 3_000_000, life: 6000, eleRes: 75 },
  { name: "The Feared", category: "Pinnacle", dps: 5_000_000, life: 6000, eleRes: 75 },
  // Uber
  { name: "Uber Shaper", category: "Uber", dps: 8_000_000, life: 7000, eleRes: 75, spellSupp: 100 },
  { name: "Uber Sirus", category: "Uber", dps: 10_000_000, life: 7000, eleRes: 75, chaosRes: 30, spellSupp: 100 },
  { name: "Uber Maven", category: "Uber", dps: 10_000_000, life: 7000, eleRes: 75, spellSupp: 100 },
  { name: "Uber Elder", category: "Uber", dps: 10_000_000, life: 7000, eleRes: 75, spellSupp: 100 },
];

function formatDps(v: number): string {
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + "M";
  if (v >= 1_000) return (v / 1_000).toFixed(0) + "K";
  return Math.round(v).toString();
}

function checkStat(value: number, need: number, warnPct: number = 0.7): Status {
  if (value >= need) return "pass";
  if (value >= need * warnPct) return "warn";
  return "fail";
}

function checkRes(value: number, need: number): Status {
  if (value >= need) return "pass";
  if (value >= need - 10) return "warn";
  return "fail";
}

function evaluateBoss(
  boss: BossThresholds,
  dps: number,
  def: DefenceResult,
): { checks: Check[]; overall: Status } {
  const checks: Check[] = [];
  const fireRes = def.elemental_resistances?.fire ?? 0;
  const coldRes = def.elemental_resistances?.cold ?? 0;
  const lightRes = def.elemental_resistances?.lightning ?? 0;
  const minEleRes = Math.min(fireRes, coldRes, lightRes);
  const chaosRes = def.chaos_resistance ?? 0;

  // DPS check
  const dpsStatus = checkStat(dps, boss.dps);
  checks.push({
    label: "DPS",
    value: formatDps(dps),
    need: formatDps(boss.dps) + "+",
    status: dpsStatus,
  });

  // Life check
  const lifeStatus = checkStat(def.life, boss.life);
  checks.push({
    label: "Life",
    value: formatDps(def.life),
    need: formatDps(boss.life) + "+",
    status: lifeStatus,
  });

  // Elemental res check
  const resStatus = checkRes(minEleRes, boss.eleRes);
  checks.push({
    label: "Ele Res",
    value: `${minEleRes.toFixed(0)}%`,
    need: `${boss.eleRes}%`,
    status: resStatus,
  });

  // Chaos res (if boss requires it)
  if (boss.chaosRes !== undefined) {
    const crStatus = checkRes(chaosRes, boss.chaosRes);
    checks.push({
      label: "Chaos Res",
      value: `${chaosRes.toFixed(0)}%`,
      need: `${boss.chaosRes}%+`,
      status: crStatus,
    });
  }

  // Spell suppression (if boss requires it)
  if (boss.spellSupp !== undefined) {
    const ssStatus = checkStat(def.spell_suppression, boss.spellSupp, 0.8);
    checks.push({
      label: "Spell Supp",
      value: `${def.spell_suppression.toFixed(0)}%`,
      need: `${boss.spellSupp}%`,
      status: ssStatus,
    });
  }

  // Overall = worst check
  const statuses = checks.map((c) => c.status);
  const overall: Status = statuses.includes("fail") ? "fail" : statuses.includes("warn") ? "warn" : "pass";

  return { checks, overall };
}

const STATUS_ICON: Record<Status, string> = {
  pass: "\u2705",
  warn: "\u26A0\uFE0F",
  fail: "\u274C",
};

export default function BossReadiness(props: BossReadinessProps) {
  const [expanded, setExpanded] = createSignal(false);

  const categories = createMemo(() => {
    const r = props.dpsResult;
    if (!r || !r.defence) return [];

    const dps = r.combined_dps;
    const def = r.defence;

    const groups: { category: string; bosses: { boss: BossThresholds; checks: Check[]; overall: Status }[] }[] = [];
    const catMap = new Map<string, typeof groups[0]>();

    for (const boss of BOSSES) {
      const { checks, overall } = evaluateBoss(boss, dps, def);
      let group = catMap.get(boss.category);
      if (!group) {
        group = { category: boss.category, bosses: [] };
        catMap.set(boss.category, group);
        groups.push(group);
      }
      group.bosses.push({ boss, checks, overall });
    }

    return groups;
  });

  const summary = createMemo(() => {
    let pass = 0, warn = 0, fail = 0;
    for (const g of categories()) {
      for (const b of g.bosses) {
        if (b.overall === "pass") pass++;
        else if (b.overall === "warn") warn++;
        else fail++;
      }
    }
    return { pass, warn, fail };
  });

  return (
    <Show when={props.dpsResult?.defence && categories().length > 0}>
      <div class="boss-readiness">
        <button class="boss-readiness-toggle" onClick={() => setExpanded(!expanded())}>
          <span class="boss-readiness-title">Boss Readiness</span>
          <span class="boss-readiness-summary">
            <span class="boss-summary-pass">{summary().pass} ready</span>
            <span class="boss-summary-warn">{summary().warn} close</span>
            <span class="boss-summary-fail">{summary().fail} not ready</span>
          </span>
          <span class="boss-readiness-chevron">{expanded() ? "\u25B2" : "\u25BC"}</span>
        </button>
        <Show when={expanded()}>
        <For each={categories()}>
          {(group) => (
            <div class="boss-category">
              <div class="boss-category-label">{group.category}</div>
              <div class="boss-cards">
                <For each={group.bosses}>
                  {(entry) => (
                    <div class={`boss-card boss-${entry.overall}`}>
                      <div class="boss-card-header">
                        <span class="boss-card-icon">{STATUS_ICON[entry.overall]}</span>
                        <span class="boss-card-name">{entry.boss.name}</span>
                      </div>
                      <div class="boss-checks">
                        <For each={entry.checks}>
                          {(check) => (
                            <div class={`boss-check boss-check-${check.status}`}>
                              <span class="boss-check-label">{check.label}</span>
                              <span class="boss-check-value">{check.value}</span>
                              <span class="boss-check-need">/ {check.need}</span>
                            </div>
                          )}
                        </For>
                      </div>
                      <Show when={entry.boss.notes}>
                        <div class="boss-note">{entry.boss.notes}</div>
                      </Show>
                    </div>
                  )}
                </For>
              </div>
            </div>
          )}
        </For>
        </Show>
      </div>
    </Show>
  );
}
