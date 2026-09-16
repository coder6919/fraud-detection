from pydantic import BaseModel


class NodeOut(BaseModel):
    id: str
    num_transactions: int
    fraud_rate: float
    first_seen: float
    last_seen: float
    total_amount: float
    primary_email: str | None
    device_type: str | None
    ring_id: str | None
    ring_score: float | None


class EdgeOut(BaseModel):
    source: str
    target: str
    weight: float
    evidence: dict[str, str]


class GraphMeta(BaseModel):
    node_count: int
    edge_count: int
    truncated: bool


class GraphResponse(BaseModel):
    nodes: list[NodeOut]
    edges: list[EdgeOut]
    meta: GraphMeta


class HubAccount(BaseModel):
    account_id: str
    centrality: float


class RingSummary(BaseModel):
    ring_id: str
    size: int
    density: float
    fraud_rate: float
    creation_tightness: float
    score: float
    oversized: bool
    hub_accounts: list[HubAccount]


class RingDetail(RingSummary):
    graph: GraphResponse


class AccountDetail(BaseModel):
    node: NodeOut
    ring: RingSummary | None
    neighbors: list[EdgeOut]
