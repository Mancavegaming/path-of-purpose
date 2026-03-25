import { createSignal, onMount, onCleanup, Show, For } from "solid-js";

// ─── Atlas Tree Data Types ───────────────────────────────────────────
interface AtlasNode {
  skill?: number;
  name?: string;
  icon?: string;
  isNotable?: boolean;
  isKeystone?: boolean;
  stats?: string[];
  flavourText?: string[];
  group: number;
  orbit: number;
  orbitIndex: number;
  out: string[];
  in: string[];
}

interface AtlasGroup {
  x: number;
  y: number;
  orbits: number[];
  nodes: string[];
}

interface AtlasTreeData {
  nodes: Record<string, AtlasNode>;
  groups: Record<string, AtlasGroup>;
  constants: {
    skillsPerOrbit: number[];
    orbitRadii: number[];
  };
  min_x: number;
  min_y: number;
  max_x: number;
  max_y: number;
  points: { totalPoints: number };
}

// ─── Computed Node Position ──────────────────────────────────────────
interface RenderedNode {
  id: string;
  x: number;
  y: number;
  name: string;
  stats: string[];
  isNotable: boolean;
  isKeystone: boolean;
  connections: string[];
}

// ─── Constants ───────────────────────────────────────────────────────
const ATLAS_DATA_URL = "https://raw.githubusercontent.com/grindinggear/atlastree-export/master/data.json";

const NODE_COLORS = {
  small:    { fill: "#2a2a36", stroke: "#3a3a4a", allocFill: "#c4a44e", allocStroke: "#e8d48b" },
  notable:  { fill: "#3a3524", stroke: "#8a7a4a", allocFill: "#d4b45e", allocStroke: "#f0e0a0" },
  keystone: { fill: "#4a2030", stroke: "#9a4060", allocFill: "#e06080", allocStroke: "#ff90b0" },
};

const NODE_RADII = { small: 5, notable: 9, keystone: 13 };

