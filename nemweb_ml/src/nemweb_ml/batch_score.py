"""Deterministic batch-scoring output contract."""

from __future__ import annotations

from datetime import timezone
from typing import Any, Callable, Iterable, Mapping

from .contracts import parse_timestamp
from .features import FEATURE_COLUMNS, feature_vector

Scorer = Callable[[list[float]], float]


def score_rows(
    rows: Iterable[Mapping[str, Any]], *, scorer: Scorer, model_version: str,
    scored_at: str, stale_after_seconds: int = 900,
) -> list[dict[str, Any]]:
    if not model_version:
        raise ValueError("model_version is mandatory")
    scoring_time = parse_timestamp(scored_at, "scored_at")
    output: dict[tuple[str, str], dict[str, Any]] = {}
    for source in rows:
        region = str(source.get("region_id") or "")
        prediction_time = str(source.get("prediction_time") or "")
        feature_time = str(source.get("feature_time") or "")
        if not region or not prediction_time or not feature_time:
            raise ValueError("region_id, prediction_time, and feature_time are mandatory")
        parsed_feature_time = parse_timestamp(feature_time, "feature_time")
        missing = [name for name in FEATURE_COLUMNS if source.get(name) is None]
        freshness_seconds = (scoring_time - parsed_feature_time).total_seconds()
        status = "MISSING" if missing else "COMPLETE"
        stale = freshness_seconds > stale_after_seconds
        score = None if missing or stale else float(scorer(feature_vector(source)))
        key = (region, prediction_time)
        if key in output:
            raise ValueError("batch score target key is not unique")
        output[key] = {
            "region_id": region,
            "prediction_time": prediction_time,
            "prediction_score": score,
            "prediction_model_version": model_version,
            "prediction_feature_time": feature_time,
            "prediction_scored_at": scoring_time.astimezone(timezone.utc).isoformat(),
            "prediction_source_freshness": "STALE" if stale else "CURRENT",
            "prediction_missing_feature_status": status,
        }
    return [output[key] for key in sorted(output)]
