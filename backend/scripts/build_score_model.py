"""One-off CLI: train the section-5 baseline Random Forest, persist it for
live serving, and curate a small set of "try a real transaction" samples
(spec 9c-1 / 9d).

Must run against the SAME dataset sample the persisted graph was built from
(default: full dataset, matching graph_store/graph.pkl and rings.json) —
otherwise a curated sample's account_id may not exist in the served graph,
and the ring-matching demo (9d) would silently never fire.

    python -m scripts.build_score_model

Writes to graph_store/:
    score_model.pkl        joblib-serialized RandomForestClassifier
    score_model_meta.json  one-hot feature schema, field defaults, importances
    score_samples.json     curated try-it transactions, seeded ring matches
"""
import argparse
import json

import joblib
import pandas as pd

from pipeline import baseline_rf
from pipeline.config import GRAPH_STORE_DIR, SCORE_FLAG_THRESHOLD
from pipeline.ingest import load_clean
from pipeline.score_model import (
    aggregate_feature_importance,
    compute_defaults,
    row_fields,
)

NUMERIC_FIELDS = baseline_rf.NUMERIC + ["hour_of_day", "day_of_week"]
CATEGORICAL_FIELDS = baseline_rf.CATEGORICAL

DEFAULT_NUM_SAMPLES = 8
DEFAULT_MAX_RING_SAMPLES = 3
DEFAULT_TOP_N_FIELDS = 8


def _load_account_to_ring() -> dict[str, dict]:
    rings_path = GRAPH_STORE_DIR / "rings.json"
    if not rings_path.exists():
        print(f"warning: {rings_path} not found — samples will have no ring matches. "
              "Run `python -m scripts.build_graph --save` first.")
        return {}
    with open(rings_path) as f:
        rings = json.load(f)
    account_to_ring: dict[str, dict] = {}
    for ring in rings:
        for account_id in ring["members"]:
            account_to_ring[account_id] = ring
    return account_to_ring


def _ring_summary(ring: dict | None) -> dict | None:
    if ring is None:
        return None
    return {
        "ring_id": ring["ring_id"],
        "size": ring["size"],
        "density": ring["density"],
        "fraud_rate": ring["fraud_rate"],
        "creation_tightness": ring["creation_tightness"],
        "score": ring["score"],
        "oversized": ring["oversized"],
        "hub_accounts": ring["hub_accounts"],
    }


def _label_for(row: pd.Series, ring: dict | None) -> str:
    amt = row["TransactionAmt"]
    product = row["ProductCD"]
    device = row["DeviceType"] if pd.notna(row["DeviceType"]) else "no device info"
    email = row["P_emaildomain"] if pd.notna(row["P_emaildomain"]) else "no email domain"
    base = f"${amt:,.0f} {product} purchase, {device}, {email}"
    if ring is not None:
        return f"{base} — linked to {ring['ring_id']} ({ring['size']} accounts, {ring['fraud_rate']:.0%} fraud rate)"
    return base


