"""Evidence contracts and live capture for the governed NEMWEB workflow.

This module deliberately separates evidence from resource state.  It polls one
explicit Lakeflow update ID, inspects that update's events, and queries data
watermarks and counts through the SQL Statement Execution API.  A green job or
pipeline resource state is never treated as proof that data reached Gold.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import subprocess
import time
import urllib.parse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .contracts import NEM_TIMEZONE
from .lander import LanderLimits, NemwebClient

REQUIRED_PROFILE = "daveok"
EVIDENCE_SCHEMA_VERSION = 2
TERMINAL_PIPELINE_STATES = frozenset({"COMPLETED", "FAILED", "CANCELED"})
TERMINAL_JOB_STATES = frozenset({"TERMINATED", "SKIPPED", "INTERNAL_ERROR"})
_SUCCESS_JOB_RESULTS = frozenset({"SUCCESS", "SUCCESS_WITH_FAILURES"})
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_PUBLICATION_TOKEN = re.compile(r"(20\d{10})")
# Capture inspects the live listing after a cycle that can take longer than
# AEMO's five-minute publication cadence.  Two intervals cover that unavoidable
# race while still failing closed once the source is materially ahead.
DISPATCH_INTERVAL = timedelta(minutes=5)
MAX_SOURCE_LEAD_INTERVALS = 2
MAX_SOURCE_LEAD = DISPATCH_INTERVAL * MAX_SOURCE_LEAD_INTERVALS


@dataclass(frozen=True)
class SubjectSpec:
    subject: str
    source_report_family: str
    listing_url: str
    listing_prefix: str
    bronze_tables: tuple[str, ...]
    quarantine_tables: tuple[str, ...]
    silver_table: str
    gold_table: str
    gold_natural_key: tuple[str, ...]
    gold_fingerprint_columns: tuple[str, ...]
    quality_flow_names: tuple[str, ...]
    availability_note: str = ""
    sparse_gold_intervals: bool = False


SUBJECTS: tuple[SubjectSpec, ...] = (
    SubjectSpec(
        "regional dispatch price and demand", "dispatchis",
        "https://www.nemweb.com.au/REPORTS/CURRENT/DispatchIS_Reports/", "PUBLIC_DISPATCHIS_",
        ("bronze_nem_dispatch_price", "bronze_nem_dispatch_region_sum"),
        ("quarantine_nem_dispatch_price", "quarantine_nem_dispatch_region_sum"),
        "silver_nem_region_dispatch", "gold_nem_region_dispatch_5min",
        ("interval_end", "region_id", "intervention"),
        ("interval_end", "region_id", "intervention", "is_effective_run", "rrp_aud_per_mwh", "total_demand_mw"),
        ("bronze_nem_dispatch_price", "bronze_nem_dispatch_region_sum", "gold_nem_region_dispatch_5min"),
    ),
    SubjectSpec(
        "unit/facility dispatch", "dispatch_scada",
        "https://www.nemweb.com.au/REPORTS/CURRENT/Dispatch_SCADA/", "PUBLIC_DISPATCHSCADA_",
        ("bronze_nem_dispatch_unit_scada",), ("quarantine_nem_dispatch_unit_scada",),
        "silver_nem_dispatch_unit_scada", "gold_nem_unit_dispatch_5min",
        ("interval_end", "duid"),
        ("interval_end", "duid", "actual_generation_mw", "region_id", "fuel_type", "dimension_match_status"),
        ("bronze_nem_dispatch_unit_scada", "gold_nem_unit_dispatch_5min"),
        "SCADA actual_generation_mw; Current does not publish five-minute target or availability",
    ),
    SubjectSpec(
        "SCADA generation by region and fuel", "dispatch_scada",
        "https://www.nemweb.com.au/REPORTS/CURRENT/Dispatch_SCADA/", "PUBLIC_DISPATCHSCADA_",
        ("bronze_nem_dispatch_unit_scada",), ("quarantine_nem_dispatch_unit_scada",),
        "silver_nem_dispatch_unit_scada", "gold_nem_scada_generation_5min",
        ("interval_end", "region_id", "fuel_type"),
        ("interval_end", "region_id", "fuel_type", "actual_generation_mw", "facility_count", "partially_enriched_facility_count"),
        ("bronze_nem_dispatch_unit_scada", "gold_nem_scada_generation_5min"),
    ),
    SubjectSpec(
        "binding dispatch constraints", "dispatchis",
        "https://www.nemweb.com.au/REPORTS/CURRENT/DispatchIS_Reports/", "PUBLIC_DISPATCHIS_",
        ("bronze_nem_dispatch_constraint",), ("quarantine_nem_dispatch_constraint",),
        "silver_nem_dispatch_constraint", "gold_nem_binding_constraints_5min",
        ("interval_end", "constraint_id", "intervention"),
        ("interval_end", "constraint_id", "intervention", "is_effective_run", "rhs", "lhs", "marginal_value", "violation_degree"),
        ("bronze_nem_dispatch_constraint", "gold_nem_binding_constraints_5min"),
        sparse_gold_intervals=True,
    ),
    SubjectSpec(
        "interconnector flows", "dispatchis",
        "https://www.nemweb.com.au/REPORTS/CURRENT/DispatchIS_Reports/", "PUBLIC_DISPATCHIS_",
        ("bronze_nem_dispatch_interconnector_res",), ("quarantine_nem_dispatch_interconnector_res",),
        "silver_nem_interconnector_flow", "gold_nem_interconnector_flows_5min",
        ("interval_end", "interconnector_id", "intervention"),
        ("interval_end", "interconnector_id", "intervention", "is_effective_run", "mw_flow", "metered_mw_flow", "mw_losses"),
        ("bronze_nem_dispatch_interconnector_res", "gold_nem_interconnector_flows_5min"),
    ),
)


@dataclass(frozen=True)
class SourceListing:
    checked_at: str
    filename: str
    source_interval: str
    publication_timestamp: str


@dataclass(frozen=True)
class EvidenceRow:
    subject: str
    cycle_started_at: str
    cycle_ended_at: str
    orchestration_run_id: str
    pipeline_update_id: str
    source_report_family: str
    newest_source_interval: str | None
    source_publication_timestamp: str | None
    source_publication_lag_seconds: float | None
    source_listing_checked_at: str
    source_listing_filename: str
    raw_zip_checksums: tuple[str, ...]
    landed_timestamp: str | None
    landed_row_count: int
    bronze_watermark: str | None
    bronze_row_count: int
    silver_watermark: str | None
    silver_row_count: int
    gold_watermark: str | None
    gold_row_count: int
    gold_publication_timestamp: str | None
    gold_content_fingerprint: str
    source_interval_to_gold_lag_seconds: float | None
    bronze_interval_to_gold_lag_seconds: float | None
    landed_to_gold_processing_lag_seconds: float | None
    duplicate_natural_key_count: int
    duplicate_natural_key_result: str
    quality_expectation_rule_count: int
    quality_expectation_passed_count: int
    quality_expectation_failed_count: int
    quality_expectation_result: str
    lander_outcome: str
    pipeline_outcome: str
    orchestration_outcome: str
    source_changed: bool
    rows_changed: bool
    freshness_check_result: str
    availability_note: str

    def validate(self) -> None:
        if not self.pipeline_update_id:
            raise ValueError("pipeline_update_id is mandatory")
        if self.pipeline_outcome != "COMPLETED":
            raise ValueError("evidence row cannot pass unless the exact pipeline update COMPLETED")
        if self.duplicate_natural_key_count != 0 or self.duplicate_natural_key_result != "PASS":
            raise ValueError("duplicate natural keys fail evidence")
        if self.quality_expectation_rule_count < 1:
            raise ValueError("missing quality expectation metrics fail evidence")
        if self.quality_expectation_failed_count != 0:
            raise ValueError("non-zero quality expectation failures fail evidence")
        if self.quality_expectation_result != "PASS":
            raise ValueError("quality expectations must pass with zero failures")
        if self.gold_row_count < 1:
            raise ValueError("critical Gold subject must contain published rows")
        if not self.gold_watermark:
            raise ValueError("critical Gold subject must have a watermark")
        if not self.gold_publication_timestamp:
            raise ValueError("critical Gold subject must have a publication timestamp")
        source = _parse_timestamp(self.newest_source_interval)
        bronze = _parse_timestamp(self.bronze_watermark)
        gold = _parse_timestamp(self.gold_watermark)
        publication = _parse_timestamp(self.gold_publication_timestamp)
        landed = _parse_timestamp(self.landed_timestamp)
        if not all((source, bronze, gold, publication, landed)):
            raise ValueError(
                "source, landing, Bronze and Gold timestamps must be parseable"
            )
        source_lead = source - bronze
        if source_lead > MAX_SOURCE_LEAD:
            raise ValueError("newest source interval is more than two dispatch intervals ahead of Bronze")
        if source_lead > timedelta(0) and self.freshness_check_result != "PASS_SOURCE_WITHIN_LEAD":
            raise ValueError("a tolerated source lead must be recorded explicitly")
        if source_lead <= timedelta(0) and self.freshness_check_result == "PASS_SOURCE_WITHIN_LEAD":
            raise ValueError("PASS_SOURCE_WITHIN_LEAD requires source to be ahead of Bronze")

        # A closure artifact must prove publication chronology, not merely carry
        # parseable timestamp strings. Each lag is mandatory and must agree with
        # the timestamp pair named by its field. Spark DATE_FORMAT emits
        # millisecond precision, so a 1 ms tolerance covers only serialization
        # rounding and cannot conceal a materially forged lag.
        expected_source_lag = (publication - source).total_seconds()
        expected_bronze_lag = (publication - bronze).total_seconds()
        expected_landed_lag = (publication - landed).total_seconds()
        # A bounded post-cycle listing lead can legitimately put the newest
        # source interval after this cycle's Gold publication. Preserve that
        # signed source-to-Gold value; the separate Bronze-relative lag proves
        # processing chronology for the interval the cycle actually represented.
        if expected_source_lag < 0 and self.freshness_check_result != "PASS_SOURCE_WITHIN_LEAD":
            raise ValueError("Gold publication precedes its source interval")
        if expected_bronze_lag < 0:
            raise ValueError("Gold publication precedes its Bronze interval")
        if expected_landed_lag < 0:
            raise ValueError("Gold publication precedes landing")
        if self.source_interval_to_gold_lag_seconds is None:
            raise ValueError("source-to-Gold lag is mandatory")
        if self.bronze_interval_to_gold_lag_seconds is None:
            raise ValueError("Bronze-interval-to-Gold lag is mandatory")
        if self.landed_to_gold_processing_lag_seconds is None:
            raise ValueError("landed-to-Gold processing lag is mandatory")
        for label, reported, expected in (
            (
                "source-to-Gold lag",
                self.source_interval_to_gold_lag_seconds,
                expected_source_lag,
            ),
            (
                "Bronze-interval-to-Gold lag",
                self.bronze_interval_to_gold_lag_seconds,
                expected_bronze_lag,
            ),
            (
                "landed-to-Gold processing lag",
                self.landed_to_gold_processing_lag_seconds,
                expected_landed_lag,
            ),
        ):
            if not math.isfinite(reported) or abs(reported - expected) > 0.001:
                raise ValueError(f"{label} does not agree with its timestamps")
        spec = next((item for item in SUBJECTS if item.subject == self.subject), None)
        if spec is None:
            raise ValueError(f"unknown critical evidence subject: {self.subject}")
        if spec.sparse_gold_intervals:
            # Binding constraints are sparse: AEMO can publish a dispatch interval
            # with no binding row. The existing non-empty Gold table may therefore
            # retain an older watermark, but it must never claim an interval newer
            # than the Bronze source inspected by this cycle.
            if gold > bronze:
                raise ValueError("sparse Gold watermark is ahead of Bronze")
        elif gold != bronze:
            raise ValueError("critical Gold watermark does not match Bronze")
        if self.lander_outcome != "SUCCESS" or self.orchestration_outcome != "SUCCESS":
            raise ValueError("lander and orchestration must both succeed")
        if not self.freshness_check_result.startswith("PASS_"):
            raise ValueError("source freshness check failed")
        if (
            self.freshness_check_result == "PASS_NO_NEW_SOURCE"
            and self.source_changed
        ):
            raise ValueError(
                "PASS_NO_NEW_SOURCE requires an unchanged source signature"
            )
        if not self.rows_changed and not self.source_changed and self.freshness_check_result != "PASS_NO_NEW_SOURCE":
            raise ValueError("a no-change cycle requires an unchanged listing and successful freshness check")


class DatabricksCLI:
    """Small injectable CLI adapter; every workspace call carries a profile."""

    def __init__(self, profile: str, runner: Callable[[list[str]], dict[str, Any]] | None = None):
        if profile != REQUIRED_PROFILE:
            raise ValueError(f"workspace-aware capture requires profile {REQUIRED_PROFILE}")
        self.profile = profile
        self._runner = runner or self._run

    @staticmethod
    def _run(args: list[str]) -> dict[str, Any]:
        completed = subprocess.run(args, capture_output=True, text=True, check=False)
        if completed.returncode:
            raise RuntimeError(f"Databricks CLI transport failed ({completed.returncode}): {completed.stderr.strip()}")
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Databricks CLI returned non-JSON output") from exc

    def call(self, args: Sequence[str]) -> dict[str, Any]:
        return self._runner(["databricks", *args, "--profile", self.profile, "-o", "json"])

    def poll_pipeline_update(self, pipeline_id: str, update_id: str, timeout_seconds: int) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while True:
            response = self.call(["pipelines", "get-update", pipeline_id, update_id])
            update = response.get("update", response)
            state = update.get("state")
            if state in TERMINAL_PIPELINE_STATES:
                if state != "COMPLETED":
                    events = self.pipeline_events(pipeline_id, update_id)
                    message = extract_pipeline_error(events) or "no error.exceptions[0].message found"
                    raise RuntimeError(f"pipeline update {update_id} ended {state}: {message}")
                return update
            if time.monotonic() >= deadline:
                raise TimeoutError(f"pipeline update {update_id} did not reach a terminal state")
            time.sleep(2)

    def pipeline_events(self, pipeline_id: str, update_id: str) -> list[dict[str, Any]]:
        # The supported filter attribute is `update_id`, not `origin.update_id`;
        # the latter is rejected with "Invalid filter expression" by CLI 1.14.1.
        # The CLI also returns a bare JSON list here rather than an {"events": []}
        # envelope, so both shapes are accepted. --max-results is capped at 250
        # ("Cannot have more than 250 events per page"); the filter already scopes
        # the response to this single update, which stays well inside that cap.
        response = self.call([
            "pipelines", "list-pipeline-events", pipeline_id,
            "--filter", f"update_id = '{update_id}'", "--max-results", "250",
        ])
        if isinstance(response, list):
            events = response
        elif isinstance(response, dict):
            events = response.get("events", [])
        else:
            raise RuntimeError("pipeline event response has no events list")
        if not isinstance(events, list):
            raise RuntimeError("pipeline event response has no events list")
        foreign = [e for e in events if e.get("origin", {}).get("update_id") not in (None, update_id)]
        if foreign:
            raise RuntimeError("pipeline event response included a different update ID")
        return events

    def list_job_runs(self, job_id: str, limit: int = 25) -> list[dict[str, Any]]:
        """Return recent runs for one job, newest first."""
        response = self.call(["jobs", "list-runs", "--job-id", str(job_id), "--limit", str(limit)])
        runs = response if isinstance(response, list) else response.get("runs", [])
        if not isinstance(runs, list):
            raise RuntimeError("job run listing has no runs list")
        return runs

    def get_job_run(self, run_id: str) -> dict[str, Any]:
        return self.call(["jobs", "get-run", str(run_id)])

    def get_pipeline(self, pipeline_id: str) -> dict[str, Any]:
        return self.call(["pipelines", "get", pipeline_id])

    def execute_sql(self, sql: str, warehouse_id: str, catalog: str, schema: str, timeout_seconds: int) -> dict[str, Any]:
        payload = {
            "warehouse_id": warehouse_id, "catalog": catalog, "schema": schema,
            "statement": sql, "wait_timeout": "0s", "disposition": "INLINE", "format": "JSON_ARRAY",
        }
        response = self.call(["api", "post", "/api/2.0/sql/statements", "--json", json.dumps(payload)])
        statement_id = response.get("statement_id")
        if not statement_id:
            raise RuntimeError("SQL submission returned no statement_id")
        deadline = time.monotonic() + timeout_seconds
        while response.get("status", {}).get("state") not in {"SUCCEEDED", "FAILED", "CANCELED", "CLOSED"}:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"SQL statement {statement_id} did not reach a terminal state")
            time.sleep(2)
            response = self.call(["api", "get", f"/api/2.0/sql/statements/{statement_id}"])
        state = response.get("status", {}).get("state")
        if state != "SUCCEEDED":
            raise RuntimeError(f"SQL statement {statement_id} ended {state}: {response.get('status', {}).get('error', {})}")
        return response


def _walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def extract_pipeline_error(events: Sequence[Mapping[str, Any]]) -> str | None:
    """Extract the underlying exception, not the top-level update message."""
    for event in reversed(events):
        for node in _walk_dicts(event):
            exceptions = node.get("exceptions")
            if isinstance(exceptions, list) and exceptions:
                first = exceptions[0]
                if isinstance(first, dict) and isinstance(first.get("message"), str):
                    return first["message"]
    return None


def expectation_totals(events: Sequence[Mapping[str, Any]], flow_names: Sequence[str]) -> tuple[int, int, int]:
    """Sum per-microbatch expectation counters for the exact update."""
    # Flow identities are configured as bare table names, but the UC event log
    # reports fully-qualified `catalog.schema.table` flow names. Compare on the
    # final name segment so both sources match the same subject.
    wanted = {name.rsplit(".", 1)[-1] for name in flow_names}
    identities: set[tuple[str, str]] = set()
    passed_total = 0
    failed_total = 0
    for event in events:
        origin = event.get("origin", {})
        flow = origin.get("flow_name") or origin.get("dataset_name") or ""
        details = event.get("details", {})
        progress = details.get("flow_progress", {}) if isinstance(details, dict) else {}
        flow = flow or progress.get("name", "")
        if wanted and flow.rsplit(".", 1)[-1] not in wanted:
            continue
        quality = progress.get("data_quality", {}) if isinstance(progress, dict) else {}
        expectations = quality.get("expectations", []) if isinstance(quality, dict) else []
        for item in expectations if isinstance(expectations, list) else []:
            name = str(item.get("name", "unnamed"))
            passed = int(item.get("passed_records", 0) or 0)
            failed = int(item.get("failed_records", 0) or 0)
            identities.add((flow, name))
            passed_total += passed
            failed_total += failed
    return len(identities), passed_total, failed_total


EVENT_LOG_TABLE = "nemweb_pipeline_event_log_d4"


def event_log_expectation_events(
    client: DatabricksCLI,
    *,
    catalog: str,
    schema: str,
    warehouse_id: str,
    update_id: str,
    timeout_seconds: int = 600,
) -> list[dict[str, Any]]:
    """Read per-expectation metrics for one update from the UC event log.

    Returns rows shaped like list-pipeline-events entries so ``expectation_totals``
    can consume both sources identically. Returns an empty list when the event log
    table does not exist yet, so a caller can still fail closed on a missing rule
    count rather than crash.
    """

    _quote_identifier(catalog)
    _quote_identifier(schema)
    table = f"`{catalog}`.`{schema}`.`{EVENT_LOG_TABLE}`"
    sql = (
        "SELECT origin.flow_name AS flow_name, "
        "details:flow_progress.data_quality:expectations AS expectations "
        f"FROM {table} "
        f"WHERE origin.update_id = '{update_id}' "
        "AND details:flow_progress.data_quality:expectations IS NOT NULL"
    )
    try:
        response = client.execute_sql(sql, warehouse_id, catalog, schema, timeout_seconds)
    except RuntimeError as exc:
        if "TABLE_OR_VIEW_NOT_FOUND" in str(exc):
            return []
        raise
    rows = (response.get("result", {}) or {}).get("data_array") or []
    events: list[dict[str, Any]] = []
    for row in rows:
        flow_name, payload = row[0], row[1]
        if not payload:
            continue
        try:
            expectations = json.loads(payload)
        except (TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("event log expectations payload is not valid JSON") from exc
        events.append({
            "origin": {"flow_name": flow_name, "update_id": update_id},
            "details": {
                "flow_progress": {"data_quality": {"expectations": expectations}}
            },
        })
    return events


def inspect_source_listing(spec: SubjectSpec, *, client: NemwebClient | None = None) -> SourceListing:
    client = client or NemwebClient(LanderLimits(max_files_per_cycle=5))
    urls = client.list_archives(spec.listing_url, prefix=spec.listing_prefix)
    if not urls:
        raise RuntimeError(f"source freshness check found no {spec.source_report_family} archives")
    filename = Path(urllib.parse.urlsplit(urls[-1]).path).name
    match = _PUBLICATION_TOKEN.search(filename)
    if not match:
        raise RuntimeError(f"latest source filename has no 12-digit market interval: {filename}")
    market = datetime.strptime(match.group(1), "%Y%m%d%H%M").replace(tzinfo=NEM_TIMEZONE)

    # The filename token is the report interval, not its publication time.  The
    # public NEMWEB listing separately exposes the server's publication/last-
    # modified timestamp.  Capture both so source lag is not conflated with
    # processing lag.  NEMWEB listing timestamps follow NEM market time (AEST).
    listing_text = html.unescape(client.fetch_text(spec.listing_url))
    stamp_pattern = re.compile(
        r"([A-Z][a-z]+,\s+[A-Z][a-z]+\s+\d{1,2},\s+20\d{2}\s+\d{1,2}:\d{2}\s+[AP]M)"
        r"\s+\d+\s+<A HREF=\"[^\"]*/" + re.escape(filename) + r"\"",
        re.IGNORECASE,
    )
    stamp_match = stamp_pattern.search(listing_text)
    if not stamp_match:
        raise RuntimeError(f"source listing has no publication timestamp for {filename}")
    # Parse independently of the process locale; IIS uses English month names.
    stamp = stamp_match.group(1)
    parts = re.fullmatch(
        r"[A-Za-z]+,\s+([A-Za-z]+)\s+(\d{1,2}),\s+(20\d{2})\s+"
        r"(\d{1,2}):(\d{2})\s+([AP]M)", stamp, re.IGNORECASE,
    )
    if not parts:
        raise RuntimeError(f"unrecognised source listing timestamp for {filename}")
    months = {name: index for index, name in enumerate(
        ("january", "february", "march", "april", "may", "june",
         "july", "august", "september", "october", "november", "december"), 1
    )}
    month = months.get(parts.group(1).lower())
    if month is None:
        raise RuntimeError(f"unrecognised source listing month for {filename}")
    hour = int(parts.group(4)) % 12 + (12 if parts.group(6).upper() == "PM" else 0)
    published_market = datetime(
        int(parts.group(3)), month, int(parts.group(2)), hour,
        int(parts.group(5)), tzinfo=NEM_TIMEZONE,
    )
    return SourceListing(
        datetime.now(timezone.utc).isoformat(), filename,
        market.astimezone(timezone.utc).isoformat(),
        published_market.astimezone(timezone.utc).isoformat(),
    )


def _quote_identifier(value: str) -> str:
    if not _SAFE_IDENTIFIER.fullmatch(value):
        raise ValueError(f"unsafe Databricks identifier: {value!r}")
    return f"`{value}`"


def _table(catalog: str, schema: str, table: str) -> str:
    return ".".join((_quote_identifier(catalog), _quote_identifier(schema), _quote_identifier(table)))


def archive_ownership_sql(
    catalog: str, schema: str, landing_root: str, lander_run_id: str
) -> str:
    """Resolve each current-manifest checksum to its first Bronze owner.

    Auto Loader emits one canonical parsed input per checksum.  A later lander
    manifest can therefore relist bytes whose Bronze rows retain the first
    landing's ``ingestion_run_id``.  Joining the current manifest to published
    Bronze/quarantine provenance preserves that ownership instead of assuming
    the current lander run created new rows.
    """
    if not re.fullmatch(r"/Volumes/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/live", landing_root):
        raise ValueError("live landing root must be a safe Unity Catalog Volume path")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", lander_run_id):
        raise ValueError("unsafe ingestion run ID")
    sources: list[str] = []
    seen: set[tuple[str, str]] = set()
    for spec in SUBJECTS:
        for table in (*spec.bronze_tables, *spec.quarantine_tables):
            identity = (spec.source_report_family, table)
            if identity in seen:
                continue
            seen.add(identity)
            sources.append(
                f"SELECT '{spec.source_report_family}' AS report_family, "
                "ingestion_run_id, source_archive_sha256 "
                f"FROM {_table(catalog, schema, table)} "
                "WHERE source_mode = 'live'"
            )
    landed = " UNION ALL ".join(sources)
    families = ", ".join(f"'{family}'" for family in sorted({s.source_report_family for s in SUBJECTS}))
    manifest_path = f"{landing_root}/manifests/{lander_run_id}.json"
    return f"""WITH current_manifest AS (
  SELECT archive.report_family AS report_family,
         archive.source_archive_sha256 AS source_archive_sha256
  FROM (SELECT EXPLODE(archives) AS archive FROM json.`{manifest_path}`)
  WHERE archive.report_family IN ({families})
), landed AS ({landed})
SELECT current_manifest.report_family,
       current_manifest.source_archive_sha256,
       COUNT(DISTINCT landed.ingestion_run_id) AS owner_count,
       CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(landed.ingestion_run_id))) AS owner_run_ids,
       SUM(CASE WHEN landed.source_archive_sha256 IS NOT NULL
                     AND landed.ingestion_run_id IS NULL THEN 1 ELSE 0 END) AS null_owner_count
