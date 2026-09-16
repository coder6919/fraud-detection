import { useEffect, useRef, useState } from "react";
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY } from "d3-force";
import GraphNode, { nodeRadius } from "./GraphNode.jsx";
import GraphEdge from "./GraphEdge.jsx";

const MIN_ZOOM = 0.3;
const MAX_ZOOM = 3;
const SETTLE_TICKS = 300;
const DRAG_TICKS_PER_MOVE = 3;
// Real mouse/trackpad clicks routinely include a few pixels of incidental
// movement between press and release — too tight a threshold here makes
// ordinary clicks misfire as drags and silently skip navigation.
const CLICK_SLOP_PX = 8;

// Simulation ticking is driven synchronously (sim.tick()) rather than d3-force's
// own internal rAF-scheduled timer. The timer-driven version stalls badly (or
// never fires at all) in a backgrounded/inactive tab, since it's gated on
// requestAnimationFrame — synchronous stepping makes layout deterministic and
// independent of the tab's real frame rate.
export default function ForceGraph({ nodes, edges, width = 720, height = 520, onNodeClick, selectedId }) {
  const [, setRenderTick] = useState(0);
  const [hoveredId, setHoveredId] = useState(null);
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });

  const simNodesRef = useRef([]);
  const simEdgesRef = useRef([]);
  const simRef = useRef(null);
  const svgRef = useRef(null);
  const dragRef = useRef(null); // { id, pointerId }
  const panRef = useRef(null); // { startX, startY, viewX, viewY }
  const userInteractedRef = useRef(false);

  useEffect(() => {
    const simNodes = nodes.map((n) => ({ ...n }));
    const idSet = new Set(simNodes.map((n) => n.id));
    const simEdges = edges
      .filter((e) => idSet.has(e.source) && idSet.has(e.target))
      .map((e) => ({ ...e }));

    const sim = forceSimulation(simNodes)
      .force(
        "link",
        forceLink(simEdges)
          .id((d) => d.id)
          .distance((d) => 60 - Math.min(30, d.weight * 20))
          .strength((d) => Math.min(0.9, 0.15 + d.weight * 0.1))
      )
      .force("charge", forceManyBody().strength(-90))
      .force("collide", forceCollide((d) => nodeRadius(d) + 6))
      .force("x", forceX(width / 2).strength(0.03))
      .force("y", forceY(height / 2).strength(0.03))
      .force("center", forceCenter(width / 2, height / 2))
      .stop();

    for (let i = 0; i < SETTLE_TICKS; i++) sim.tick();

    simNodesRef.current = simNodes;
    simEdgesRef.current = simEdges;
    simRef.current = sim;
    userInteractedRef.current = false;

    fitToContent(simNodes, width, height, userInteractedRef, setView);
    setRenderTick((t) => t + 1);

    return () => sim.stop();
  }, [nodes, edges, width, height]);

  function handleNodePointerDown(node) {
    return (e) => {
      e.stopPropagation();
      e.currentTarget.setPointerCapture(e.pointerId);
      userInteractedRef.current = true;
      dragRef.current = { id: node.id, pointerId: e.pointerId, startX: e.clientX, startY: e.clientY, moved: false };
      node.fx = node.x;
      node.fy = node.y;
    };
  }

  function toLocalPoint(e) {
    const rect = svgRef.current.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left - view.x) / view.k,
      y: (e.clientY - rect.top - view.y) / view.k,
    };
  }

  function handlePointerMove(e) {
    if (dragRef.current) {
      const drag = dragRef.current;
      if (!drag.moved && Math.hypot(e.clientX - drag.startX, e.clientY - drag.startY) > CLICK_SLOP_PX) {
        drag.moved = true;
      }
      const node = simNodesRef.current.find((n) => n.id === drag.id);
      if (node) {
        const p = toLocalPoint(e);
        node.fx = p.x;
        node.fy = p.y;
        const sim = simRef.current;
        if (sim) {
          sim.alpha(Math.max(sim.alpha(), 0.4));
          for (let i = 0; i < DRAG_TICKS_PER_MOVE; i++) sim.tick();
        }
        setRenderTick((t) => t + 1);
      }
    } else if (panRef.current) {
      const dx = e.clientX - panRef.current.startX;
      const dy = e.clientY - panRef.current.startY;
      setView((v) => ({ ...v, x: panRef.current.viewX + dx, y: panRef.current.viewY + dy }));
    }
  }

  function handlePointerUp() {
    if (dragRef.current) {
      const drag = dragRef.current;
      const node = simNodesRef.current.find((n) => n.id === drag.id);
      if (node) {
        node.fx = null;
        node.fy = null;
        const sim = simRef.current;
        if (sim) {
          for (let i = 0; i < 30; i++) sim.tick();
        }
        setRenderTick((t) => t + 1);
      }
      dragRef.current = null;
      if (!drag.moved) onNodeClick?.(drag.id);
    }
    panRef.current = null;
  }

  function handleBackgroundPointerDown(e) {
    userInteractedRef.current = true;
    panRef.current = { startX: e.clientX, startY: e.clientY, viewX: view.x, viewY: view.y };
  }

  function handleWheel(e) {
    e.preventDefault();
    userInteractedRef.current = true;
    const delta = -e.deltaY * 0.0012;
    setView((v) => ({ ...v, k: Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, v.k + delta)) }));
  }

  const simNodes = simNodesRef.current;
  const simEdges = simEdgesRef.current;
  const simNodeById = new Map(simNodes.map((n) => [n.id, n]));

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerUp}
      onWheel={handleWheel}
      style={{ background: "var(--color-paper)", touchAction: "none" }}
    >
      <rect
        x={0} y={0} width={width} height={height}
        fill="transparent"
        onPointerDown={handleBackgroundPointerDown}
      />
      <g transform={`translate(${view.x}, ${view.y}) scale(${view.k})`}>
        {simEdges.map((e, i) => {
          const source = typeof e.source === "object" ? e.source : simNodeById.get(e.source);
          const target = typeof e.target === "object" ? e.target : simNodeById.get(e.target);
          if (!source || !target) return null;
          return <GraphEdge key={i} source={source} target={target} evidence={e.evidence} />;
        })}
        {simNodes.map((node) => (
          <GraphNode
            key={node.id}
            node={node}
            hovered={hoveredId === node.id}
            selected={selectedId === node.id}
            onPointerDown={handleNodePointerDown(node)}
            onEnter={() => setHoveredId(node.id)}
            onLeave={() => setHoveredId(null)}
          />
        ))}
      </g>
      {hoveredId && simNodeById.get(hoveredId) && (
        <NodeTooltip node={simNodeById.get(hoveredId)} view={view} />
      )}
    </svg>
  );
}

