import { EVIDENCE_TYPES } from "../../lib/evidence.js";
import styles from "./EdgeLegend.module.css";

const ENTRIES = [
  ["DeviceInfo", EVIDENCE_TYPES.DeviceInfo],
  ["id_31", EVIDENCE_TYPES.id_31],
  ["P_emaildomain", EVIDENCE_TYPES.P_emaildomain],
  ["addr1", EVIDENCE_TYPES.addr1],
];

export default function EdgeLegend() {
  return (
    <ul className={styles.legend}>
      {ENTRIES.map(([field, style]) => (
        <li key={field} className={styles.item}>
          <svg width="24" height="8" aria-hidden="true">
            <line
              x1="0" y1="4" x2="24" y2="4"
              stroke="var(--color-rule-2)"
              strokeWidth={style.strokeWidth}
              strokeDasharray={style.dash}
            />
          </svg>
          <span>{style.label}</span>
        </li>
      ))}
    </ul>
  );
}
