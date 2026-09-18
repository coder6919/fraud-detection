"""Loads the persisted graph + scored rings once at process start.

Regenerate the artifacts with `python -m scripts.build_graph` — the API
never touches the raw CSVs or rebuilds the graph itself.
"""
import json

import joblib

from pipeline.config import GRAPH_STORE_DIR
from pipeline.graph_build import load_graph


class Store:
    def __init__(self):
        self.graph = load_graph()
        with open(GRAPH_STORE_DIR / "rings.json") as f:
            self.rings = json.load(f)

        self.rings_by_id = {r["ring_id"]: r for r in self.rings}

        self.account_to_ring: dict[str, str] = {}
        for ring in self.rings:
            for account_id in ring["members"]:
                self.account_to_ring[account_id] = ring["ring_id"]

        # Live scoring (section 9) — see scripts/build_score_model.py.
        self.score_model = joblib.load(GRAPH_STORE_DIR / "score_model.pkl")
        with open(GRAPH_STORE_DIR / "score_model_meta.json") as f:
            self.score_meta = json.load(f)
        with open(GRAPH_STORE_DIR / "score_samples.json") as f:
            self.score_samples = json.load(f)
        self.score_samples_by_id = {s["sample_id"]: s for s in self.score_samples}

    def ring_for_account(self, account_id: str) -> dict | None:
        ring_id = self.account_to_ring.get(account_id)
        return self.rings_by_id.get(ring_id) if ring_id else None


store = Store()
