import { Link } from "react-router-dom";
import styles from "./RingList.module.css";

export default function RingList({ rings, selectedId }) {
  return (
    <ul className={styles.list}>
      {rings.map((r) => (
        <li key={r.ring_id} className={r.ring_id === selectedId ? styles.active : undefined}>
          <Link to={`/rings/${r.ring_id}`} className={styles.row}>
            <span className="mono">{r.ring_id}</span>
            <span className={styles.meta}>
              {r.size} accts · {Math.round(r.fraud_rate * 100)}% fraud · score {r.score.toFixed(2)}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
