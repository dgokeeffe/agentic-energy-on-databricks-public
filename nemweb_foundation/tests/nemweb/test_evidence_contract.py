from __future__ import annotations

from dataclasses import asdict, fields, replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]

from agentic_energy.nemweb.evidence import (
    DatabricksCLI,
    EVIDENCE_SCHEMA_VERSION,
    EvidenceRow,
    SourceListing,
    SUBJECTS,
    capture_live_evidence,
    expectation_totals,
    extract_pipeline_error,
    render_markdown,
    resolve_archive_owners,
    subject_sql,
)


EXPECTED_FIELDS = {
    "subject", "cycle_started_at", "cycle_ended_at", "orchestration_run_id",
    "pipeline_update_id", "source_report_family", "newest_source_interval",
    "source_publication_timestamp", "source_publication_lag_seconds",
    "source_listing_checked_at", "source_listing_filename", "raw_zip_checksums",
    "landed_timestamp", "landed_row_count", "bronze_watermark", "bronze_row_count",
    "silver_watermark", "silver_row_count", "gold_watermark", "gold_row_count",
    "gold_publication_timestamp", "gold_content_fingerprint", "source_interval_to_gold_lag_seconds",
    "bronze_interval_to_gold_lag_seconds", "landed_to_gold_processing_lag_seconds",
    "duplicate_natural_key_count",
    "duplicate_natural_key_result", "quality_expectation_rule_count",
    "quality_expectation_passed_count", "quality_expectation_failed_count",
    "quality_expectation_result", "lander_outcome", "pipeline_outcome",
    "orchestration_outcome", "source_changed", "rows_changed",
    "freshness_check_result", "availability_note",
}


def _sql_response(gold_count: int = 10):
    names = [
        "newest_source_interval", "source_publication_timestamp", "landed_timestamp",
        "landed_row_count", "raw_zip_checksums", "bronze_watermark", "bronze_row_count",
        "silver_watermark", "silver_row_count", "gold_watermark", "gold_row_count",
        "gold_publication_timestamp", "gold_content_fingerprint", "duplicate_natural_key_count",
    ]
    values = [
        "2026-09-02 11:30:00+00:00", "2026-09-02 11:30:00+00:00",
        "2026-09-02 11:31:30+00:00", "12", "a" * 64,
        "2026-09-02 11:30:00+00:00", "12", "2026-09-02 11:30:00+00:00", "10",
        "2026-09-02 11:30:00+00:00", str(gold_count),
        "2026-09-02 11:32:00+00:00", "b" * 64, "0",
    ]
    return {
        "manifest": {"schema": {"columns": [{"name": name} for name in names]}},
        "result": {"data_array": [values]}, "status": {"state": "SUCCEEDED"},
    }


class FakeClient:
    def __init__(self):
        quality_names = sorted({name for spec in SUBJECTS for name in spec.quality_flow_names})
        self.events = [
            {
                "timestamp": "2026-09-02T11:32:00Z",
                "origin": {"update_id": "update-123", "flow_name": name},
                "details": {"flow_progress": {"data_quality": {"expectations": [
                    {"name": f"valid_{name}", "passed_records": 10, "failed_records": 0}
                ]}}},
            }
            for name in quality_names
        ]

    def poll_pipeline_update(self, pipeline_id, update_id, timeout_seconds):
        assert pipeline_id == "pipeline-1"
        assert update_id == "update-123"
        return {"update_id": update_id, "state": "COMPLETED"}

    def pipeline_events(self, pipeline_id, update_id):
        return self.events

    def get_job_run(self, run_id):
        assert run_id == "run-1"
        return {
            "start_time": 1788348600000, "end_time": 1788348900000,
            "state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"},
            "tasks": [
                {
                    "task_key": "land_current", "run_id": "owner-run",
                    "state": {"result_state": "SUCCESS"},
                },
                {"task_key": "publish_medallion", "state": {"result_state": "SUCCESS"}},
            ],
        }

    def get_pipeline(self, pipeline_id):
        assert pipeline_id == "pipeline-1"
        return {"spec": {"configuration": {
            "nemweb.landing_path": "/Volumes/daveok/nemweb_dev/nemweb_landing",
            "nemweb.source_mode": "live",
        }}}

    def execute_sql(self, sql, warehouse_id, catalog, schema, timeout_seconds):
        assert warehouse_id == "warehouse"
        # Expectation metrics are read from the UC pipeline event log because the
        # list-pipeline-events API omits the data_quality payload. That query is
        # answered separately from the per-subject watermark query.
        if "data_quality:expectations" in sql:
            assert "nemweb_pipeline_event_log_d4" in sql
            return {"result": {"data_array": [[
                "daveok.nemweb_dev.bronze_nem_dispatch_price",
                json.dumps([{
                    "name": "valid_dispatch_price_contract",
                    "dataset": "daveok.nemweb_dev.bronze_nem_dispatch_price",
                    "passed_records": 5,
                    "failed_records": 0,
                }]),
            ]]}}
        if "current_manifest AS" in sql:
            names = ["report_family", "source_archive_sha256", "owner_count", "owner_run_ids"]
            return {
                "manifest": {"schema": {"columns": [{"name": name} for name in names]}},
                "result": {"data_array": [
                    ["dispatchis", "a" * 64, "1", "owner-run"],
                    ["dispatch_scada", "a" * 64, "1", "owner-run"],
                ]},
            }
        assert "duplicate_count" in sql and "source_archive_sha256" in sql
        assert "ingestion_run_id = 'owner-run'" in sql
        return _sql_response()


