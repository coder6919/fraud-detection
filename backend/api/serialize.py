import networkx as nx

from api.store import store


def node_out(account_id: str) -> dict:
    data = store.graph.nodes[account_id]
    ring = store.ring_for_account(account_id)
    return {
        "id": account_id,
        "num_transactions": data["num_transactions"],
        "fraud_rate": data["fraud_rate"],
        "first_seen": data["first_seen"],
        "last_seen": data["last_seen"],
        "total_amount": data["total_amount"],
        "primary_email": data["primary_email"],
        "device_type": data["device_type"],
        "ring_id": ring["ring_id"] if ring else None,
        "ring_score": ring["score"] if ring else None,
    }


def edge_out(a: str, b: str) -> dict:
    data = store.graph[a][b]
    return {"source": a, "target": b, "weight": data["weight"], "evidence": data["evidence"]}


def subgraph_response(account_ids: list[str], node_limit: int, full_size: int | None = None) -> dict:
    truncated = len(account_ids) > node_limit
    kept = account_ids[:node_limit]
    kept_set = set(kept)

    subgraph = store.graph.subgraph(kept)
    nodes = [node_out(n) for n in kept]
    edges = [edge_out(u, v) for u, v in subgraph.edges() if u in kept_set and v in kept_set]

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "truncated": truncated or (full_size is not None and full_size > len(account_ids)),
        },
    }
