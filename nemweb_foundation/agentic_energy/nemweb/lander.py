"""Bounded, idempotent NEMWEB raw/parsed file lander.

This is a security-focused rewrite of the reference ``nemweb_lander.py``.  Raw
ZIPs remain immutable provenance anchors; parsed JSONL is a deterministic input
to later Lakeflow Bronze tables.  The module performs no Spark or workspace
operations.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import ssl
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

from .contracts import (
    ContractError,
    NEM_TIMEZONE,
    ParseResult,
    initialise_mode_root,
    mode_landing_root,
    validate_source_mode,
)
from .parser import ZipLimits, canonical_record_json, parse_zip_bytes
from .schema_drift import assess_schema_drift
from .schemas import required_sections

ALLOWED_HOSTS = frozenset({"www.nemweb.com.au", "nemweb.com.au"})
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$")


class LanderError(RuntimeError):
    """Base class for observable landing failures."""


class NetworkPolicyError(LanderError):
    """A URL or network response violates the NEMWEB network policy."""


class WriteOnceError(LanderError):
    """A completed or active ingestion run ID already exists."""


class RequiredReportError(LanderError):
    """One or more reports required for a complete run did not land."""

    def __init__(self, message: str, manifest_path: Path):
        super().__init__(message)
        self.manifest_path = manifest_path


@dataclass(frozen=True)
class LanderLimits:
    timeout_seconds: float = 30.0
    retry_count: int = 3
    retry_backoff_seconds: float = 0.25
    max_pages: int = 1
    max_files_per_cycle: int = 24
    max_response_bytes: int = 64 * 1024 * 1024
    zip: ZipLimits = ZipLimits()

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0 or self.retry_count < 0:
            raise ValueError("timeout must be positive and retry count non-negative")
        if self.max_pages <= 0 or self.max_files_per_cycle <= 0 or self.max_response_bytes <= 0:
            raise ValueError("page, file and response bounds must be positive")


@dataclass(frozen=True)
class ArchiveInput:
    report_family: str
    publication: str
    filename: str
    data: bytes
    source_url_path: str
    source_mode: str
    retrieved_at: str
    synthetic: bool = False
    # HTTP/listing publication time. This is deliberately distinct from the
    # market-interval token embedded in the filename.
    source_publication_at: str | None = None
    # Split MMSDM archives contain one table each, unlike multi-section Current
    # reports. When supplied, validate only these sections for this archive.
    expected_sections: tuple[tuple[str, str, str], ...] | None = None


@dataclass(frozen=True)
class LandResult:
    status: str
    manifest_path: Path
    manifest_sha256: str
    archive_count: int
    unique_archive_count: int
    parsed_row_count: int
    quarantine_count: int


class _HrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value)


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        raise NetworkPolicyError(f"redirect rejected with HTTP status {code}")


def _parse_iis_publication(value: str) -> str | None:
    match = re.fullmatch(
        r"[A-Za-z]+,\s+([A-Za-z]+)\s+(\d{1,2}),\s+(20\d{2})\s+"
        r"(\d{1,2}):(\d{2})\s+([AP]M)", value, re.IGNORECASE,
    )
    if not match:
        return None
    months = {name: index for index, name in enumerate(
        ("january", "february", "march", "april", "may", "june", "july",
         "august", "september", "october", "november", "december"), 1
    )}
    month = months.get(match.group(1).lower())
    if month is None:
        return None
    hour = int(match.group(4)) % 12 + (12 if match.group(6).upper() == "PM" else 0)
    return datetime(
        int(match.group(3)), month, int(match.group(2)), hour,
        int(match.group(5)), tzinfo=NEM_TIMEZONE,
    ).astimezone(timezone.utc).isoformat()


def _fully_unquote(value: str) -> str:
    decoded = value
    for _ in range(4):
        next_value = urllib.parse.unquote(decoded)
        if next_value == decoded:
            return decoded
        decoded = next_value
    return decoded


def validate_nemweb_url(url: str) -> str:
    """Validate scheme, authority and public NEMWEB report-path constraints."""

    try:
        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as exc:
        raise NetworkPolicyError("malformed NEMWEB URL authority") from exc
    if parsed.scheme.lower() != "https":
        raise NetworkPolicyError("NEMWEB URL must use HTTPS")
    if host not in ALLOWED_HOSTS:
        raise NetworkPolicyError("NEMWEB URL host is not allowlisted")
    if parsed.username or parsed.password:
        raise NetworkPolicyError("credentials are not allowed in NEMWEB URLs")
    if port not in (None, 443):
        raise NetworkPolicyError("NEMWEB URL must use the standard HTTPS port")
    decoded_path = _fully_unquote(parsed.path).replace("\\", "/")
    allowed_prefixes = (
        "/reports/",
        "/data_archive/wholesale_electricity/mmsdm/",
    )
    if not decoded_path.casefold().startswith(allowed_prefixes) or ".." in decoded_path.split("/"):
        raise NetworkPolicyError(
            "NEMWEB URL must remain under /REPORTS/ or the MMSDM wholesale archive"
        )
    if parsed.query or parsed.fragment:
        raise NetworkPolicyError("NEMWEB URL queries and fragments are not accepted")
    return urllib.parse.urlunsplit(("https", host, parsed.path, "", ""))


def _safe_segment(value: str, label: str) -> str:
    if not _SAFE_SEGMENT.fullmatch(value):
        raise ContractError(f"unsafe {label}: {value!r}")
    return value


def _validate_source_url_path(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    decoded = _fully_unquote(parsed.path).replace("\\", "/")
    allowed_prefixes = (
        "/reports/",
        "/data_archive/wholesale_electricity/mmsdm/",
    )
    if not decoded.casefold().startswith(allowed_prefixes) or ".." in decoded.split("/"):
        raise ContractError(
            "source_url_path must remain under /REPORTS/ or the MMSDM wholesale archive"
        )
    if any(character in value for character in ("\r", "\n", "@")):
        raise ContractError("source_url_path contains forbidden characters")
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ContractError("source_url_path must contain only a public report path")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _atomic_write(path: Path, data: bytes) -> bool:
    """Write bytes using UC-Volume-compatible rename semantics.

    UC Volume FUSE mounts do not support hard links or guarantee ``fsync``.
    A unique same-directory temporary file followed by ``os.replace`` is the
    supported atomic publication primitive. Immutable checksum/run paths make
    concurrent different-content publication a contract violation.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise LanderError(f"immutable destination must not be a symlink: {path.name}")
    if path.exists():
        if path.is_file() and path.read_bytes() == data:
            return False
        raise LanderError(f"immutable destination already exists with different content: {path.name}")
    fd, tmp_name = tempfile.mkstemp(prefix=".landing-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
        # Re-check immediately before promotion. os.replace is supported on UC
        # Volumes and prevents readers from observing a partial file.
        if path.is_symlink() or path.exists():
            if path.is_file() and not path.is_symlink() and path.read_bytes() == data:
                return False
            raise LanderError(f"concurrent immutable destination conflict: {path.name}")
        os.replace(tmp_name, path)
        return True
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def _member_slug(member: str) -> str:
    stem = Path(member).stem
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", stem)[:100] or "member"
    return f"{safe}-{hashlib.sha256(member.encode()).hexdigest()[:10]}"


def _section_files(
    root: Path,
    archive: ArchiveInput,
    checksum: str,
    parsed: ParseResult,
    quarantine_keys: frozenset[tuple[str, str, str]] = frozenset(),
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], list[str]] = {}
    for record in parsed.records:
        key = (record.csv_member, record.section_group, record.section_name, record.report_version)
        payload = json.loads(canonical_record_json(record))
        if (record.section_group, record.section_name, record.report_version) in quarantine_keys:
            payload["_rescued_data"] = json.dumps({"reason": "SCHEMA_DRIFT_QUARANTINE"})
        grouped.setdefault(key, []).append(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    # Parser rejects with a known section identity become queryable quarantine
    # records rather than disappearing into a sidecar JSON document.
    for issue in parsed.issues:
        if issue.severity != "error" or not all((issue.section_group, issue.section_name, issue.report_version)):
            continue
        key = (issue.csv_member, issue.section_group, issue.section_name, issue.report_version)
        payload = {
            "report_family": archive.report_family,
            "section_group": issue.section_group,
            "section_name": issue.section_name,
            "report_version": issue.report_version,
            "csv_member": issue.csv_member,
            "row_number": issue.row_number,
            "values": {},
            "unknown_columns": [],
            "_rescued_data": json.dumps({"reason": issue.code, "raw": list(issue.raw_values)}),
        }
        grouped.setdefault(key, []).append(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    sections: list[dict[str, object]] = []
    for key in sorted(grouped):
        member, group, section, version = key
        lines = sorted(grouped[key])
        # Checksum is the canonical Auto Loader identity. Relisting identical
        # bytes under another filename/publication must not emit another input.
        rel = Path("parsed") / archive.report_family / checksum / (
            f"{_member_slug(member)}__{group}__{section}__v{version}.jsonl"
        )
        payload = ("\n".join(lines) + "\n").encode("utf-8")
        _atomic_write(root / rel, payload)
        sections.append({
            "csv_member": member,
            "section_group": group,
            "section_name": section,
            "report_version": version,
            "row_count": len(lines),
            "parsed_path": rel.as_posix(),
            "parsed_sha256": _sha256(payload),
        })
    return sections


def land_archives(
    archives: Sequence[ArchiveInput],
    destination: Path | str,
    *,
    run_id: str,
    source_mode: str,
    required_families: Iterable[str] = (),
    landed_at: str | None = None,
    limits: LanderLimits = LanderLimits(),
    raise_on_failure: bool = True,
) -> LandResult:
    """Land supplied archives with immutable raw and deterministic parsed outputs.

    A run ID is write-once even after a partial/failing run.  Required-family
    failure is captured in a durable failure manifest before an exception is
    raised, allowing a CLI caller to return non-zero without losing diagnostics.
    """

    mode = validate_source_mode(source_mode)
    # ``destination`` is the managed Volume parent.  Mode data lives below a
    # validated sibling root so snapshot and live can coexist without weakening
    # the permanent marker guarantee inside either root.  A legacy marker/data
    # layout at the parent is intentionally ignored and never deleted or moved.
    root = mode_landing_root(destination, mode)
    initialise_mode_root(root, mode)
    safe_run = _safe_segment(run_id, "run_id")
    locks = root / ".runs"
    locks.mkdir(parents=True, exist_ok=True)
    lock = locks / safe_run
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise WriteOnceError(f"ingestion run ID already exists: {run_id!r}") from exc

    manifest_path = root / "manifests" / f"{safe_run}.json"
    entries: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    seen_checksums: dict[tuple[str, str], str] = {}
    successful_families: set[str] = set()
    row_count = 0
    quarantine_count = 0
    frozen_landed_at = landed_at or datetime.now(timezone.utc).isoformat()

    for position, archive in enumerate(archives, start=1):
        try:
            if archive.source_mode != mode:
                raise ContractError(
                    f"archive source mode {archive.source_mode!r} does not match run mode {mode!r}"
                )
            family = _safe_segment(archive.report_family, "report_family")
            publication = _safe_segment(archive.publication, "publication")
            filename = Path(archive.filename).name
            if filename != archive.filename or not filename.lower().endswith(".zip"):
                raise ContractError(f"unsafe source filename: {archive.filename!r}")
            if len(archive.data) > limits.max_response_bytes:
                raise LanderError("archive exceeds response-byte limit")
            source_url_path = _validate_source_url_path(archive.source_url_path)
            checksum = _sha256(archive.data)
            parsed = parse_zip_bytes(archive.data, family, limits.zip)
            expected = (
                frozenset(archive.expected_sections)
                if archive.expected_sections is not None
                else required_sections(family)
            )
            missing_sections = sorted(expected - set(parsed.headers))
            if missing_sections:
                raise LanderError(
                    f"required sections are missing from {family!r}: {missing_sections}"
                )
            drift = assess_schema_drift(parsed)
            if drift.failed:
                failed_sections = [
                    f"{finding.section_group}.{finding.section_name}.v{finding.report_version}"
                    for finding in drift.findings
                    if finding.status == "fail"
                ]
                raise LanderError(
                    f"required source columns are missing in {failed_sections}"
                )
            raw_rel = Path("raw") / family / publication / f"{checksum}.zip"
            duplicate_of = seen_checksums.get((family, checksum))
            promoted = _atomic_write(root / raw_rel, archive.data)
            # Parse into a run-private staging root. The manifest is published
            # before files become visible under /parsed, so Auto Loader can
            # never consume provenance-orphaned records.
            staging_root = root / ".incoming" / safe_run
            quarantine_keys = frozenset(
                (finding.section_group, finding.section_name, finding.report_version)
                for finding in drift.findings if finding.status == "quarantine"
            )
            sections = _section_files(
                staging_root, archive, checksum, parsed, quarantine_keys
            )
            drift_quarantine_rows = sum(
                record.section_key in quarantine_keys for record in parsed.records
            )
            archive_quarantine_count = parsed.quarantine_count + drift_quarantine_rows
            issue_rel = Path("parsed") / family / checksum / "issues.json"
            issue_payload = _canonical_bytes([asdict(issue) for issue in parsed.issues])
            _atomic_write(staging_root / issue_rel, issue_payload)
            drift_rel = Path("parsed") / family / checksum / "schema_drift.json"
            drift_payload = _canonical_bytes([asdict(finding) for finding in drift.findings])
            _atomic_write(staging_root / drift_rel, drift_payload)
            entry = {
                "input_sequence": position,
                "report_family": family,
                "publication": publication,
                "source_filename": filename,
                "source_url_path": source_url_path,
                "retrieved_at": archive.retrieved_at,
                "source_publication_at": archive.source_publication_at or archive.retrieved_at,
                "source_publication_basis": "listing_or_http" if archive.source_publication_at else "retrieval_fallback",
                "synthetic": archive.synthetic,
                "source_archive_sha256": checksum,
                "source_archive_bytes": len(archive.data),
                "raw_path": raw_rel.as_posix(),
                "raw_promoted": promoted,
                "duplicate_checksum_of": duplicate_of,
                "row_count": parsed.row_count,
                "quarantine_count": archive_quarantine_count,
                "control_record_count": len(parsed.controls),
                "sections": sections,
                "issues_path": issue_rel.as_posix(),
                "schema_drift_path": drift_rel.as_posix(),
                "schema_drift_failed": drift.failed,
            }
            entries.append(entry)
            seen_checksums.setdefault((family, checksum), raw_rel.as_posix())
            successful_families.add(family)
            row_count += parsed.row_count
            quarantine_count += archive_quarantine_count
        except Exception as exc:  # per-file failure is made durable below
            errors.append({
                "input_sequence": str(position),
                "report_family": archive.report_family,
                "source_filename": Path(archive.filename).name,
                "error_type": type(exc).__name__,
                "message": str(exc),
            })

    missing = sorted(set(required_families) - successful_families)
    if missing:
        errors.append({
            "input_sequence": "",
            "report_family": ",".join(missing),
            "source_filename": "",
            "error_type": "MissingRequiredReports",
            "message": f"required report families did not land: {missing}",
        })
    status = "failure" if missing or (errors and not entries) else "partial" if errors else "success"
    manifest = {
        "manifest_version": 1,
        "run_id": run_id,
        "source_mode": mode,
        "landed_at": frozen_landed_at,
        "status": status,
        "required_families": sorted(set(required_families)),
        "archive_count": len(archives),
        "unique_archive_count": len(seen_checksums),
        "parsed_row_count": row_count,
        "quarantine_count": quarantine_count,
        "archives": entries,
        "errors": errors,
    }
    manifest_bytes = _canonical_bytes(manifest)
    _atomic_write(manifest_path, manifest_bytes)
    # Only after durable provenance exists, publish staged parser outputs.
    incoming = root / ".incoming" / safe_run / "parsed"
    if incoming.exists():
        for staged in sorted(incoming.rglob("*")):
            if staged.is_file():
                relative = staged.relative_to(root / ".incoming" / safe_run)
                _atomic_write(root / relative, staged.read_bytes())
        shutil.rmtree(root / ".incoming" / safe_run, ignore_errors=True)
    result = LandResult(
        status, manifest_path, _sha256(manifest_bytes), len(archives),
        len(seen_checksums), row_count, quarantine_count,
    )
    if status != "success" and raise_on_failure:
        raise RequiredReportError(
            f"NEMWEB landing run {run_id!r} completed with status {status!r}", manifest_path
        )
    return result


def land_snapshot(
    snapshot_root: Path | str,
    destination: Path | str,
    *,
    run_id: str = "snapshot-v1",
) -> LandResult:
    """Verify and land every artifact declared by a versioned snapshot manifest."""

    source = Path(snapshot_root)
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    archives: list[ArchiveInput] = []
    for item in manifest["artifacts"]:
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise LanderError("snapshot artifact path must stay inside snapshot root")
        path = (source / relative).resolve()
        if source.resolve() not in path.parents:
            raise LanderError("snapshot artifact path escapes snapshot root")
        data = path.read_bytes()
        actual = _sha256(data)
        if actual != item["sha256"]:
            raise LanderError(f"snapshot checksum mismatch for {item['path']}")
        source_url = validate_nemweb_url(item["source_url"])
        archives.append(ArchiveInput(
            item["report_family"], item["publication"], path.name, data,
            urllib.parse.urlsplit(source_url).path, "snapshot",
            item["retrieved_at"], item["synthetic"], item.get("source_publication_at"),
        ))
    return land_archives(
        archives, destination, run_id=run_id, source_mode="snapshot",
        required_families=manifest["required_families"],
        landed_at=manifest["frozen_landed_at"],
    )


class NemwebClient:
    """Small bounded HTTPS client for NEMWEB CURRENT listings and archives."""

    def __init__(
        self,
        limits: LanderLimits = LanderLimits(),
        *,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.limits = limits
        self._sleep = sleep
        self._opener = urllib.request.build_opener(
            _RejectRedirects(), urllib.request.HTTPSHandler(context=ssl.create_default_context())
        )
        self._publication_by_url: dict[str, str] = {}

    def _get(self, url: str) -> bytes:
        safe_url = validate_nemweb_url(url)
        last_error: Exception | None = None
        for attempt in range(self.limits.retry_count + 1):
            request = urllib.request.Request(
                safe_url,
                headers={"User-Agent": "agentic-energy-nemweb/1.0", "Accept": "*/*"},
            )
            try:
                with self._opener.open(request, timeout=self.limits.timeout_seconds) as response:
                    final_url = validate_nemweb_url(response.geturl())
                    if final_url != safe_url:
                        raise NetworkPolicyError("response URL changed unexpectedly")
                    declared = response.headers.get("Content-Length")
                    if declared:
                        try:
                            declared_bytes = int(declared)
                        except ValueError as exc:
                            raise NetworkPolicyError("response has invalid Content-Length") from exc
                        if declared_bytes < 0 or declared_bytes > self.limits.max_response_bytes:
                            raise NetworkPolicyError("response exceeds configured byte limit")
                    data = response.read(self.limits.max_response_bytes + 1)
                    if len(data) > self.limits.max_response_bytes:
                        raise NetworkPolicyError("response exceeds configured byte limit")
                    return data
            except NetworkPolicyError:
                # Policy violations are deterministic and must never be retried
                # or collapsed into a generic transport failure.
                raise
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt < self.limits.retry_count:
                    self._sleep(self.limits.retry_backoff_seconds * (2**attempt))
        raise LanderError(f"bounded NEMWEB request failed after retries: {type(last_error).__name__}")

    def fetch_text(self, listing_url: str) -> str:
        """Fetch one allowlisted listing page as UTF-8 text."""

        body = self._get(listing_url)
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LanderError("NEMWEB listing is not UTF-8") from exc

    def list_archives(self, listing_url: str, *, prefix: str) -> tuple[str, ...]:
        """Return a bounded, validated set of archive URLs from one listing."""

        if self.limits.max_pages < 1:  # guarded by config; explicit for auditability
            raise LanderError("page bound exhausted")
        body = self._get(listing_url)
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LanderError("NEMWEB listing is not UTF-8") from exc
        parser = _HrefParser()
        parser.feed(text)
        decoded_text = html.unescape(text)
        matches: list[str] = []
        for href in parser.hrefs:
            candidate = urllib.parse.urljoin(validate_nemweb_url(listing_url), href)
            try:
                candidate = validate_nemweb_url(candidate)
            except NetworkPolicyError:
                continue
            name = Path(urllib.parse.urlsplit(candidate).path).name
            if name.upper().startswith(prefix.upper()) and name.lower().endswith(".zip"):
                matches.append(candidate)
                # IIS directory listings expose an English timestamp adjacent
                # to each anchor. Capture it as source publication metadata;
                # download retrieval time remains an explicitly labelled fallback.
                stamp = re.search(
                    r"([A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2},\s+20\d{2}\s+"
                    r"\d{1,2}:\d{2}\s+[AP]M)\s+\d+\s+<A HREF=\"[^\"]*/"
                    + re.escape(name) + r"\"",
                    decoded_text, re.IGNORECASE,
                )
                if stamp:
                    parsed_stamp = _parse_iis_publication(stamp.group(1))
                    if parsed_stamp:
                        self._publication_by_url[candidate] = parsed_stamp
        return tuple(sorted(set(matches))[-self.limits.max_files_per_cycle :])

    def download_archive(
        self,
        url: str,
        *,
        report_family: str,
        publication: str,
        retrieved_at: str | None = None,
        source_publication_at: str | None = None,
        expected_sections: tuple[tuple[str, str, str], ...] | None = None,
    ) -> ArchiveInput:
        safe_url = validate_nemweb_url(url)
        data = self._get(safe_url)
        source_publication_at = source_publication_at or self._publication_by_url.get(safe_url)
        # Central directory and expansion constraints are checked before return.
        parse_zip_bytes(data, report_family, self.limits.zip)
        parsed_url = urllib.parse.urlsplit(safe_url)
        return ArchiveInput(
            report_family, publication, Path(parsed_url.path).name, data,
            parsed_url.path, "live",
            retrieved_at or datetime.now(timezone.utc).isoformat(), False,
            source_publication_at, expected_sections,
        )


_CURRENT_SOURCES = (
    ("dispatchis", "https://www.nemweb.com.au/REPORTS/CURRENT/DispatchIS_Reports/", "PUBLIC_DISPATCHIS_"),
    ("dispatch_scada", "https://www.nemweb.com.au/REPORTS/CURRENT/Dispatch_SCADA/", "PUBLIC_DISPATCHSCADA_"),
)
_CONTEXT_CURRENT_SOURCES = (
    ("next_day_dispatch", "https://www.nemweb.com.au/REPORTS/CURRENT/Next_Day_Dispatch/", "PUBLIC_NEXT_DAY_DISPATCH_"),
    ("bids", "https://www.nemweb.com.au/REPORTS/CURRENT/Bidmove_Complete/", "PUBLIC_BIDMOVE_COMPLETE_"),
    ("trading", "https://www.nemweb.com.au/REPORTS/CURRENT/TradingIS_Reports/", "PUBLIC_TRADINGIS_"),
)
_PUBLICATION_RE = re.compile(r"(20\d{10}|20\d{6})")


def _publication_token(filename: str) -> str:
    match = _PUBLICATION_RE.search(filename)
    if not match:
        raise LanderError("NEMWEB archive filename has no market date/interval token")
    return match.group(1)


def _within_lookback(urls: Sequence[str], hours: int) -> tuple[str, ...]:
    cutoff = datetime.now(NEM_TIMEZONE) - timedelta(hours=hours)
    selected: list[str] = []
    for url in urls:
        filename = Path(urllib.parse.urlsplit(url).path).name
        token = _publication_token(filename)
        if len(token) == 12:
            observed = datetime.strptime(token, "%Y%m%d%H%M").replace(tzinfo=NEM_TIMEZONE)
            if observed >= cutoff:
                selected.append(url)
        else:
            observed = datetime.strptime(token, "%Y%m%d").replace(tzinfo=NEM_TIMEZONE)
            if observed >= cutoff:
                selected.append(url)
    return tuple(selected)


def _monthly_listing(month: datetime) -> str:
    ym = month.strftime("%Y_%m")
    return (
        "https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/"
        f"{month.year}/MMSDM_{ym}/MMSDM_Historical_Data_SQLLoader/DATA/"
    )


def _discover_live(
    scope: str, client: NemwebClient, *, critical_lookback_hours: int = 2,
    context_lookback_days: int = 7,
) -> tuple[list[ArchiveInput], tuple[str, ...]]:
    sources = _CURRENT_SOURCES if scope == "critical" else _CONTEXT_CURRENT_SOURCES
    archives: list[ArchiveInput] = []
    required: list[str] = []
    for family, listing, prefix in sources:
        listed = client.list_archives(listing, prefix=prefix)
        window_hours = (
            critical_lookback_hours if scope == "critical" else context_lookback_days * 24
        )
        urls = _within_lookback(listed, window_hours)
        if not urls:
            # Distinguish "AEMO published nothing" from "our window is too narrow".
            # Conflating them hid a real misconfiguration: Next_Day_Dispatch is a
            # T+1 report whose filename token is the prior trading day, so the
            # newest archive is routinely >24h old by that token.
            if listed:
                newest = Path(urllib.parse.urlsplit(listed[-1]).path).name
                raise LanderError(
                    f"required live report listing has no archive inside the "
                    f"{window_hours}h lookback: {family}; the listing is not empty "
                    f"and its newest archive is {newest}, so widen the lookback "
                    f"rather than treating the source as stale"
                )
            raise LanderError(f"required live report listing is empty/stale: {family}")
        required.append(family)
        for url in urls:
            filename = Path(urllib.parse.urlsplit(url).path).name
            archives.append(client.download_archive(
                url, report_family=family, publication=_publication_token(filename)
            ))
    if scope == "context":
        # Monthly MMSDM tables are independently zipped; validate one expected
        # section per archive, then require the family across the whole cycle.
        now = datetime.now(NEM_TIMEZONE)
        month = (now.replace(day=1) - timedelta(days=35)).replace(day=1)
        listing = _monthly_listing(month)
        monthly = (
            ("registration", "DUDETAILSUMMARY", ("PARTICIPANT_REGISTRATION", "DUDETAILSUMMARY", "7")),
            ("registration", "DUALLOC", ("PARTICIPANT_REGISTRATION", "DUALLOC", "1")),
            ("registration", "GENUNITS", ("PARTICIPANT_REGISTRATION", "GENUNITS", "3")),
            ("settlement", "SETFCASREGIONRECOVERY", ("SETTLEMENTS", "FCASREGIONRECOVERY", "6")),
            ("settlement", "SETIRSURPLUS", ("SETTLEMENTS", "IRSURPLUS", "6")),
        )
        for family, table, expected in monthly:
            prefix = f"PUBLIC_ARCHIVE%23{table}%23"
            urls = client.list_archives(listing, prefix=prefix)
            if not urls:
                raise LanderError(f"required monthly MMSDM archive is absent: {table}")
            url = urls[-1]
            filename = Path(urllib.parse.urlsplit(url).path).name
            archives.append(client.download_archive(
                url, report_family=family, publication=month.strftime("%Y%m%d"),
                expected_sections=(expected,),
            ))
            if family not in required:
                required.append(family)
    return archives, tuple(required)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI used by the bundle lander Job; returns non-zero on any partial run."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("snapshot", "live"), required=True)
    parser.add_argument("--scope", choices=("critical", "context"), default="critical")
    parser.add_argument("--volume-path", required=True)
    parser.add_argument("--critical-lookback-hours", type=int, default=2)
    parser.add_argument("--context-lookback-days", type=int, default=7)
    parser.add_argument("--max-files", type=int, default=100)
    parser.add_argument("--network-timeout-seconds", type=float, default=30)
    parser.add_argument("--network-retry-count", type=int, default=3)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--snapshot-root")
    parser.add_argument("--allow-live", choices=("true", "false"), default="false")
    args = parser.parse_args(argv)
    if args.mode == "live" and args.allow_live != "true":
        raise LanderError("live mode requires deployment-controlled --allow-live approval")
    if args.mode == "snapshot":
        if args.scope == "context":
            # The one versioned snapshot includes critical and context families;
            # checksum idempotency means the second scope is harmless.
            pass
        from importlib.resources import files
        root = Path(args.snapshot_root) if args.snapshot_root else Path(
            str(files("agentic_energy.resources").joinpath("nemweb_snapshot/v1"))
        )
        result = land_snapshot(root, args.volume_path, run_id=args.cycle_id)
    else:
        # BIDMOVE expands to ~134 MiB. Raise bounds only for the reviewed daily
        # context scope; critical five-minute downloads retain the 64 MiB cap.
        expanded = 256 * 1024 * 1024 if args.scope == "context" else 64 * 1024 * 1024
        limits = LanderLimits(
            timeout_seconds=args.network_timeout_seconds,
            retry_count=args.network_retry_count,
            max_files_per_cycle=args.max_files,
            max_response_bytes=expanded,
            zip=ZipLimits(max_member_bytes=expanded, max_total_expanded_bytes=expanded),
        )
        client = NemwebClient(limits)
        archives, required = _discover_live(
            args.scope, client,
            critical_lookback_hours=args.critical_lookback_hours,
            context_lookback_days=args.context_lookback_days,
        )
        result = land_archives(
            archives, args.volume_path, run_id=args.cycle_id,
            source_mode="live", required_families=required, limits=limits,
            raise_on_failure=False,
        )
    print(json.dumps({"status": result.status, "manifest_path": str(result.manifest_path)}))
    return 0 if result.status == "success" else 1
