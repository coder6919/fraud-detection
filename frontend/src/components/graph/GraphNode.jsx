const MIN_R = 5;
const MAX_R = 13;

export function nodeRadius(node) {
  const t = Math.min(node.num_transactions ?? 1, 12);
  return MIN_R + (t / 12) * (MAX_R - MIN_R);
}

export default function GraphNode({ node, hovered, selected, onPointerDown, onEnter, onLeave }) {
  const flagged = node.ring_id != null;
  const r = nodeRadius(node) * (selected ? 1.25 : hovered ? 1.12 : 1);

  const fill = flagged ? "var(--color-accent-soft)" : "var(--color-paper-2)";
  const stroke = flagged ? "var(--color-accent)" : "var(--color-rule-2)";
  const strokeWidth = flagged ? 1.5 + node.fraud_rate * 2 : 1;

  return (
    <g
      transform={`translate(${node.x}, ${node.y})`}
      onPointerDown={onPointerDown}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      style={{ cursor: "grab" }}
    >
      <circle r={r} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
      {selected && <circle r={r + 4} fill="none" stroke="var(--color-ink)" strokeWidth={1} opacity={0.5} />}
    </g>
  );
}
