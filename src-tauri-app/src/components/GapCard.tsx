import type { DeltaGap } from "../lib/types";

interface GapCardProps {
  gap: DeltaGap;
}

export default function GapCard(props: GapCardProps) {
  const gap = () => props.gap;

  return (
    <div class={`card gap-card gap-${gap().severity}`}>
      <div class="card-header" style={{ "align-items": "flex-start" }}>
        <div style={{ display: "flex", "align-items": "flex-start" }}>
          <span class="gap-rank">#{gap().rank}</span>
          <div class="gap-body">
            <div style={{ display: "flex", "align-items": "center", gap: "8px" }}>
              <h4 class="card-title">{gap().title}</h4>
              <span class={`severity-badge severity-${gap().severity}`}>
                {gap().severity}
              </span>
            </div>
            <span class="gap-category">{gap().category}</span>
            <p class="gap-detail">{gap().detail}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
