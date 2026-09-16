import { EVIDENCE_TYPES, primaryEvidenceField } from "../../lib/evidence.js";

export default function GraphEdge({ source, target, evidence }) {
  const field = primaryEvidenceField(evidence);
  const style = EVIDENCE_TYPES[field] ?? { dash: "0", strokeWidth: 1 };

  return (
    <line
      x1={source.x}
      y1={source.y}
      x2={target.x}
      y2={target.y}
      stroke="var(--color-rule-2)"
      strokeWidth={style.strokeWidth}
      strokeDasharray={style.dash}
      opacity={0.75}
    />
  );
}
