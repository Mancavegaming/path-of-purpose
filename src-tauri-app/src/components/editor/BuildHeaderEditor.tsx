import { createMemo, For } from "solid-js";

const POE_CLASSES: Record<string, string[]> = {
  Marauder: ["Juggernaut", "Berserker", "Chieftain"],
  Ranger: ["Raider", "Deadeye", "Pathfinder"],
  Witch: ["Necromancer", "Elementalist", "Occultist"],
  Duelist: ["Slayer", "Gladiator", "Champion"],
  Templar: ["Inquisitor", "Hierophant", "Guardian"],
  Shadow: ["Assassin", "Trickster", "Saboteur"],
  Scion: ["Ascendant"],
};

interface BuildHeaderEditorProps {
  buildName: string;
  className: string;
  ascendancyName: string;
  level: number;
  onBuildNameChange: (v: string) => void;
  onClassChange: (v: string) => void;
  onAscendancyChange: (v: string) => void;
  onLevelChange: (v: number) => void;
}

export default function BuildHeaderEditor(props: BuildHeaderEditorProps) {
  const ascendancies = createMemo(() => POE_CLASSES[props.className] ?? []);

  function handleClassChange(cls: string) {
    props.onClassChange(cls);
    // Auto-clear ascendancy when class changes
    const available = POE_CLASSES[cls] ?? [];
    if (!available.includes(props.ascendancyName)) {
      props.onAscendancyChange(available[0] ?? "");
    }
  }

  return (
    <div class="editor-header">
      <div class="editor-header-row">
        <label class="editor-field">
          <span class="editor-label">Build Name</span>
          <input
            type="text"
            class="editor-input"
            value={props.buildName}
            onInput={(e) => props.onBuildNameChange(e.currentTarget.value)}
            placeholder="My Build"
          />
        </label>
        <label class="editor-field editor-field-sm">
          <span class="editor-label">Level</span>
          <input
            type="number"
            class="editor-input"
            value={props.level}
            min={1}
            max={100}
            onInput={(e) => props.onLevelChange(parseInt(e.currentTarget.value) || 1)}
          />
        </label>
      </div>
      <div class="editor-header-row">
        <label class="editor-field">
          <span class="editor-label">Class</span>
          <select
            class="editor-select"
            value={props.className}
            onChange={(e) => handleClassChange(e.currentTarget.value)}
          >
            <For each={Object.keys(POE_CLASSES)}>
              {(cls) => <option value={cls}>{cls}</option>}
            </For>
          </select>
        </label>
        <label class="editor-field">
          <span class="editor-label">Ascendancy</span>
          <select
            class="editor-select"
            value={props.ascendancyName}
            onChange={(e) => props.onAscendancyChange(e.currentTarget.value)}
          >
            <option value="">None</option>
            <For each={ascendancies()}>
              {(asc) => <option value={asc}>{asc}</option>}
            </For>
          </select>
        </label>
      </div>
    </div>
  );
}
