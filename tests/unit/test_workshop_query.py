"""Verification must reject failed or partial warehouse evidence."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("workshop_query", Path(__file__).resolve().parents[2] / "scripts/workshop-query.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def response():
    return {"status": {"state": "SUCCEEDED"},
            "manifest": {"schema": {"columns": [{"name": "check_name"}, {"name": "violations"}]}},
            "result": {"data_array": [["coverage", "0"]]}}


def test_complete_evidence_rows():
    assert module.rows(response()) == [{"check_name": "coverage", "violations": "0"}]


@pytest.mark.parametrize("kind", ["failed", "truncated", "next_chunk"])
def test_incomplete_evidence_is_not_accepted(kind):
    value = response()
    if kind == "failed":
        value["status"]["state"] = "FAILED"
    elif kind == "truncated":
        value["manifest"]["truncated"] = True
    else:
        value["result"]["next_chunk_index"] = 1
    with pytest.raises(ValueError):
        module.rows(value)


@pytest.mark.parametrize("value", ["x.y", "a;DROP", "a`", "../x", ""])
def test_catalog_schema_placeholders_reject_nonidentifiers(value):
    with pytest.raises(ValueError):
        module.identifier(value)
