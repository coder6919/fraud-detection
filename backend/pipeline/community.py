
"""Each community is a *candidate* ring — scoring.py decides which ones actually
look like fraud rather than a legitimate dense cluster (e.g. a family sharing
a device) or leftover common-identifier noise.

Run standalone for a sanity check:
    python -m pipeline.community --sample-frac 0.15
"""
import argparse
from collections import Counter

import community as community_louvain
import networkx as nx

from pipeline.graph_build import build_graph, load_graph, save_graph
from pipeline.ingest import load_clean


def detect_communities(graph: nx.Graph) -> dict:
    """Returns {node: community_id}. Isolated nodes each become their own community."""
    if graph.number_of_edges() == 0:
        return {n: i for i, n in enumerate(graph.nodes())}
    return community_louvain.best_partition(graph, weight="weight", random_state=42)


def communities_by_size(partition: dict, min_size: int = 2) -> list[list[str]]:
    groups: dict[int, list[str]] = {}
    for node, comm_id in partition.items():
        groups.setdefault(comm_id, []).append(node)
    return sorted((members for members in groups.values() if len(members) >= min_size), key=len, reverse=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-frac", type=float, default=0.15)
    args = parser.parse_args()

    df = load_clean(sample_frac=args.sample_frac)
    graph = build_graph(df)

    partition = detect_communities(graph)
    clusters = communities_by_size(partition, min_size=2)

    sizes = [len(c) for c in clusters]
    print(f"\ncandidate clusters (size >= 2): {len(clusters):,}")
    print(f"size distribution: min={min(sizes)}, median={sorted(sizes)[len(sizes)//2]}, max={max(sizes)}")
    print("size histogram (bucketed):")
    buckets = Counter()
    for s in sizes:
        if s <= 5:
            buckets[str(s)] += 1
        elif s <= 10:
            buckets["6-10"] += 1
        elif s <= 25:
            buckets["11-25"] += 1
        elif s <= 50:
            buckets["26-50"] += 1
        else:
            buckets["50+"] += 1
    for k in sorted(buckets, key=lambda k: (len(k), k)):
        print(f"  {k}: {buckets[k]}")

    print("\nlargest 5 clusters (size, avg internal fraud_rate):")
    for c in clusters[:5]:
        fraud_rates = [graph.nodes[n]["fraud_rate"] for n in c]
        print(f"  size={len(c)}, avg_fraud_rate={sum(fraud_rates)/len(fraud_rates):.3f}")

    modularity = community_louvain.modularity(partition, graph, weight="weight")
    print(f"\nmodularity: {modularity:.4f}")
