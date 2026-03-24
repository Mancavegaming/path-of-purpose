import { createSignal, Show, For } from "solid-js";
import type { StashTab, StashTabValuation, PricedItem } from "../lib/types";
import {
  stashListTabs,
  stashScanTab,
  stashCurrencyRates,
  fetchLeagues,
  poeCheckLogin,
  poeLogin,
} from "../lib/commands";

export default function StashPage() {
  const [loggedIn, setLoggedIn] = createSignal(false);
  const [leagues, setLeagues] = createSignal<string[]>([]);
  const [league, setLeague] = createSignal("Standard");
  const [tabs, setTabs] = createSignal<StashTab[]>([]);
  const [selectedTabId, setSelectedTabId] = createSignal("");
  const [valuations, setValuations] = createSignal<Record<string, StashTabValuation>>({});
  const [rates, setRates] = createSignal<Record<string, number>>({});
  const [divineRatio, setDivineRatio] = createSignal(180);
  const [loading, setLoading] = createSignal("");
  const [scanning, setScanning] = createSignal(false);
  const [scanProgress, setScanProgress] = createSignal({ current: 0, total: 0, tabName: "" });
  const [hideRemoveOnly, setHideRemoveOnly] = createSignal(true);
  const [error, setError] = createSignal("");

  // No polling intervals — all user-initiated. Nothing to clean up.

  async function checkLogin() {
    try {
      const result = await poeCheckLogin();
      setLoggedIn(result.logged_in === true);
    } catch {
      setLoggedIn(false);
    }
  }

  async function handleLogin() {
    setError("");
    setLoading("Waiting for PoE authorization...");
    try {
      const result = await poeLogin();
      // Python returns {"error": "..."} as valid JSON — check for it
      if (result.error) {
        setError(`Login failed: ${result.error}`);
      }
    } catch (e) {
      setError(`Login error: ${String(e)}`);
    }
    setLoading("");
    // Always re-check login status after attempting login
    await checkLogin();
    if (loggedIn()) {
      setError("");
      await loadLeagues();
    }
  }

  async function loadLeagues() {
    try {
      const result = await fetchLeagues();
      setLeagues(result);
      if (result.length > 0 && !result.includes(league())) {
        setLeague(result[0]);
      }
    } catch {
      setLeagues(["Standard", "Settlers of Kalguur"]);
    }
  }

  async function loadTabs() {
    setError("");
    setLoading("Loading stash tabs...");
    try {
      const result = await stashListTabs(league());
      // Flatten folder children into top-level list for simplicity
      const flatTabs: StashTab[] = [];
      for (const tab of result.tabs || []) {
        if (tab.type === "Folder" && tab.children?.length > 0) {
          for (const child of tab.children) {
            flatTabs.push({ ...child, name: `${tab.name}/${child.name}` });
          }
        } else {
          flatTabs.push(tab);
        }
      }
      setTabs(flatTabs);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading("");
    }
  }

  async function loadRates() {
    try {
      const result = await stashCurrencyRates(league());
      setRates(result.rates || {});
      setDivineRatio(result.divine_ratio || 180);
    } catch {
      // Use empty rates — currency items won't be priced
    }
  }

  async function handleLoadStash() {
    await loadRates();
    await loadTabs();
  }

  async function scanTab(tabId: string) {
    setError("");
    setScanning(true);
    const tab = tabs().find((t) => t.id === tabId);
    setScanProgress({ current: 0, total: 1, tabName: tab?.name || tabId });
    try {
      const result = await stashScanTab(league(), tabId, rates(), divineRatio());
      setValuations((prev) => ({ ...prev, [tabId]: result }));
      setSelectedTabId(tabId);
    } catch (e) {
      setError(String(e));
    } finally {
      setScanning(false);
      setScanProgress({ current: 0, total: 0, tabName: "" });
    }
  }

  async function scanAllTabs() {
    setError("");
    setScanning(true);
    const toScan = displayedTabs();
    setValuations({});

    for (let i = 0; i < toScan.length; i++) {
      const tab = toScan[i];
      setScanProgress({ current: i + 1, total: toScan.length, tabName: tab.name });
      try {
        const result = await stashScanTab(league(), tab.id, rates(), divineRatio());
        setValuations((prev) => ({ ...prev, [tab.id]: result }));
      } catch {
        // Skip failed tabs, continue scanning
      }
      // Rate limit pacing: 1.5s delay between tab scans
      if (i < toScan.length - 1) {
        await new Promise((r) => setTimeout(r, 1500));
      }
    }

    setScanning(false);
    setScanProgress({ current: 0, total: 0, tabName: "" });
  }

  // Computed totals across all scanned tabs
  function totalValue() {
    const vals = Object.values(valuations());
    const chaos = vals.reduce((sum, v) => sum + v.total_chaos, 0);
    const divine = divineRatio() > 0 ? chaos / divineRatio() : 0;
    return { chaos: Math.round(chaos * 100) / 100, divine: Math.round(divine * 100) / 100 };
  }

  function selectedValuation(): StashTabValuation | null {
    const id = selectedTabId();
    return id ? valuations()[id] || null : null;
  }

  function displayedTabs() {
    if (!hideRemoveOnly()) return tabs();
    return tabs().filter((t) => !t.name.includes("(Remove-only)"));
  }

  function removeOnlyCount() {
    return tabs().filter((t) => t.name.includes("(Remove-only)")).length;
  }

  // Format price display
  function formatPrice(chaos: number): string {
    if (chaos >= 1000) return `${(chaos / divineRatio()).toFixed(1)} div`;
    return `${chaos.toFixed(1)}c`;
  }

  // Init
  checkLogin().then(() => {
    if (loggedIn()) loadLeagues();
  });

  return (
    <div>
      <h1 class="page-title">Stash Value</h1>
      <p class="page-subtitle">Scan your stash tabs and see what your items are worth.</p>

      <Show when={error()}>
        <div class="card" style={{ "border-color": "var(--severity-critical)", background: "rgba(224, 80, 80, 0.08)" }}>
          <div style={{ color: "var(--severity-critical)", "font-size": "13px", "word-break": "break-word" }}>{error()}</div>
        </div>
      </Show>

      <Show when={!loggedIn()}>
        <div class="card">
          <p style={{ color: "var(--text-secondary)", "margin-bottom": "12px" }}>
            Log in with your PoE account to access your stash tabs.
          </p>
          <button onClick={handleLogin} disabled={!!loading()}>
            {loading() || "Login with PoE"}
          </button>
        </div>
      </Show>

      <Show when={loggedIn()}>
        {/* League selector + load button */}
        <div class="card" style={{ display: "flex", "align-items": "center", gap: "12px", "flex-wrap": "wrap" }}>
          <label style={{ "font-size": "12px", color: "var(--text-secondary)", "text-transform": "uppercase", "letter-spacing": "0.5px" }}>
            League
          </label>
          <select
            value={league()}
            onChange={(e) => setLeague(e.currentTarget.value)}
            style={{
              background: "var(--bg-input)",
              border: "1px solid var(--border)",
              "border-radius": "var(--radius)",
              color: "var(--text-primary)",
              padding: "6px 12px",
              "font-size": "13px",
            }}
          >
            <For each={leagues()}>{(l) => <option value={l}>{l}</option>}</For>
          </select>
          <button onClick={handleLoadStash} disabled={!!loading() || scanning()}>
            {loading() || "Load Stash Tabs"}
          </button>

          <Show when={tabs().length > 0}>
            <button onClick={scanAllTabs} disabled={scanning()} style={{ "margin-left": "auto" }}>
              {scanning()
                ? `Scanning ${scanProgress().current}/${scanProgress().total}: ${scanProgress().tabName}`
                : "Scan All Tabs"
              }
            </button>
          </Show>
        </div>

        {/* Total value banner */}
        <Show when={Object.keys(valuations()).length > 0}>
          <div class="card" style={{
            display: "flex",
            "align-items": "center",
            gap: "24px",
            background: "linear-gradient(135deg, rgba(200, 162, 82, 0.08) 0%, var(--bg-card) 60%)",
            "border-color": "rgba(200, 162, 82, 0.2)",
          }}>
            <div>
              <div style={{ "font-size": "11px", color: "var(--text-muted)", "text-transform": "uppercase", "letter-spacing": "0.5px" }}>Total Value</div>
              <div style={{ "font-size": "28px", "font-weight": "700", color: "var(--accent)" }}>
                {totalValue().divine.toFixed(1)} <span style={{ "font-size": "16px", color: "var(--text-secondary)" }}>divine</span>
              </div>
            </div>
            <div style={{ color: "var(--text-muted)", "font-size": "14px" }}>
              {totalValue().chaos.toLocaleString()}c
            </div>
            <div style={{ "margin-left": "auto", "font-size": "12px", color: "var(--text-muted)" }}>
              {Object.keys(valuations()).length} tabs scanned
            </div>
          </div>
        </Show>


        {/* Two-column layout: tab list + item detail */}
        <Show when={tabs().length > 0}>
          <div style={{ display: "flex", gap: "16px" }}>
            {/* Left: Tab list */}
            <div style={{ width: "280px", "flex-shrink": "0" }}>
              <div class="section-title" style={{ display: "flex", "justify-content": "space-between", "align-items": "center" }}>
                <span>Stash Tabs</span>
                <span style={{ "font-size": "11px", color: "var(--text-muted)", "font-weight": "400", "text-transform": "none", "letter-spacing": "0" }}>
                  {displayedTabs().length} tabs
                </span>
              </div>
              <Show when={removeOnlyCount() > 0}>
                <label style={{
                  display: "flex",
                  "align-items": "center",
                  gap: "6px",
                  "font-size": "11px",
                  color: "var(--text-muted)",
                  padding: "4px 0 8px",
                  cursor: "pointer",
                }}>
                  <input
                    type="checkbox"
                    checked={hideRemoveOnly()}
                    onChange={(e) => setHideRemoveOnly(e.currentTarget.checked)}
                  />
                  Hide Remove-only tabs ({removeOnlyCount()})
                </label>
              </Show>
              <div style={{ display: "flex", "flex-direction": "column", gap: "4px" }}>
                <For each={displayedTabs()}>
                  {(tab) => {
                    const val = () => valuations()[tab.id];
                    const isSelected = () => selectedTabId() === tab.id;
                    const tabColor = () =>
                      tab.colour?.r != null
                        ? `rgb(${tab.colour.r}, ${tab.colour.g}, ${tab.colour.b})`
                        : "var(--text-muted)";
                    return (
                      <div
                        onClick={() => val() ? setSelectedTabId(tab.id) : scanTab(tab.id)}
                        style={{
                          display: "flex",
                          "align-items": "center",
                          gap: "8px",
                          padding: "8px 12px",
                          "border-radius": "var(--radius)",
                          cursor: "pointer",
                          background: isSelected() ? "var(--accent-bg)" : "transparent",
                          border: isSelected() ? "1px solid rgba(200, 162, 82, 0.2)" : "1px solid transparent",
                          transition: "background 0.15s",
                        }}
                      >
                        <div style={{
                          width: "8px",
                          height: "8px",
                          "border-radius": "50%",
                          background: tabColor(),
                          "flex-shrink": "0",
                        }} />
                        <div style={{ flex: "1", "min-width": "0" }}>
                          <div style={{
                            "font-size": "13px",
                            color: isSelected() ? "var(--accent)" : "var(--text-primary)",
                            overflow: "hidden",
                            "text-overflow": "ellipsis",
                            "white-space": "nowrap",
                          }}>
                            {tab.name || "Unnamed"}
                          </div>
                          <div style={{ "font-size": "11px", color: "var(--text-muted)" }}>
                            {tab.type.replace("Stash", "")}
                          </div>
                        </div>
                        <Show when={val()}>
                          <div style={{
                            "font-size": "12px",
                            "font-weight": "600",
                            color: val()!.total_chaos > 0 ? "var(--accent)" : "var(--text-muted)",
                            "white-space": "nowrap",
                          }}>
                            {formatPrice(val()!.total_chaos)}
                          </div>
                        </Show>
                      </div>
                    );
                  }}
                </For>
              </div>
            </div>

            {/* Right: Selected tab items */}
            <div style={{ flex: "1", "min-width": "0" }}>
              <Show when={selectedValuation()} fallback={
                <div class="card" style={{ "text-align": "center", color: "var(--text-muted)", padding: "40px" }}>
                  Click a tab to scan and view its contents
                </div>
              }>
                {(val) => (
                  <>
                    <div class="section-title" style={{ display: "flex", "justify-content": "space-between" }}>
                      <span>{val().tab_name}</span>
                      <span style={{ "font-size": "12px", "text-transform": "none", "letter-spacing": "0", color: "var(--text-muted)" }}>
                        {val().priced_count}/{val().item_count} priced — {formatPrice(val().total_chaos)}
                      </span>
                    </div>
                    <div style={{ display: "flex", "flex-direction": "column", gap: "2px" }}>
                      <For each={val().items}>
                        {(item: PricedItem) => (
                          <div style={{
                            display: "flex",
                            "align-items": "center",
                            gap: "10px",
                            padding: "6px 10px",
                            "border-radius": "var(--radius)",
                            background: item.total_price_chaos > 0 ? "rgba(200, 162, 82, 0.03)" : "transparent",
                          }}>
                            <Show when={item.icon}>
                              <img
                                src={item.icon}
                                alt=""
                                style={{ width: "28px", height: "28px", "object-fit": "contain", "flex-shrink": "0" }}
                                loading="lazy"
                              />
                            </Show>
                            <div style={{ flex: "1", "min-width": "0" }}>
                              <div style={{
                                "font-size": "13px",
                                color: item.rarity === "Unique" ? "var(--rarity-unique)"
                                  : item.rarity === "Rare" ? "var(--rarity-rare)"
                                  : item.rarity === "Magic" ? "var(--rarity-magic)"
                                  : item.rarity === "Currency" ? "var(--accent)"
                                  : "var(--text-primary)",
                                overflow: "hidden",
                                "text-overflow": "ellipsis",
                                "white-space": "nowrap",
                              }}>
                                {item.name}
                              </div>
                            </div>
                            <Show when={item.stack_size > 1}>
                              <div style={{ "font-size": "11px", color: "var(--text-muted)" }}>
                                x{item.stack_size}
                              </div>
                            </Show>
                            <div style={{
                              "font-size": "13px",
                              "font-weight": "600",
                              color: item.total_price_chaos > 0 ? "var(--accent)" : "var(--text-muted)",
                              "white-space": "nowrap",
                              "min-width": "60px",
                              "text-align": "right",
                            }}>
                              {item.total_price_chaos > 0 ? formatPrice(item.total_price_chaos) : "—"}
                            </div>
                          </div>
                        )}
                      </For>
                    </div>
                  </>
                )}
              </Show>
            </div>
          </div>
        </Show>
      </Show>
    </div>
  );
}
