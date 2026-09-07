import json
from pathlib import Path

import pytest

from nemweb_ml.split import chronological_split

ROWS = json.loads((Path(__file__).parent / "fixtures/history.json").read_text())


def test_split_is_chronological_non_overlapping_and_complete():
    train, validation, test = chronological_split(ROWS)
    assert len(train) + len(validation) + len(test) == len(ROWS)
    assert max(row["prediction_time"] for row in train) < min(row["prediction_time"] for row in validation)
    assert max(row["prediction_time"] for row in validation) < min(row["prediction_time"] for row in test)
    assert {id(row) for row in train}.isdisjoint({id(row) for row in validation + test})


def test_split_rejects_too_little_history_and_invalid_fractions():
    with pytest.raises(ValueError, match="three distinct"):
        chronological_split(ROWS[:2])
    with pytest.raises(ValueError, match="leave a test"):
        chronological_split(ROWS, train_fraction=0.8, validation_fraction=0.2)
