import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ForceGraph from "../components/graph/ForceGraph.jsx";
import EdgeLegend from "../components/graph/EdgeLegend.jsx";
import LoadingHint from "../components/LoadingHint.jsx";
import { getRing } from "../lib/api.js";
import styles from "./RingDetailView.module.css";

export default function RingDetailView() {
  const { ringId } = useParams();
  const navigate = useNavigate();
  const [ring, setRing] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setRing(null);
    setError(null);
    getRing(ringId).then(setRing).catch((e) => setError(e.message));
  }, [ringId]);

  if (error) {
    return (
      <div className={styles.page}>
        <p className={styles.error}>Couldn't load {ringId}: {error}</p>
        <Link to="/">Back to overview</Link>
      </div>
    );
  }

  if (!ring) {
    return <div className={styles.page}><LoadingHint label={`Loading ${ringId}...`} /></div>;
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <Link to="/" className={styles.back}>&larr; Overview</Link>
          <h1 className={styles.title}>{ring.ring_id}</h1>
        </div>
        <dl className={styles.stats}>
          <Stat label="Accounts" value={ring.size} />
          <Stat label="Density" value={ring.density.toFixed(2)} />
          <Stat label="Fraud rate" value={`${Math.round(ring.fraud_rate * 100)}%`} accent={ring.fraud_rate > 0.3} />
          <Stat label="Creation tightness" value={ring.creation_tightness.toFixed(2)} />
          <Stat label="Score" value={ring.score.toFixed(2)} accent />
          {ring.oversized && <Stat label="Note" value="oversized cluster" />}
        </dl>
      </header>

      <div className={styles.body}>
        <div className={styles.graphPane}>
          <ForceGraph
            nodes={ring.graph.nodes}
            edges={ring.graph.edges}
            width={760}
            height={520}
            onNodeClick={(id) => navigate(`/account/${id}`)}
          />
          <EdgeLegend />
        </div>

        <aside className={styles.sidebar}>
          <h2 className={styles.sectionTitle}>Hub accounts</h2>
          <p className={styles.muted}>Highest betweenness centrality — likely coordinating identities.</p>
          <ul className={styles.hubList}>
            {ring.hub_accounts.map((h) => (
              <li key={h.account_id}>
                <Link to={`/account/${h.account_id}`} className="mono">{h.account_id}</Link>
                <span className={styles.muted}> · centrality {h.centrality.toFixed(3)}</span>
              </li>
            ))}
          </ul>

          <h2 className={styles.sectionTitle}>Members ({ring.graph.nodes.length})</h2>
          <ul className={styles.memberList}>
            {ring.graph.nodes.map((n) => (
              <li key={n.id}>
                <Link to={`/account/${n.id}`} className="mono">{n.id}</Link>
                <span className={styles.muted}> · {n.num_transactions} txn</span>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div className={styles.stat}>
      <dt className={styles.statLabel}>{label}</dt>
      <dd className={`${styles.statValue} ${accent ? styles.statAccent : ""}`}>{value}</dd>
    </div>
  );
}
