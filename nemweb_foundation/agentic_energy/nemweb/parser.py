"""Safe, section-aware parser for AEMO NEMWEB CSV-in-ZIP reports.

Adapted conceptually from the reference repository's ``nemweb_utils.py``.
Unlike that utility, this parser consumes every CSV member, tracks every
interleaved C/I/D/F record, and never falls back silently to an all-string
schema.
"""

from __future__ import annotations

import csv
import io
import json
import math
import posixpath
import stat
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, Iterable

from .contracts import (
    ContractError,
    ControlRecord,
    ParseIssue,
    ParseResult,
    ParsedRecord,
    parse_market_time,
)
from .schemas import get_schema, is_known_complete_header


class UnsafeArchiveError(ContractError):
    """Raised when an archive violates expansion or path safety policy."""


@dataclass(frozen=True)
class ZipLimits:
    max_files: int = 64
    max_member_bytes: int = 20 * 1024 * 1024
    max_total_expanded_bytes: int = 64 * 1024 * 1024
    max_compression_ratio: float = 200.0

    def __post_init__(self) -> None:
        if min(self.max_files, self.max_member_bytes, self.max_total_expanded_bytes) <= 0:
            raise ValueError("ZIP count and size limits must be positive")
        if self.max_compression_ratio <= 0:
            raise ValueError("ZIP compression ratio must be positive")


def _validate_member(info: zipfile.ZipInfo, limits: ZipLimits) -> None:
    name = info.filename.replace("\\", "/")
    path = PurePosixPath(name)
    if not name or name.startswith("/") or path.is_absolute() or ".." in path.parts:
        raise UnsafeArchiveError(f"unsafe ZIP member path: {info.filename!r}")
    if info.flag_bits & 0x1:
        raise UnsafeArchiveError(f"encrypted ZIP member is not supported: {name!r}")
    mode = info.external_attr >> 16
    if info.is_dir():
        raise UnsafeArchiveError(f"ZIP directories are not accepted: {name!r}")
    if mode and not stat.S_ISREG(mode):
        raise UnsafeArchiveError(f"non-regular ZIP member is not accepted: {name!r}")
    if info.file_size > limits.max_member_bytes:
        raise UnsafeArchiveError(f"ZIP member exceeds expanded-byte limit: {name!r}")
    compressed = max(info.compress_size, 1)
    if info.file_size / compressed > limits.max_compression_ratio:
        raise UnsafeArchiveError(f"ZIP member exceeds compression-ratio limit: {name!r}")
    if path.suffix.upper() != ".CSV":
        raise UnsafeArchiveError(f"unexpected non-CSV ZIP member: {name!r}")


def inspect_zip(data: bytes, limits: ZipLimits = ZipLimits()) -> tuple[zipfile.ZipInfo, ...]:
    """Validate a ZIP central directory before any member is parsed."""

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError) as exc:
        raise UnsafeArchiveError("invalid ZIP central directory") from exc
    with archive:
        infos = tuple(archive.infolist())
        if not infos:
            raise UnsafeArchiveError("ZIP archive is empty")
        if len(infos) > limits.max_files:
            raise UnsafeArchiveError("ZIP archive exceeds member-count limit")
        total = 0
        for info in infos:
            _validate_member(info, limits)
            total += info.file_size
            if total > limits.max_total_expanded_bytes:
                raise UnsafeArchiveError("ZIP archive exceeds total expanded-byte limit")
    return infos


def _convert(value: str, kind: str) -> Any:
    stripped = value.strip()
    if stripped == "":
        return None
    if kind == "string":
        return stripped
    if kind == "int":
        # NEMWEB occasionally serialises integral values as 1.0.
        numeric = float(stripped)
        if not math.isfinite(numeric) or not numeric.is_integer():
            raise ValueError(f"expected integer, got {value!r}")
        return int(numeric)
    if kind == "float":
        numeric = float(stripped)
        if not math.isfinite(numeric):
            raise ValueError(f"non-finite number {value!r}")
        return numeric
    if kind == "market_timestamp":
        return parse_market_time(stripped).isoformat()
    raise ValueError(f"unknown field kind {kind!r}")


def _issue(
    code: str,
    severity: str,
    member: str,
    row_number: int,
    message: str,
    key: tuple[str, str, str] | None = None,
    raw: Iterable[str] = (),
) -> ParseIssue:
    group, section, version = key or (None, None, None)
    return ParseIssue(
        code, severity, member, row_number, message,
        group, section, version, tuple(raw),
    )


