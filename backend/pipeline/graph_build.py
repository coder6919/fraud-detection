
"""Nodes are accounts (see ingest.account_id). Edges connect two accounts that
share a genuinely matching non-null identifier value (device, email domain,
address). Values shared by too many accounts are treated as noise, not
signal, and excluded; common free-mail domains are down-weighted rather
than excluded outright, since a shared "gmail.com" *combined* with another
shared identifier is still useful evidence.

Run standalone for a sanity check:
    python -m pipeline.graph_build --sample-frac 0.15
"""
import argparse
import pickle
from collections import defaultdict
from itertools import combinations

import networkx as nx
import pandas as pd

from pipeline.config import (
    COMMON_DOMAIN_WEIGHT_MULTIPLIER,
    COMMON_EMAIL_DOMAINS,
    GRAPH_STORE_DIR,
    IDENTIFIER_FIELDS,
    MAX_ACCOUNTS_PER_IDENTIFIER_VALUE,
)
from pipeline.ingest import load_clean

EMAIL_FIELDS = {"P_emaildomain", "R_emaildomain"}
FULL_WEIGHT_GROUP_SIZE = 4  # groups at or below this size keep full base weight


def _edge_weight(field: str, value: str, group_size: int) -> float:
    base = IDENTIFIER_FIELDS[field]
    if field in EMAIL_FIELDS and value in COMMON_EMAIL_DOMAINS:
        base *= COMMON_DOMAIN_WEIGHT_MULTIPLIER

    # Inverse-frequency dampening: a value shared by 2 accounts is strong
    # evidence, one shared by 30 is weak, regardless of field. Applies to every
    # identifier field, not just email, so generic buckets (e.g. a DeviceInfo
    # value that's really just "Windows") don't act as free bridges either.
    dampening = min(1.0, FULL_WEIGHT_GROUP_SIZE / group_size)
    return base * dampening


def build_account_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per account_id, aggregated from its transactions."""
    agg = df.groupby("account_id").agg(
        num_transactions=("TransactionID", "count"),
        fraud_rate=("isFraud", "mean"),
        first_seen=("TransactionDT", "min"),
        last_seen=("TransactionDT", "max"),
        total_amount=("TransactionAmt", "sum"),
        primary_email=("P_emaildomain", lambda s: s.dropna().mode().iat[0] if s.notna().any() else None),
        device_type=("DeviceType", lambda s: s.dropna().mode().iat[0] if s.notna().any() else None),
    )
    return agg


def build_graph(df: pd.DataFrame) -> nx.Graph:
    accounts = build_account_table(df)

    graph = nx.Graph()
    for account_id, row in accounts.iterrows():
        graph.add_node(
            account_id,
            num_transactions=int(row["num_transactions"]),
            fraud_rate=float(row["fraud_rate"]),
            first_seen=float(row["first_seen"]),
            last_seen=float(row["last_seen"]),
            total_amount=float(row["total_amount"]),
            primary_email=row["primary_email"],
            device_type=row["device_type"],
        )

    excluded_values = 0
    edges_added = 0

    for field in IDENTIFIER_FIELDS:
        if field not in df.columns:
            continue

        # Only genuinely matching non-null values create an edge — never
        # connect two accounts just because both happen to be missing this field.
        non_null = df[["account_id", field]].dropna(subset=[field])
        non_null = non_null[non_null[field] != "NA"]

        groups = non_null.groupby(field)["account_id"].apply(lambda s: sorted(set(s)))

        for value, account_ids in groups.items():
            if len(account_ids) < 2:
                continue
            if len(account_ids) > MAX_ACCOUNTS_PER_IDENTIFIER_VALUE:
                excluded_values += 1
                continue

            weight = _edge_weight(field, value, len(account_ids))
            for a, b in combinations(account_ids, 2):
                if graph.has_edge(a, b):
                    edge = graph[a][b]
                    edge["weight"] += weight
                    edge["evidence"][field] = value
                else:
                    graph.add_edge(a, b, weight=weight, evidence={field: value})
                    edges_added += 1

    print(f"identifier values excluded as noise (> {MAX_ACCOUNTS_PER_IDENTIFIER_VALUE} accounts): {excluded_values}")
    print(f"edges created: {edges_added}")

    return graph


def save_graph(graph: nx.Graph, path=None) -> None:
    path = path or (GRAPH_STORE_DIR / "graph.pkl")
    GRAPH_STORE_DIR.mkdir(exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(graph, f)


def load_graph(path=None) -> nx.Graph:
    path = path or (GRAPH_STORE_DIR / "graph.pkl")
    with open(path, "rb") as f:
        return pickle.load(f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-frac", type=float, default=0.15)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    df = load_clean(sample_frac=args.sample_frac)
    graph = build_graph(df)

    print(f"\nnodes: {graph.number_of_nodes():,}")
    print(f"edges: {graph.number_of_edges():,}")

    degrees = [d for _, d in graph.degree()]
    isolated = sum(1 for d in degrees if d == 0)
    print(f"isolated accounts (no shared identifiers): {isolated:,} ({isolated / graph.number_of_nodes():.1%})")
    print(f"max degree: {max(degrees)}")
    print(f"avg degree (connected only): {sum(d for d in degrees if d > 0) / max(1, graph.number_of_nodes() - isolated):.2f}")

    components = sorted(nx.connected_components(graph), key=len, reverse=True)
    print(f"\nconnected components: {len(components):,}")
    print("largest 5 component sizes:", [len(c) for c in components[:5]])

    if args.save:
        save_graph(graph)
        print(f"\nsaved to {GRAPH_STORE_DIR / 'graph.pkl'}")
