"""
Run standalone for a quick sanity check:
    python -m pipeline.ingest --sample-frac 0.1
"""
import argparse
import hashlib

import pandas as pd

from pipeline.config import ACCOUNT_FIELDS, DATA_DIR

TRANSACTION_COLS = [
    "TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "ProductCD",
    "card1", "card2", "card3", "card4", "card5", "card6",
    "addr1", "addr2", "P_emaildomain", "R_emaildomain",
]
IDENTITY_COLS = ["TransactionID", "id_31", "DeviceType", "DeviceInfo"]


def _account_id(row: pd.Series) -> str:
    key = "|".join(str(row[f]) for f in ACCOUNT_FIELDS)
    return hashlib.md5(key.encode()).hexdigest()[:12]


def load_raw(sample_frac: float | None = None, random_state: int = 42) -> pd.DataFrame:
    txn = pd.read_csv(DATA_DIR / "train_transaction.csv", usecols=TRANSACTION_COLS)
    identity = pd.read_csv(DATA_DIR / "train_identity.csv", usecols=IDENTITY_COLS)

    if sample_frac is not None:
        txn = txn.sample(frac=sample_frac, random_state=random_state)

    df = txn.merge(identity, on="TransactionID", how="left")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # card1 is present on essentially every row; without it we can't anchor an
    # account fingerprint at all, so those rows can't be placed in the graph.
    df = df[df["card1"].notna()]

    for col in ["card2", "card3", "card4", "card5", "card6", "addr1", "addr2"]:
        df[col] = df[col].astype("string")
    df[["card2", "card3", "card4", "card5", "card6", "addr1", "addr2"]] = df[
        ["card2", "card3", "card4", "card5", "card6", "addr1", "addr2"]
    ].fillna("NA")
    df["card1"] = df["card1"].astype("string")

    for col in ["P_emaildomain", "R_emaildomain", "DeviceInfo", "id_31", "DeviceType"]:
        df[col] = df[col].astype("string").str.strip().str.lower()

    df["account_id"] = df.apply(_account_id, axis=1)

    return df.reset_index(drop=True)


def load_clean(sample_frac: float | None = None) -> pd.DataFrame:
    return clean(load_raw(sample_frac=sample_frac))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-frac", type=float, default=0.15)
    args = parser.parse_args()

    df = load_clean(sample_frac=args.sample_frac)

    print(f"rows: {len(df):,}")
    print(f"unique account_ids: {df['account_id'].nunique():,}")
    print(f"fraud rate: {df['isFraud'].mean():.4f}")
    print("\nmissing-value rates on identifier fields:")
    for col in ["P_emaildomain", "R_emaildomain", "DeviceInfo", "id_31", "addr1"]:
        print(f"  {col}: {df[col].isna().mean():.2%}")
    print("\naccounts per identifier value (top 10, P_emaildomain):")
    print(df["P_emaildomain"].value_counts().head(10))