FROM current_manifest
LEFT JOIN landed
  ON landed.report_family = current_manifest.report_family
 AND landed.source_archive_sha256 = current_manifest.source_archive_sha256
GROUP BY current_manifest.report_family, current_manifest.source_archive_sha256
ORDER BY current_manifest.report_family, current_manifest.source_archive_sha256"""


def resolve_archive_owners(
    client: "DatabricksCLI",
    *,
    catalog: str,
    schema: str,
    warehouse_id: str,
    pipeline_id: str,
    lander_run_id: str,
    timeout_seconds: int,
) -> dict[str, tuple[tuple[str, str], ...]]:
    """Return current-cycle checksums paired with their one published owner.

    Missing checksums, owners, or ambiguous ownership fail closed.  In
    particular, an empty current manifest is never reinterpreted as a healthy
    no-new-source cycle.
    """
    pipeline = client.get_pipeline(pipeline_id)
    configuration = (pipeline.get("spec", pipeline).get("configuration") or {})
    landing_parent = str(configuration.get("nemweb.landing_path") or "").rstrip("/")
    if configuration.get("nemweb.source_mode") != "live":
        raise RuntimeError("live evidence requires pipeline configuration nemweb.source_mode=live")
    landing_root = f"{landing_parent}/live"
    response = client.execute_sql(
        archive_ownership_sql(catalog, schema, landing_root, lander_run_id),
        warehouse_id, catalog, schema, timeout_seconds,
    )
    columns = response.get("manifest", {}).get("schema", {}).get("columns", [])
    names = [item.get("name") for item in columns]
    values = response.get("result", {}).get("data_array", [])
    expected_families = {spec.source_report_family for spec in SUBJECTS}
    owners: dict[str, list[tuple[str, str]]] = {}
    for value in values:
        row = dict(zip(names, value, strict=True))
        family = str(row.get("report_family") or "")
        checksum = str(row.get("source_archive_sha256") or "")
        owner_count = int(row.get("owner_count") or 0)
        owner_ids = tuple(filter(None, str(row.get("owner_run_ids") or "").split(",")))
        null_owner_count = int(row.get("null_owner_count") or 0)
        if family not in expected_families:
            raise RuntimeError(f"current manifest returned unexpected critical family {family!r}")
        if not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise RuntimeError(f"current manifest has invalid checksum for {family!r}")
        if null_owner_count:
            raise RuntimeError(
                f"cannot determine one first-landing owner for {family} checksum {checksum}; "
                f"found {null_owner_count} matched rows with NULL ingestion_run_id"
            )
        if owner_count != 1 or len(owner_ids) != 1:
            raise RuntimeError(
                f"cannot determine one first-landing owner for {family} checksum {checksum}; "
                f"found {owner_count} owners ({', '.join(owner_ids) or 'none'})"
            )
        owners.setdefault(family, []).append((checksum, owner_ids[0]))
    missing = sorted(expected_families - owners.keys())
    if missing:
        raise RuntimeError(
            "current lander manifest has no owned critical archives for: " + ", ".join(missing)
        )
    return {family: tuple(entries) for family, entries in owners.items()}


def subject_sql(
    spec: SubjectSpec,
    catalog: str,
    schema: str,
    ingestion_run_id: str | None = None,
    *,
    archive_owners: Sequence[tuple[str, str]] | None = None,
) -> str:
    run_filter = ""
    if ingestion_run_id is not None and archive_owners is not None:
        raise ValueError("provide either ingestion_run_id or archive_owners, not both")
    if archive_owners is not None:
        if not archive_owners:
            raise ValueError("archive ownership is empty")
        clauses: list[str] = []
        for checksum, owner_run_id in archive_owners:
            if not re.fullmatch(r"[0-9a-f]{64}", checksum):
                raise ValueError("unsafe source archive checksum")
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner_run_id):
                raise ValueError("unsafe ingestion run ID")
            clauses.append(
                f"(source_archive_sha256 = '{checksum}' AND ingestion_run_id = '{owner_run_id}')"
            )
        run_filter = " WHERE " + " OR ".join(clauses)
    elif ingestion_run_id is not None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", ingestion_run_id):
            raise ValueError("unsafe ingestion run ID")
        run_filter = f" WHERE ingestion_run_id = '{ingestion_run_id}'"
    bronze_parts = [f"SELECT interval_end, source_publication_at, landed_at, source_archive_sha256 FROM {_table(catalog, schema, t)}{run_filter}" for t in spec.bronze_tables]
    quarantine_parts = [f"SELECT interval_end, source_publication_at, landed_at, source_archive_sha256 FROM {_table(catalog, schema, t)}{run_filter}" for t in spec.quarantine_tables]
    key = ", ".join(_quote_identifier(k) for k in spec.gold_natural_key)
    fingerprint_columns = ", ".join(_quote_identifier(k) for k in spec.gold_fingerprint_columns)
    bronze = " UNION ALL ".join(bronze_parts)
    quarantine = " UNION ALL ".join(quarantine_parts)
    silver = _table(catalog, schema, spec.silver_table)
    gold = _table(catalog, schema, spec.gold_table)
    if spec.sparse_gold_intervals:
        # Binding constraints can have no row at a valid dispatch interval. Use
        # the newest actually-published Gold interval at or before the Bronze
        # cycle so evidence distinguishes a sparse interval from an empty table.
        gold_scope = (
            "source_interval_watermark = (SELECT MAX(source_interval_watermark) "
            f"FROM {gold} WHERE source_interval_watermark <= "
            "(SELECT interval_end FROM cycle))"
        )
    else:
        gold_scope = "source_interval_watermark = (SELECT interval_end FROM cycle)"
    return f"""WITH bronze AS ({bronze}), quarantine AS ({quarantine}),
