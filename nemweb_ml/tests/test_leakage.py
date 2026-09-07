from copy import deepcopy
import json
from pathlib import Path

import pytest

from nemweb_ml.contracts import validate_training_rows

ROWS = json.loads((Path(__file__).parent / "fixtures/history.json").read_text())


def test_fixture_features_are_available_at_prediction_time_and_labels_are_future():
    assert len(validate_training_rows(ROWS)) == len(ROWS)


def test_future_feature_and_non_future_label_fail_closed():
    leaked = deepcopy(ROWS)
    leaked[0]["feature_time"] = "2026-07-01T00:10:00+10:00"
    with pytest.raises(ValueError, match="feature leakage"):
        validate_training_rows(leaked)
    invalid_label = deepcopy(ROWS)
    invalid_label[0]["label_time"] = invalid_label[0]["prediction_time"]
    with pytest.raises(ValueError, match="label_time"):
        validate_training_rows(invalid_label)