function fitToContent(simNodes, width, height, userInteractedRef, setView) {
  if (userInteractedRef.current || simNodes.length === 0) return;

  const xs = simNodes.map((n) => n.x);
  const ys = simNodes.map((n) => n.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const bboxW = Math.max(1, maxX - minX);
  const bboxH = Math.max(1, maxY - minY);
  const padding = 64;

  const k = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.min((width - padding) / bboxW, (height - padding) / bboxH, 1.6)));
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;

  setView({ x: width / 2 - cx * k, y: height / 2 - cy * k, k });
}

function NodeTooltip({ node, view }) {
  const x = node.x * view.k + view.x + 14;
  const y = node.y * view.k + view.y - 10;
  return (
    <g transform={`translate(${x}, ${y})`} pointerEvents="none">
      <rect
        x={0} y={-14} width={168} height={48} rx={6}
        fill="var(--color-graphite)"
        opacity={0.95}
      />
      <text x={8} y={2} fill="var(--color-on-graphite)" fontSize="11" fontFamily="var(--font-mono)">
        {node.id}
      </text>
      <text x={8} y={16} fill="var(--color-on-graphite-muted)" fontSize="10">
        {node.num_transactions} txn · fraud {Math.round(node.fraud_rate * 100)}%
      </text>
    </g>
  );
}
