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


@pytest.mark.parametrize("kind", ["short_row", "duplicate_column"])
def test_result_shape_cannot_silently_discard_values(kind):
    value = response()
    if kind == "short_row":
        value["result"]["data_array"] = [["coverage"]]
    else:
        value["manifest"]["schema"]["columns"][1]["name"] = "check_name"
    with pytest.raises(ValueError):
        module.rows(value)


@pytest.mark.parametrize('mismatch', ['statement', 'context'])
def test_resume_cannot_observe_a_different_query(tmp_path, monkeypatch, capsys, mismatch):
    import json
    import sys
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    sql = tmp_path / 'query.sql'
    sql.write_text('SELECT 1')
    output = tmp_path / '.databricks' / 'result.json'
    output.parent.mkdir()
    context = {'profile': 'chosen', 'warehouse_id': 'warehouse', 'catalog': 'catalog',
               'schema': 'schema', 'sql': 'SELECT 1'}
    saved = {'statement_id': 'original', '_workshop_context': context}
    if mismatch == 'context':
        context['warehouse_id'] = 'different'
    output.write_text(json.dumps(saved))
    monkeypatch.setattr(sys, 'argv', ['workshop-query', '--profile', 'chosen',
        '--warehouse-id', 'warehouse', '--catalog', 'catalog', '--schema', 'schema',
        '--sql-file', str(sql), '--output', str(output), '--resume',
        'different' if mismatch == 'statement' else 'original'])
    def no_cli(*args, **kwargs):
        raise AssertionError('A mismatched resume must not reach the workspace')
    monkeypatch.setattr(module, 'cli', no_cli)
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 2
    assert 'original query context' in capsys.readouterr().err
