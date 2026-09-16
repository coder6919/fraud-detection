
import argparse

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score
from sklearn.model_selection import train_test_split

from pipeline.ingest import load_clean

CATEGORICAL = ["ProductCD", "card4", "card6", "P_emaildomain", "R_emaildomain", "DeviceType"]
NUMERIC = ["TransactionAmt"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    features = df[NUMERIC].copy()
    features["hour_of_day"] = (df["TransactionDT"] // 3600) % 24
    features["day_of_week"] = (df["TransactionDT"] // 86400) % 7

    for col in CATEGORICAL:
        dummies = pd.get_dummies(df[col].fillna("missing"), prefix=col, dtype=int)
        features = pd.concat([features, dummies], axis=1)

    return features


def train_baseline(df: pd.DataFrame, random_state: int = 42):
    X = build_features(df)
    y = df["isFraud"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=random_state
    )

    clf = RandomForestClassifier(
        n_estimators=200, max_depth=12, class_weight="balanced_subsample",
        n_jobs=-1, random_state=random_state,
    )
    clf.fit(X_train, y_train)

    proba = clf.predict_proba(X_test)[:, 1]
    return clf, X_test, y_test, proba


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-frac", type=float, default=0.15)
    args = parser.parse_args()

    df = load_clean(sample_frac=args.sample_frac)
    clf, X_test, y_test, proba = train_baseline(df)

    print(f"test set size: {len(y_test):,}, fraud rate: {y_test.mean():.4f}")
    print(f"ROC-AUC: {roc_auc_score(y_test, proba):.4f}")
    print(f"Average precision (PR-AUC): {average_precision_score(y_test, proba):.4f}")

    precision, recall, thresholds = precision_recall_curve(y_test, proba)
    # Report precision/recall at the threshold that flags roughly the top 5% by risk,
    # a comparable "flag rate" to what a ring-based approach would surface.
    k = max(1, int(0.05 * len(proba)))
    top_k_idx = proba.argsort()[::-1][:k]
    top_k_precision = y_test.values[top_k_idx].mean()
    top_k_recall = y_test.values[top_k_idx].sum() / y_test.sum()
    print(f"\nAt top {k} ({k/len(proba):.1%} of test set) by predicted risk:")
    print(f"  precision: {top_k_precision:.4f}")
    print(f"  recall: {top_k_recall:.4f}")

    importances = pd.Series(clf.feature_importances_, index=X_test.columns).sort_values(ascending=False)
    print("\ntop 10 feature importances:")
    print(importances.head(10))
