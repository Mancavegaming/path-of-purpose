import type { Accessor, Setter } from "solid-js";

export type Page = "decode" | "delta" | "guide";

interface SidebarProps {
  page: Accessor<Page>;
  setPage: Setter<Page>;
}

export default function Sidebar(props: SidebarProps) {
  return (
    <aside class="sidebar">
      <div class="sidebar-brand">
        <h1>Path of Purpose</h1>
        <p>Build mentor for exiles</p>
      </div>
      <nav class="sidebar-nav">
        <button
          class={`nav-item ${props.page() === "decode" ? "active" : ""}`}
          onClick={() => props.setPage("decode")}
        >
          <span class="nav-icon">{"\u{1F4DC}"}</span>
          Decode Build
        </button>
        <button
          class={`nav-item ${props.page() === "guide" ? "active" : ""}`}
          onClick={() => props.setPage("guide")}
        >
          <span class="nav-icon">{"\u{1F4D6}"}</span>
          Build Guide
        </button>
        <button
          class={`nav-item ${props.page() === "delta" ? "active" : ""}`}
          onClick={() => props.setPage("delta")}
        >
          <span class="nav-icon">{"\u{1F50D}"}</span>
          Delta Report
        </button>
      </nav>
    </aside>
  );
}
