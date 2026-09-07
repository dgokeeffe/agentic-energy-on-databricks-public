from copy import deepcopy
import json
from pathlib import Path

import pytest

from nemweb_ml.contracts import validate_training_rows

ROWS = json.loads((Path(__file__).parent / "fixtures/history.json").read_text())


def test_missing_key_bad_type_naive_time_and_duplicate_key_are_rejected():
    missing = deepcopy(ROWS)
    del missing[0]["region_id"]
    with pytest.raises(ValueError, match="missing fields"):
        validate_training_rows(missing)
    bad_type = deepcopy(ROWS)
    bad_type[0]["demand_mw"] = "8000"
    with pytest.raises(ValueError, match="numeric"):
        validate_training_rows(bad_type)
    naive = deepcopy(ROWS)
    naive[0]["feature_time"] = "2026-07-01T00:05:00"
    with pytest.raises(ValueError, match="timezone"):
        validate_training_rows(naive)
    duplicate = deepcopy(ROWS) + [deepcopy(ROWS[0])]
    with pytest.raises(ValueError, match="not unique"):
        validate_training_rows(duplicate)
