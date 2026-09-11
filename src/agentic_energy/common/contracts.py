"""Core contracts shared by the NEMWEB parser and lander.

NEMWEB dispatch timestamps are interval-ending Australian Eastern Standard Time
(AEST, UTC+10) throughout the NEM; daylight-saving conversion must not be
applied.  This module is intentionally independent of Spark so the exact same
contracts can be exercised by local snapshot tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import time
from typing import Any, Mapping
from uuid import uuid4

NEM_TIMEZONE = timezone(timedelta(hours=10), name="AEST")
UTC = timezone.utc
SOURCE_MODES = frozenset({"live", "snapshot"})


class ContractError(ValueError):
    """Raised when source data violates a NEMWEB contract."""


class ModeIsolationError(ContractError):
    """Raised when live and snapshot material are directed to the same root."""


@dataclass(frozen=True)
class ParsedRecord:
    """A typed NEMWEB data record with its complete source identity."""

    report_family: str
    section_group: str
    section_name: str
    report_version: str
    csv_member: str
    row_number: int
    values: Mapping[str, Any]
    unknown_columns: tuple[str, ...] = ()
    selected_encoding: str = "utf-8-sig"

    @property
    def section_key(self) -> tuple[str, str, str]:
        return (self.section_group, self.section_name, self.report_version)


@dataclass(frozen=True)
class ControlRecord:
    """A preserved C, I, or F metadata/control record."""

    kind: str
    csv_member: str
    row_number: int
    values: tuple[str, ...]


@dataclass(frozen=True)
class ParseIssue:
    """A measurable parser or schema issue; issues are never silently dropped."""

    code: str
    severity: str
    csv_member: str
    row_number: int
    message: str
    section_group: str | None = None
    section_name: str | None = None
    report_version: str | None = None
    raw_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParseResult:
    """All valid records, controls, headers and quarantined issues for an archive."""

    report_family: str
    records: tuple[ParsedRecord, ...]
    controls: tuple[ControlRecord, ...]
    issues: tuple[ParseIssue, ...]
    headers: Mapping[tuple[str, str, str], tuple[str, ...]] = field(default_factory=dict)

    @property
    def row_count(self) -> int:
        return len(self.records)

    @property
    def quarantine_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")


def parse_market_time(value: str) -> datetime:
    """Parse an interval-ending NEM timestamp as fixed-offset AEST.

    Only unambiguous local NEM timestamp forms and an explicit ``+10:00`` offset
    are accepted.  UTC, daylight-saving offsets, timezone names, and date-only
    values are rejected so a caller cannot accidentally apply civil-time DST.
    """

    raw = value.strip()
    if not raw:
        raise ContractError("NEM market timestamp is empty")

    # Explicit offsets are accepted only when they are exactly NEM AEST.
    if raw.endswith("Z"):
        raise ContractError("NEM market timestamps must be expressed in AEST, not UTC")
    try:
        aware = datetime.fromisoformat(raw)
    except ValueError:
        aware = None
    if aware is not None and aware.tzinfo is not None:
        if aware.utcoffset() != timedelta(hours=10):
            raise ContractError("NEM market timestamp offset must be +10:00 AEST")
        return aware.astimezone(NEM_TIMEZONE)

    formats = ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S")
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=NEM_TIMEZONE)
        except ValueError:
            pass
    raise ContractError(f"unsupported or ambiguous NEM market timestamp: {value!r}")


def market_time_to_utc(value: str) -> datetime:
    """Return an aware UTC instant for an interval-ending NEM timestamp."""

    return parse_market_time(value).astimezone(UTC)


def validate_source_mode(source_mode: str) -> str:
    if source_mode not in SOURCE_MODES:
        raise ContractError(f"source_mode must be one of {sorted(SOURCE_MODES)}")
    return source_mode


def mode_landing_root(parent: Path | str, source_mode: str) -> Path:
    """Return the isolated landing root for ``source_mode`` below one Volume.

    ``parent`` must be the unscoped managed-Volume root. Snapshot and live data
    coexist as sibling roots below it. Rejecting an already-scoped parent is
    deliberate: silently accepting ``.../live`` would make the lander and
    pipeline watch ``.../live/live`` and hide the operator's configuration
    error behind an empty nested tree.
    """

    mode = validate_source_mode(source_mode)
    landing_parent = Path(parent)
    if landing_parent.name in SOURCE_MODES:
        expected = landing_parent.parent.as_posix()
        raise ContractError(
            f"landing path {landing_parent.as_posix()!r} is already mode-scoped; "
            f"configure the unscoped parent {expected!r} instead"
        )
    return landing_parent / mode


def _marker_value(marker: Path) -> str | None:
    """Read a marker, returning ``None`` while an old write is incomplete."""

    try:
        value = marker.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if value in SOURCE_MODES:
        return value
    # The old open("x") implementation exposed an empty or partially-written
    # marker to concurrent readers. Treat only a valid mode prefix as an
    # incomplete old write; arbitrary content remains a loud corruption error.
    if not value or any(mode.startswith(value) for mode in SOURCE_MODES):
        return None
    raise ModeIsolationError(
        f"landing root has invalid mode marker content {value!r}"
    )


def _assert_marker_mode(marker: Path, mode: str) -> bool:
    """Return whether a complete matching marker exists; reject a mismatch."""

    existing = _marker_value(marker)
    if existing is None:
        return False
    if existing != mode:
        raise ModeIsolationError(
            f"landing root is reserved for {existing!r}, not {mode!r}"
        )
    return True


def initialise_mode_root(root: Path, source_mode: str) -> None:
    """Atomically mark an already mode-scoped root as permanently single-mode.

    Normal callers first derive ``<volume>/<mode>`` with
    :func:`mode_landing_root`, so live and snapshot isolation is structural. The
    marker remains a final corruption/misrouting guard inside that derived root.

    Initialisation uses an atomic directory lock and a complete same-directory
    temporary file followed by ``os.replace``. Concurrent first users therefore
    never observe the empty marker exposed by the former ``open('x')`` write.
    """

    mode = validate_source_mode(source_mode)
    root.mkdir(parents=True, exist_ok=True)
    marker = root / ".nemweb-source-mode"
    if _assert_marker_mode(marker, mode):
        return

    lock = root / ".nemweb-source-mode.lock"
    deadline = time.monotonic() + 5.0
    while True:
        try:
            lock.mkdir()
            owns_lock = True
        except FileExistsError:
            owns_lock = False
        if owns_lock:
            break
        if _assert_marker_mode(marker, mode):
            return
        if time.monotonic() >= deadline:
            raise ModeIsolationError(
                "mode marker initialisation did not complete within 5 seconds"
            )
        time.sleep(0.01)

    temporary = root / (
        f".nemweb-source-mode.{os.getpid()}.{uuid4().hex}.tmp"
    )
    try:
        # Another implementation may have completed immediately before this
        # process acquired the lock. Re-check before publishing our marker.
        if _assert_marker_mode(marker, mode):
            return
        temporary.write_text(mode + "\n", encoding="utf-8")
        os.replace(temporary, marker)
        if not _assert_marker_mode(marker, mode):  # pragma: no cover - defensive
            raise ModeIsolationError("mode marker publication did not complete")
    finally:
        temporary.unlink(missing_ok=True)
        try:
            lock.rmdir()
        except FileNotFoundError:
            pass
