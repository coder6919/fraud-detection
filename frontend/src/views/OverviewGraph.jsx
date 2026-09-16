import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import ForceGraph from "../components/graph/ForceGraph.jsx";
import EdgeLegend from "../components/graph/EdgeLegend.jsx";
import LoadingHint from "../components/LoadingHint.jsx";
import RingList from "../components/RingList.jsx";
import { getGraph, listRings } from "../lib/api.js";
import styles from "./OverviewGraph.module.css";

export default function OverviewGraph() {
  const navigate = useNavigate();
  const [rings, setRings] = useState([]);
  const [graph, setGraph] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([listRings({ minScore: 0.3, limit: 30 }), getGraph({ minScore: 0.3, limit: 250 })])
      .then(([ringsRes, graphRes]) => {
        setRings(ringsRes.rings);
        setGraph(graphRes);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Flagged rings</h1>
        <p className={styles.muted}>
          Candidate fraud rings from shared-identifier clustering, ranked by score. Click a node or a ring to
          open its detail view.
        </p>
      </header>

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.body}>
        <div className={styles.graphPane}>
          {graph ? (
            <>
              <ForceGraph
                nodes={graph.nodes}
                edges={graph.edges}
                width={780}
                height={560}
                onNodeClick={(id) => navigate(`/account/${id}`)}
              />
              <EdgeLegend />
            </>
          ) : (
            <LoadingHint label="Loading graph..." />
          )}
        </div>
        <aside className={styles.sidebar}>
          <h2 className={styles.sectionTitle}>Top {rings.length} rings</h2>
          <RingList rings={rings} />
        </aside>
      </div>
    </div>
  );
}
