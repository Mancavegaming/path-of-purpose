import { createSignal, For } from "solid-js";
import type { SkillGroup } from "../lib/types";

interface SkillGroupCardProps {
  group: SkillGroup;
  isMain: boolean;
}

/** Build a poewiki gem icon URL from the gem name. */
function gemIconUrl(name: string): string {
  const slug = name.replace(/ /g, "_");
  return `https://www.poewiki.net/wiki/Special:FilePath/${slug}_inventory_icon.png`;
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

  const colorClass = () => {
    if (!gem().is_enabled) return "gem-icon-disabled";
    if (gem().is_support) return "gem-icon-support";
    return "gem-icon-active";
  };

  return (
    <div class={`gem-row ${!gem().is_enabled ? "gem-row-disabled" : ""}`}>
      <div class={`gem-icon-wrapper ${colorClass()}`}>
        {!imgFailed() ? (
          <img
            src={gem().icon_url || gemIconUrl(gem().name)}
            alt={gem().name}
            class="gem-icon-img"
            loading="lazy"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div class={`gem-icon-fallback ${colorClass()}`}>
            {gem().is_support ? "S" : "A"}
          </div>
        )}
      </div>
      <div class="gem-info">
        <span class={`gem-name ${gem().is_support ? "gem-name-support" : "gem-name-active"}`}>
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