landed AS (SELECT * FROM bronze UNION ALL SELECT * FROM quarantine),
cycle AS (SELECT MAX(interval_end) AS interval_end FROM landed),
duplicates AS (
  SELECT COALESCE(SUM(c - 1), 0) AS duplicate_count FROM (
    SELECT COUNT(*) AS c FROM {gold} GROUP BY {key} HAVING COUNT(*) > 1
  )
)
SELECT
  (SELECT DATE_FORMAT(MAX(interval_end), "yyyy-MM-dd'T'HH:mm:ss.SSSXXX") FROM landed) AS newest_source_interval,
  (SELECT DATE_FORMAT(MAX(source_publication_at), "yyyy-MM-dd'T'HH:mm:ss.SSSXXX") FROM landed) AS source_publication_timestamp,
  (SELECT DATE_FORMAT(MAX(landed_at), "yyyy-MM-dd'T'HH:mm:ss.SSSXXX") FROM landed) AS landed_timestamp,
  (SELECT COUNT(*) FROM landed) AS landed_row_count,
  (SELECT CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(source_archive_sha256))) FROM landed) AS raw_zip_checksums,
  (SELECT DATE_FORMAT(MAX(interval_end), "yyyy-MM-dd'T'HH:mm:ss.SSSXXX") FROM bronze) AS bronze_watermark,
  (SELECT COUNT(*) FROM bronze) AS bronze_row_count,
  (SELECT DATE_FORMAT(MAX(interval_end), "yyyy-MM-dd'T'HH:mm:ss.SSSXXX") FROM {silver} WHERE interval_end = (SELECT interval_end FROM cycle)) AS silver_watermark,
  (SELECT COUNT(*) FROM {silver} WHERE interval_end = (SELECT interval_end FROM cycle)) AS silver_row_count,
  (SELECT DATE_FORMAT(MAX(source_interval_watermark), "yyyy-MM-dd'T'HH:mm:ss.SSSXXX") FROM {gold} WHERE {gold_scope}) AS gold_watermark,
  (SELECT COUNT(*) FROM {gold} WHERE {gold_scope}) AS gold_row_count,
  (SELECT DATE_FORMAT(MAX(gold_published_at), "yyyy-MM-dd'T'HH:mm:ss.SSSXXX") FROM {gold} WHERE {gold_scope}) AS gold_publication_timestamp,
  (SELECT SHA2(CONCAT_WS('|', CAST(COUNT(*) AS STRING),
      COALESCE(CAST(SUM(CAST(XXHASH64({fingerprint_columns}) AS DECIMAL(38,0))) AS STRING), 'empty'),
      COALESCE(CAST(MIN(XXHASH64({fingerprint_columns})) AS STRING), 'empty'),
      COALESCE(CAST(MAX(XXHASH64({fingerprint_columns})) AS STRING), 'empty')), 256) FROM {gold} WHERE {gold_scope}) AS gold_content_fingerprint,
  (SELECT duplicate_count FROM duplicates) AS duplicate_natural_key_count"""


def _sql_row(response: Mapping[str, Any]) -> dict[str, str | None]:
    columns = response.get("manifest", {}).get("schema", {}).get("columns", [])
    data = response.get("result", {}).get("data_array", [])
    if len(data) != 1:
        raise RuntimeError(f"evidence aggregate returned {len(data)} rows instead of one")
    names = [item.get("name") for item in columns]
    return dict(zip(names, data[0], strict=True))


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00").replace(" ", "T"))
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc)


def _lag(later: str | None, earlier: str | None) -> float | None:
    a, b = _parse_timestamp(later), _parse_timestamp(earlier)
    return (a - b).total_seconds() if a and b else None


def resolve_lander_run_id(
    client: "DatabricksCLI", run: Mapping[str, Any], candidate_limit: int = 25
) -> str:
    """Return the job run ID that Bronze stamps as ``ingestion_run_id``.

    ``land_current`` is a ``run_job_task``, so the task's own ``run_id`` belongs
    to the orchestrating refresh job, whereas the lander stamps the *inner*
    lander job run ID. Current Jobs responses expose the outer task run in the
    inner run's ``trigger_info.run_id``; that exact link wins. Older responses
    can omit it, so the bounded start/end-window fallback must select exactly
    one run. An ambiguous or empty result is raised rather than guessed because a wrong
    ingestion run ID silently scopes every Gold query to zero rows.
    """
    tasks = {task.get("task_key"): task for task in run.get("tasks", [])}
    task = tasks.get("land_current")
    if not task:
        raise RuntimeError("orchestration run has no land_current task")
    run_job_task = task.get("run_job_task") or {}
    inner_job_id = run_job_task.get("job_id")
    if not inner_job_id:
        # Not a run_job_task: the task run ID is itself the ingestion run.
        return str(task.get("run_id") or "")
    all_candidates = client.list_job_runs(str(inner_job_id), candidate_limit)
    task_run_id = str(task.get("run_id") or "")
    linked = [
        candidate
        for candidate in all_candidates
        if str((candidate.get("trigger_info") or {}).get("run_id") or "") == task_run_id
    ]
    if len(linked) == 1:
        return str(linked[0].get("run_id") or "")
    if len(linked) > 1:
        found = ", ".join(str(candidate.get("run_id")) for candidate in linked)
        raise RuntimeError(f"land_current task matched multiple linked lander runs ({found})")

    started, ended = task.get("start_time"), task.get("end_time")
    if not started:
        raise RuntimeError("land_current task has no start time to resolve its lander run")
    upper = ended or None
    candidates = [
        candidate
        for candidate in all_candidates
        if candidate.get("start_time")
        and candidate["start_time"] >= started
        and (upper is None or candidate["start_time"] <= upper)
    ]
    if not candidates:
        raise RuntimeError(
            f"no run of lander job {inner_job_id} started inside the land_current window; "
            "widen candidate_limit or confirm the cycle really landed"
        )
    if len(candidates) > 1:
        found = ", ".join(str(candidate.get("run_id")) for candidate in candidates)
        raise RuntimeError(
            f"land_current window matched multiple lander runs ({found}); refusing to guess"
        )
    return str(candidates[0].get("run_id") or "")


def job_outcomes(run: Mapping[str, Any]) -> tuple[str, str, str, str, str, str]:
    """Return cycle times and lander/pipeline/orchestration outcomes.

    The trailing element is the ``land_current`` *task* run ID. For a
    ``run_job_task`` that is not the ID Bronze stamps; use
    :func:`resolve_lander_run_id` for the ingestion run ID.
    """
    tasks = {task.get("task_key"): task for task in run.get("tasks", [])}
    def outcome(key: str) -> str:
        state = tasks.get(key, {}).get("state", {})
        return str(state.get("result_state") or state.get("life_cycle_state") or "UNKNOWN")
    state = run.get("state", {})
    overall = str(state.get("result_state") or state.get("life_cycle_state") or "UNKNOWN")
    start_ms, end_ms = run.get("start_time"), run.get("end_time")
    start = datetime.fromtimestamp(start_ms / 1000, timezone.utc).isoformat() if start_ms else ""
    end = datetime.fromtimestamp(end_ms / 1000, timezone.utc).isoformat() if end_ms else datetime.now(timezone.utc).isoformat()
    lander_run_id = str(tasks.get("land_current", {}).get("run_id") or "")
    return start, end, outcome("land_current"), outcome("publish_medallion"), overall, lander_run_id


def capture_live_evidence(
    *, client: DatabricksCLI, catalog: str, schema: str, warehouse_id: str,
    pipeline_id: str, pipeline_update_id: str, orchestration_run_id: str,
    timeout_seconds: int = 600, previous: Mapping[str, Mapping[str, Any]] | None = None,
    listing_inspector: Callable[[SubjectSpec], SourceListing] = inspect_source_listing,
) -> list[EvidenceRow]:
    for value in (catalog, schema):
        _quote_identifier(value)
    update = client.poll_pipeline_update(pipeline_id, pipeline_update_id, timeout_seconds)
    if update.get("update_id") not in (None, pipeline_update_id):
        raise RuntimeError("get-update response does not match requested update ID")
    events = client.pipeline_events(pipeline_id, pipeline_update_id)
    # The list-pipeline-events API does not return the data_quality/expectations
    # payload for these updates (0 of 478 events on update 76139c2c, 2026-09-02),
    # so expectation metrics are read from the UC-published pipeline event log,
    # which does carry per-expectation passed_records/failed_records. The API
    # events remain authoritative for update state and nested error extraction.
    events = events + event_log_expectation_events(
        client,
        catalog=catalog,
        schema=schema,
        warehouse_id=warehouse_id,
        update_id=pipeline_update_id,
        timeout_seconds=timeout_seconds,
    )
    run = client.get_job_run(orchestration_run_id)
    started, ended, lander, pipeline_task, orchestration, _task_run_id = job_outcomes(run)
    lander_run_id = resolve_lander_run_id(client, run)
    if pipeline_task not in _SUCCESS_JOB_RESULTS:
        raise RuntimeError(f"orchestration pipeline task outcome is {pipeline_task}")
    archive_owners = resolve_archive_owners(
        client,
        catalog=catalog,
        schema=schema,
        warehouse_id=warehouse_id,
        pipeline_id=pipeline_id,
        lander_run_id=lander_run_id,
        timeout_seconds=timeout_seconds,
    )
    previous = previous or {}
    listings: dict[str, SourceListing] = {}
    rows: list[EvidenceRow] = []
    for spec in SUBJECTS:
        if spec.source_report_family not in listings:
            listings[spec.source_report_family] = listing_inspector(spec)
        listing = listings[spec.source_report_family]
        values = _sql_row(client.execute_sql(
            subject_sql(
                spec, catalog, schema,
                archive_owners=archive_owners[spec.source_report_family],
            ),
            warehouse_id, catalog, schema, timeout_seconds,
        ))
        # The authoritative newest-available interval comes from the fresh
        # post-cycle NEMWEB listing. The SQL value is the newest interval this
        # cycle actually landed and is represented separately by Bronze.
        newest = listing.source_interval
        source_pub = listing.publication_timestamp
        bronze_watermark = values.get("bronze_watermark")
        gold_watermark = values.get("gold_watermark")
        gold_count = int(values.get("gold_row_count") or 0)
        checksums = tuple(filter(None, str(values.get("raw_zip_checksums") or "").split(",")))
        prior = previous.get(spec.subject)
        source_signature = (listing.filename, newest, source_pub, checksums)
        prior_source = None if prior is None else (
            prior.get("source_listing_filename"), prior.get("newest_source_interval"),
            prior.get("source_publication_timestamp"), tuple(prior.get("raw_zip_checksums", ())),
        )
        source_changed = prior is None or source_signature != prior_source
        gold_fingerprint = str(values.get("gold_content_fingerprint") or "")
        if not gold_fingerprint:
            raise RuntimeError(f"Gold fingerprint missing for {spec.subject}")
        gold_signature = (gold_watermark, gold_count, gold_fingerprint)
        prior_gold = None if prior is None else (
            prior.get("gold_watermark"), int(prior.get("gold_row_count", 0)),
            prior.get("gold_content_fingerprint"),
        )
        rows_changed = prior is None and gold_count > 0 or (prior is not None and gold_signature != prior_gold)
        latest_listing = _parse_timestamp(listing.source_interval)
        bronze_latest = _parse_timestamp(bronze_watermark)
        gold_latest = _parse_timestamp(gold_watermark)
        rule_count, passed, failed = expectation_totals(events, spec.quality_flow_names)
        landed_count = int(values.get("landed_row_count") or 0)
        bronze_count = int(values.get("bronze_row_count") or 0)
        # Live closure is intentionally stricter than table-level quarantine:
        # every emitted expectation for the exact update must have zero failures.
        # An aggregate landed-minus-Bronze count cannot prove that a specific
        # failed Silver/Gold rule reconciles to a matching quarantine record.
        quality_result = "PASS" if rule_count > 0 and failed == 0 else "FAIL"
        duplicate_count = int(values.get("duplicate_natural_key_count") or 0)
        freshness = "FAIL_SOURCE_AHEAD_OF_BRONZE"
        if latest_listing and bronze_latest:
            source_lead = latest_listing - bronze_latest
            if source_lead <= timedelta(0):
                freshness = "PASS_SOURCE_CURRENT" if source_changed else "PASS_NO_NEW_SOURCE"
            else:
                watermarks_healthy = bool(gold_latest) and (
                    gold_latest <= bronze_latest
                    if spec.sparse_gold_intervals
                    else gold_latest == bronze_latest
                )
                if (
                    source_lead <= MAX_SOURCE_LEAD
                    and watermarks_healthy
                    and rule_count > 0
                    and failed == 0
                    and duplicate_count == 0
                ):
                    freshness = "PASS_SOURCE_WITHIN_LEAD"
        row = EvidenceRow(
            subject=spec.subject, cycle_started_at=started, cycle_ended_at=ended,
            orchestration_run_id=str(orchestration_run_id), pipeline_update_id=pipeline_update_id,
            source_report_family=spec.source_report_family,
            newest_source_interval=newest, source_publication_timestamp=source_pub,
            source_publication_lag_seconds=_lag(source_pub, newest),
            source_listing_checked_at=listing.checked_at, source_listing_filename=listing.filename,
            raw_zip_checksums=checksums, landed_timestamp=values.get("landed_timestamp"),
            landed_row_count=landed_count,
            bronze_watermark=bronze_watermark, bronze_row_count=bronze_count,
            silver_watermark=values.get("silver_watermark"), silver_row_count=int(values.get("silver_row_count") or 0),
            gold_watermark=gold_watermark, gold_row_count=gold_count,
            gold_publication_timestamp=values.get("gold_publication_timestamp"),
            gold_content_fingerprint=gold_fingerprint,
            source_interval_to_gold_lag_seconds=_lag(
                values.get("gold_publication_timestamp"), newest
            ),
            bronze_interval_to_gold_lag_seconds=_lag(
                values.get("gold_publication_timestamp"), bronze_watermark
            ),
            landed_to_gold_processing_lag_seconds=_lag(values.get("gold_publication_timestamp"), values.get("landed_timestamp")),
            duplicate_natural_key_count=duplicate_count,
            duplicate_natural_key_result="PASS" if duplicate_count == 0 else "FAIL",
            quality_expectation_rule_count=rule_count,
            quality_expectation_passed_count=passed, quality_expectation_failed_count=failed,
            quality_expectation_result=quality_result,
            lander_outcome=lander, pipeline_outcome=str(update.get("state")),
            orchestration_outcome=orchestration, source_changed=source_changed,
            rows_changed=rows_changed, freshness_check_result=freshness,
            availability_note=spec.availability_note,
        )
        row.validate()
        rows.append(row)
    return rows


def evidence_document(rows: Sequence[EvidenceRow]) -> dict[str, Any]:
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "rows": [asdict(row) for row in rows],
    }


def render_markdown(rows: Sequence[EvidenceRow]) -> str:
    headers = [field for field in EvidenceRow.__dataclass_fields__]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        values = asdict(row)
        rendered = []
        for header in headers:
            value = values[header]
            if isinstance(value, (tuple, list)):
                value = ", ".join(map(str, value))
            rendered.append(str(value if value is not None else "").replace("|", "\\|"))
        lines.append("| " + " | ".join(rendered) + " |")
    return "\n".join(lines) + "\n"


def write_evidence(rows: Sequence[EvidenceRow], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(evidence_document(rows), indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(rows), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    """Record orchestration callback context without claiming live data proof.

    The authoritative capture runs externally through ``capture_nemweb_evidence.py``
    with an explicit profile, warehouse and update ID.  The in-job callback only
    emits the run identifiers made available by Jobs; it never fabricates the
    missing pipeline update ID or watermarks.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--mode", choices=("live", "snapshot"), required=True)
    parser.add_argument("--orchestration-run-id", required=True)
    parser.add_argument("--lander-task-run-id", required=True)
    parser.add_argument("--pipeline-task-run-id", required=True)
    args = parser.parse_args(argv)
    # The authoritative capture requires pipeline configuration
    # nemweb.source_mode=live and refuses to run in snapshot mode.  Advertising
    # it unconditionally sends a snapshot operator into a guaranteed
    # RuntimeError, so name the next command that actually applies.
    if args.mode == "live":
        next_command = (
            "scripts/capture_nemweb_evidence.py with explicit --pipeline-update-id"
        )
    else:
        next_command = (
            "scripts/validate_nemweb_snapshot.py; snapshot mode cannot produce live "
            "evidence, so capture_nemweb_evidence.py does not apply"
        )
    print(json.dumps({
        "status": "capture_pending_exact_update_id",
        "mode": args.mode,
        "orchestration_run_id": args.orchestration_run_id,
        "lander_task_run_id": args.lander_task_run_id,
        "pipeline_task_run_id": args.pipeline_task_run_id,
        "live_evidence": args.mode == "live",
        "next_command": next_command,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