def _listing(_spec):
    return SourceListing(
        "2026-09-02T11:33:00+00:00",
        "PUBLIC_DISPATCHIS_202609022130_000.zip",
        "2026-09-02T11:30:00+00:00",
        "2026-09-02T11:31:00+00:00",
    )


def _capture(previous=None):
    return capture_live_evidence(
        client=FakeClient(), catalog="daveok", schema="nemweb_dev", warehouse_id="warehouse",
        pipeline_id="pipeline-1", pipeline_update_id="update-123",
        orchestration_run_id="run-1", previous=previous or {}, listing_inspector=_listing,
    )


def test_evidence_contract_contains_every_mandatory_cycle_field():
    assert {field.name for field in fields(EvidenceRow)} == EXPECTED_FIELDS
    rows = _capture()
    assert len(rows) == 5
    assert {row.subject for row in rows} == {spec.subject for spec in SUBJECTS}
    for row in rows:
        row.validate()
        assert row.pipeline_update_id == "update-123"
        assert row.pipeline_outcome == "COMPLETED"
        assert row.raw_zip_checksums == ("a" * 64,)
        assert row.gold_content_fingerprint == "b" * 64
        assert row.duplicate_natural_key_result == "PASS"
        assert row.quality_expectation_rule_count >= 2
        assert row.quality_expectation_result == "PASS"
        assert row.source_publication_lag_seconds == 60
        assert row.source_interval_to_gold_lag_seconds == 120
        assert row.bronze_interval_to_gold_lag_seconds == 120
        assert row.landed_to_gold_processing_lag_seconds == 30


def test_capture_scopes_relisted_archives_to_their_first_landing_owner():
    """Exercise the deployed run_job_task shape through capture, not just helpers."""

    class RelistedClient(FakeClient):
        current_lander_run = "current-lander-run"
        first_owner_run = "first-owner-run"

        def get_job_run(self, run_id):
            assert run_id == "run-1"
            return {
                "start_time": 1788348600000, "end_time": 1788348900000,
                "state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"},
                "tasks": [
                    {
                        "task_key": "land_current", "run_id": "outer-task-run",
                        "start_time": 1788348610000, "end_time": 1788348700000,
                        "state": {"result_state": "SUCCESS"},
                        "run_job_task": {"job_id": 980288191176099},
                    },
                    {"task_key": "publish_medallion", "state": {"result_state": "SUCCESS"}},
                ],
            }

        def list_job_runs(self, job_id, limit=25):
            assert job_id == "980288191176099"
            return [{"run_id": self.current_lander_run, "start_time": 1788348650000}]

        def execute_sql(self, sql, warehouse_id, catalog, schema, timeout_seconds):
            if "current_manifest AS" in sql:
                assert f"manifests/{self.current_lander_run}.json" in sql
                names = ["report_family", "source_archive_sha256", "owner_count", "owner_run_ids"]
                return {
                    "manifest": {"schema": {"columns": [{"name": name} for name in names]}},
                    "result": {"data_array": [
                        ["dispatchis", "a" * 64, "1", self.first_owner_run],
                        ["dispatch_scada", "a" * 64, "1", self.first_owner_run],
                    ]},
                }
            if "duplicate_count" in sql:
                # This is the integration assertion: reverting capture to scope
                # by the current lander run makes this test fail immediately.
                assert f"ingestion_run_id = '{self.first_owner_run}'" in sql
                assert self.current_lander_run not in sql
                return _sql_response()
            return super().execute_sql(sql, warehouse_id, catalog, schema, timeout_seconds)

    rows = capture_live_evidence(
        client=RelistedClient(), catalog="daveok", schema="nemweb_dev",
        warehouse_id="warehouse", pipeline_id="pipeline-1",
        pipeline_update_id="update-123", orchestration_run_id="run-1",
        listing_inspector=_listing,
    )
    assert len(rows) == len(SUBJECTS)
    assert all(row.freshness_check_result == "PASS_SOURCE_CURRENT" for row in rows)