def _parse_member(report_family: str, member: str, data: bytes) -> tuple[
    list[ParsedRecord], list[ControlRecord], list[ParseIssue],
    dict[tuple[str, str, str], tuple[str, ...]],
]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ContractError(f"CSV member {member!r} is not UTF-8") from exc

    records: list[ParsedRecord] = []
    controls: list[ControlRecord] = []
    issues: list[ParseIssue] = []
    headers: dict[tuple[str, str, str], tuple[str, ...]] = {}
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        for row_number, row in enumerate(reader, start=1):
            if not row or all(not value.strip() for value in row):
                continue
            kind = row[0].strip().upper()
            if kind not in {"C", "I", "D", "F"}:
                issues.append(_issue("UNKNOWN_RECORD_KIND", "error", member, row_number,
                                     f"unknown NEMWEB record kind {row[0]!r}", raw=row))
                continue
            if kind in {"C", "F"}:
                controls.append(ControlRecord(kind, member, row_number, tuple(row[1:])))
                if kind == "F" and len(row) < 2:
                    issues.append(_issue("MALFORMED_FOOTER", "error", member, row_number,
                                         "footer has no content", raw=row))
                continue
            if len(row) < 4:
                issues.append(_issue("MALFORMED_SECTION_ROW", "error", member, row_number,
                                     "I/D record has fewer than four identity columns", raw=row))
                continue
            key = (row[1].strip(), row[2].strip(), row[3].strip())
            if not all(key):
                issues.append(_issue("MALFORMED_SECTION_ID", "error", member, row_number,
                                     "section group, name and version are required", key, row))
                continue
            if kind == "I":
                columns = tuple(value.strip().upper() for value in row[4:])
                controls.append(ControlRecord(kind, member, row_number, tuple(row[1:])))
                if not columns or any(not column for column in columns) or len(set(columns)) != len(columns):
                    issues.append(_issue("INVALID_HEADER", "error", member, row_number,
                                         "header columns must be non-empty and unique", key, row))
                    continue
                previous = headers.get(key)
                if previous is not None and previous != columns:
                    issues.append(_issue("CONFLICTING_HEADER", "error", member, row_number,
                                         "same section/version declared different columns", key, row))
                    continue
                headers[key] = columns
                schema = get_schema(report_family, *key)
                if schema is None:
                    issues.append(_issue("UNKNOWN_SECTION", "warning", member, row_number,
                                         "section/version has no registered typed schema", key, row))
                continue

            columns = headers.get(key)
            if columns is None:
                issues.append(_issue("DATA_BEFORE_HEADER", "error", member, row_number,
                                     "data record has no preceding matching header", key, row))
                continue
            raw_values = row[4:]
            if len(raw_values) != len(columns):
                issues.append(_issue("COLUMN_COUNT_MISMATCH", "error", member, row_number,
                                     f"expected {len(columns)} values, got {len(raw_values)}",
                                     key, row))
                continue
            schema = get_schema(report_family, *key)
            schema_kinds = schema.kinds if schema else {}
            complete_known_header = is_known_complete_header(
                report_family, *key, columns
            )
            unknown = () if complete_known_header else tuple(
                column for column in columns if column not in schema_kinds
            )
            values: dict[str, Any] = {}
            conversion_error: str | None = None
            for column, value in zip(columns, raw_values):
                try:
                    values[column] = _convert(value, schema_kinds.get(column, "string"))
                except (ValueError, ContractError) as exc:
                    conversion_error = f"{column}: {exc}"
                    break
            if conversion_error:
                issues.append(_issue("TYPE_CONVERSION_FAILED", "error", member, row_number,
                                     conversion_error, key, row))
                continue
            if schema:
                missing_values = sorted(
                    name for name in schema.required_names if values.get(name) is None
                )
                if missing_values:
                    issues.append(_issue("MISSING_REQUIRED_VALUE", "error", member, row_number,
                                         f"required values are null: {missing_values}", key, row))
                    continue
            records.append(ParsedRecord(
                report_family, key[0], key[1], key[2], member, row_number,
                values, unknown,
            ))
    except csv.Error as exc:
        issues.append(_issue("MALFORMED_CSV", "error", member, reader.line_num,
                             str(exc)))
    return records, controls, issues, headers


def parse_zip_bytes(
    data: bytes,
    report_family: str,
    limits: ZipLimits = ZipLimits(),
) -> ParseResult:
    """Validate and parse every CSV member and interleaved section in a ZIP."""

    infos = inspect_zip(data, limits)
    records: list[ParsedRecord] = []
    controls: list[ControlRecord] = []
    issues: list[ParseIssue] = []
    headers: dict[tuple[str, str, str], tuple[str, ...]] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in sorted(infos, key=lambda item: item.filename):
            try:
                member_data = archive.read(info)
            except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
                raise UnsafeArchiveError(f"ZIP CRC/read failure for {info.filename!r}") from exc
            parsed = _parse_member(report_family, info.filename, member_data)
            records.extend(parsed[0])
            controls.extend(parsed[1])
            issues.extend(parsed[2])
            for key, columns in parsed[3].items():
                previous = headers.get(key)
                if previous is not None and previous != columns:
                    issues.append(_issue("CONFLICTING_ARCHIVE_HEADER", "error", info.filename, 0,
                                         "section/version differs across CSV members", key))
                else:
                    headers[key] = columns
    return ParseResult(report_family, tuple(records), tuple(controls), tuple(issues), headers)


def canonical_record_json(record: ParsedRecord) -> str:
    """Stable JSON representation used by parsed landing files and hash tests."""

    payload = asdict(record)
    payload["values"] = dict(sorted(record.values.items()))
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
