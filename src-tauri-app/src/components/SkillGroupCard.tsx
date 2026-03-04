import { For } from "solid-js";
import type { SkillGroup } from "../lib/types";

interface SkillGroupCardProps {
  group: SkillGroup;
  isMain: boolean;
}

export default function SkillGroupCard(props: SkillGroupCardProps) {
  const group = () => props.group;

  const activeGem = () =>
    group().gems.find((g) => !g.is_support && g.is_enabled);

  const title = () => {
    const active = activeGem();
    if (active) return active.name;
    if (group().label) return group().label;
    return "Unnamed Group";
  };

  return (
    <div class="card">
      <div class="card-header">
        <h4 class="card-title">
          {title()}
          {props.isMain ? " (Main)" : ""}
        </h4>
        {group().slot && (
          <span class="build-meta">{group().slot}</span>
        )}
      </div>

      <ul class="gem-list">
        <For each={group().gems}>
          {(gem) => {
            const cls = !gem.is_enabled
              ? "gem-disabled"
              : gem.is_support
                ? "gem-support"
                : "gem-active";
            return (
              <li>
                <span class={cls}>{gem.name}</span>
                <span class="gem-level">
                  Lv{gem.level}
                  {gem.quality > 0 ? ` / ${gem.quality}%` : ""}
                </span>
              </li>
            );
          }}
        </For>
      </ul>
    </div>
  );
}