def test_snapshot_and_live_history_resolves_to_the_live_archive_owner():
    class CoexistingModesClient(FakeClient):
        def execute_sql(self, sql, warehouse_id, catalog, schema, timeout_seconds):
            if "current_manifest AS" in sql:
                # Every ownership source must exclude the supported snapshot
                # sibling before aggregating owners for live evidence.
                landed = sql.split("), landed AS (", 1)[1].split(")\nSELECT", 1)[0]
                sources = landed.split(" UNION ALL ")
                assert sources
                assert all("WHERE source_mode = 'live'" in source for source in sources)
                names = [
                    "report_family", "source_archive_sha256", "owner_count",
                    "owner_run_ids", "null_owner_count",
                ]
                return {
                    "manifest": {"schema": {"columns": [{"name": name} for name in names]}},
                    # These are the one live owners after same-checksum snapshot
                    # rows in the shared tables have been filtered out.
                    "result": {"data_array": [
                        ["dispatchis", "a" * 64, "1", "live-dispatch-owner", "0"],
                        ["dispatch_scada", "b" * 64, "1", "live-scada-owner", "0"],
                    ]},
                }
            return super().execute_sql(sql, warehouse_id, catalog, schema, timeout_seconds)

    assert resolve_archive_owners(
        CoexistingModesClient(), catalog="daveok", schema="nemweb_dev",
        warehouse_id="warehouse", pipeline_id="pipeline-1",
        lander_run_id="current-run", timeout_seconds=30,
    ) == {
        "dispatchis": (("a" * 64, "live-dispatch-owner"),),
        "dispatch_scada": (("b" * 64, "live-scada-owner"),),
    }


def test_archive_ownership_resolution_fails_closed_when_missing_ambiguous_or_null():
    class OwnershipClient(FakeClient):
        ownership_rows = []

        def execute_sql(self, sql, warehouse_id, catalog, schema, timeout_seconds):
            if "current_manifest AS" in sql:
                assert "WHERE source_mode = 'live'" in sql
                names = [
                    "report_family", "source_archive_sha256", "owner_count",
                    "owner_run_ids", "null_owner_count",
                ]
                return {
                    "manifest": {"schema": {"columns": [{"name": name} for name in names]}},
                    "result": {"data_array": self.ownership_rows},
                }
            return super().execute_sql(sql, warehouse_id, catalog, schema, timeout_seconds)

    client = OwnershipClient()
    with pytest.raises(RuntimeError, match="no owned critical archives"):
        resolve_archive_owners(
            client, catalog="daveok", schema="nemweb_dev",
            warehouse_id="warehouse", pipeline_id="pipeline-1",
            lander_run_id="current-run", timeout_seconds=30,
        )

    # Two distinct live owners remain ambiguous after snapshot rows are excluded.
    client.ownership_rows = [
        ["dispatchis", "a" * 64, "2", "first-live-owner,second-live-owner", "0"],
        ["dispatch_scada", "b" * 64, "1", "first-live-owner", "0"],
    ]
    with pytest.raises(RuntimeError, match="cannot determine one first-landing owner"):
        resolve_archive_owners(
            client, catalog="daveok", schema="nemweb_dev",
            warehouse_id="warehouse", pipeline_id="pipeline-1",
            lander_run_id="current-run", timeout_seconds=30,
        )

    # Spark COUNT(DISTINCT ...) and COLLECT_SET both ignore NULL, so the
    # separate positive count must prevent one valid owner from hiding a
    # matching row whose provenance is incomplete.
    client.ownership_rows = [
        ["dispatchis", "a" * 64, "1", "live-owner", "1"],
        ["dispatch_scada", "b" * 64, "1", "live-owner", "0"],
    ]
    with pytest.raises(RuntimeError, match="NULL ingestion_run_id"):
        resolve_archive_owners(
            client, catalog="daveok", schema="nemweb_dev",
            warehouse_id="warehouse", pipeline_id="pipeline-1",
            lander_run_id="current-run", timeout_seconds=30,
        )