def curate_samples(
    df: pd.DataFrame,
    test_index: pd.Index,
    proba,
    account_to_ring: dict[str, dict],
    top_fields: list[str],
    num_samples: int = DEFAULT_NUM_SAMPLES,
    max_ring_samples: int = DEFAULT_MAX_RING_SAMPLES,
) -> list[dict]:
    test_df = df.loc[test_index].copy()
    test_df["fraud_proba"] = pd.Series(proba, index=test_index)
    test_df["ring"] = test_df["account_id"].map(account_to_ring)

    ring_rows = test_df[test_df["ring"].notna()].copy()
    ring_rows["ring_score"] = ring_rows["ring"].apply(lambda r: r["score"])
    # Prefer true-fraud rows in the highest-scoring rings first — the demo
    # should show the ring-matching path landing on a genuinely bad account,
    # not an arbitrary one (spec 9d edge case: seed real ring-matched examples).
    # One row per account_id, so three picks show three different accounts
    # rather than the same account's near-identical repeat transactions.
    ring_rows = ring_rows.sort_values(["isFraud", "ring_score"], ascending=[False, False])
    ring_rows = ring_rows.drop_duplicates(subset="account_id")
    ring_picks = ring_rows.head(max_ring_samples)

    remaining = max(0, num_samples - len(ring_picks))
    # True non-ring rows only — not just "rows we didn't already pick", which
    # would still let another transaction from an already-picked ring account
    # back in through the fraud/clean slots below.
    non_ring = test_df[test_df["ring"].isna()].drop_duplicates(subset="account_id")
    non_ring_sorted = non_ring.sort_values("fraud_proba", ascending=False)

    fraud_slots = remaining - remaining // 2
    clean_slots = remaining // 2
    fraud_picks = non_ring_sorted[non_ring_sorted["isFraud"] == 1].head(fraud_slots)
    # Lowest-probability clean rows = most confidently clean, for contrast.
    clean_picks = non_ring_sorted[non_ring_sorted["isFraud"] == 0].tail(clean_slots)

    picks = pd.concat([ring_picks, fraud_picks, clean_picks])
    picks = picks[~picks.index.duplicated()].head(num_samples)

    samples = []
    for i, (_, row) in enumerate(picks.iterrows()):
        ring = row["ring"] if isinstance(row["ring"], dict) else None
        fields = row_fields(row, NUMERIC_FIELDS, CATEGORICAL_FIELDS)
        samples.append({
            "sample_id": f"sample_{i:02d}",
            "label": _label_for(row, ring),
            "true_is_fraud": bool(row["isFraud"]),
            "account_id": row["account_id"],
            "fields": fields,
            "display_fields": {f: fields[f] for f in top_fields if f in fields},
            "matched_ring_id": ring["ring_id"] if ring else None,
            "matched_ring": _ring_summary(ring),
        })
    return samples


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-frac", type=float, default=None,
                         help="Dataset fraction to train on. Default (None) = full dataset, "
                              "matching the persisted graph. Only lower this for fast dev iteration.")
    parser.add_argument("--num-samples", type=int, default=DEFAULT_NUM_SAMPLES)
    parser.add_argument("--max-ring-samples", type=int, default=DEFAULT_MAX_RING_SAMPLES)
    parser.add_argument("--top-n-fields", type=int, default=DEFAULT_TOP_N_FIELDS)
    args = parser.parse_args()

    print(f"loading + cleaning (sample_frac={args.sample_frac})...")
    df = load_clean(sample_frac=args.sample_frac)
    print(f"  {len(df):,} transactions, {df['account_id'].nunique():,} accounts")

    print("training baseline Random Forest...")
    clf, X_test, y_test, proba = baseline_rf.train_baseline(df)
    feature_columns = list(X_test.columns)
    print(f"  {len(feature_columns)} one-hot feature columns, {len(y_test):,} held-out test rows")

    importance_by_field = aggregate_feature_importance(
        clf.feature_importances_, feature_columns, CATEGORICAL_FIELDS, NUMERIC_FIELDS
    )
    top_fields = sorted(importance_by_field, key=importance_by_field.get, reverse=True)[: args.top_n_fields]
    print(f"  top {args.top_n_fields} fields by importance: {top_fields}")

    defaults = compute_defaults(df, NUMERIC_FIELDS, CATEGORICAL_FIELDS)

    GRAPH_STORE_DIR.mkdir(exist_ok=True)

    joblib.dump(clf, GRAPH_STORE_DIR / "score_model.pkl")

    meta = {
        "feature_columns": feature_columns,
        "numeric_fields": NUMERIC_FIELDS,
        "categorical_fields": CATEGORICAL_FIELDS,
        "top_fields": top_fields,
        "field_importances": {k: round(v, 4) for k, v in importance_by_field.items()},
        "defaults": defaults,
        "flag_threshold": SCORE_FLAG_THRESHOLD,
    }
    with open(GRAPH_STORE_DIR / "score_model_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print("\ncurating try-it sample transactions...")
    account_to_ring = _load_account_to_ring()
    samples = curate_samples(
        df, X_test.index, proba, account_to_ring, top_fields,
        num_samples=args.num_samples, max_ring_samples=args.max_ring_samples,
    )
    ring_matched = sum(1 for s in samples if s["matched_ring_id"])
    print(f"  {len(samples)} samples curated, {ring_matched} with a ring match")
    if ring_matched == 0:
        print("  warning: no ring-matched sample found — the ring-matching path (9d) won't be demoed. "
              "Check rings.json is built from the same sample_frac as this run.")

    with open(GRAPH_STORE_DIR / "score_samples.json", "w") as f:
        json.dump(samples, f, indent=2, default=str)

    print(f"\nsaved score_model.pkl, score_model_meta.json, score_samples.json to {GRAPH_STORE_DIR}")
