
"""Structure alone isn't enough evidence (a family sharing a device forms a
small dense cluster too) — score combines density, the cluster's actual
fraud-transaction rate, and how tightly the accounts were created in time.
Oversized clusters are capped/flagged rather than trusted as one ring, since
they're usually identifier noise that slipped past graph construction.

Run standalone for a sanity check:
    python -m pipeline.scoring --sample-frac 0.15
"""
import argparse
import statistics

import networkx as nx
import pandas as pd

from pipeline.centrality import hub_accounts
from pipeline.community import communities_by_size, detect_communities
from pipeline.graph_build import build_graph
from pipeline.ingest import load_clean

OVERSIZED_SIZE = 50
OVERSIZED_PENALTY = 0.5  # multiplicative penalty applied to the raw score

# Fraud rate dominates: on the full dataset, density is ~1.0 for nearly every
# candidate cluster (Louvain tends to produce near-complete small subgraphs
# here), so it contributes almost no ranking signal by itself. Creation-time
# tightness is real evidence but noisy on its own — weighted too heavily it
# surfaces date-coincidental clusters with zero actual fraud ahead of real
# rings. Empirically (see PROGRESS.md), this weighting took top-ring precision
# from ~6% to 100% at a 0.7 score threshold on the full dataset.
WEIGHTS = {"density": 0.15, "fraud_rate": 0.70, "tightness": 0.15}


def _density(graph: nx.Graph, members: list[str]) -> float:
    n = len(members)
    if n < 2:
        return 0.0
    possible = n * (n - 1) / 2
    actual = graph.subgraph(members).number_of_edges()
    return actual / possible


def _fraud_rate(graph: nx.Graph, members: list[str]) -> float:
    total_txn = sum(graph.nodes[m]["num_transactions"] for m in members)
    if total_txn == 0:
        return 0.0
    fraud_txn = sum(graph.nodes[m]["num_transactions"] * graph.nodes[m]["fraud_rate"] for m in members)
    return fraud_txn / total_txn


def _creation_tightness(graph: nx.Graph, members: list[str], global_std: float) -> float:
    first_seen = [graph.nodes[m]["first_seen"] for m in members]
    if len(first_seen) < 2 or global_std == 0:
        return 1.0
    cluster_std = statistics.pstdev(first_seen)
    return 1.0 - min(1.0, cluster_std / global_std)


def _normalize(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def score_clusters(graph: nx.Graph, min_size: int = 3, top_n_hubs: int = 3) -> list[dict]:
    partition = detect_communities(graph)
    clusters = communities_by_size(partition, min_size=min_size)

    all_first_seen = [d["first_seen"] for _, d in graph.nodes(data=True)]
    global_std = statistics.pstdev(all_first_seen) if len(all_first_seen) > 1 else 0.0

    raw = []
    for members in clusters:
        raw.append({
            "members": members,
            "size": len(members),
            "density": _density(graph, members),
            "fraud_rate": _fraud_rate(graph, members),
            "tightness": _creation_tightness(graph, members, global_std),
        })

    density_n = _normalize([r["density"] for r in raw])
    fraud_n = _normalize([r["fraud_rate"] for r in raw])
    tight_n = _normalize([r["tightness"] for r in raw])

    results = []
    for i, r in enumerate(raw):
        score = (
            WEIGHTS["density"] * density_n[i]
            + WEIGHTS["fraud_rate"] * fraud_n[i]
            + WEIGHTS["tightness"] * tight_n[i]
        )
        oversized = r["size"] > OVERSIZED_SIZE
        if oversized:
            score *= OVERSIZED_PENALTY

        results.append({
            "ring_id": f"ring_{i:04d}",
            "size": r["size"],
            "density": round(r["density"], 4),
            "fraud_rate": round(r["fraud_rate"], 4),
            "creation_tightness": round(r["tightness"], 4),
            "score": round(score, 4),
            "oversized": oversized,
            "members": r["members"],
            "hub_accounts": hub_accounts(graph, r["members"], top_n=top_n_hubs),
        })

    return sorted(results, key=lambda r: r["score"], reverse=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-frac", type=float, default=0.15)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    df = load_clean(sample_frac=args.sample_frac)
    graph = build_graph(df)
    rings = score_clusters(graph)

    print(f"\nscored {len(rings)} candidate rings\n")
    print(f"{'ring_id':<10} {'size':>5} {'density':>8} {'fraud_rate':>11} {'tightness':>10} {'score':>7}  oversized")
    for r in rings[: args.top]:
        print(
            f"{r['ring_id']:<10} {r['size']:>5} {r['density']:>8.3f} {r['fraud_rate']:>11.3f} "
            f"{r['creation_tightness']:>10.3f} {r['score']:>7.3f}  {r['oversized']}"
        )

    top = rings[0]
    print(f"\ntop ring hub accounts: {top['hub_accounts']}")