def test_unchanged_source_is_valid_only_with_fresh_listing_check():
    first = _capture()
    previous = {row.subject: asdict(row) for row in first}
    second = _capture(previous)
    assert all(not row.source_changed and not row.rows_changed for row in second)
    assert all(row.freshness_check_result == "PASS_NO_NEW_SOURCE" for row in second)

    invalid = asdict(second[0])
    invalid["raw_zip_checksums"] = tuple(invalid["raw_zip_checksums"])
    invalid["freshness_check_result"] = "FAIL_SOURCE_AHEAD_OF_BRONZE"
    with pytest.raises(ValueError, match="source freshness check failed"):
        EvidenceRow(**invalid).validate()


def test_same_interval_gold_correction_is_detected_by_content_fingerprint():
    first = _capture()
    previous = {row.subject: asdict(row) for row in first}
    for row in previous.values():
        row["gold_content_fingerprint"] = "c" * 64
    corrected = _capture(previous)
    assert all(not row.source_changed for row in corrected)
    assert all(row.rows_changed for row in corrected)


def test_empty_or_stale_gold_cannot_pass_live_evidence() -> None:
    base = _capture()
    row = asdict(base[0])
    row["raw_zip_checksums"] = tuple(row["raw_zip_checksums"])
    row.update(
        gold_row_count=0,
        gold_watermark=None,
        gold_publication_timestamp=None,
    )
    with pytest.raises(ValueError, match="critical Gold subject must contain"):
        EvidenceRow(**row).validate()

    stale = asdict(base[0])
    stale["raw_zip_checksums"] = tuple(stale["raw_zip_checksums"])
    stale["gold_watermark"] = "2026-09-02 11:25:00+00:00"
    with pytest.raises(ValueError, match="Gold watermark does not match Bronze"):
        EvidenceRow(**stale).validate()

    # Binding rows are legitimately sparse. A newly inspected DISPATCHIS
    # interval may have no binding row, so an already-published non-empty Gold
    # table may retain an older watermark while Bronze proves source freshness.
    binding = next(row for row in base if row.subject == "binding dispatch constraints")
    sparse = replace(binding, gold_watermark="2026-09-02 11:25:00+00:00")
    sparse.validate()


def test_publication_chronology_and_reported_lags_fail_closed() -> None:
    row = _capture()[0]

    impossible = replace(
        row,
        gold_publication_timestamp="0001-01-01T00:00:00+00:00",
        source_interval_to_gold_lag_seconds=None,
        bronze_interval_to_gold_lag_seconds=None,
        landed_to_gold_processing_lag_seconds=None,
    )
    with pytest.raises(ValueError, match="Gold publication precedes"):
        impossible.validate()

    with pytest.raises(ValueError, match="source-to-Gold lag is mandatory"):
        replace(row, source_interval_to_gold_lag_seconds=None).validate()
    with pytest.raises(ValueError, match="Bronze-interval-to-Gold lag is mandatory"):
        replace(row, bronze_interval_to_gold_lag_seconds=None).validate()
    with pytest.raises(ValueError, match="landed-to-Gold processing lag is mandatory"):
        replace(row, landed_to_gold_processing_lag_seconds=None).validate()
    for field_name in (
        "source_interval_to_gold_lag_seconds",
        "bronze_interval_to_gold_lag_seconds",
        "landed_to_gold_processing_lag_seconds",
    ):
        with pytest.raises(ValueError, match="does not agree with its timestamps"):
            replace(row, **{field_name: getattr(row, field_name) + 1}).validate()


def test_pass_no_new_source_requires_unchanged_source_signature() -> None:
    row = _capture()[0]
    with pytest.raises(ValueError, match="requires an unchanged source signature"):
        replace(
            row,
            source_changed=True,
            rows_changed=True,
            freshness_check_result="PASS_NO_NEW_SOURCE",
        ).validate()

    # A sparse subject can have a changed source with an unchanged older Gold
    # watermark, but it is source-current rather than "no new source".
    binding = next(
        item for item in _capture()
        if item.subject == "binding dispatch constraints"
    )
    replace(
        binding,
        gold_watermark="2026-09-02 11:25:00+00:00",
        source_changed=True,
        rows_changed=False,
        freshness_check_result="PASS_SOURCE_CURRENT",
    ).validate()


