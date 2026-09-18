from fastapi import APIRouter, HTTPException

from api.schemas import SampleListResponse, ScoreRequest, ScoreResponse
from api.store import store
from pipeline.score_model import build_feature_row, fill_defaults

router = APIRouter(prefix="/score", tags=["score"])

NO_ACCOUNT_MATCH_NOTE = "No existing ring connections found for this account — scored on transaction features alone."
BUILD_YOUR_OWN_NOTE = (
    "This simplified form doesn't collect the device/card fingerprint fields used for "
    "ring matching — scored on transaction features alone."
)


def _ring_summary(ring: dict | None) -> dict | None:
    if ring is None:
        return None
    return {
        "ring_id": ring["ring_id"],
        "size": ring["size"],
        "density": ring["density"],
        "fraud_rate": ring["fraud_rate"],
        "creation_tightness": ring["creation_tightness"],
        "score": ring["score"],
        "oversized": ring["oversized"],
        "hub_accounts": ring["hub_accounts"],
    }


def _score(fields: dict) -> float:
    row = build_feature_row(
        fields,
        store.score_meta["feature_columns"],
        store.score_meta["categorical_fields"],
        store.score_meta["numeric_fields"],
    )
    return float(store.score_model.predict_proba(row)[0, 1])


@router.post("")
def score_transaction(req: ScoreRequest) -> ScoreResponse:
    if (req.sample_id is None) == (req.fields is None):
        raise HTTPException(400, "provide exactly one of sample_id or fields")

    if req.sample_id is not None:
        sample = store.score_samples_by_id.get(req.sample_id)
        if sample is None:
            raise HTTPException(404, f"sample {req.sample_id} not found")

        proba = _score(sample["fields"])
        ring = store.ring_for_account(sample["account_id"])
        if ring:
            note = (
                f"{proba:.0%} fraud probability (model) — AND this account is linked to "
                f"{ring['ring_id']}, which has a {ring['fraud_rate']:.0%} fraud rate "
                f"among its {ring['size']} accounts."
            )
        else:
            note = NO_ACCOUNT_MATCH_NOTE

        return ScoreResponse(
            fraud_probability=round(proba, 4),
            flagged=proba >= store.score_meta["flag_threshold"],
            matched_ring_id=ring["ring_id"] if ring else None,
            ring_context=_ring_summary(ring),
            ring_note=note,
        )

    fields = fill_defaults(
        req.fields,
        store.score_meta["defaults"],
        store.score_meta["numeric_fields"],
        store.score_meta["categorical_fields"],
    )
    proba = _score(fields)

    return ScoreResponse(
        fraud_probability=round(proba, 4),
        flagged=proba >= store.score_meta["flag_threshold"],
        matched_ring_id=None,
        ring_context=None,
        ring_note=BUILD_YOUR_OWN_NOTE,
    )


@router.get("/samples")
def list_samples() -> SampleListResponse:
    return SampleListResponse(
        samples=[
            {
                "sample_id": s["sample_id"],
                "label": s["label"],
                "true_is_fraud": s["true_is_fraud"],
                "account_id": s["account_id"],
                "display_fields": s["display_fields"],
                "matched_ring_id": s["matched_ring_id"],
            }
            for s in store.score_samples
        ],
        top_fields=store.score_meta["top_fields"],
        field_importances=store.score_meta["field_importances"],
    )
