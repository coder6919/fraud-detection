import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import LoadingHint from "../components/LoadingHint.jsx";
import { getScoreSamples, scoreFields, scoreSample } from "../lib/api.js";
import styles from "./ScoreView.module.css";

// Static, since these mirror the fixed IEEE-CIS schema the backend trains
// on (pipeline/baseline_rf.py) — only which of these count as "top fields"
// changes run to run, and that ordering comes from the API.
const FIELD_META = {
  TransactionAmt: { label: "Transaction amount ($)", type: "number", step: "0.01", min: 0 },
  hour_of_day: { label: "Hour of day", type: "number", step: 1, min: 0, max: 23 },
  day_of_week: { label: "Day of week (0 = Mon)", type: "number", step: 1, min: 0, max: 6 },
  ProductCD: { label: "Product code", type: "select", options: ["W", "C", "R", "H", "S"] },
  card4: { label: "Card network", type: "select", options: ["visa", "mastercard", "american express", "discover"] },
  card6: { label: "Card type", type: "select", options: ["credit", "debit"] },
  P_emaildomain: {
    label: "Purchaser email domain", type: "select",
    options: ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "anonymous.com"],
  },
  R_emaildomain: {
    label: "Recipient email domain", type: "select",
    options: ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "anonymous.com"],
  },
  DeviceType: { label: "Device type", type: "select", options: ["mobile", "desktop"] },
};

export default function ScoreView() {
  const [searchParams] = useSearchParams();
  const initialMode = searchParams.get("mode") === "own" ? "own" : "sample";
  const [mode, setMode] = useState(initialMode);
  const [samples, setSamples] = useState(null);
  const [topFields, setTopFields] = useState([]);
  const [loadError, setLoadError] = useState(null);

  const [selectedSampleId, setSelectedSampleId] = useState(null);
  const [fields, setFields] = useState({});

  const [result, setResult] = useState(null);
  const [scoring, setScoring] = useState(false);
  const [scoreError, setScoreError] = useState(null);

  useEffect(() => {
    getScoreSamples()
      .then((res) => {
        setSamples(res.samples);
        setTopFields(res.top_fields);
      })
      .catch((e) => setLoadError(e.message));
  }, []);

  function switchMode(next) {
    setMode(next);
    setResult(null);
    setScoreError(null);
  }

  function handleSampleClick(sample) {
    setSelectedSampleId(sample.sample_id);
    setResult(null);
    setScoreError(null);
    setScoring(true);
    scoreSample(sample.sample_id)
      .then(setResult)
      .catch((e) => setScoreError(e.message))
      .finally(() => setScoring(false));
  }

  function handleFormSubmit(e) {
    e.preventDefault();
    setResult(null);
    setScoreError(null);
    setScoring(true);
    scoreFields(fields)
      .then(setResult)
      .catch((e) => setScoreError(e.message))
      .finally(() => setScoring(false));
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Score a transaction</h1>
        <p className={styles.muted}>
          Serves the same baseline Random Forest used for the graph-vs-baseline comparison — no new model.
          Try a real held-out transaction, or build a simplified one, and see whether it also connects to a
          known ring.
        </p>
      </header>

      <div className={styles.tabs}>
        <button
          className={mode === "sample" ? styles.tabActive : styles.tab}
          onClick={() => switchMode("sample")}
        >
          Try a sample
        </button>
        <button
          className={mode === "own" ? styles.tabActive : styles.tab}
          onClick={() => switchMode("own")}
        >
          Build your own
        </button>
      </div>

      {loadError && <p className={styles.error}>Couldn't load samples: {loadError}</p>}

      {mode === "sample" && (
        <section>
          {!samples && !loadError && <LoadingHint label="Loading sample transactions..." />}
          {samples && (
            <ul className={styles.sampleList}>
              {samples.map((s) => (
                <li key={s.sample_id}>
                  <button
                    className={s.sample_id === selectedSampleId ? styles.sampleCardActive : styles.sampleCard}
                    onClick={() => handleSampleClick(s)}
                  >
                    <span>{s.label}</span>
                    {s.matched_ring_id && <span className={styles.ringBadge}>ring-linked</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {mode === "own" && (
        <section>
          <p className={styles.muted}>
            Simplified — only the {topFields.length || 8} fields the model relies on most. Everything else is
            filled with the dataset median/mode behind the scenes. This mode never checks for ring connections:
            it doesn't collect the raw device/card fingerprint fields ring-matching needs (see "Try a sample"
            for that).
          </p>
          <form className={styles.form} onSubmit={handleFormSubmit}>
            <div className={styles.formGrid}>
              {topFields.map((field) => (
                <FieldInput
                  key={field}
                  field={field}
                  value={fields[field] ?? ""}
                  onChange={(value) => setFields((f) => ({ ...f, [field]: value }))}
                />
              ))}
            </div>
            <button className={styles.submit} type="submit" disabled={scoring || topFields.length === 0}>
              {scoring ? "Scoring..." : "Score this transaction"}
            </button>
          </form>
        </section>
      )}

      {scoreError && <p className={styles.error}>{scoreError}</p>}
      {scoring && mode === "sample" && <LoadingHint label="Scoring..." />}
      {result && <ResultPanel result={result} />}
    </div>
  );
}

function FieldInput({ field, value, onChange }) {
  const meta = FIELD_META[field] ?? { label: field, type: "text" };

  return (
    <label className={styles.field}>
      <span className={styles.fieldLabel}>{meta.label}</span>
      {meta.type === "select" ? (
        <select className={styles.input} value={value} onChange={(e) => onChange(e.target.value)}>
          <option value="">(use dataset default)</option>
          {meta.options.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      ) : (
        <input
          className={styles.input}
          type="number"
          step={meta.step}
          min={meta.min}
          max={meta.max}
          placeholder="(use dataset default)"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
    </label>
  );
}

function ResultPanel({ result }) {
  const pct = Math.round(result.fraud_probability * 100);

  return (
    <div className={styles.resultPanel}>
      <div className={styles.resultHeadline}>
        <span className={styles.probability}>{pct}%</span>
        <span className={styles.probabilityLabel}>fraud probability</span>
        <span className={result.flagged ? styles.flagBadge : styles.okBadge}>
          {result.flagged ? "Flagged" : "Not flagged"}
        </span>
      </div>

      {result.matched_ring_id && result.ring_context ? (
        <p className={styles.ringNote}>
          Linked to{" "}
          <Link to={`/rings/${result.matched_ring_id}`} className="mono">{result.matched_ring_id}</Link>
          {" "}— {result.ring_context.size} accounts, {Math.round(result.ring_context.fraud_rate * 100)}% fraud rate,
          ring score {result.ring_context.score.toFixed(2)}.
        </p>
      ) : (
        <p className={styles.muted}>{result.ring_note}</p>
      )}
    </div>
  );
}
