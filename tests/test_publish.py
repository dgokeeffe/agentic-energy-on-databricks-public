"""Contract tests for Unity Catalog publication.

These run offline with a recording writer instead of Spark. The point is to lock
the governed table contracts and the idempotency/reconciliation rules that make
published counts trustworthy, without needing a workspace in the test suite.
"""

from datetime import datetime, timezone
import json

import pytest

from agentic_energy.pipeline import run_pipeline
from agentic_energy.publish import (
    BRONZE_TABLE,
    GOLD_TABLE,
    MANIFEST_TABLE,
    QUARANTINE_TABLE,
    SILVER_TABLE,
    TABLE_SCHEMAS,
    create_table_statements,
    publish_run,
)

UTC = timezone.utc


class RecordingWriter:
    """Captures statements and appended rows in order."""

    def __init__(self):
        self.statements = []
        self.appends = []

    def execute(self, statement):
        self.statements.append(statement)

    def append(self, table, schema, rows):
        self.appends.append((table, schema, rows))

    def rows_for(self, table):
        for name, schema, rows in self.appends:
            if name.endswith(f".{table}"):
                return [dict(zip([column for column, _ in schema], row)) for row in rows]
        raise AssertionError(f"no append recorded for {table}")


@pytest.fixture
def published(tmp_path):
    output = tmp_path / "run"
    run_pipeline(output_dir=output, run_id="job-run-1", mode="fixture")
    writer = RecordingWriter()
    counts = publish_run(
        output,
        catalog="edp_landing",
        schema="agentic_energy",
        run_id="job-run-1",
        writer=writer,
    )
    return output, writer, counts


def test_publishes_every_layer_with_manifest_counts(published):
    _, _, counts = published
    # Matches the fixture baseline the rest of the suite asserts on.
    assert counts[BRONZE_TABLE] == 11
    assert counts[SILVER_TABLE] == 6
    assert counts[QUARANTINE_TABLE] == 3
    assert counts[GOLD_TABLE] == 3
    assert counts[MANIFEST_TABLE] == 1


def test_tables_are_created_before_being_written(published):
    _, writer, _ = published
    create_statements = [s for s in writer.statements if s.startswith("CREATE TABLE")]
    assert len(create_statements) == len(TABLE_SCHEMAS)
    assert all("IF NOT EXISTS" in s and "USING DELTA" in s for s in create_statements)
    first_delete = next(i for i, s in enumerate(writer.statements) if s.startswith("DELETE"))
    last_create = max(i for i, s in enumerate(writer.statements) if s.startswith("CREATE TABLE"))
    assert last_create < first_delete


def test_republishing_a_run_deletes_that_run_first(published):
    """A retried job task must not double-count rows in the governed tables."""
    _, writer, _ = published
    deletes = [s for s in writer.statements if s.startswith("DELETE")]
    assert len(deletes) == len(TABLE_SCHEMAS)
    assert all("WHERE run_id = 'job-run-1'" in s for s in deletes)
    # Every table carries run_id so the delete predicate is always valid.
    assert all("run_id" in dict(schema) for schema in TABLE_SCHEMAS.values())


def test_manifest_row_is_written_last(published):
    """If publication dies midway the run must not look published."""
    _, writer, _ = published
    appended = [table for table, _, _ in writer.appends]
    assert appended[-1].endswith(f".{MANIFEST_TABLE}")


def test_gold_is_typed_and_flattened_for_business_consumption(published):
    _, writer, _ = published
    gold = writer.rows_for(GOLD_TABLE)
    assert [(r["region"], r["interval_utc"]) for r in gold] == [
        ("NSW1", datetime(2024, 1, 14, 23, 0, tzinfo=UTC)),
        ("NSW1", datetime(2024, 4, 7, 0, 0, tzinfo=UTC)),
        ("VIC1", datetime(2024, 4, 7, 0, 30, tzinfo=UTC)),
    ]
    assert all(isinstance(r["demand_mw"], float) for r in gold)
    # Lineage and freshness are flattened into columns, not nested structs.
    assert all(r["market_provider"] == "AEMO" for r in gold)
    assert all(r["market_licensing_provenance"] for r in gold)
    assert all(r["pipeline_ingested_at"] == datetime(2024, 4, 7, tzinfo=UTC) for r in gold)
    assert all(r["run_id"] == "job-run-1" for r in gold)


def test_silver_keeps_sources_as_data_in_one_table(published):
    """One Silver table with nullable measures, not one table per source."""
    _, writer, _ = published
    silver = writer.rows_for(SILVER_TABLE)
    assert {r["source_id"] for r in silver} == {"aemo_dispatch_fixture", "weather_fixture"}
    market = [r for r in silver if r["dataset"] == "DISPATCH_SCADA"]
    weather = [r for r in silver if r["dataset"] == "HOURLY_WEATHER"]
    assert market and weather
    # A source's absent measures are null, and its own measures are populated.
    assert all(r["temperature_c"] is None and r["demand_mw"] is not None for r in market)
    assert all(r["demand_mw"] is None and r["temperature_c"] is not None for r in weather)


def test_bronze_preserves_the_raw_record_verbatim(published):
    _, writer, _ = published
    bronze = writer.rows_for(BRONZE_TABLE)
    assert len(bronze) == 11
    assert all(r["raw_line"] for r in bronze)
    parsed = [json.loads(r["raw_record_json"]) for r in bronze if r["raw_record_json"]]
    assert parsed and all(isinstance(record, dict) for record in parsed)
    assert all(r["ingested_at"] == datetime(2024, 4, 7, tzinfo=UTC) for r in bronze)