def test_capture_records_bounded_post_cycle_listing_lead_explicitly():
    class LeadClient(FakeClient):
        def execute_sql(self, sql, warehouse_id, catalog, schema, timeout_seconds):
            response = super().execute_sql(sql, warehouse_id, catalog, schema, timeout_seconds)
            if "duplicate_count" in sql:
                # Publication occurs after the fresh listing interval, preserving
                # the independent source-to-Gold chronology invariant.
                response["result"]["data_array"][0][11] = "2026-09-02 11:42:00+00:00"
            return response

    def lead_listing(_spec):
        return SourceListing(
            "2026-09-02T11:42:30+00:00",
            "PUBLIC_DISPATCHIS_202609022140_000.zip",
            "2026-09-02T11:40:00+00:00",  # two intervals ahead of Bronze
            "2026-09-02T11:41:00+00:00",
        )

    rows = capture_live_evidence(
        client=LeadClient(), catalog="daveok", schema="nemweb_dev",
        warehouse_id="warehouse", pipeline_id="pipeline-1",
        pipeline_update_id="update-123", orchestration_run_id="run-1",
        listing_inspector=lead_listing,
    )
    assert all(row.freshness_check_result == "PASS_SOURCE_WITHIN_LEAD" for row in rows)
    assert all(row.newest_source_interval == "2026-09-02T11:40:00+00:00" for row in rows)
    assert all(row.source_interval_to_gold_lag_seconds == 120 for row in rows)
    assert all(row.bronze_interval_to_gold_lag_seconds == 720 for row in rows)


def test_tolerated_lead_preserves_signed_source_lag_and_represented_bronze_lag():
    row = _capture()[0]
    source = datetime(2026, 9, 2, 11, 40, tzinfo=timezone.utc)
    publication = datetime(2026, 9, 2, 11, 32, tzinfo=timezone.utc)
    landed = datetime.fromisoformat(row.landed_timestamp.replace(" ", "T"))
    tolerated = replace(
        row,
        newest_source_interval=source.isoformat(),
        gold_publication_timestamp=publication.isoformat(),
        source_interval_to_gold_lag_seconds=(publication - source).total_seconds(),
        bronze_interval_to_gold_lag_seconds=(
            publication - datetime(2026, 9, 2, 11, 30, tzinfo=timezone.utc)
        ).total_seconds(),
        landed_to_gold_processing_lag_seconds=(publication - landed).total_seconds(),
        freshness_check_result="PASS_SOURCE_WITHIN_LEAD",
    )

    tolerated.validate()
    assert tolerated.source_interval_to_gold_lag_seconds == -480
    assert tolerated.bronze_interval_to_gold_lag_seconds == 120


@pytest.mark.parametrize(
    ("lead_intervals", "freshness"),
    [
        (0, "PASS_SOURCE_CURRENT"),
        (1, "PASS_SOURCE_WITHIN_LEAD"),
        (2, "PASS_SOURCE_WITHIN_LEAD"),
    ],
)
def test_source_lead_up_to_two_dispatch_intervals_is_explicitly_tolerated(
    lead_intervals, freshness
):
    row = _capture()[0]
    source = datetime(2026, 9, 2, 11, 30, tzinfo=timezone.utc) + timedelta(
        minutes=5 * lead_intervals
    )
    publication = datetime(2026, 9, 2, 11, 45, tzinfo=timezone.utc)
    landed = datetime.fromisoformat(row.landed_timestamp.replace(" ", "T"))
    replace(
        row,
        newest_source_interval=source.isoformat(),
        gold_publication_timestamp=publication.isoformat(),
        source_interval_to_gold_lag_seconds=(publication - source).total_seconds(),
        bronze_interval_to_gold_lag_seconds=(
            publication - datetime(2026, 9, 2, 11, 30, tzinfo=timezone.utc)
        ).total_seconds(),
        landed_to_gold_processing_lag_seconds=(publication - landed).total_seconds(),
        freshness_check_result=freshness,
    ).validate()


