import { For } from "solid-js";
import type { SkillGroup } from "../../lib/types";
import SkillGroupEditor from "./SkillGroupEditor";

interface SkillsEditorProps {
  skillGroups: SkillGroup[];
  mainSocketGroup: number; // 1-based
  onUpdate: (groups: SkillGroup[]) => void;
  onSetMain: (index: number) => void; // 0-based
}

export default function SkillsEditor(props: SkillsEditorProps) {
  function updateGroup(idx: number, group: SkillGroup) {
    const groups = [...props.skillGroups];
    groups[idx] = group;
    props.onUpdate(groups);
  }

  function removeGroup(idx: number) {
    const groups = props.skillGroups.filter((_, i) => i !== idx);
    props.onUpdate(groups);
  }

  function addGroup() {
    const groups = [
      ...props.skillGroups,
      {
        slot: "Body Armour",
        label: "",
        is_enabled: true,
        gems: [
          { name: "", gem_id: "", level: 20, quality: 0, is_support: false, is_enabled: true },
        ],
      },
    ];
    props.onUpdate(groups);
  }

  return (
    <div class="editor-skills">
      <For each={props.skillGroups}>
        {(group, i) => (
          <SkillGroupEditor
            group={group}
            index={i()}
            isMain={i() === props.mainSocketGroup - 1}
            onUpdate={(g) => updateGroup(i(), g)}
            onRemove={() => removeGroup(i())}
            onSetMain={() => props.onSetMain(i())}
          />
        )}
      </For>
      <button class="editor-btn editor-btn-add" onClick={addGroup}>
        + Add Skill Group
      </button>
    </div>
  );
}
