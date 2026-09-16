"""One-off CLI: run the pipeline and persist artifacts for the API to serve.

    python -m scripts.build_graph --sample-frac 0.4

Writes graph_store/graph.pkl (NetworkX graph) and graph_store/rings.json
(scored rings, without the full member lists duplicated per-node) so the API
never rebuilds anything per-request.
"""
import argparse
import json

from pipeline.config import GRAPH_STORE_DIR
from pipeline.graph_build import build_graph, save_graph
from pipeline.ingest import load_clean
from pipeline.scoring import score_clusters

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-frac", type=float, default=0.4)
    parser.add_argument("--min-ring-size", type=int, default=3)
    args = parser.parse_args()

    print(f"loading + cleaning (sample_frac={args.sample_frac})...")
    df = load_clean(sample_frac=args.sample_frac)
    print(f"  {len(df):,} transactions")

    print("building graph...")
    graph = build_graph(df)
    print(f"  {graph.number_of_nodes():,} nodes, {graph.number_of_edges():,} edges")

    print("scoring rings...")
    rings = score_clusters(graph, min_size=args.min_ring_size)
    print(f"  {len(rings):,} candidate rings")

    GRAPH_STORE_DIR.mkdir(exist_ok=True)
    save_graph(graph)
    with open(GRAPH_STORE_DIR / "rings.json", "w") as f:
        json.dump(rings, f)

    print(f"\nsaved graph.pkl + rings.json to {GRAPH_STORE_DIR}")
