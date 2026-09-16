"""Betweenness centrality within a single cluster's induced subgraph — used to
find the likely coordinating/hub account within a flagged ring.
"""
import networkx as nx


def hub_accounts(graph: nx.Graph, members: list[str], top_n: int = 3) -> list[dict]:
    subgraph = graph.subgraph(members)
    if subgraph.number_of_nodes() < 3:
        degree = dict(subgraph.degree(weight="weight"))
        ranked = sorted(degree.items(), key=lambda kv: kv[1], reverse=True)
    else:
        betweenness = nx.betweenness_centrality(subgraph, weight="weight", normalized=True)
        ranked = sorted(betweenness.items(), key=lambda kv: kv[1], reverse=True)

    return [{"account_id": account_id, "centrality": float(score)} for account_id, score in ranked[:top_n]]
