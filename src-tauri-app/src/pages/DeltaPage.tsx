import { createSignal, For, Show } from "solid-js";
import { analyzeDelta } from "../lib/commands";
import type { DeltaPendingResponse, DeltaReport } from "../lib/types";
import GapCard from "../components/GapCard";

export default function DeltaPage() {
  const [pobCode, setPobCode] = createSignal("");
  const [charName, setCharName] = createSignal("");
  const [report, setReport] = createSignal<DeltaReport | null>(null);
  const [pending, setPending] = createSignal<DeltaPendingResponse | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");

  function isPending(
    result: DeltaReport | DeltaPendingResponse,
  ): result is DeltaPendingResponse {
    return "status" in result && result.status === "oauth_pending";
  }

  async function handleAnalyze() {
    const code = pobCode().trim();
    const name = charName().trim();
    if (!code || !name) return;

    setLoading(true);
    setError("");
    setReport(null);
    setPending(null);

    try {
      const result = await analyzeDelta(code, name);
      if (isPending(result)) {
        setPending(result);
      } else {
        setReport(result);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 class="page-title">Delta Report</h1>
      <p class="page-subtitle">
        Compare your character against a guide build to see what to fix next.
      </p>

      <div class="input-group">
        <label for="delta-pob">Guide PoB Code</label>
        <textarea
          id="delta-pob"
          placeholder="Paste the guide's PoB export code..."
          value={pobCode()}
          onInput={(e) => setPobCode(e.currentTarget.value)}
          rows={3}
        />
      </div>

      <div class="input-group">
        <label for="delta-char">Character Name</label>
        <input
          type="text"
          id="delta-char"
          placeholder="Your PoE character name"
          value={charName()}
          onInput={(e) => setCharName(e.currentTarget.value)}
        />
      </div>

      <button
        onClick={handleAnalyze}
        disabled={loading() || !pobCode().trim() || !charName().trim()}
      >
        <Show when={loading()} fallback="Analyze Delta">
          <span class="spinner" />
          Analyzing...
        </Show>
      </button>

      <Show when={error()}>
        <div class="error-toast" style={{ "margin-top": "16px" }}>
          {error()}
        </div>
      </Show>

      <Show when={pending()}>
        <div class="info-box" style={{ "margin-top": "16px" }}>
          {pending()!.message}
        </div>
      </Show>

      <Show when={report()}>
        <div style={{ "margin-top": "24px" }}>
          <h3 class="section-title">
            Top Gaps: {report()!.character_name} vs{" "}
            {report()!.guide_build_name}
          </h3>
          <For each={report()!.top_gaps}>
            {(gap) => <GapCard gap={gap} />}
          </For>
        </div>
      </Show>
    </div>
  );
}
