import { createSignal, createEffect, For, Show, onMount } from "solid-js";
import type {
  Build,
  BuildGuide,
  BuildPreferences,
  ChatMessage,
} from "../lib/types";
import {
  generatorChatRemote,
  generateBuildRemote,
  refineBuildRemote,
  tradeSearch,
  refreshKnowledge,
  checkKnowledge,
  saveBuildGuide,
} from "../lib/commands";
import { guideToBuild } from "../lib/buildUtils";
import {
  token,
  isLoggedIn,
  isSubscribed,
  discordLogin,
  openCheckout,
  refreshUserStatus,
} from "../lib/auth";

const DISCORD_CLIENT_ID = "1479135178650554510";

type Phase = "auth" | "intake" | "generating" | "price_check" | "complete";

interface GeneratorPageProps {
  onComplete: (build: Build) => void;
  onSave?: () => void;
}

export default function GeneratorPage(props: GeneratorPageProps) {
  const [phase, setPhase] = createSignal<Phase>(
    isLoggedIn() && isSubscribed() ? "intake" : "auth",
  );
  const [messages, setMessages] = createSignal<ChatMessage[]>([]);
  const [input, setInput] = createSignal("");
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");
  const [guide, setGuide] = createSignal<BuildGuide | null>(null);
  const [priceProgress, setPriceProgress] = createSignal("");
  const [preferences, setPreferences] = createSignal<BuildPreferences | null>(
    null,
  );
  const [knowledgeVersion, setKnowledgeVersion] = createSignal("");
  const [knowledgeLoading, setKnowledgeLoading] = createSignal(false);
  const [saveName, setSaveName] = createSignal("");
  const [showSaveInput, setShowSaveInput] = createSignal(false);
  const [saveStatus, setSaveStatus] = createSignal("");
  const [loginLoading, setLoginLoading] = createSignal(false);

  // React to subscription status changes (e.g., after Stripe payment)
  createEffect(() => {
    if (isLoggedIn() && isSubscribed() && phase() === "auth") {
      setPhase("intake");
    }
  });

  onMount(async () => {
    // Update phase based on auth state
    if (isLoggedIn() && isSubscribed()) {
      setPhase("intake");
    } else {
      setPhase("auth");
    }

    // Auto-check game data
    try {
      const kb = await checkKnowledge();
      if (kb.version) {
        setKnowledgeVersion(kb.version);
      }
    } catch {
      // Non-critical
    }
  });

  async function handleRefreshKnowledge() {
    setKnowledgeLoading(true);
    setError("");
    try {
      const result = await refreshKnowledge();
      setKnowledgeVersion(result.version);
    } catch (e) {
      setError(`Failed to update game data: ${String(e)}`);
    } finally {
      setKnowledgeLoading(false);
    }
  }

  async function handleLogin() {
    setLoginLoading(true);
    setError("");
    try {
      const ok = await discordLogin(DISCORD_CLIENT_ID);
      if (ok) {
        if (isSubscribed()) {
          setPhase("intake");
        }
      } else {
        setError("Login failed. Please try again.");
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoginLoading(false);
    }
  }

  async function handleSubscribe() {
    setError("");
    try {
      await openCheckout();
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleRefreshStatus() {
    try {
      await refreshUserStatus();
      if (isSubscribed()) {
        setPhase("intake");
      }
    } catch (e) {
      setError(String(e));
    }
  }

  function getToken(): string {
    return token() || "";
  }

  function parseIntakeComplete(text: string): BuildPreferences | null {
    const match = text.match(/```json\s*\n?(.*?)```/s);
    if (!match) return null;
    try {
      const data = JSON.parse(match[1].trim());
      if (data.intake_complete && data.preferences) {
        return data.preferences as BuildPreferences;
      }
    } catch {
      // Not valid JSON
    }
    return null;
  }

  function stripJsonBlock(text: string): string {
    return text.replace(/```json\s*\n?.*?```/s, "").trim();
  }

  async function handleSend() {
    const msg = input().trim();
    if (!msg || loading()) return;

    const t = getToken();
    if (!t) {
      setError("Please log in first.");
      return;
    }

    setInput("");
    const userMsg: ChatMessage = { role: "user", content: msg };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError("");

    try {
      if (phase() === "intake") {
        const history = messages().slice(0, -1);
        const resp = await generatorChatRemote(t, msg, history);

        const prefs = parseIntakeComplete(resp.message);
        if (prefs) {
          const displayText = stripJsonBlock(resp.message);
          if (displayText) {
            setMessages((prev) => [
              ...prev,
              { role: "assistant", content: displayText },
            ]);
          }
          setPreferences(prefs);
          await startGeneration(t, prefs);
        } else {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: resp.message },
          ]);
        }
      } else if (phase() === "complete") {
        const currentGuide = guide();
        if (currentGuide) {
          setLoading(true);
          const refined = await refineBuildRemote(
            t,
            currentGuide,
            [],
            preferences()?.budget_chaos ?? 500,
            messages(),
            msg,
          );
          setGuide(refined);
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `Build updated! "${refined.title}" now has ${refined.brackets.length} level brackets. Click "Load into Build Viewer" to see the changes.`,
            },
          ]);
        }
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function startGeneration(t: string, prefs: BuildPreferences) {
    setPhase("generating");
    try {
      const history = messages();
      const generatedGuide = await generateBuildRemote(t, prefs, history);
      setGuide(generatedGuide);
      await checkPrices(t, generatedGuide, prefs);
    } catch (e) {
      setError(String(e));
      setPhase("intake");
    }
  }

  async function checkPrices(
    t: string,
    generatedGuide: BuildGuide,
    prefs: BuildPreferences,
  ) {
    setPhase("price_check");

    const endgame = generatedGuide.brackets.find(
      (b) => b.title.includes("Endgame") || b.title.includes("90"),
    );
    if (!endgame || endgame.items.length === 0) {
      finishGeneration(generatedGuide);
      return;
    }

    const prices: Array<{ name: string; price_chaos: number }> = [];
    const items = endgame.items;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      setPriceProgress(
        `Checking prices... ${i + 1}/${items.length}: ${item.name}`,
      );

      try {
        const searchItem = {
          id: 0,
          slot: item.slot,
          name: item.name,
          base_type: item.base_type || "",
          rarity: "UNIQUE",
          level: 0,
          quality: 0,
          sockets: "",
          implicits: [],
          explicits: [],
          raw_text: "",
        };
        const result = await tradeSearch(
          searchItem,
          prefs.league || "Standard",
        );
        if (result.listings.length > 0 && result.listings[0].price) {
          const listing = result.listings[0];
          let priceChaos = listing.price!.amount;
          if (listing.price!.currency === "divine") {
            priceChaos *= 150;
          }
          prices.push({ name: item.name, price_chaos: priceChaos });
        }
      } catch {
        // Skip items we can't price
      }

      if (i < items.length - 1) {
        await new Promise((r) => setTimeout(r, 1000));
      }
    }

    const totalCost = prices.reduce((sum, p) => sum + p.price_chaos, 0);
    const budget = prefs.budget_chaos || 500;

    if (prices.length > 0 && totalCost > budget) {
      setPriceProgress("Refining build to fit budget...");
      try {
        const refined = await refineBuildRemote(
          t,
          generatedGuide,
          prices,
          budget,
          messages(),
          "",
        );
        setGuide(refined);
        finishGeneration(refined);
      } catch {
        finishGeneration(generatedGuide);
      }
    } else {
      finishGeneration(generatedGuide);
    }
  }

  function finishGeneration(finalGuide: BuildGuide) {
    setPhase("complete");
    const priceNote = guide() !== finalGuide ? " (adjusted for budget)" : "";
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content:
          `Your build guide is ready${priceNote}! "${finalGuide.title}" ` +
          `with ${finalGuide.brackets.length} level brackets. ` +
          `Click "Load into Build Viewer" below to see it, or ask me to make changes.`,
      },
    ]);
    setGuide(finalGuide);
  }

  function handleLoadBuild() {
    const g = guide();
    if (g) {
      props.onComplete(guideToBuild(g));
    }
  }

  function handleStartSave() {
    const g = guide();
    if (g) {
      setSaveName(g.title);
      setShowSaveInput(true);
      setSaveStatus("");
    }
  }

  async function handleConfirmSave() {
    const g = guide();
    const name = saveName().trim();
    if (!g || !name) return;

    try {
      await saveBuildGuide(name, g);
      setSaveStatus("Saved!");
      setShowSaveInput(false);
      props.onSave?.();
    } catch (e) {
      setSaveStatus(`Error: ${String(e)}`);
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleReset() {
    setPhase(isLoggedIn() && isSubscribed() ? "intake" : "auth");
    setMessages([]);
    setGuide(null);
    setPreferences(null);
    setError("");
    setPriceProgress("");
  }

  function phaseLabel(): string {
    switch (phase()) {
      case "auth":
        return "Login required";
      case "intake":
        return "Tell me about your build";
      case "generating":
        return "Generating build guide...";
      case "price_check":
        return priceProgress() || "Checking trade prices...";
      case "complete":
        return "Build ready!";
    }
  }

  return (
    <div class="generator-page">
      <h1 class="page-title">Build Generator</h1>
      <p class="page-subtitle">
        Let the AI create a complete PoE 1 leveling guide for you
      </p>

      {/* Phase indicator */}
      <div class="generator-phase">
        <span
          class="generator-phase-dot"
          classList={{ active: phase() !== "auth" }}
        />
        <span class="generator-phase-label">{phaseLabel()}</span>
        <Show when={phase() === "generating" || phase() === "price_check"}>
          <span class="spinner" />
        </Show>
      </div>

      {/* Update Game Data button */}
      <Show when={phase() === "auth" || phase() === "intake"}>
        <div class="knowledge-update-row">
          <button
            class="knowledge-update-btn"
            onClick={handleRefreshKnowledge}
            disabled={knowledgeLoading()}
          >
            <Show when={knowledgeLoading()} fallback="Update Game Data">
              Updating...
            </Show>
          </button>
          <Show when={knowledgeVersion()}>
            <span class="knowledge-version">
              Game data: v{knowledgeVersion()}
            </span>
          </Show>
        </div>
      </Show>

      {/* Auth gate */}
      <Show when={phase() === "auth"}>
        <div class="ai-auth-gate">
          <Show when={!isLoggedIn()}>
            <p class="ai-auth-prompt">
              Log in with Discord to use the Build Generator
            </p>
            <button
              class="discord-login-btn"
              onClick={handleLogin}
              disabled={loginLoading()}
            >
              <Show when={loginLoading()} fallback="Login with Discord">
                Connecting...
              </Show>
            </button>
          </Show>
          <Show when={isLoggedIn() && !isSubscribed()}>
            <p class="ai-auth-prompt">
              Subscribe to Path of Purpose to unlock the Build Generator
            </p>
            <button class="subscribe-btn" onClick={handleSubscribe}>
              Subscribe — $4.99/mo
            </button>
            <button class="refresh-status-btn" onClick={handleRefreshStatus}>
              I already subscribed (refresh)
            </button>
          </Show>
        </div>
      </Show>

      {/* Chat + actions */}
      <Show when={phase() !== "auth"}>
        <div class="generator-chat">
          <div class="chat-messages">
            <Show when={messages().length === 0 && phase() === "intake"}>
              <div class="panel-empty">
                Tell me what kind of build you'd like to play! I'll ask a few
                questions then generate a complete leveling guide.
              </div>
            </Show>
            <For each={messages()}>
              {(msg) => (
                <div
                  class={
                    msg.role === "user"
                      ? "chat-bubble chat-bubble-user"
                      : "chat-bubble chat-bubble-assistant"
                  }
                >
                  {msg.content}
                </div>
              )}
            </For>
            <Show when={loading()}>
              <div class="chat-bubble chat-bubble-assistant chat-bubble-loading">
                <span class="spinner" /> Thinking...
              </div>
            </Show>
          </div>

          <Show when={error()}>
            <div class="error-toast">{error()}</div>
          </Show>

          {/* Actions bar */}
          <div class="generator-actions">
            <Show when={phase() === "complete" && guide()}>
              <button class="generator-load-btn" onClick={handleLoadBuild}>
                Load into Build Viewer
              </button>
              <Show when={!showSaveInput()}>
                <button class="generator-save-btn" onClick={handleStartSave}>
                  Save Build
                </button>
              </Show>
            </Show>
            <Show when={phase() === "complete"}>
              <button class="generator-reset-btn" onClick={handleReset}>
                Start Over
              </button>
            </Show>
          </div>
          <Show when={showSaveInput()}>
            <div class="save-build-row">
              <input
                type="text"
                value={saveName()}
                onInput={(e) => setSaveName(e.currentTarget.value)}
                placeholder="Build name..."
                class="save-build-input"
              />
              <button onClick={handleConfirmSave} disabled={!saveName().trim()}>
                Confirm
              </button>
              <button
                class="generator-reset-btn"
                onClick={() => setShowSaveInput(false)}
              >
                Cancel
              </button>
            </div>
          </Show>
          <Show when={saveStatus()}>
            <div
              class={
                saveStatus().startsWith("Error") ? "error-toast" : "info-box"
              }
            >
              {saveStatus()}
            </div>
          </Show>

          {/* Chat input */}
          <Show when={phase() === "intake" || phase() === "complete"}>
            <div class="chat-input-row">
              <textarea
                placeholder={
                  phase() === "intake"
                    ? "Describe your ideal build..."
                    : "Ask for changes to the build..."
                }
                value={input()}
                onInput={(e) => setInput(e.currentTarget.value)}
                onKeyDown={handleKeyDown}
                rows={2}
                disabled={loading()}
              />
              <button
                onClick={handleSend}
                disabled={loading() || !input().trim()}
              >
                Send
              </button>
            </div>
          </Show>
        </div>
      </Show>
    </div>
  );
}
