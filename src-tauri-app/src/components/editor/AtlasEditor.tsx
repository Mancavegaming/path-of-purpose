// Atlas & Notes editor for build brackets

interface AtlasEditorProps {
  notes: string;
  atlasStrategy: string;
  mapWarnings: string[];
  onNotesChange: (v: string) => void;
  onAtlasChange: (v: string) => void;
  onMapWarningsChange: (v: string[]) => void;
}

export default function AtlasEditor(props: AtlasEditorProps) {
  function handleWarningsChange(value: string) {
    const warnings = value.split(",").map((s) => s.trim()).filter(Boolean);
    props.onMapWarningsChange(warnings);
  }

  return (
    <div class="editor-atlas">
      <label class="editor-field">
        <span class="editor-label">Bracket Notes</span>
        <textarea
          class="editor-textarea"
          value={props.notes}
          rows={3}
          placeholder="General notes for this bracket..."
          onInput={(e) => props.onNotesChange(e.currentTarget.value)}
        />
      </label>

      <label class="editor-field">
        <span class="editor-label">Atlas Strategy</span>
        <textarea
          class="editor-textarea"
          value={props.atlasStrategy}
          rows={3}
          placeholder="Focus on map sustain, run adjacent maps, prioritize..."
          onInput={(e) => props.onAtlasChange(e.currentTarget.value)}
        />
      </label>

      <label class="editor-field">
        <span class="editor-label">Map Warnings (comma-separated mods to avoid)</span>
        <input
          type="text"
          class="editor-input"
          value={props.mapWarnings.join(", ")}
          placeholder="No Leech, Reflect Physical, -max res"
          onInput={(e) => handleWarningsChange(e.currentTarget.value)}
        />
      </label>
    </div>
  );
}
