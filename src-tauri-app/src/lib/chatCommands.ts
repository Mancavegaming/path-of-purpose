/**
 * Twitch chat command handlers.
 *
 * Each handler reads from the stream store and returns a response string.
 */
import {
  streamBuild,
  streamDpsResult,
  addChatLogEntry,
  addViewerSuggestion,
} from "./streamStore";

function formatDps(v: number): string {
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + "M";
  if (v >= 1_000) return (v / 1_000).toFixed(0) + "K";
  return Math.round(v).toString();
}

type CommandHandler = (user: string, args: string) => string | null;

const handlers: Record<string, CommandHandler> = {
  build: () => {
    const build = streamBuild();
    const dps = streamDpsResult();
    if (!build) return "No build loaded yet.";

    const parts: string[] = [];
    if (build.level) parts.push(`Lv${build.level}`);
    if (build.ascendancy_name) parts.push(build.ascendancy_name);
    if (dps?.skill_name) parts.push(dps.skill_name);
    if (dps) parts.push(`${formatDps(dps.combined_dps)} DPS`);

    return parts.length > 0 ? parts.join(" | ") : "Build loaded but no details available.";
  },

  dps: () => {
    const dps = streamDpsResult();
    if (!dps) return "DPS not calculated yet. Streamer needs to hit Calculate DPS.";

    let msg = `${dps.skill_name}: ${formatDps(dps.combined_dps)} DPS`;
    if (dps.total_dps > 0 && dps.total_dot_dps > 0) {
      msg += ` (Hit: ${formatDps(dps.total_dps)}, DoT: ${formatDps(dps.total_dot_dps)})`;
    }
    if (dps.impale_dps > 0) {
      msg += ` +${formatDps(dps.impale_dps)} Impale`;
    }
    return msg;
  },

  gear: (_user: string, args: string) => {
    const build = streamBuild();
    if (!build) return "No build loaded.";

    if (args) {
      // Look up specific slot
      const slotQuery = args.toLowerCase();
      const item = build.items.find(
        (i) => i.slot.toLowerCase().includes(slotQuery) || i.name.toLowerCase().includes(slotQuery),
      );
      if (item) {
        const mods = item.explicits.slice(0, 3).map((m) => m.text.replace(/\{[^}]*\}/g, "").trim());
        return `${item.slot}: ${item.name} — ${mods.join(", ")}`;
      }
      return `No item found for "${args}".`;
    }

    // Show all slots summary
    const slots = ["Weapon 1", "Body Armour", "Helmet", "Gloves", "Boots", "Amulet"];
    const parts = slots
      .map((s) => {
        const item = build.items.find((i) => i.slot === s);
        return item ? `${s}: ${item.name || item.base_type}` : null;
      })
      .filter(Boolean);
    return parts.join(" | ") || "No gear equipped.";
  },

  boss: () => {
    const dps = streamDpsResult();
    if (!dps || !dps.defence) return "Calculate DPS first to check boss readiness.";

    const def = dps.defence;
    const minRes = Math.min(
      def.elemental_resistances?.fire ?? 0,
      def.elemental_resistances?.cold ?? 0,
      def.elemental_resistances?.lightning ?? 0,
    );
    const bosses = [
      { name: "Shaper", dps: 2_000_000, life: 5500, res: 75 },
      { name: "Maven", dps: 3_000_000, life: 5500, res: 75 },
      { name: "Uber Elder", dps: 3_000_000, life: 6000, res: 75 },
      { name: "Feared", dps: 5_000_000, life: 6000, res: 75 },
    ];

    const ready: string[] = [];
    const close: string[] = [];
    const notReady: string[] = [];

    for (const b of bosses) {
      const dpsPasses = dps.combined_dps >= b.dps;
      const lifePasses = def.life >= b.life;
      const resPasses = minRes >= b.res;
      if (dpsPasses && lifePasses && resPasses) ready.push(b.name);
      else if ((dpsPasses || lifePasses) && resPasses) close.push(b.name);
      else notReady.push(b.name);
    }

    const parts: string[] = [];
    if (ready.length) parts.push(`Ready: ${ready.join(", ")}`);
    if (close.length) parts.push(`Close: ${close.join(", ")}`);
    if (notReady.length) parts.push(`Not ready: ${notReady.join(", ")}`);
    return parts.join(" | ") || "No boss data.";
  },

  tree: () => {
    const build = streamBuild();
    if (!build || !build.passive_specs.length) return "No passive tree data.";

    const spec = build.passive_specs[0];
    const points = spec.nodes?.length || 0;
    const version = spec.tree_version || "3.28";
    return `Passive tree: ${points} points allocated (PoE ${version})`;
  },

  skills: () => {
    const build = streamBuild();
    if (!build) return "No build loaded.";

    const groups = build.skill_groups;
    if (!groups.length) return "No skill groups found.";

    // Find main skill group
    const mainIdx = build.main_socket_group > 0 ? build.main_socket_group - 1 : 0;
    const main = groups[mainIdx];
    if (!main) return "No main skill group.";

    const activeGem = main.gems.find((g) => !g.is_support && g.is_enabled);
    const supports = main.gems
      .filter((g) => g.is_support && g.is_enabled)
      .map((g) => g.name)
      .slice(0, 5);

    const name = activeGem?.name || main.label || "Unknown";
    return `Main: ${name} + ${supports.join(", ")}`;
  },

  defences: () => {
    const dps = streamDpsResult();
    if (!dps || !dps.defence) return "Calculate DPS first to see defences.";

    const d = dps.defence;
    const res = d.elemental_resistances;
    const parts = [`Life: ${d.life}`];
    if (d.energy_shield > 0) parts.push(`ES: ${d.energy_shield}`);
    if (d.armour > 0) parts.push(`Armour: ${d.armour}`);
    if (d.evasion > 0) parts.push(`Evasion: ${d.evasion}`);
    if (res) {
      parts.push(
        `Res: ${res.fire ?? 0}/${res.cold ?? 0}/${res.lightning ?? 0}F/C/L, ${d.chaos_resistance ?? 0} chaos`,
      );
    }
    return parts.join(" | ");
  },

  suggest: (user: string, args: string) => {
    if (!args) return "Usage: !suggest <item name or advice>";
    addViewerSuggestion(user, args);
    return `Suggestion from ${user} queued for streamer!`;
  },

  whatif: (_user: string, args: string) => {
    if (!args) return "Usage: !whatif <gem name or change>";
    addViewerSuggestion(_user, `What if: ${args}`);
    return `What-if "${args}" queued for streamer review!`;
  },

  challenge: (_user: string, args: string) => {
    const dps = streamDpsResult();
    if (!dps || !dps.defence) return "Need DPS calculated first!";

    const bossName = args || "random";
    const bosses = [
      { name: "Shaper", dps: 2_000_000 },
      { name: "Maven", dps: 3_000_000 },
      { name: "Uber Elder", dps: 3_000_000 },
      { name: "Feared", dps: 5_000_000 },
      { name: "Uber Maven", dps: 10_000_000 },
    ];

    let boss: typeof bosses[0];
    if (bossName === "random") {
      boss = bosses[Math.floor(Math.random() * bosses.length)];
    } else {
      boss = bosses.find((b) => b.name.toLowerCase().includes(bossName.toLowerCase())) || bosses[0];
    }

    const ready = dps.combined_dps >= boss.dps;
    return ready
      ? `Challenge: ${boss.name}! Current DPS ${formatDps(dps.combined_dps)} vs needed ${formatDps(boss.dps)} — READY! Go for it!`
      : `Challenge: ${boss.name}! Need ${formatDps(boss.dps)} DPS but only have ${formatDps(dps.combined_dps)} — risky!`;
  },

  help: () => {
    return "Commands: !build !dps !gear !boss !tree !skills !defences !suggest !whatif !challenge";
  },
};

/** Enabled command set — all enabled by default. */
const enabledCommands = new Set(Object.keys(handlers));

export function isCommandEnabled(cmd: string): boolean {
  return enabledCommands.has(cmd);
}

export function toggleCommand(cmd: string, enabled: boolean): void {
  if (enabled) enabledCommands.add(cmd);
  else enabledCommands.delete(cmd);
}

export function getCommandNames(): string[] {
  return Object.keys(handlers);
}

/** Process a chat command. Returns the response to send, or null. */
export function handleCommand(user: string, command: string, args: string): string | null {
  const handler = handlers[command];
  if (!handler || !enabledCommands.has(command)) return null;

  const response = handler(user, args);
  if (response) {
    addChatLogEntry({
      timestamp: Date.now(),
      user,
      command: `!${command}${args ? " " + args : ""}`,
      response,
    });
  }
  return response;
}
