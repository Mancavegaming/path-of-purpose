import { createSignal, createEffect, onMount, onCleanup } from "solid-js";
import type { TreeLayout, TreeLayoutNode } from "../lib/commands";
import { getTreeLayout, decodeTreeUrl } from "../lib/commands";

interface PassiveTreeCanvasProps {
  url: string; // pathofexile.com tree URL with encoded node IDs
  width?: number;
  height?: number;
  highlightNodes?: number[]; // Node IDs to highlight (e.g., suggestions)
}

// Node rendering config
const NODE_COLORS = {
  normal: { fill: "#3a3a3a", stroke: "#555", allocFill: "#c4a44e", allocStroke: "#e8d48b" },
  notable: { fill: "#4a4a3a", stroke: "#8a7a4a", allocFill: "#d4b45e", allocStroke: "#f0e0a0" },
  keystone: { fill: "#4a3a4a", stroke: "#7a5a7a", allocFill: "#e4c46e", allocStroke: "#fff0b0" },
  mastery: { fill: "#2a2a2a", stroke: "#444", allocFill: "#a08030", allocStroke: "#c4a44e" },
  jewel: { fill: "#2a3a2a", stroke: "#4a6a4a", allocFill: "#50a050", allocStroke: "#80d080" },
  start: { fill: "#3a4a5a", stroke: "#5a7a9a", allocFill: "#5a9ade", allocStroke: "#8ac0ff" },
};

const NODE_RADII = { normal: 4, notable: 7, keystone: 10, mastery: 5, jewel: 6, start: 12 };

function getNodeStyle(type: number): keyof typeof NODE_COLORS {
  switch (type) {
    case 1: return "notable";
    case 2: return "keystone";
    case 3: return "mastery";
    case 4: return "jewel";
    case 5: return "start";
    default: return "normal";
  }
}

