"""Serving-time helpers for the live /score endpoint (build spec section 9).

Training happens once in `scripts/build_score_model.py`, which persists the
fitted classifier (score_model.pkl) and this module's metadata
(score_model_meta.json: the one-hot feature schema, field defaults, and
aggregated feature importances). The API only ever builds a single scoreable
row against that persisted schema — it never retrains or touches the raw CSVs.
"""
import pandas as pd


def base_field_of(column: str, categorical_fields: list[str], numeric_fields: list[str]) -> str:
    """Maps a one-hot column (e.g. "card4_visa") back to its source field
    ("card4"), so importance can be reported per real-world field rather than
    per dummy column."""
    if column in numeric_fields:
        return column
    for field in categorical_fields:
        if column.startswith(field + "_"):
            return field
    return column


def aggregate_feature_importance(
    importances, feature_columns: list[str], categorical_fields: list[str], numeric_fields: list[str]
) -> dict[str, float]:
    totals: dict[str, float] = {}
    for column, importance in zip(feature_columns, importances):
        base = base_field_of(column, categorical_fields, numeric_fields)
        totals[base] = totals.get(base, 0.0) + float(importance)
    return totals


def compute_defaults(df: pd.DataFrame, numeric_fields: list[str], categorical_fields: list[str]) -> dict:
    """Dataset median (numeric) / mode (categorical) for every field, used to
    fill whatever the "build your own" form doesn't expose (spec 9c-2)."""
    defaults = {}
    for field in numeric_fields:
        if field == "hour_of_day":
            defaults[field] = float(((df["TransactionDT"] // 3600) % 24).median())
        elif field == "day_of_week":
            defaults[field] = float(((df["TransactionDT"] // 86400) % 7).median())
        else:
            defaults[field] = float(df[field].median())
    for field in categorical_fields:
        non_null = df[field].dropna()
        defaults[field] = str(non_null.mode().iat[0]) if not non_null.empty else "missing"
    return defaults


def row_fields(row, numeric_fields: list[str], categorical_fields: list[str]) -> dict:
    """Builds the same field dict a live score request supplies, but from a
    real historical dataset row (used to score curated sample transactions
    with their true values, not simplified-form defaults)."""
    fields = {}
    for field in numeric_fields:
        if field == "hour_of_day":
            fields[field] = float((row["TransactionDT"] // 3600) % 24)
        elif field == "day_of_week":
            fields[field] = float((row["TransactionDT"] // 86400) % 7)
        else:
            fields[field] = float(row[field])
    for field in categorical_fields:
        value = row[field]
        fields[field] = str(value) if pd.notna(value) else "missing"
    return fields


def build_feature_row(
    fields: dict, feature_columns: list[str], categorical_fields: list[str], numeric_fields: list[str]
) -> pd.DataFrame:
    """A single scoreable row aligned to the model's training-time one-hot
    schema. A categorical value unseen at training time leaves that field's
    dummy columns all zero — equivalent to an unrecognized/"other" bucket,
    not a crash."""
    row = {column: 0 for column in feature_columns}
    for field in numeric_fields:
        if field in row:
            row[field] = float(fields[field])
    for field in categorical_fields:
        value = fields.get(field, "missing")
        column = f"{field}_{value}"
        if column in row:
            row[column] = 1
    return pd.DataFrame([row], columns=feature_columns)


def fill_defaults(
    user_fields: dict, defaults: dict, numeric_fields: list[str], categorical_fields: list[str]
) -> dict:
    """Merges user-supplied top fields with dataset median/mode for every
    field the simplified "build your own" form doesn't show."""
    filled = dict(defaults)
    for field in numeric_fields:
        if field in user_fields and user_fields[field] not in (None, ""):
            try:
                filled[field] = float(user_fields[field])
            except (TypeError, ValueError):
                pass
    for field in categorical_fields:
        if field in user_fields and user_fields[field] not in (None, ""):
            filled[field] = str(user_fields[field])
    return filled