def test_source_lead_over_two_intervals_and_dirty_tolerated_rows_fail_closed():
    row = _capture()[0]
    publication = datetime(2026, 9, 2, 11, 50, tzinfo=timezone.utc)
    landed = datetime.fromisoformat(row.landed_timestamp.replace(" ", "T"))

    def with_lead(intervals, **changes):
        source = datetime(2026, 9, 2, 11, 30, tzinfo=timezone.utc) + timedelta(
            minutes=5 * intervals
        )
        return replace(
            row,
            newest_source_interval=source.isoformat(),
            gold_publication_timestamp=publication.isoformat(),
            source_interval_to_gold_lag_seconds=(publication - source).total_seconds(),
            bronze_interval_to_gold_lag_seconds=(
                publication - datetime(2026, 9, 2, 11, 30, tzinfo=timezone.utc)
            ).total_seconds(),
            landed_to_gold_processing_lag_seconds=(publication - landed).total_seconds(),
            freshness_check_result="PASS_SOURCE_WITHIN_LEAD",
            **changes,
        )

    with pytest.raises(ValueError, match="more than two dispatch intervals"):
        with_lead(3).validate()
    with pytest.raises(ValueError, match="non-zero quality expectation failures"):
        with_lead(
            1,
            quality_expectation_failed_count=1,
            quality_expectation_result="FAIL",
        ).validate()
    with pytest.raises(ValueError, match="duplicate natural keys"):
        with_lead(
            1,
            duplicate_natural_key_count=1,
            duplicate_natural_key_result="FAIL",
        ).validate()


def test_failed_or_missing_expectations_and_duplicate_keys_fail_closed():
    row = asdict(_capture()[0])
    row["raw_zip_checksums"] = tuple(row["raw_zip_checksums"])
    row["quality_expectation_rule_count"] = 0
    row["quality_expectation_result"] = "FAIL"
    with pytest.raises(ValueError, match="missing quality expectation"):
        EvidenceRow(**row).validate()
    row = asdict(_capture()[0])
    row["raw_zip_checksums"] = tuple(row["raw_zip_checksums"])
    row["quality_expectation_failed_count"] = 1
    row["quality_expectation_result"] = "PASS_WITH_QUARANTINE"
    with pytest.raises(ValueError, match="non-zero quality expectation failures"):
        EvidenceRow(**row).validate()
    row = asdict(_capture()[0])
    row["raw_zip_checksums"] = tuple(row["raw_zip_checksums"])
    row["duplicate_natural_key_count"] = 1
    row["duplicate_natural_key_result"] = "FAIL"
    with pytest.raises(ValueError, match="duplicate natural keys"):
        EvidenceRow(**row).validate()


def test_pipeline_poller_uses_exact_update_and_extracts_underlying_exception(monkeypatch):
    calls = []
    responses = iter([
        {"update": {"update_id": "u1", "state": "RUNNING"}},
        {"update": {"update_id": "u1", "state": "COMPLETED"}},
    ])
    client = DatabricksCLI("daveok", runner=lambda args: calls.append(args) or next(responses))
    monkeypatch.setattr("agentic_energy.nemweb.evidence.time.sleep", lambda _seconds: None)
    update = client.poll_pipeline_update("p1", "u1", 5)
    assert update["state"] == "COMPLETED"
    assert all(call[1:5] == ["pipelines", "get-update", "p1", "u1"] for call in calls)

    events = [{"details": {"update_progress": {"error": {"exceptions": [
        {"message": "Auto Loader schema mismatch: missing REGIONID"}
    ]}}}}]
    assert extract_pipeline_error(events) == "Auto Loader schema mismatch: missing REGIONID"


def test_expectation_totals_sum_distinct_microbatch_events():
    events = [
        {"timestamp": "1", "origin": {"flow_name": "gold"}, "details": {"flow_progress": {"data_quality": {"expectations": [{"name": "key", "passed_records": 2, "failed_records": 1}]}}}},
        {"timestamp": "2", "origin": {"flow_name": "gold"}, "details": {"flow_progress": {"data_quality": {"expectations": [{"name": "key", "passed_records": 5, "failed_records": 0}]}}}},
    ]
    assert expectation_totals(events, ["gold"]) == (1, 7, 1)