export default function PassiveTreeCanvas(props: PassiveTreeCanvasProps) {
  let canvasRef: HTMLCanvasElement | undefined;
  const [layout, setLayout] = createSignal<TreeLayout | null>(null);
  const [loading, setLoading] = createSignal(true);
  const [error, setError] = createSignal("");

  // View transform state
  let viewX = 0;
  let viewY = 0;
  let viewScale = 0.04; // Initial zoom level to fit the tree
  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let dragViewX = 0;
  let dragViewY = 0;

  // Tooltip state
  let hoveredNode: TreeLayoutNode | null = null;
  let tooltipX = 0;
  let tooltipY = 0;

  // Pre-computed lookup
  let nodeMap: Map<number, TreeLayoutNode> = new Map();

  onMount(async () => {
    try {
      const data = await getTreeLayout();
      setLayout(data);

      // Build node lookup map
      nodeMap = new Map(data.nodes.map(n => [n.id, n]));

      // Center the view on the tree
      const [minX, minY, maxX, maxY] = data.bounds;
      const centerX = (minX + maxX) / 2;
      const centerY = (minY + maxY) / 2;
      viewX = -centerX;
      viewY = -centerY;

      setLoading(false);
      render();
    } catch (e) {
      setError(String(e));
      setLoading(false);
    }
  });

  // Re-render when URL or highlights change
  createEffect(() => {
    void props.url;
    void props.highlightNodes;
    if (layout()) render();
  });

  function getAllocatedNodes(): Set<number> {
    return decodeTreeUrl(props.url);
  }

  function render() {
    const canvas = canvasRef;
    const data = layout();
    if (!canvas || !data) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    const allocated = getAllocatedNodes();

    // Clear
    ctx.fillStyle = "#0a0a12";
    ctx.fillRect(0, 0, w, h);

    // Apply view transform
    ctx.save();
    ctx.translate(w / 2, h / 2);
    ctx.scale(viewScale, viewScale);
    ctx.translate(viewX, viewY);

    // Build allocated edge set for fast lookup
    const allocSet = allocated;

    // Draw edges (unallocated first, then allocated on top)
    ctx.lineWidth = 1.5 / viewScale;

    // Unallocated edges
    ctx.strokeStyle = "#1a1a24";
    ctx.beginPath();
    for (const [fromId, toId] of data.edges) {
      const fromNode = nodeMap.get(fromId);
      const toNode = nodeMap.get(toId);
      if (!fromNode || !toNode) continue;
      // Skip ascendancy edges for the main view
      if (fromNode.ascendancy || toNode.ascendancy) continue;
      if (allocSet.has(fromId) && allocSet.has(toId)) continue; // draw later
      ctx.moveTo(fromNode.x, fromNode.y);
      ctx.lineTo(toNode.x, toNode.y);
    }
    ctx.stroke();

    // Allocated edges
    ctx.strokeStyle = "#c4a44e";
    ctx.lineWidth = 2.5 / viewScale;
    ctx.shadowColor = "#c4a44e";
    ctx.shadowBlur = 4 / viewScale;
    ctx.beginPath();
    for (const [fromId, toId] of data.edges) {
      if (!allocSet.has(fromId) || !allocSet.has(toId)) continue;
      const fromNode = nodeMap.get(fromId);
      const toNode = nodeMap.get(toId);
      if (!fromNode || !toNode) continue;
      if (fromNode.ascendancy || toNode.ascendancy) continue;
      ctx.moveTo(fromNode.x, fromNode.y);
      ctx.lineTo(toNode.x, toNode.y);
    }
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Draw nodes (unallocated first)
    for (const node of data.nodes) {
      if (node.ascendancy) continue; // Skip ascendancy nodes in main view
      if (allocSet.has(node.id)) continue; // Draw allocated later

      const style = getNodeStyle(node.type);
      const colors = NODE_COLORS[style];
      const radius = NODE_RADII[style];

      ctx.fillStyle = colors.fill;
      ctx.strokeStyle = colors.stroke;
      ctx.lineWidth = 1 / viewScale;
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      ctx.fill();
      if (node.type === 1 || node.type === 2) {
        ctx.stroke();
      }
    }

    // Draw allocated nodes (on top, with glow)
    for (const nodeId of allocSet) {
      const node = nodeMap.get(nodeId);
      if (!node || node.ascendancy) continue;

      const style = getNodeStyle(node.type);
      const colors = NODE_COLORS[style];
      const radius = NODE_RADII[style] * 1.2;

      ctx.shadowColor = colors.allocStroke;
      ctx.shadowBlur = 8 / viewScale;
      ctx.fillStyle = colors.allocFill;
      ctx.strokeStyle = colors.allocStroke;
      ctx.lineWidth = 1.5 / viewScale;
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
    ctx.shadowBlur = 0;

    // Draw highlighted/suggested nodes (cyan glow)
    const highlights = new Set(props.highlightNodes ?? []);
    if (highlights.size > 0) {
      for (const nodeId of highlights) {
        const node = nodeMap.get(nodeId);
        if (!node || node.ascendancy || allocSet.has(nodeId)) continue;

        const style = getNodeStyle(node.type);
        const radius = NODE_RADII[style] * 1.4;

        ctx.shadowColor = "#00e5ff";
        ctx.shadowBlur = 12 / viewScale;
        ctx.fillStyle = "#00bcd4";
        ctx.strokeStyle = "#00e5ff";
        ctx.lineWidth = 2 / viewScale;
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
      ctx.shadowBlur = 0;
    }

    // Draw tooltip if hovering
    if (hoveredNode) {
      ctx.restore();
      // Draw tooltip in screen space
      drawTooltip(ctx, hoveredNode, tooltipX, tooltipY, allocated.has(hoveredNode.id));
    } else {
      ctx.restore();
    }

    // Draw legend in bottom-left
    drawLegend(ctx, w, h, allocated.size);
  }

  function drawTooltip(
    ctx: CanvasRenderingContext2D,
    node: TreeLayoutNode,
    sx: number,
    sy: number,
    isAllocated: boolean,
  ) {
    const text = node.name || `Node ${node.id}`;
    const typeLabel = getNodeStyle(node.type).charAt(0).toUpperCase() + getNodeStyle(node.type).slice(1);
    const label = `${text} (${typeLabel})`;

    ctx.font = "13px monospace";
    const metrics = ctx.measureText(label);
    const padding = 6;
    const boxW = metrics.width + padding * 2;
    const boxH = 22;

    let tx = sx + 12;
    let ty = sy - 10;
    // Keep tooltip on screen
    const canvas = canvasRef!;
    if (tx + boxW > canvas.width) tx = sx - boxW - 12;
    if (ty < 0) ty = sy + 20;

    ctx.fillStyle = isAllocated ? "rgba(60, 50, 20, 0.95)" : "rgba(20, 20, 30, 0.95)";
    ctx.strokeStyle = isAllocated ? "#c4a44e" : "#555";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(tx, ty, boxW, boxH, 4);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = isAllocated ? "#e8d48b" : "#ccc";
    ctx.fillText(label, tx + padding, ty + 15);
  }

  function drawLegend(ctx: CanvasRenderingContext2D, _w: number, h: number, allocCount: number) {
    const text = `${allocCount} nodes allocated`;
    ctx.font = "12px monospace";
    ctx.fillStyle = "rgba(10, 10, 18, 0.8)";
    ctx.fillRect(8, h - 28, ctx.measureText(text).width + 16, 22);
    ctx.fillStyle = "#c4a44e";
    ctx.fillText(text, 16, h - 12);
  }

  // Mouse handlers
  function onWheel(e: WheelEvent) {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
    const newScale = Math.max(0.005, Math.min(0.3, viewScale * factor));

    // Zoom toward cursor position
    const canvas = canvasRef!;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    // World position under cursor before zoom
    const wx = (mx - canvas.width / 2) / viewScale - viewX;
    const wy = (my - canvas.height / 2) / viewScale - viewY;

    viewScale = newScale;

    // Adjust view so the same world point stays under cursor
    viewX = (mx - canvas.width / 2) / viewScale - wx;
    viewY = (my - canvas.height / 2) / viewScale - wy;

    render();
  }

  function onMouseDown(e: MouseEvent) {
    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragViewX = viewX;
    dragViewY = viewY;
    if (canvasRef) canvasRef.style.cursor = "grabbing";
  }

  function onMouseMove(e: MouseEvent) {
    const canvas = canvasRef;
    if (!canvas) return;

    if (isDragging) {
      const dx = e.clientX - dragStartX;
      const dy = e.clientY - dragStartY;
      viewX = dragViewX + dx / viewScale;
      viewY = dragViewY + dy / viewScale;
      render();
      return;
    }

    // Hit-test for tooltip
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    // Convert screen to world coords
    const wx = (mx - canvas.width / 2) / viewScale - viewX;
    const wy = (my - canvas.height / 2) / viewScale - viewY;

    // Find closest node within threshold
    const data = layout();
    if (!data) return;

    const threshold = 15 / viewScale; // 15 screen pixels
    let closest: TreeLayoutNode | null = null;
    let closestDist = threshold * threshold;

    for (const node of data.nodes) {
      if (node.ascendancy) continue;
      const dx = node.x - wx;
      const dy = node.y - wy;
      const dist = dx * dx + dy * dy;
      if (dist < closestDist) {
        closestDist = dist;
        closest = node;
      }
    }

    if (closest !== hoveredNode) {
      hoveredNode = closest;
      tooltipX = mx;
      tooltipY = my;
      canvas.style.cursor = closest ? "pointer" : "grab";
      render();
    }
  }

  function onMouseUp() {
    isDragging = false;
    if (canvasRef) canvasRef.style.cursor = hoveredNode ? "pointer" : "grab";
  }

  function onMouseLeave() {
    isDragging = false;
    hoveredNode = null;
    if (canvasRef) canvasRef.style.cursor = "grab";
    render();
  }

  // Canvas resize
  function updateCanvasSize() {
    const canvas = canvasRef;
    if (!canvas) return;
    const parent = canvas.parentElement;
    if (!parent) return;
    const w = parent.clientWidth;
    const h = props.height || 550;
    canvas.width = w;
    canvas.height = h;
    render();
  }

  onMount(() => {
    window.addEventListener("resize", updateCanvasSize);
    // Initial size after a tick
    setTimeout(updateCanvasSize, 50);
  });

  onCleanup(() => {
    window.removeEventListener("resize", updateCanvasSize);
  });

  return (
    <div class="passive-tree-canvas-container">
      {loading() && <div class="tree-canvas-loading"><span class="spinner" /> Loading passive tree...</div>}
      {error() && <div class="error-toast">{error()}</div>}
      <canvas
        ref={canvasRef}
        class="passive-tree-canvas"
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseLeave}
      />
    </div>
  );
}
