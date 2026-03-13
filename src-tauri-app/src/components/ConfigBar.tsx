import { createSignal, Show } from "solid-js";

export interface CalcConfigState {
  enemy_is_boss: boolean;
  enemy_level: number;
  use_power_charges: boolean;
  power_charges: number;
  use_frenzy_charges: boolean;
  frenzy_charges: number;
  use_endurance_charges: boolean;
  endurance_charges: number;
  use_flasks: boolean;
  use_curses: boolean;
  enemy_is_shocked: boolean;
  shock_value: number;
  enemy_is_chilled: boolean;
  enemy_is_intimidated: boolean;
  wither_stacks: number;
  onslaught: boolean;
}

export const DEFAULT_CONFIG: CalcConfigState = {
  enemy_is_boss: false,
  enemy_level: 84,
  use_power_charges: false,
  power_charges: 3,
  use_frenzy_charges: false,
  frenzy_charges: 3,
  use_endurance_charges: false,
  endurance_charges: 3,
  use_flasks: false,
  use_curses: true,
  enemy_is_shocked: false,
  shock_value: 15,
  enemy_is_chilled: false,
  enemy_is_intimidated: false,
  wither_stacks: 0,
  onslaught: false,
};

/** Boss presets that set enemy level and resistances */
export const BOSS_PRESETS = {
  normal: { label: "Normal", enemy_is_boss: false, enemy_level: 84 },
  map_boss: { label: "Map Boss", enemy_is_boss: true, enemy_level: 84 },
  pinnacle: { label: "Pinnacle Boss", enemy_is_boss: true, enemy_level: 85 },
} as const;

interface ConfigBarProps {
  config: CalcConfigState;
  onChange: (config: CalcConfigState) => void;
}

