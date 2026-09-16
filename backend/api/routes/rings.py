from fastapi import APIRouter, HTTPException, Query

from api.serialize import subgraph_response
from api.store import store

router = APIRouter(prefix="/rings", tags=["rings"])

DEFAULT_RING_NODE_LIMIT = 300


@router.get("")
def list_rings(
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    include_oversized: bool = True,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    rings = [r for r in store.rings if r["score"] >= min_score]
    if not include_oversized:
        rings = [r for r in rings if not r["oversized"]]

    rings = sorted(rings, key=lambda r: r["score"], reverse=True)
    page = rings[offset : offset + limit]

    return {
        "rings": [
            {
                "ring_id": r["ring_id"],
                "size": r["size"],
                "density": r["density"],
                "fraud_rate": r["fraud_rate"],
                "creation_tightness": r["creation_tightness"],
                "score": r["score"],
                "oversized": r["oversized"],
                "hub_accounts": r["hub_accounts"],
            }
            for r in page
        ],
        "total": len(rings),
        "offset": offset,
        "limit": limit,
    }


@router.get("/{ring_id}")
def get_ring(ring_id: str, node_limit: int = Query(DEFAULT_RING_NODE_LIMIT, ge=1, le=1000)):
    ring = store.rings_by_id.get(ring_id)
    if ring is None:
        raise HTTPException(status_code=404, detail=f"ring {ring_id} not found")

    graph = subgraph_response(ring["members"], node_limit=node_limit, full_size=ring["size"])

    return {
        "ring_id": ring["ring_id"],
        "size": ring["size"],
        "density": ring["density"],
        "fraud_rate": ring["fraud_rate"],
        "creation_tightness": ring["creation_tightness"],
        "score": ring["score"],
        "oversized": ring["oversized"],
        "hub_accounts": ring["hub_accounts"],
        "graph": graph,
    }
