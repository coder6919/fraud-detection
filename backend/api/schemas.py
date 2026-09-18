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


class ScoreRequest(BaseModel):
    """Exactly one of sample_id (score a curated real transaction, using its
    true feature values) or fields (score a "build your own" simplified
    submission, defaults filling everything else) must be set."""
    sample_id: str | None = None
    fields: dict[str, str | float | int] | None = None


class ScoreResponse(BaseModel):
    fraud_probability: float
    flagged: bool
    matched_ring_id: str | None
    ring_context: RingSummary | None
    ring_note: str


class SampleTransaction(BaseModel):
    sample_id: str
    label: str
    true_is_fraud: bool
    account_id: str
    display_fields: dict[str, str | float]
    matched_ring_id: str | None


class SampleListResponse(BaseModel):
    samples: list[SampleTransaction]
    top_fields: list[str]
    field_importances: dict[str, float]
