import { useSlowLoadHint } from "../lib/useSlowLoadHint.js";
import styles from "./LoadingHint.module.css";

export default function LoadingHint({ label }) {
  const showSlowHint = useSlowLoadHint(true);

  return (
    <p className={styles.loading}>
      {label}
      {showSlowHint && (
        <span className={styles.slowHint}>
          {" "}Waking up the server — this can take up to a minute on the free tier.
        </span>
      )}
    </p>
  );
}
