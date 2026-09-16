
"""Ring-level:
  precision = of flagged rings, fraction with a majority-fraud transaction mix
  recall    = fraction of all fraud transactions that fall inside a flagged ring
              (fraud with no shared identifiers to any other account is outside
              this approach's reach by design — reported separately, not hidden)

Baseline comparison: the RF's precision/recall at a flag-count matched to how
many transactions the flagged rings cover, so the two numbers describe
"flagging about the same number of transactions" rather than different scales.

Run standalone:
    python -m pipeline.evaluate --sample-frac 0.15
"""
import argparse

from pipeline.baseline_rf import train_baseline
from pipeline.graph_build import build_graph
from pipeline.ingest import load_clean
from pipeline.scoring import score_clusters

DEFAULT_SCORE_THRESHOLD = 0.5


def ring_level_metrics(df, graph, rings, score_threshold: float = DEFAULT_SCORE_THRESHOLD) -> dict:
    total_fraud_txn = int(df["isFraud"].sum())

    flagged = [r for r in rings if r["score"] >= score_threshold]
    if not flagged:
        return {
            "flagged_rings": 0, "precision": None, "recall": None,
            "flagged_txn_count": 0, "fraud_txn_in_flagged": 0, "total_fraud_txn": total_fraud_txn,
        }

    precision = sum(1 for r in flagged if r["fraud_rate"] > 0.5) / len(flagged)

    flagged_accounts = set()
    for r in flagged:
        flagged_accounts.update(r["members"])

    flagged_txn_count = sum(graph.nodes[a]["num_transactions"] for a in flagged_accounts)
    fraud_txn_in_flagged = sum(
        graph.nodes[a]["num_transactions"] * graph.nodes[a]["fraud_rate"] for a in flagged_accounts
    )
    recall = fraud_txn_in_flagged / total_fraud_txn if total_fraud_txn else 0.0

    isolated_fraud_txn = total_fraud_txn - fraud_txn_in_flagged

    return {
        "flagged_rings": len(flagged),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "flagged_txn_count": flagged_txn_count,
        "fraud_txn_in_flagged": round(fraud_txn_in_flagged, 1),
        "total_fraud_txn": total_fraud_txn,
        "isolated_fraud_txn_missed_by_design": round(isolated_fraud_txn, 1),
    }


def baseline_metrics_at_matched_flag_count(df, flag_count: int) -> dict:
    clf, X_test, y_test, proba = train_baseline(df)
    k = min(flag_count, len(proba))
    if k == 0:
        return {"precision": None, "recall": None, "flagged_txn_count": 0}

    top_k_idx = proba.argsort()[::-1][:k]
    precision = float(y_test.values[top_k_idx].mean())
    recall = float(y_test.values[top_k_idx].sum() / y_test.sum())
    return {"precision": round(precision, 4), "recall": round(recall, 4), "flagged_txn_count": k}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-frac", type=float, default=0.15)
    parser.add_argument("--score-threshold", type=float, default=DEFAULT_SCORE_THRESHOLD)
    args = parser.parse_args()

    df = load_clean(sample_frac=args.sample_frac)
    graph = build_graph(df)
    rings = score_clusters(graph)

    ring_metrics = ring_level_metrics(df, graph, rings, args.score_threshold)
    print(f"\n=== Ring-level evaluation (score >= {args.score_threshold}) ===")
    for k, v in ring_metrics.items():
        print(f"  {k}: {v}")

    print(f"\nNote: fraud_rate is one of the inputs to ring score, so precision here is")
    print(f"partly circular by construction — reported as a structural sanity check,")
    print(f"not a held-out generalization claim. The scaled-down baseline comparison")
    print(f"below IS a fair held-out number (RF trained on a separate split).")

    flag_count = ring_metrics["flagged_txn_count"]
    if flag_count:
        baseline = baseline_metrics_at_matched_flag_count(df, flag_count)
        print(f"\n=== Baseline RF at matched flag count ({flag_count:,} transactions) ===")
        for k, v in baseline.items():
            print(f"  {k}: {v}")