def test_quarantine_reasons_are_queryable_as_array_and_text(published):
    _, writer, _ = published
    rejected = writer.rows_for(QUARANTINE_TABLE)
    assert len(rejected) == 3
    assert all(isinstance(r["reason_codes"], list) and r["reason_codes"] for r in rejected)
    assert all(r["reason_codes_text"] == ",".join(r["reason_codes"]) for r in rejected)


def test_manifest_table_carries_reconciliation_evidence(published):
    output, writer, _ = published
    row = writer.rows_for(MANIFEST_TABLE)[0]
    manifest = json.loads((output / "manifest.json").read_text())
    assert row["run_id"] == "job-run-1"
    assert row["mode"] == "fixture"
    assert row["metadata_sha256"] == manifest["metadata_sha256"]
    assert row["bronze_count"] == 11
    assert row["silver_count"] == 6
    assert row["quarantine_count"] == 3
    assert row["gold_count"] == 3
    assert row["source_ids"] == sorted(manifest["source_ids"])


def test_publication_reconciles_against_the_manifest(tmp_path):
    """Tables must never report counts the run manifest disagrees with."""
    output = tmp_path / "run"
    run_pipeline(output_dir=output, run_id="job-run-2", mode="fixture")
    gold_path = output / "gold" / "market_weather.jsonl"
    gold_path.write_text("".join(gold_path.read_text().splitlines(keepends=True)[:-1]))
    writer = RecordingWriter()
    with pytest.raises(RuntimeError, match="PUBLISH_RECONCILIATION_FAILED:gold"):
        publish_run(output, catalog="c", schema="s", run_id="job-run-2", writer=writer)
    # Reconciliation happens before any DDL or write.
    assert writer.statements == [] and writer.appends == []


def test_run_id_must_match_the_manifest(tmp_path):
    output = tmp_path / "run"
    run_pipeline(output_dir=output, run_id="job-run-3", mode="fixture")
    with pytest.raises(ValueError, match="RUN_ID_DOES_NOT_MATCH_MANIFEST"):
        publish_run(output, catalog="c", schema="s", run_id="job-run-4", writer=RecordingWriter())


def test_identifiers_and_run_ids_are_allowlisted(tmp_path):
    """Names reach DDL and DELETE predicates, so they are validated, not escaped."""
    output = tmp_path / "run"
    run_pipeline(output_dir=output, run_id="job-run-5", mode="fixture")
    for catalog, schema, run_id, expected in [
        ("bad-catalog", "s", "job-run-5", "INVALID_CATALOG"),
        ("c", "bad schema", "job-run-5", "INVALID_SCHEMA"),
        ("c", "s", "run'; DROP TABLE x --", "INVALID_RUN_ID"),
    ]:
        with pytest.raises(ValueError, match=expected):
            publish_run(output, catalog=catalog, schema=schema, run_id=run_id, writer=RecordingWriter())
    with pytest.raises(ValueError, match="INVALID_CATALOG"):
        create_table_statements("bad-catalog", "s")


def test_missing_manifest_fails_clearly(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError, match="RUN_MANIFEST_NOT_FOUND"):
        publish_run(tmp_path / "empty", catalog="c", schema="s", run_id="r1", writer=RecordingWriter())


def test_publication_does_not_mutate_run_evidence(tmp_path):
    """The Volume run directory stays the immutable source of truth."""
    output = tmp_path / "run"
    run_pipeline(output_dir=output, run_id="job-run-6", mode="fixture")
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    publish_run(output, catalog="c", schema="s", run_id="job-run-6", writer=RecordingWriter())
    after = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert before == after


def test_retry_after_publication_failure_resumes_instead_of_failing(tmp_path):
    """A publication failure must leave the run retryable.

    Observed in the workspace: attempt 0 wrote valid run evidence and then failed
    on a missing CREATE TABLE grant. The platform retried, the pipeline refused
    to overwrite write-once evidence, and the retry died with
    OUTPUT_ALREADY_EXISTS -- masking the permission error that actually needed
    fixing. The second attempt must reuse the evidence and retry publication.
    """
    from agentic_energy.cli import _completed_run

    output = tmp_path / "runs" / "456"
    output.mkdir(parents=True)
    (output / "manifest.json").write_text(
        json.dumps({"run_id": "456", "layers": {"bronze": 11, "silver": 6, "quarantine": 3, "gold": 3}}),
        encoding="utf-8",
    )
    assert _completed_run(str(output), "456") == {
        "bronze": 11,
        "silver": 6,
        "quarantine": 3,
        "gold": 3,
    }


def test_completed_run_refuses_evidence_from_a_different_run(tmp_path):
    """Adopting another run's directory would publish it under the wrong key."""
    from agentic_energy.cli import _completed_run

    output = tmp_path / "runs" / "456"
    output.mkdir(parents=True)
    (output / "manifest.json").write_text(
        json.dumps({"run_id": "999", "layers": {"bronze": 11}}), encoding="utf-8"
    )
    assert _completed_run(str(output), "456") is None


def test_completed_run_ignores_absent_or_unusable_evidence(tmp_path):
    """Without a trustworthy manifest the pipeline must run normally."""
    from agentic_energy.cli import _completed_run

    missing = tmp_path / "nope"
    assert _completed_run(str(missing), "456") is None

    corrupt = tmp_path / "runs" / "456"
    corrupt.mkdir(parents=True)
    (corrupt / "manifest.json").write_text("{not json", encoding="utf-8")
    assert _completed_run(str(corrupt), "456") is None

    # No run_id means no idempotency key, so resuming is never safe.
    assert _completed_run(str(corrupt), None) is None