def test_subject_sql_uses_fully_qualified_tables_and_actual_gold_keys():
    for spec in SUBJECTS:
        sql = subject_sql(spec, "daveok", "nemweb_dev")
        assert f"`daveok`.`nemweb_dev`.`{spec.gold_table}`" in sql
        assert all(f"`{key}`" in sql for key in spec.gold_natural_key)
        assert all(f"`{column}`" in sql for column in spec.gold_fingerprint_columns)
        assert "XXHASH64" in sql and "GROUP BY" in sql and "HAVING COUNT(*) > 1" in sql
    binding = next(spec for spec in SUBJECTS if spec.sparse_gold_intervals)
    binding_sql = subject_sql(binding, "daveok", "nemweb_dev")
    assert "MAX(source_interval_watermark)" in binding_sql
    assert "source_interval_watermark <= (SELECT interval_end FROM cycle)" in binding_sql
    with pytest.raises(ValueError, match="unsafe Databricks identifier"):
        subject_sql(SUBJECTS[0], "daveok", "schema; DROP TABLE x")


@pytest.mark.parametrize(
    ("archive_owners", "message"),
    [
        ((("not-a-sha", "owner-run"),), "unsafe source archive checksum"),
        ((("a" * 64, "owner' OR 1=1 --"),), "unsafe ingestion run ID"),
        ((), "archive ownership is empty"),
    ],
)
def test_subject_sql_rejects_unsafe_or_empty_archive_ownership(
    archive_owners, message
):
    with pytest.raises(ValueError, match=message):
        subject_sql(
            SUBJECTS[0], "daveok", "nemweb_dev",
            archive_owners=archive_owners,
        )


def test_subject_sql_rejects_unsafe_legacy_run_id_and_mixed_scopes():
    with pytest.raises(ValueError, match="unsafe ingestion run ID"):
        subject_sql(
            SUBJECTS[0], "daveok", "nemweb_dev",
            ingestion_run_id="owner' OR 1=1 --",
        )
    with pytest.raises(ValueError, match="either ingestion_run_id or archive_owners"):
        subject_sql(
            SUBJECTS[0], "daveok", "nemweb_dev",
            ingestion_run_id="owner-run",
            archive_owners=(("a" * 64, "owner-run"),),
        )


def test_markdown_is_copyable_and_has_no_private_workspace_location():
    markdown = render_markdown(_capture())
    assert markdown.count("\n") == 7
    assert "pipeline_update_id" in markdown
    assert "cloud.databricks.com" not in markdown
    assert "five-minute target or availability" in markdown


