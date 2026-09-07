"""Schema and point-in-time eligibility gates for NEMWEB training rows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

REQUIRED_FIELDS = {
    "region_id", "prediction_time", "feature_time", "label_time",
    "price_aud_per_mwh", "demand_mw", "label_price_spike_next_30m",
}


def parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp string") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate_training_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    materialised = [dict(row) for row in rows]
    if not materialised:
        raise ValueError("training rows are empty")
    keys: set[tuple[str, str]] = set()
    for row in materialised:
        missing = REQUIRED_FIELDS - row.keys()
        if missing:
            raise ValueError(f"training row missing fields: {sorted(missing)}")
        if not isinstance(row["region_id"], str) or not row["region_id"]:
            raise ValueError("region_id must be a non-empty string")
        for field in ("price_aud_per_mwh", "demand_mw"):
            if not isinstance(row[field], (int, float)) or isinstance(row[field], bool):
                raise ValueError(f"{field} must be numeric")
        if not isinstance(row["label_price_spike_next_30m"], bool):
            raise ValueError("label_price_spike_next_30m must be boolean")
        prediction = parse_timestamp(row["prediction_time"], "prediction_time")
        feature = parse_timestamp(row["feature_time"], "feature_time")
        label = parse_timestamp(row["label_time"], "label_time")
        if feature > prediction:
            raise ValueError("feature leakage: feature_time is newer than prediction_time")
        if label <= prediction:
            raise ValueError("label_time must be after prediction_time")
        key = (row["region_id"], row["prediction_time"])
        if key in keys:
            raise ValueError("region/prediction-time key is not unique")
        keys.add(key)
    return materialised
