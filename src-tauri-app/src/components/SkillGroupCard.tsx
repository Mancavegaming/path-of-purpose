import { createSignal, For } from "solid-js";
import type { SkillGroup } from "../lib/types";
import { getGemColor, gemIconUrl, type GemColor } from "../lib/gemColors";

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
    <div class={`skill-card ${props.isMain ? "skill-card-main" : ""}`}>
      <div class="skill-card-header">
        <span class="skill-card-title">{title()}</span>
        {group().slot && (
          <span class="skill-card-slot">{group().slot}</span>
        )}
        {props.isMain && <span class="skill-card-main-badge">Main</span>}
      </div>

      <div class="gem-grid">
        <For each={group().gems}>
          {(gem) => <GemRow gem={gem} />}
        </For>
      </div>
    </div>
  );
}

function GemRow(props: { gem: SkillGroupCardProps["group"]["gems"][0] }) {
  const gem = () => props.gem;
  const [imgFailed, setImgFailed] = createSignal(false);

  const color = (): GemColor => {
    if (!gem().is_enabled) return "white";
    return getGemColor(gem().name);
  };

  const colorClass = () => {
    if (!gem().is_enabled) return "gem-color-disabled";
    return `gem-color-${color()}`;
  };

  return (
    <div class={`gem-row ${!gem().is_enabled ? "gem-row-disabled" : ""}`}>
      <div class={`gem-icon-wrapper ${colorClass()}`}>
        {!imgFailed() ? (
          <img
            src={gem().icon_url || gemIconUrl(gem().name, gem().is_support)}
            alt={gem().name}
            class="gem-icon-img"
            loading="lazy"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div class={`gem-icon-fallback ${colorClass()}`}>
            {gem().is_support ? "S" : gem().name.charAt(0)}
          </div>
        )}
      </div>
      <div class="gem-info">
        <span class={`gem-name ${colorClass()}-text`}>
          {gem().name}
        </span>
        <span class="gem-meta">
          Lv {gem().level}
          {gem().quality > 0 ? ` / ${gem().quality}%` : ""}
        </span>
      </div>
    </div>
  );
}
