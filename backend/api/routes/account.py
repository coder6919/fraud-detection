from fastapi import APIRouter, HTTPException, Query

from api.serialize import edge_out, node_out
from api.store import store

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/{account_id}")
def get_account(account_id: str, neighbor_limit: int = Query(100, ge=1, le=500)):
    if account_id not in store.graph.nodes:
        raise HTTPException(status_code=404, detail=f"account {account_id} not found")

    node = node_out(account_id)
    ring = store.ring_for_account(account_id)

    neighbor_ids = sorted(
        store.graph.neighbors(account_id),
        key=lambda n: store.graph[account_id][n]["weight"],
        reverse=True,
    )[:neighbor_limit]
    neighbors = [edge_out(account_id, n) for n in neighbor_ids]

    return {"node": node, "ring": ring, "neighbors": neighbors}