export default function ConfigBar(props: ConfigBarProps) {
  const [expanded, setExpanded] = createSignal(false);

  function update(partial: Partial<CalcConfigState>) {
    props.onChange({ ...props.config, ...partial });
  }

  function summaryText(): string {
    const c = props.config;
    const parts: string[] = [];
    if (c.enemy_is_boss) {
      parts.push(c.enemy_level >= 85 ? "Pinnacle" : "Map Boss");
    } else {
      parts.push("Normal");
    }
    if (c.use_power_charges) parts.push(`${c.power_charges}P`);
    if (c.use_frenzy_charges) parts.push(`${c.frenzy_charges}F`);
    if (c.use_endurance_charges) parts.push(`${c.endurance_charges}E`);
    if (c.use_flasks) parts.push("Flasks");
    if (c.onslaught) parts.push("Onslaught");
    if (c.enemy_is_shocked) parts.push(`Shock ${c.shock_value}%`);
    if (c.enemy_is_chilled) parts.push("Chill");
    if (c.enemy_is_intimidated) parts.push("Intim.");
    if (c.wither_stacks > 0) parts.push(`Wither×${c.wither_stacks}`);
    if (!c.use_curses) parts.push("No Curses");
    return parts.join(" · ");
  }

  return (
    <div class="config-bar">
      <button class="config-bar-toggle" onClick={() => setExpanded(!expanded())}>
        <span class="config-bar-icon">&#9881;</span>
        <span class="config-bar-summary">{summaryText()}</span>
        <span class="config-bar-chevron">{expanded() ? "▲" : "▼"}</span>
      </button>

      <Show when={expanded()}>
        <div class="config-bar-panel">
          {/* Enemy Type */}
          <div class="config-section">
            <div class="config-section-label">Enemy</div>
            <div class="config-btn-group">
              {Object.entries(BOSS_PRESETS).map(([_key, preset]) => (
                <button
                  class={`config-btn ${
                    props.config.enemy_is_boss === preset.enemy_is_boss &&
                    props.config.enemy_level === preset.enemy_level
                      ? "config-btn-active"
                      : ""
                  }`}
                  onClick={() =>
                    update({
                      enemy_is_boss: preset.enemy_is_boss,
                      enemy_level: preset.enemy_level,
                    })
                  }
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Charges */}
          <div class="config-section">
            <div class="config-section-label">Charges</div>
            <div class="config-toggles">
              <label class="config-toggle">
                <input
                  type="checkbox"
                  checked={props.config.use_power_charges}
                  onChange={(e) => update({ use_power_charges: e.currentTarget.checked })}
                />
                Power
                <Show when={props.config.use_power_charges}>
                  <input
                    type="number"
                    class="config-num"
                    min={0}
                    max={10}
                    value={props.config.power_charges}
                    onChange={(e) => update({ power_charges: parseInt(e.currentTarget.value) || 0 })}
                  />
                </Show>
              </label>
              <label class="config-toggle">
                <input
                  type="checkbox"
                  checked={props.config.use_frenzy_charges}
                  onChange={(e) => update({ use_frenzy_charges: e.currentTarget.checked })}
                />
                Frenzy
                <Show when={props.config.use_frenzy_charges}>
                  <input
                    type="number"
                    class="config-num"
                    min={0}
                    max={10}
                    value={props.config.frenzy_charges}
                    onChange={(e) => update({ frenzy_charges: parseInt(e.currentTarget.value) || 0 })}
                  />
                </Show>
              </label>
              <label class="config-toggle">
                <input
                  type="checkbox"
                  checked={props.config.use_endurance_charges}
                  onChange={(e) => update({ use_endurance_charges: e.currentTarget.checked })}
                />
                Endurance
                <Show when={props.config.use_endurance_charges}>
                  <input
                    type="number"
                    class="config-num"
                    min={0}
                    max={10}
                    value={props.config.endurance_charges}
                    onChange={(e) => update({ endurance_charges: parseInt(e.currentTarget.value) || 0 })}
                  />
                </Show>
              </label>
            </div>
          </div>

          {/* Buffs */}
          <div class="config-section">
            <div class="config-section-label">Buffs</div>
            <div class="config-toggles">
              <label class="config-toggle">
                <input
                  type="checkbox"
                  checked={props.config.use_flasks}
                  onChange={(e) => update({ use_flasks: e.currentTarget.checked })}
                />
                Flasks Active
              </label>
              <label class="config-toggle">
                <input
                  type="checkbox"
                  checked={props.config.onslaught}
                  onChange={(e) => update({ onslaught: e.currentTarget.checked })}
                />
                Onslaught
              </label>
              <label class="config-toggle">
                <input
                  type="checkbox"
                  checked={props.config.use_curses}
                  onChange={(e) => update({ use_curses: e.currentTarget.checked })}
                />
                Curses
              </label>
            </div>
          </div>

          {/* Enemy Conditions */}
          <div class="config-section">
            <div class="config-section-label">Enemy Conditions</div>
            <div class="config-toggles">
              <label class="config-toggle">
                <input
                  type="checkbox"
                  checked={props.config.enemy_is_shocked}
                  onChange={(e) => update({ enemy_is_shocked: e.currentTarget.checked })}
                />
                Shocked
                <Show when={props.config.enemy_is_shocked}>
                  <input
                    type="number"
                    class="config-num"
                    min={0}
                    max={50}
                    value={props.config.shock_value}
                    onChange={(e) => update({ shock_value: parseInt(e.currentTarget.value) || 0 })}
                  />
                  <span class="config-unit">%</span>
                </Show>
              </label>
              <label class="config-toggle">
                <input
                  type="checkbox"
                  checked={props.config.enemy_is_chilled}
                  onChange={(e) => update({ enemy_is_chilled: e.currentTarget.checked })}
                />
                Chilled
              </label>
              <label class="config-toggle">
                <input
                  type="checkbox"
                  checked={props.config.enemy_is_intimidated}
                  onChange={(e) => update({ enemy_is_intimidated: e.currentTarget.checked })}
                />
                Intimidated
              </label>
              <label class="config-toggle">
                Wither
                <input
                  type="number"
                  class="config-num"
                  min={0}
                  max={15}
                  value={props.config.wither_stacks}
                  onChange={(e) => update({ wither_stacks: parseInt(e.currentTarget.value) || 0 })}
                />
              </label>
            </div>
          </div>
        </div>
      </Show>
    </div>
  );
}
