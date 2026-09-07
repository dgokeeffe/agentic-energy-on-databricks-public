"""Measurable schema-drift policy for parsed NEMWEB section headers."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import ParseResult
from .schemas import get_schema, is_known_complete_header


@dataclass(frozen=True)
class DriftFinding:
    report_family: str
    section_group: str
    section_name: str
    report_version: str
    status: str
    missing_required: tuple[str, ...] = ()
    unexpected_columns: tuple[str, ...] = ()
    message: str = ""


@dataclass(frozen=True)
class DriftReport:
    findings: tuple[DriftFinding, ...]

    @property
    def failed(self) -> bool:
        return any(finding.status == "fail" for finding in self.findings)

    @property
    def warning_count(self) -> int:
        return sum(finding.status == "quarantine" for finding in self.findings)


def assess_schema_drift(parsed: ParseResult) -> DriftReport:
    """Fail required-column loss and quarantine unexpected additions.

    Unknown sections are quarantined as a whole rather than implicitly accepted
    as string-only records.  The parser still preserves their header and data so
    an operator can review and add a versioned contract deliberately.
    """

    findings: list[DriftFinding] = []
    for (group, section, version), columns in sorted(parsed.headers.items()):
        schema = get_schema(parsed.report_family, group, section, version)
        if schema is None:
            findings.append(DriftFinding(
                parsed.report_family, group, section, version, "quarantine",
                unexpected_columns=tuple(columns),
                message="unknown section/version requires contract review",
            ))
            continue
        observed = set(columns)
        missing = tuple(sorted(schema.required_names - observed))
        unexpected = () if is_known_complete_header(
            parsed.report_family, group, section, version, columns
        ) else tuple(sorted(observed - set(schema.field_names)))
        if missing:
            status = "fail"
            message = "required source columns are missing"
        elif unexpected:
            status = "quarantine"
            message = "unexpected columns retained for schema review"
        else:
            status = "compatible"
            message = "observed required schema is compatible"
        findings.append(DriftFinding(
            parsed.report_family, group, section, version, status,
            missing, unexpected, message,
        ))
    return DriftReport(tuple(findings))
