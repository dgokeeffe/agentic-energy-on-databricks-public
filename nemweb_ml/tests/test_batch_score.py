from copy import deepcopy
import json
from pathlib import Path

import pytest

from nemweb_ml.batch_score import score_rows

ROWS = json.loads((Path(__file__).parent / "fixtures/history.json").read_text())


def test_batch_output_has_lineage_freshness_and_idempotent_keys():
    result = score_rows(
        ROWS[:2], scorer=lambda features: sum(features) / 10000,
        model_version="7", scored_at="2026-06-30T14:11:00Z", stale_after_seconds=600,
    )
    assert len(result) == 2
    assert len({(row["region_id"], row["prediction_time"]) for row in result}) == 2
    for row in result:
        assert row["prediction_model_version"] == "7"
        assert row["prediction_feature_time"]
        assert row["prediction_scored_at"]
        assert row["prediction_source_freshness"] == "CURRENT"
        assert row["prediction_missing_feature_status"] == "COMPLETE"
        assert row["prediction_score"] is not None


def test_missing_or_stale_features_never_look_current():
    missing = deepcopy(ROWS[0])
    missing["demand_mw"] = None
    output = score_rows([missing], scorer=lambda _: 0.5, model_version="7", scored_at="2026-06-30T14:06:00Z")
    assert output[0]["prediction_score"] is None
    assert output[0]["prediction_missing_feature_status"] == "MISSING"
    stale = score_rows([ROWS[0]], scorer=lambda _: 0.5, model_version="7", scored_at="2026-06-30T15:06:00Z")
    assert stale[0]["prediction_score"] is None
    assert stale[0]["prediction_source_freshness"] == "STALE"


def test_duplicate_target_key_and_missing_model_version_fail():
    with pytest.raises(ValueError, match="not unique"):
        score_rows([ROWS[0], ROWS[0]], scorer=lambda _: 0.5, model_version="7", scored_at="2026-06-30T14:06:00Z")
    with pytest.raises(ValueError, match="model_version"):
        score_rows([ROWS[0]], scorer=lambda _: 0.5, model_version="", scored_at="2026-06-30T14:06:00Z")
