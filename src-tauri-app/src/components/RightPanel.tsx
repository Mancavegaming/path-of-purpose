import { createSignal, Show } from "solid-js";
import type { Build, CalcResult, Item, TradeListing } from "../lib/types";
import TradePanel from "./TradePanel";
import ItemComparisonPanel from "./ItemComparisonPanel";
import AiAdvisorPanel from "./AiAdvisorPanel";

interface RightPanelProps {
  selectedItem: Item | null;
  league: string;
  build: Build | null;
  dpsResult?: CalcResult | null;
}

export default function RightPanel(props: RightPanelProps) {
  const [selectedListing, setSelectedListing] = createSignal<TradeListing | null>(null);

  return (
    <div class="right-panel">
      <div class="right-panel-header">
        <span class="right-panel-title">Trade & Advisor</span>
      </div>

      {/* Top section: Trade results + item comparison */}
      <div class="right-panel-top">
        <TradePanel
          selectedItem={props.selectedItem}
          league={props.league}
          build={props.build}
          onListingSelect={setSelectedListing}
        />

        <Show when={props.selectedItem && selectedListing()}>
          <ItemComparisonPanel
            equippedItem={props.selectedItem!}
            tradeListing={selectedListing()!}
            build={props.build}
          />
        </Show>
      </div>

      {/* Bottom section: AI Advisor chat */}
      <div class="right-panel-bottom">
        <AiAdvisorPanel
          build={props.build}
          selectedItem={props.selectedItem}
          selectedListing={selectedListing()}
          dpsResult={props.dpsResult}
        />
      </div>
    </div>
  );
}
