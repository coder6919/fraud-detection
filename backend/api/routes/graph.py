from fastapi import APIRouter, HTTPException, Query

import networkx as nx

from api.serialize import subgraph_response
from api.store import store

router = APIRouter(prefix="/graph", tags=["graph"])

DEFAULT_NODE_LIMIT = 300


@router.get("")
def get_graph(
    ring_id: str | None = None,
    account_id: str | None = None,
    hops: int = Query(1, ge=1, le=3),
    min_score: float = Query(0.3, ge=0.0, le=1.0),
    limit: int = Query(DEFAULT_NODE_LIMIT, ge=1, le=1000),
):
    """
    No filters: overview of top flagged rings (by score), up to `limit` nodes.
    ring_id: that ring's members.
    account_id: that account's ego-network out to `hops` shared-identifier hops.
    The frontend should never need the full graph — every mode here is capped.
    """
    if ring_id is not None:
        ring = store.rings_by_id.get(ring_id)
        if ring is None:
            raise HTTPException(status_code=404, detail=f"ring {ring_id} not found")
        return subgraph_response(ring["members"], node_limit=limit, full_size=ring["size"])

    if account_id is not None:
        if account_id not in store.graph.nodes:
            raise HTTPException(status_code=404, detail=f"account {account_id} not found")
        ego = nx.ego_graph(store.graph, account_id, radius=hops)
        account_ids = list(ego.nodes())
        return subgraph_response(account_ids, node_limit=limit, full_size=len(account_ids))

    rings = sorted(
        (r for r in store.rings if r["score"] >= min_score),
        key=lambda r: r["score"],
        reverse=True,
    )
    account_ids: list[str] = []
    seen = set()
    for r in rings:
        for a in r["members"]:
            if a not in seen:
                seen.add(a)
                account_ids.append(a)
        if len(account_ids) >= limit:
            break

    return subgraph_response(account_ids, node_limit=limit)
