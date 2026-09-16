import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ForceGraph from "../components/graph/ForceGraph.jsx";
import LoadingHint from "../components/LoadingHint.jsx";
import { getAccount, getGraph } from "../lib/api.js";
import styles from "./AccountView.module.css";

export default function AccountView() {
  const { accountId } = useParams();
  const navigate = useNavigate();
  const [account, setAccount] = useState(null);
  const [graph, setGraph] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setAccount(null);
    setGraph(null);
    setError(null);
    getAccount(accountId)
      .then(setAccount)
      .catch((e) => setError(e.message));
    getGraph({ accountId, hops: 1, limit: 150 })
      .then(setGraph)
      .catch(() => {});
  }, [accountId]);

  if (error) {
    return (
      <div className={styles.page}>
        <p className={styles.error}>Couldn't load account {accountId}: {error}</p>
        <Link to="/">Back to overview</Link>
      </div>
    );
  }

  if (!account) {
    return <div className={styles.page}><LoadingHint label={`Loading ${accountId}...`} /></div>;
  }

  const { node, ring } = account;

  return (
    <div className={styles.page}>
      <Link to="/" className={styles.back}>&larr; Overview</Link>
      <h1 className={styles.title}>{node.id}</h1>

      <dl className={styles.stats}>
        <Stat label="Transactions" value={node.num_transactions} />
        <Stat label="Fraud rate" value={`${Math.round(node.fraud_rate * 100)}%`} accent={node.fraud_rate > 0.3} />
        <Stat label="Total amount" value={`$${node.total_amount.toFixed(2)}`} />
        <Stat label="Primary email domain" value={node.primary_email ?? "—"} />
        <Stat label="Device type" value={node.device_type ?? "—"} />
      </dl>

      {ring ? (
        <p className={styles.ringNote}>
          Member of{" "}
          <Link to={`/rings/${ring.ring_id}`} className="mono">{ring.ring_id}</Link>
          {" "}— {ring.size} accounts, score {ring.score.toFixed(2)}.
        </p>
      ) : (
        <p className={styles.muted}>Not part of any flagged ring.</p>
      )}

      <div className={styles.graphPane}>
        <h2 className={styles.sectionTitle}>Connections</h2>
        {graph && graph.nodes.length > 1 ? (
          <ForceGraph
            nodes={graph.nodes}
            edges={graph.edges}
            width={720}
            height={440}
            selectedId={node.id}
            onNodeClick={(id) => id !== node.id && navigate(`/account/${id}`)}
          />
        ) : (
          <p className={styles.muted}>No shared-identifier connections to other accounts.</p>
        )}
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
