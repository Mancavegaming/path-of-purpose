import { For } from "solid-js";

interface VariantTabsProps {
  titles: string[];
  active: number;
  onSelect: (idx: number) => void;
}

export default function VariantTabs(props: VariantTabsProps) {
  return (
    <div class="variant-tabs">
      <For each={props.titles}>
        {(title, i) => (
          <button
            class={`variant-tab ${i() === props.active ? "variant-tab-active" : ""}`}
            onClick={() => props.onSelect(i())}
          >
            {title}
          </button>
        )}
      </For>
    </div>
  );
}
