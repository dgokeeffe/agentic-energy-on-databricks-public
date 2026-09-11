from __future__ import annotations

import hashlib
import json
from pathlib import Path

from agentic_energy.ingestion.lander import land_snapshot

SNAPSHOT = Path(__file__).parents[1] / "fixtures" / "nemweb" / "v1"
PACKAGED_SNAPSHOT = Path(__file__).parents[2] / "src" / "agentic_energy" / "resources" / "nemweb_snapshot" / "v1"


def _files(root: Path, pattern: str) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob(pattern))
    }


def _canonical_rows(root: Path) -> bytes:
    rows: list[str] = []
    for path in sorted((root / "parsed").rglob("*.jsonl")):
        rows.extend(line for line in path.read_text().splitlines() if line)
    return ("\n".join(sorted(rows)) + "\n").encode()


def test_snapshot_landing_is_byte_deterministic_across_independent_roots(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    first = land_snapshot(SNAPSHOT, left, run_id="deterministic-v1")
    second = land_snapshot(SNAPSHOT, right, run_id="deterministic-v1")

    assert first.status == second.status == "success"
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.parsed_row_count == second.parsed_row_count == 103
    assert first.quarantine_count == second.quarantine_count == 0
    assert _files(left, "*.zip") == _files(right, "*.zip")
    assert _files(left, "*.jsonl") == _files(right, "*.jsonl")
    assert _files(left, "*.json") == _files(right, "*.json")
    assert _canonical_rows(left) == _canonical_rows(right)
    assert hashlib.sha256(_canonical_rows(left)).hexdigest() == hashlib.sha256(
        _canonical_rows(right)
    ).hexdigest()


def test_wheel_snapshot_copy_matches_authoritative_test_snapshot() -> None:
    def all_files(root: Path) -> dict[str, bytes]:
        return {path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*") if path.is_file()}
    assert all_files(PACKAGED_SNAPSHOT) == all_files(SNAPSHOT)


def test_snapshot_manifest_checksums_attribution_and_cases_are_complete() -> None:
    manifest = json.loads((SNAPSHOT / "manifest.json").read_text())
    assert manifest["required_families"] == [
        "dispatchis", "dispatch_scada", "next_day_dispatch", "registration"
    ]
    assert "Australian Energy Market Operator" in manifest["attribution"]
    for artifact in manifest["artifacts"]:
        path = SNAPSHOT / artifact["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
        assert artifact["source_url"].startswith((
            "https://www.nemweb.com.au/REPORTS/",
            "https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/",
        ))
        assert artifact["retrieved_at"]
        assert isinstance(artifact["synthetic"], bool)
        if artifact["report_family"] == "registration":
            assert artifact["synthetic"] is False
            assert artifact["original_archive_sha256"]
        else:
            assert artifact["synthetic"] is True
        assert "not live evidence" in artifact["classification"]

    expected_cases = {
        "duplicate_archive", "later_correction", "multi_section", "malformed_footer",
        "malformed_row", "unknown_column", "missing_required_column", "timezone_boundary",
    }
    assert {Path(item["path"]).parts[1] for item in manifest["cases"]} == expected_cases
    assert all((SNAPSHOT / item["path"]).is_file() for item in manifest["cases"])
