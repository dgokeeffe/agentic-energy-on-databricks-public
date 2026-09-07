from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from workshop.lakebase.cdf import reduce_current_state, validate_update_pairs

ROOT = Path(__file__).resolve().parents[1]


def _events():
    return json.loads((ROOT / "fixtures/investigation-cdf.json").read_text())


def test_insert_update_delete_and_resnapshot_produce_current_state_without_mutating_history():
    events = _events()
    original = deepcopy(events)
    current = reduce_current_state(events)
    assert events == original
    assert [row["investigation_id"] for row in current] == ["11111111-1111-4111-8111-111111111111"]
    assert current[0]["status"] == "closed"
    assert current[0]["version"] == 3
    assert current[0]["_pg_change_type"] == "insert"


def test_duplicate_replay_and_reordered_input_are_idempotent():
    events = _events()
    expected = reduce_current_state(events)
    replayed = list(reversed(events)) + [deepcopy(events[2]), deepcopy(events[-1])]
    assert reduce_current_state(replayed) == expected
    assert reduce_current_state(replayed) == reduce_current_state(replayed)


def test_update_preimage_never_becomes_current_and_delete_removes_only_current_row():
    events = _events()[:5]
    current = reduce_current_state(events)
    assert len(current) == 1
    assert current[0]["status"] == "reviewing"
    assert not any(row["investigation_id"].startswith("2222") for row in current)
    assert any(row["_pg_change_type"] == "delete" for row in events)


def test_update_preimages_and_postimages_are_paired_by_key_and_transaction():
    events = _events()
    postimage = next(event for event in events if event["_pg_change_type"] == "update_postimage")
    postimage["_pg_lsn"] = "0/21"
    validate_update_pairs(events)
    without_postimage = [event for event in events if event["_pg_change_type"] != "update_postimage"]
    with pytest.raises(ValueError, match="unpaired"):
        validate_update_pairs(without_postimage)


def test_integer_lsn_and_sort_order_are_supported():
    event = deepcopy(_events()[0])
    event["_pg_lsn"] = 16
    event["_sort_by"] = "1"
    assert reduce_current_state([event])[0]["investigation_id"] == event["investigation_id"]


def test_missing_metadata_and_unknown_change_type_fail_closed():
    event = _events()[0]
    broken = {key: value for key, value in event.items() if key != "_pg_lsn"}
    with pytest.raises(ValueError, match="missing metadata"):
        reduce_current_state([broken])
    event["_pg_change_type"] = "truncate"
    with pytest.raises(ValueError, match="unsupported"):
        reduce_current_state([event])