// ─── Component ───────────────────────────────────────────────────────
export default function AtlasPage() {
  let canvasRef: HTMLCanvasElement | undefined;
  let animFrameId: number | null = null;

  const [treeData, setTreeData] = createSignal<AtlasTreeData | null>(null);
  const [nodes, setNodes] = createSignal<RenderedNode[]>([]);
  const [allocated, setAllocated] = createSignal<Set<string>>(new Set());
  const [loading, setLoading] = createSignal(true);
  const [error, setError] = createSignal("");
  const [importUrl, setImportUrl] = createSignal("");
  const [importError, setImportError] = createSignal("");
  const [searchQuery, setSearchQuery] = createSignal("");
  const [searchResults, setSearchResults] = createSignal<RenderedNode[]>([]);

  // View transform
  let viewX = 0;
  let viewY = 0;
  let viewScale = 0.06;
  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let dragViewX = 0;
  let dragViewY = 0;

  // Tooltip
  let hoveredNode: RenderedNode | null = null;
  let tooltipX = 0;
  let tooltipY = 0;

  // Node lookup
  let nodeMap = new Map<string, RenderedNode>();

  // ─── Fetch & Parse ───────────────────────────────────────────────
  onMount(async () => {
    try {
      const resp = await fetch(ATLAS_DATA_URL);
      if (!resp.ok) throw new Error(`Failed to fetch atlas data: ${resp.status}`);
      const data: AtlasTreeData = await resp.json();
      setTreeData(data);

      const computed = computeNodePositions(data);
      setNodes(computed);
      nodeMap = new Map(computed.map(n => [n.id, n]));

      // Center view
      const cx = (data.min_x + data.max_x) / 2;
      const cy = (data.min_y + data.max_y) / 2;
      viewX = -cx;
      viewY = -cy;

      setLoading(false);
      scheduleRender();
    } catch (e) {
      setError(String(e));
      setLoading(false);
    }
  });

  onCleanup(() => {
    if (animFrameId !== null) cancelAnimationFrame(animFrameId);
  });

  // ─── Node Position Calculation ─────────────────────────────────
  function computeNodePositions(data: AtlasTreeData): RenderedNode[] {
    const result: RenderedNode[] = [];
    const { skillsPerOrbit, orbitRadii } = data.constants;

    for (const [nodeId, node] of Object.entries(data.nodes)) {
      if (nodeId === "root") continue;
      const group = data.groups[String(node.group)];
      if (!group) continue;

      const orbit = node.orbit;
      const orbitIndex = node.orbitIndex;
      const radius = orbitRadii[orbit] ?? 0;
      const nodesInOrbit = skillsPerOrbit[orbit] ?? 1;
      const angle = (2 * Math.PI * orbitIndex) / nodesInOrbit - Math.PI / 2;

      const x = group.x + radius * Math.cos(angle);
      const y = group.y + radius * Math.sin(angle);

      result.push({
        id: nodeId,
        x, y,
        name: node.name || "",
        stats: node.stats || [],
        isNotable: !!node.isNotable,
        isKeystone: !!node.isKeystone,
        connections: [...(node.out || []), ...(node.in || [])],
      });
    }
    return result;
  }

  // ─── Allocation ────────────────────────────────────────────────
  function toggleNode(nodeId: string) {
    setAllocated(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        if (next.size < (treeData()?.points.totalPoints ?? 138)) {
          next.add(nodeId);
        }
      }
      return next;
    });
    scheduleRender();
  }

  function clearAll() {
    setAllocated(new Set<string>());
    scheduleRender();
  }

  // ─── Import from poeplanner.com ────────────────────────────────
  function handleImport() {
    setImportError("");
    const url = importUrl().trim();
    if (!url) return;

    // poeplanner URLs: https://poeplanner.com/a/HASH
    // The hash encodes allocated node hashes — try to decode
    // For now, support comma-separated node IDs as fallback
    if (url.includes("poeplanner.com/a/")) {
      setImportError("poeplanner.com URL import coming soon. For now, paste comma-separated node IDs.");
      return;
    }

    // Try parsing as comma-separated node IDs
    const ids = url.split(",").map(s => s.trim()).filter(Boolean);
    const valid = ids.filter(id => nodeMap.has(id));
    if (valid.length > 0) {
      setAllocated(new Set<string>(valid));
      setImportError("");
      scheduleRender();
    } else {
      setImportError("No valid node IDs found.");
    }
  }

  // ─── Search ────────────────────────────────────────────────────
  function handleSearch(query: string) {
    setSearchQuery(query);
    if (!query.trim()) {
      setSearchResults([]);
      scheduleRender();
      return;
    }
    const q = query.toLowerCase();
    const results = nodes().filter(n =>
      n.name.toLowerCase().includes(q) ||
      n.stats.some(s => s.toLowerCase().includes(q))
    );
    setSearchResults(results);
    // Pan to first result
    if (results.length > 0) {
      viewX = -results[0].x;
      viewY = -results[0].y;
      viewScale = Math.max(viewScale, 0.1);
    }
    scheduleRender();
  }

  function focusNode(node: RenderedNode) {
    viewX = -node.x;
    viewY = -node.y;
    viewScale = Math.max(viewScale, 0.12);
    scheduleRender();
  }

  // ─── Zoom Controls ────────────────────────────────────────────
  function zoomIn() {
    viewScale = Math.min(0.5, viewScale * 1.3);
    scheduleRender();
  }

  function zoomOut() {
    viewScale = Math.max(0.01, viewScale * 0.7);
    scheduleRender();
  }

  function resetView() {
    const data = treeData();
    if (data) {
      viewX = -(data.min_x + data.max_x) / 2;
      viewY = -(data.min_y + data.max_y) / 2;
      viewScale = 0.06;
      scheduleRender();
    }
  }

  // ─── Strategy Presets ──────────────────────────────────────────
  const STRATEGY_KEYWORDS: Record<string, string[]> = {
    "Essence": ["essence", "imprisoned", "corrupt"],
    "Delirium": ["delirium", "simulacrum", "reward"],
    "Breach": ["breach", "clasped", "splinter"],
    "Legion": ["legion", "monolith", "war hoard"],
    "Harvest": ["harvest", "lifeforce", "crop"],
    "Expedition": ["expedition", "excavated", "artifact", "logbook"],
    "Ritual": ["ritual", "tribute"],
    "Blight": ["blight", "anointed", "lane"],
    "Abyss": ["abyss", "abyssal", "stygian"],
    "Harbinger": ["harbinger", "shard"],
    "Strongbox": ["strongbox", "chest"],
    "Shrine": ["shrine", "blessed"],
    "Map Sustain": ["map", "adjacent", "connected", "bonus", "quantity"],
    "Boss": ["boss", "guardian", "conqueror", "elder", "shaper"],
  };

  function applyPreset(strategy: string) {
    const keywords = STRATEGY_KEYWORDS[strategy];
    if (!keywords) return;
    // Find all nodes matching the strategy keywords
    const matching = nodes().filter(n => {
      const text = (n.name + " " + n.stats.join(" ")).toLowerCase();
      return keywords.some(kw => text.includes(kw));
    });
    if (matching.length === 0) return;
    const maxPts = treeData()?.points.totalPoints ?? 138;
    setAllocated(prev => {
      const next = new Set(prev);
      for (const node of matching) {
        if (next.size >= maxPts) break;
        next.add(node.id);
      }
      return next;
    });
    scheduleRender();
  }

  // ─── Export ────────────────────────────────────────────────────
  function exportNodeIds(): string {
    return Array.from(allocated()).join(",");
  }

  function copyExport() {
    const ids = exportNodeIds();
    navigator.clipboard.writeText(ids).catch(() => {});
  }

  // ─── Canvas Rendering ──────────────────────────────────────────
  function scheduleRender() {
    if (animFrameId !== null) return;
    animFrameId = requestAnimationFrame(() => {
      animFrameId = null;
      render();
    });
  }

  function render() {
    const canvas = canvasRef;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    const alloc = allocated();
    const nodeList = nodes();

    // Clear
    ctx.fillStyle = "#0a0d12";
    ctx.fillRect(0, 0, w, h);

    ctx.save();
    ctx.translate(w / 2, h / 2);
    ctx.scale(viewScale, viewScale);
    ctx.translate(viewX, viewY);

    // ── Edges (unallocated) ──
    ctx.strokeStyle = "#1a1a28";
    ctx.lineWidth = 1.5 / viewScale;
    ctx.beginPath();
    for (const node of nodeList) {
      for (const connId of node.connections) {
        const conn = nodeMap.get(connId);
        if (!conn) continue;
        if (node.id > connId) continue; // draw each edge once
        if (alloc.has(node.id) && alloc.has(connId)) continue;
        ctx.moveTo(node.x, node.y);
        ctx.lineTo(conn.x, conn.y);
      }
    }
    ctx.stroke();

    // ── Edges (allocated) ──
    ctx.strokeStyle = "#c4a44e";
    ctx.lineWidth = 2.5 / viewScale;
    ctx.shadowColor = "#c4a44e";
    ctx.shadowBlur = 4 / viewScale;
    ctx.beginPath();
    for (const node of nodeList) {
      if (!alloc.has(node.id)) continue;
      for (const connId of node.connections) {
        if (!alloc.has(connId)) continue;
        const conn = nodeMap.get(connId);
        if (!conn) continue;
        if (node.id > connId) continue;
        ctx.moveTo(node.x, node.y);
        ctx.lineTo(conn.x, conn.y);
      }
    }
    ctx.stroke();
    ctx.shadowBlur = 0;

    // ── Nodes (unallocated) ──
    for (const node of nodeList) {
      if (alloc.has(node.id)) continue;
      const type = node.isKeystone ? "keystone" : node.isNotable ? "notable" : "small";
      const colors = NODE_COLORS[type];
      const r = NODE_RADII[type];

      ctx.fillStyle = colors.fill;
      ctx.strokeStyle = colors.stroke;
      ctx.lineWidth = 1 / viewScale;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
      ctx.fill();
      if (type !== "small") ctx.stroke();
    }

    // ── Nodes (allocated, on top with glow) ──
    for (const node of nodeList) {
      if (!alloc.has(node.id)) continue;
      const type = node.isKeystone ? "keystone" : node.isNotable ? "notable" : "small";
      const colors = NODE_COLORS[type];
      const r = NODE_RADII[type] * 1.2;

      ctx.shadowColor = colors.allocStroke;
      ctx.shadowBlur = 8 / viewScale;
      ctx.fillStyle = colors.allocFill;
      ctx.strokeStyle = colors.allocStroke;
      ctx.lineWidth = 1.5 / viewScale;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
    ctx.shadowBlur = 0;

    // ── Search highlights (cyan glow) ──
    const searchSet = new Set(searchResults().map(n => n.id));
    if (searchSet.size > 0) {
      for (const node of nodeList) {
        if (!searchSet.has(node.id) || alloc.has(node.id)) continue;
        const r = (node.isKeystone ? 13 : node.isNotable ? 9 : 5) * 1.4;
        ctx.shadowColor = "#00e5ff";
        ctx.shadowBlur = 12 / viewScale;
        ctx.fillStyle = "#00bcd4";
        ctx.strokeStyle = "#00e5ff";
        ctx.lineWidth = 2 / viewScale;
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
      ctx.shadowBlur = 0;
    }

    ctx.restore();

    // ── Tooltip ──
    if (hoveredNode) {
      drawTooltip(ctx, hoveredNode, tooltipX, tooltipY, alloc.has(hoveredNode.id));
    }

    // ── Legend ──
    ctx.fillStyle = "#8b949e";
    ctx.font = "12px monospace";
    ctx.fillText(`${alloc.size} / ${treeData()?.points.totalPoints ?? 138} points`, 12, h - 12);
  }

  function drawTooltip(ctx: CanvasRenderingContext2D, node: RenderedNode, sx: number, sy: number, isAlloc: boolean) {
    const lines: string[] = [];
    lines.push(node.name || `Node ${node.id}`);
    if (node.isKeystone) lines.push("[Keystone]");
    else if (node.isNotable) lines.push("[Notable]");
    for (const stat of node.stats.slice(0, 4)) {
      lines.push(stat.length > 50 ? stat.slice(0, 47) + "..." : stat);
    }
    if (isAlloc) lines.push("(Allocated)");

    ctx.font = "12px monospace";
    const maxW = Math.max(...lines.map(l => ctx.measureText(l).width)) + 16;
    const boxH = lines.length * 16 + 12;
    const bx = Math.min(sx + 12, (canvasRef?.width ?? 800) - maxW - 8);
    const by = Math.max(sy - boxH - 4, 4);

    ctx.fillStyle = "rgba(10, 13, 18, 0.92)";
    ctx.strokeStyle = "#c4a44e";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(bx, by, maxW, boxH, 4);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = "#e6edf3";
    lines.forEach((line, i) => {
      if (i === 0) ctx.fillStyle = node.isKeystone ? "#e06080" : node.isNotable ? "#e8d48b" : "#e6edf3";
      else ctx.fillStyle = "#c9d1d9";
      ctx.fillText(line, bx + 8, by + 16 + i * 16);
    });
  }

  // ─── Mouse / Wheel Handlers ────────────────────────────────────
  function handleWheel(e: WheelEvent) {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.85 : 1.18;
    viewScale = Math.max(0.01, Math.min(0.5, viewScale * factor));
    scheduleRender();
  }

  function handleMouseDown(e: MouseEvent) {
    if (e.button === 0) {
      isDragging = true;
      dragStartX = e.clientX;
      dragStartY = e.clientY;
      dragViewX = viewX;
      dragViewY = viewY;
    }
  }

  function handleMouseMove(e: MouseEvent) {
    if (isDragging) {
      const dx = (e.clientX - dragStartX) / viewScale;
      const dy = (e.clientY - dragStartY) / viewScale;
      viewX = dragViewX + dx;
      viewY = dragViewY + dy;
      scheduleRender();
      return;
    }

    // Hit test for tooltip
    if (!canvasRef) return;
    const rect = canvasRef.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    // Convert screen → world
    const wx = (mx - canvasRef.width / 2) / viewScale - viewX;
    const wy = (my - canvasRef.height / 2) / viewScale - viewY;

    let found: RenderedNode | null = null;
    for (const node of nodes()) {
      const r = (node.isKeystone ? 13 : node.isNotable ? 9 : 5) * 1.5;
      const dx = node.x - wx;
      const dy = node.y - wy;
      if (dx * dx + dy * dy < r * r) {
        found = node;
        break;
      }
    }
    hoveredNode = found;
    tooltipX = mx;
    tooltipY = my;
    if (canvasRef) canvasRef.style.cursor = found ? "pointer" : "grab";
    scheduleRender();
  }

  function handleMouseUp(e: MouseEvent) {
    if (isDragging && Math.abs(e.clientX - dragStartX) < 4 && Math.abs(e.clientY - dragStartY) < 4) {
      // Click — toggle node
      if (hoveredNode) {
        toggleNode(hoveredNode.id);
      }
    }
    isDragging = false;
  }

  function handleMouseLeave() {
    isDragging = false;
    hoveredNode = null;
    scheduleRender();
  }

  // ─── Allocated Summary ─────────────────────────────────────────
  function allocatedNotables() {
    const alloc = allocated();
    return nodes().filter(n => alloc.has(n.id) && (n.isNotable || n.isKeystone) && n.name);
  }

  // ─── Render ────────────────────────────────────────────────────
  return (
    <div>
      <h1 class="page-title">Atlas Passive Tree</h1>
      <p class="page-subtitle">Plan your atlas strategy. Click nodes to allocate, scroll to zoom, drag to pan.</p>

      <Show when={error()}>
        <div class="card" style={{ "border-color": "var(--severity-critical)", background: "rgba(224, 80, 80, 0.08)" }}>
          <div style={{ color: "var(--severity-critical)", "font-size": "13px" }}>{error()}</div>
        </div>
      </Show>

      {/* Import + Controls */}
      <div class="card" style={{ display: "flex", "align-items": "center", gap: "10px", "flex-wrap": "wrap" }}>
        <input
          type="text"
          value={importUrl()}
          onInput={(e) => setImportUrl(e.currentTarget.value)}
          placeholder="Paste comma-separated node IDs to import..."
          style={{
            flex: "1", "min-width": "200px",
            background: "var(--bg-input)", border: "1px solid var(--border)",
            "border-radius": "var(--radius)", color: "var(--text-primary)",
            padding: "6px 12px", "font-size": "13px",
          }}
        />
        <button onClick={handleImport} style={{ "font-size": "13px", padding: "6px 16px" }}>Import</button>
        <button onClick={copyExport} disabled={allocated().size === 0} style={{ "font-size": "13px", padding: "6px 16px", background: "var(--bg-tertiary)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
          Export IDs
        </button>
        <button onClick={clearAll} style={{ "font-size": "13px", padding: "6px 16px", background: "var(--bg-tertiary)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
          Clear All
        </button>
        <span style={{ "font-size": "13px", color: "var(--accent)", "font-weight": "600" }}>
          {allocated().size} / {treeData()?.points.totalPoints ?? 138} points
        </span>
      </div>
      <Show when={importError()}>
        <div style={{ color: "var(--severity-critical)", "font-size": "12px", padding: "4px 0" }}>{importError()}</div>
      </Show>

      {/* Search + Zoom + Presets */}
      <div class="card" style={{ display: "flex", "align-items": "center", gap: "10px", "flex-wrap": "wrap" }}>
        <input
          type="text"
          value={searchQuery()}
          onInput={(e) => handleSearch(e.currentTarget.value)}
          placeholder="Search nodes (e.g. essence, delirium, boss)..."
          style={{
            width: "220px",
            background: "var(--bg-input)", border: "1px solid var(--border)",
            "border-radius": "var(--radius)", color: "var(--text-primary)",
            padding: "6px 12px", "font-size": "13px",
          }}
        />
        <Show when={searchResults().length > 0}>
          <span style={{ "font-size": "11px", color: "var(--text-muted)" }}>{searchResults().length} found</span>
        </Show>
        <div style={{ display: "flex", gap: "4px", "margin-left": "auto" }}>
          <button onClick={zoomIn} style={{ "font-size": "14px", padding: "4px 10px", background: "var(--bg-tertiary)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>+</button>
          <button onClick={zoomOut} style={{ "font-size": "14px", padding: "4px 10px", background: "var(--bg-tertiary)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>-</button>
          <button onClick={resetView} style={{ "font-size": "12px", padding: "4px 10px", background: "var(--bg-tertiary)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>Reset</button>
        </div>
      </div>

      {/* Strategy Presets */}
      <div class="card" style={{ padding: "8px 12px" }}>
        <div style={{ "font-size": "11px", color: "var(--text-muted)", "text-transform": "uppercase", "letter-spacing": "0.5px", "margin-bottom": "6px" }}>Strategy Presets — click to add matching nodes</div>
        <div style={{ display: "flex", gap: "6px", "flex-wrap": "wrap" }}>
          {Object.keys(STRATEGY_KEYWORDS).map((strat) => (
            <button
              onClick={() => applyPreset(strat)}
              style={{ "font-size": "11px", padding: "3px 10px", background: "var(--bg-tertiary)", color: "var(--text-secondary)", border: "1px solid var(--border)", "border-radius": "var(--radius)" }}
            >
              {strat}
            </button>
          ))}
        </div>
      </div>

      {/* Canvas */}
      <Show when={!loading()} fallback={<div class="card" style={{ padding: "40px", "text-align": "center", color: "var(--text-muted)" }}>Loading atlas tree data...</div>}>
        <div style={{ position: "relative", "margin-top": "8px" }}>
          <canvas
            ref={canvasRef}
            width={1100}
            height={650}
            style={{ width: "100%", "border-radius": "var(--radius-lg)", border: "1px solid var(--border)", cursor: "grab" }}
            onWheel={handleWheel}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseLeave}
          />
        </div>
      </Show>

      {/* Search Results */}
      <Show when={searchResults().length > 0 && searchQuery()}>
        <div class="card" style={{ "margin-top": "8px" }}>
          <div class="section-title">Search Results ({searchResults().length})</div>
          <div style={{ display: "flex", "flex-direction": "column", gap: "2px", "max-height": "200px", "overflow-y": "auto" }}>
            <For each={searchResults().slice(0, 30)}>
              {(node) => (
                <div
                  onClick={() => { focusNode(node); toggleNode(node.id); }}
                  style={{
                    display: "flex", "justify-content": "space-between", padding: "4px 8px",
                    "font-size": "12px", cursor: "pointer", "border-radius": "var(--radius)",
                    background: allocated().has(node.id) ? "rgba(196, 164, 78, 0.1)" : "transparent",
                  }}
                >
                  <span style={{ color: node.isKeystone ? "#e06080" : node.isNotable ? "var(--accent)" : "var(--text-primary)" }}>
                    {allocated().has(node.id) ? "\u2713 " : ""}{node.name || `Node ${node.id}`}
                  </span>
                  <span style={{ color: "var(--text-muted)", "font-size": "11px", "max-width": "55%", overflow: "hidden", "text-overflow": "ellipsis", "white-space": "nowrap" }}>
                    {node.stats[0] || ""}
                  </span>
                </div>
              )}
            </For>
          </div>
        </div>
      </Show>

      {/* Allocated Notables Summary */}
      <Show when={allocatedNotables().length > 0}>
        <div class="card" style={{ "margin-top": "12px" }}>
          <div class="section-title">Allocated Notables & Keystones ({allocatedNotables().length})</div>
          <div style={{ display: "flex", "flex-direction": "column", gap: "4px" }}>
            <For each={allocatedNotables()}>
              {(node) => (
                <div style={{ display: "flex", "justify-content": "space-between", padding: "3px 0", "font-size": "13px" }}>
                  <span style={{ color: node.isKeystone ? "#e06080" : "var(--accent)", "font-weight": "600" }}>
                    {node.isKeystone ? "[K] " : ""}{node.name}
                  </span>
                  <span style={{ color: "var(--text-muted)", "font-size": "11px", "max-width": "60%", "text-align": "right", overflow: "hidden", "text-overflow": "ellipsis", "white-space": "nowrap" }}>
                    {node.stats[0] || ""}
                  </span>
                </div>
              )}
            </For>
          </div>
        </div>
      </Show>
    </div>
  );
}