def test_live_validator_requires_three_consecutive_complete_cycles(tmp_path):
    first = _capture()
    start = datetime(2026, 9, 2, 11, 30, tzinfo=timezone.utc)
    all_rows = []
    for cycle in range(3):
        cycle_start = start + timedelta(minutes=5 * cycle)
        for row in first:
            all_rows.append(asdict(replace(
                row,
                cycle_started_at=cycle_start.isoformat(),
                cycle_ended_at=(cycle_start + timedelta(minutes=3)).isoformat(),
                orchestration_run_id=f"run-{cycle + 1}",
                pipeline_update_id=f"update-{cycle + 1}",
                source_changed=cycle == 0,
                rows_changed=cycle == 0,
                freshness_check_result="PASS_SOURCE_CURRENT" if cycle == 0 else "PASS_NO_NEW_SOURCE",
            )))
    path = tmp_path / "live.json"
    assert EVIDENCE_SCHEMA_VERSION == 2
    assert all("bronze_interval_to_gold_lag_seconds" in row for row in all_rows)
    path.write_text(
        json.dumps({"schema_version": EVIDENCE_SCHEMA_VERSION, "rows": all_rows}),
        encoding="utf-8",
    )
    validator_env = {**os.environ, "PYTHONPATH": str(ROOT)}
    completed = subprocess.run(
        [sys.executable, "nemweb_foundation/scripts/validate_nemweb_live.py", str(path)],
        capture_output=True, text=True, check=False, env=validator_env,
    )
    assert completed.returncode == 0, completed.stderr
    assert "3 consecutive cycle(s), 15 subject rows" in completed.stdout

    path.write_text(
        json.dumps({"schema_version": 1, "rows": all_rows}), encoding="utf-8"
    )
    old_contract = subprocess.run(
        [sys.executable, "nemweb_foundation/scripts/validate_nemweb_live.py", str(path)],
        capture_output=True, text=True, check=False, env=validator_env,
    )
    assert old_contract.returncode != 0
    assert "schema version must be 2" in old_contract.stderr

    reused_update_rows = [
        {**row, "pipeline_update_id": "one-reused-update"}
        for row in all_rows
    ]
    path.write_text(
        json.dumps({"schema_version": EVIDENCE_SCHEMA_VERSION, "rows": reused_update_rows}),
        encoding="utf-8",
    )
    reused = subprocess.run(
        [sys.executable, "nemweb_foundation/scripts/validate_nemweb_live.py", str(path)],
        capture_output=True, text=True, check=False, env=validator_env,
    )
    assert reused.returncode != 0
    assert "distinct pipeline update ID" in reused.stderr

    queued_rows = []
    for cycle, offset_seconds in enumerate((0, 470, 940)):
        cycle_start = start + timedelta(seconds=offset_seconds)
        for row in first:
            queued_rows.append(asdict(replace(
                row,
                cycle_started_at=cycle_start.isoformat(),
                cycle_ended_at=(cycle_start + timedelta(minutes=7)).isoformat(),
                orchestration_run_id=f"queued-run-{cycle + 1}",
                pipeline_update_id=f"queued-update-{cycle + 1}",
                source_changed=cycle == 0,
                rows_changed=cycle == 0,
                freshness_check_result="PASS_SOURCE_CURRENT" if cycle == 0 else "PASS_NO_NEW_SOURCE",
            )))
    path.write_text(
        json.dumps({"schema_version": EVIDENCE_SCHEMA_VERSION, "rows": queued_rows}),
        encoding="utf-8",
    )
    queued = subprocess.run(
        [sys.executable, "nemweb_foundation/scripts/validate_nemweb_live.py", str(path)],
        capture_output=True, text=True, check=False, env=validator_env,
    )
    assert queued.returncode == 0, queued.stderr

    skipped_rows = []
    for cycle, offset_seconds in enumerate((0, 300, 1000)):
        cycle_start = start + timedelta(seconds=offset_seconds)
        for row in first:
            skipped_rows.append(asdict(replace(
                row,
                cycle_started_at=cycle_start.isoformat(),
                cycle_ended_at=(cycle_start + timedelta(minutes=7)).isoformat(),
                orchestration_run_id=f"skipped-run-{cycle + 1}",
                pipeline_update_id=f"skipped-update-{cycle + 1}",
            )))
    path.write_text(
        json.dumps({"schema_version": EVIDENCE_SCHEMA_VERSION, "rows": skipped_rows}),
        encoding="utf-8",
    )
    skipped = subprocess.run(
        [sys.executable, "nemweb_foundation/scripts/validate_nemweb_live.py", str(path)],
        capture_output=True, text=True, check=False, env=validator_env,
    )
    assert skipped.returncode != 0
    assert "not consecutive" in skipped.stderr

    path.write_text(
        json.dumps({"schema_version": EVIDENCE_SCHEMA_VERSION, "rows": all_rows[:10]}),
        encoding="utf-8",
    )
    failed = subprocess.run(
        [sys.executable, "nemweb_foundation/scripts/validate_nemweb_live.py", str(path)],
        capture_output=True, text=True, check=False, env=validator_env,
    )
    assert failed.returncode != 0
    assert "need at least 3 cycles" in failed.stderr


def test_pipeline_events_uses_supported_filter_and_accepts_bare_list():
    """The CLI rejects `origin.update_id` and returns a bare list for events.

    Both were real defects found against Databricks CLI v1.14.1 on 2026-09-02:
    `--filter origin.update_id='...'` failed with "Invalid filter expression",
    and the successful response is a JSON array rather than an {"events": [...]}
    envelope.
    """

    from agentic_energy.nemweb.evidence import DatabricksCLI

    captured: dict[str, list[str]] = {}

    def runner(args):
        captured["args"] = args
        return [{"origin": {"update_id": "u1"}, "event_type": "update_progress"}]

    client = DatabricksCLI(profile="daveok", runner=runner)
    events = client.pipeline_events("p1", "u1")

    assert events and events[0]["origin"]["update_id"] == "u1"
    joined = " ".join(captured["args"])
    assert "update_id = 'u1'" in joined
    assert "origin.update_id" not in joined


def test_pipeline_events_respects_the_250_event_page_cap():
    """CLI 1.14.1 rejects --max-results above 250 for pipeline events."""

    from agentic_energy.nemweb.evidence import DatabricksCLI

    captured: dict[str, list[str]] = {}

    def runner(args):
        captured["args"] = args
        return []

    DatabricksCLI(profile="daveok", runner=runner).pipeline_events("p1", "u1")
    args = captured["args"]
    cap = int(args[args.index("--max-results") + 1])
    assert cap <= 250
