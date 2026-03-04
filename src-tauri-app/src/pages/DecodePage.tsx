import { createSignal, Show } from "solid-js";
import { decodeBuild } from "../lib/commands";
import type { Build } from "../lib/types";
import BuildSummary from "../components/BuildSummary";

export default function DecodePage() {
  const [code, setCode] = createSignal("");
  const [build, setBuild] = createSignal<Build | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal("");

  async function handleDecode() {
    const input = code().trim();
    if (!input) return;

    setLoading(true);
    setError("");
    setBuild(null);

    try {
      const result = await decodeBuild(input);
      setBuild(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 class="page-title">Decode Build</h1>
      <p class="page-subtitle">
        Paste a Path of Building export code to inspect its contents.
      </p>

      <div class="input-group">
        <label for="pob-code">PoB Export Code</label>
        <textarea
          id="pob-code"
          placeholder="Paste your PoB export code here..."
          value={code()}
          onInput={(e) => setCode(e.currentTarget.value)}
          rows={4}
        />
      </div>

      <button onClick={handleDecode} disabled={loading() || !code().trim()}>
        <Show when={loading()} fallback="Decode">
          <span class="spinner" />
          Decoding...
        </Show>
      </button>

      <Show when={error()}>
        <div class="error-toast" style={{ "margin-top": "16px" }}>
          {error()}
        </div>
      </Show>

      <Show when={build()}>
        <div style={{ "margin-top": "24px" }}>
          <BuildSummary build={build()!} />
        </div>
      </Show>
    </div>
  );
}
