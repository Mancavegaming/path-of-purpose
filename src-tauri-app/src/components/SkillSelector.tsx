import { For } from "solid-js";
import type { SkillGroup } from "../lib/types";

interface SkillSelectorProps {
  skills: SkillGroup[];
  selectedIndex: number;
  onSelect: (index: number) => void;
}

/** Dropdown to pick which skill group to calculate DPS for. */
export default function SkillSelector(props: SkillSelectorProps) {
  const skillLabel = (group: SkillGroup, i: number) => {
    const active = group.gems.find((g) => !g.is_support && g.is_enabled);
    const name = active?.name || group.label || `Skill ${i + 1}`;
    return `${i + 1}. ${name}`;
  };

  return (
    <select
      class="skill-selector"
      value={props.selectedIndex}
      onChange={(e) => props.onSelect(parseInt(e.currentTarget.value))}
    >
      <For each={props.skills}>
        {(group, i) => (
          <option value={i()}>{skillLabel(group, i())}</option>
        )}
      </For>
    </select>
  );
}
