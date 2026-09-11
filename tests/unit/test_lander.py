from __future__ import annotations

import io
import json
import stat
import urllib.error
import zipfile
from pathlib import Path

import pytest

from agentic_energy.common.contracts import (
    ContractError,
    ModeIsolationError,
    initialise_mode_root,
    mode_landing_root,
)
from agentic_energy.cli import main as cli_main
from agentic_energy.ingestion.lander import (
    ArchiveInput,
    LanderLimits,
    NemwebClient,
    NetworkPolicyError,
    RequiredReportError,
    WriteOnceError,
    land_archives,
    land_snapshot,
    validate_nemweb_url,
    _discover_live,
    _parse_iis_publication,
    _publication_token,
)
from agentic_energy.ingestion.parser import UnsafeArchiveError, ZipLimits, parse_zip_bytes

FIXTURE = Path(__file__).parents[1] / "fixtures" / "nemweb" / "v1"
SCADA = next((FIXTURE / "raw" / "dispatch_scada").glob("*.zip"))


def _input(*, filename: str = "PUBLIC_DISPATCHSCADA.zip", mode: str = "snapshot") -> ArchiveInput:
    return ArchiveInput(
        "dispatch_scada", "202401010005", filename, SCADA.read_bytes(),
        "/REPORTS/CURRENT/Dispatch_SCADA/PUBLIC_DISPATCHSCADA.zip",
        mode, "2026-09-02T11:30:00+10:00", True,
    )


@pytest.mark.parametrize("url", [
    "http://www.nemweb.com.au/REPORTS/CURRENT/x.zip",
    "https://evil.example/REPORTS/CURRENT/x.zip",
    "https://www.nemweb.com.au:444/REPORTS/CURRENT/x.zip",
    "https://www.nemweb.com.au:notaport/REPORTS/CURRENT/x.zip",
    "https://user:password@www.nemweb.com.au/REPORTS/CURRENT/x.zip",
    "https://www.nemweb.com.au/REPORTS/../secret.zip",
    "https://www.nemweb.com.au/REPORTS/%252e%252e/secret.zip",
    "https://www.nemweb.com.au/REPORTS/CURRENT/x.zip?token=not-allowed",
    "https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/%252e%252e/secret.zip",
])
def test_network_allowlist_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(NetworkPolicyError):
        validate_nemweb_url(url)


def test_iis_publication_timestamp_is_locale_independent_and_utc() -> None:
    assert _parse_iis_publication("Wednesday, September 2, 2026 11:30 AM") == "2026-09-02T01:30:00+00:00"
    assert _publication_token("PUBLIC_DISPATCHIS_202609021335_000.zip") == "202609021335"


def test_network_allowlist_accepts_the_scoped_mmsdm_wholesale_archive() -> None:
    url = "https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/2026/MMSDM_2026_07/file.zip"
    assert validate_nemweb_url(url) == url


def test_critical_discovery_fetches_only_dispatchis_and_scada() -> None:
    calls: list[tuple[str, str]] = []

    class FakeClient:
        def list_archives(self, listing: str, *, prefix: str):
            calls.append((listing, prefix))
            return (f"{listing}{prefix}209901010005.zip",)

        def download_archive(self, url: str, *, report_family: str, publication: str):
            return (report_family, publication, url)

    archives, required = _discover_live("critical", FakeClient())
    assert required == ("dispatchis", "dispatch_scada")
    assert [archive[0] for archive in archives] == ["dispatchis", "dispatch_scada"]
    assert [prefix for _, prefix in calls] == [
        "PUBLIC_DISPATCHIS_",
        "PUBLIC_DISPATCHSCADA_",
    ]


def test_landing_is_checksum_idempotent_and_manifested_per_section(tmp_path: Path) -> None:
    first = _input()
    same_bytes_new_name = _input(filename="CORRECTED_FILENAME.zip")
    result = land_archives(
        [first, same_bytes_new_name], tmp_path, run_id="cycle-1",
        source_mode="snapshot", required_families=["dispatch_scada"],
        landed_at="2024-01-02T00:00:00+00:00",
    )
    manifest = json.loads(result.manifest_path.read_text())

    assert result.status == "success"
    assert result.archive_count == 2
    assert result.unique_archive_count == 1
    assert len(list((tmp_path / "snapshot" / "raw").rglob("*.zip"))) == 1
    assert manifest["archives"][1]["duplicate_checksum_of"] == manifest["archives"][0]["raw_path"]
    assert manifest["archives"][0]["sections"][0]["section_name"] == "UNIT_SCADA"
    assert manifest["archives"][0]["sections"][0]["row_count"] == 14
    assert not list(tmp_path.rglob(".landing-*"))


def test_relisted_checksum_has_one_canonical_autoloader_input(tmp_path: Path) -> None:
    first = _input()
    relisted = ArchiveInput(
        first.report_family, "202401010010", "RELISTED.zip", first.data,
        first.source_url_path, first.source_mode, first.retrieved_at, True,
    )
    land_archives([first], tmp_path, run_id="cycle-a", source_mode="snapshot")
    land_archives([relisted], tmp_path, run_id="cycle-b", source_mode="snapshot")
    assert len(list((tmp_path / "snapshot" / "parsed").rglob("*.jsonl"))) == 1


def test_atomic_writer_does_not_require_hard_links(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os
    monkeypatch.setattr(os, "link", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("unsupported")))
    result = land_archives([_input()], tmp_path, run_id="no-links", source_mode="snapshot")
    assert result.status == "success"


def test_snapshot_manifest_path_traversal_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "snapshot"
    root.mkdir()
    (root / "manifest.json").write_text(json.dumps({
        "artifacts": [{"path": "../escape.zip"}], "required_families": []
    }))
    with pytest.raises(Exception, match="inside snapshot root"):
        land_snapshot(root, tmp_path / "out")


def test_primary_cli_land_and_snapshot_are_executable(tmp_path: Path) -> None:
    snapshot_root = str(FIXTURE)
    first = tmp_path / "land"
    # The configured destination is the unscoped Volume parent. Avoid naming it
    # exactly like a source mode, which is now rejected as an already-scoped
    # configuration rather than silently creating snapshot/snapshot.
    second = tmp_path / "snapshot-command-output"
    assert cli_main(["land", "--mode", "snapshot", "--scope", "critical",
                     "--volume-path", str(first), "--snapshot-root", snapshot_root,
                     "--cycle-id", "cli-land"]) == 0
    assert cli_main(["snapshot", "--volume-path", str(second),
                     "--snapshot-root", snapshot_root, "--cycle-id", "cli-snapshot"]) == 0


def test_pipeline_reads_the_same_mode_scoped_root_the_lander_writes() -> None:
    from agentic_energy.common.config import PipelineConfig

    class Conf:
        values = {
            "nemweb.source_mode": "live",
            "nemweb.landing_path": "/Volumes/catalog/schema/landing",
            "nemweb.market_timezone": "Australia/Brisbane",
            "spark.sql.session.timeZone": "Australia/Brisbane",
        }

        def get(self, key: str) -> str:
            return self.values[key]

    config = PipelineConfig.from_spark(type("Spark", (), {"conf": Conf()})())
    assert config.landing_path == "/Volumes/catalog/schema/landing/live"


def test_context_cli_raises_only_context_zip_bound(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import agentic_energy.ingestion.lander as module
    captured = {}
    class FakeClient:
        def __init__(self, limits):
            captured["limits"] = limits
    monkeypatch.setattr(module, "NemwebClient", FakeClient)
    monkeypatch.setattr(module, "_discover_live", lambda *args, **kwargs: ([], ()))
    assert module.main([
        "--mode", "live", "--scope", "context", "--allow-live", "true",
        "--volume-path", str(tmp_path), "--cycle-id", "context-bound",
    ]) == 0
    assert captured["limits"].zip.max_total_expanded_bytes == 256 * 1024 * 1024


def test_live_cli_requires_deployment_controlled_approval(tmp_path: Path) -> None:
    with pytest.raises(Exception, match="allow-live"):
        cli_main(["land", "--mode", "live", "--scope", "critical",
                  "--volume-path", str(tmp_path), "--cycle-id", "blocked"])


def test_split_mmsdm_archive_validates_its_declared_section_only(tmp_path: Path) -> None:
    data = _zip_with(
        "PUBLIC_ARCHIVE#GENUNITS#FILE01.CSV",
        b"I,PARTICIPANT_REGISTRATION,GENUNITS,3,GENSETID\n"
        b"D,PARTICIPANT_REGISTRATION,GENUNITS,3,UNIT1\n",
    )
    source = ArchiveInput(
        "registration", "20260701", "GENUNITS.zip", data,
        "/Data_Archive/Wholesale_Electricity/MMSDM/2026/GENUNITS.zip",
        "snapshot", "2026-08-08T02:15:56+00:00", True, None,
        (("PARTICIPANT_REGISTRATION", "GENUNITS", "3"),),
    )
    result = land_archives(
        [source], tmp_path, run_id="split-mmsdm", source_mode="snapshot",
        required_families=("registration",),
    )
    assert result.status == "success"


def test_same_filename_correction_retains_both_checksums(tmp_path: Path) -> None:
    corrected_data = _zip_with(
        "PUBLIC_DISPATCHSCADA.CSV",
        b"I,DISPATCH,UNIT_SCADA,1,SETTLEMENTDATE,DUID,SCADAVALUE,LASTCHANGED\n"
        b"D,DISPATCH,UNIT_SCADA,1,2024/01/01 00:05:00,SOLAR1,43.0,2024/01/01 00:04:00\n",
    )
    corrected = ArchiveInput(
        "dispatch_scada", "202401010005", "PUBLIC_DISPATCHSCADA.zip", corrected_data,
        "/REPORTS/CURRENT/Dispatch_SCADA/PUBLIC_DISPATCHSCADA.zip",
        "snapshot", "2026-09-02T11:35:00+10:00", True,
    )
    result = land_archives(
        [_input(), corrected], tmp_path, run_id="correction-cycle",
        source_mode="snapshot", required_families=["dispatch_scada"],
    )
    manifest = json.loads(result.manifest_path.read_text())
    assert result.unique_archive_count == 2
    assert len(list((tmp_path / "snapshot" / "raw").rglob("*.zip"))) == 2
    assert len({item["source_archive_sha256"] for item in manifest["archives"]}) == 2
    assert all(item["source_filename"] == "PUBLIC_DISPATCHSCADA.zip" for item in manifest["archives"])


def test_run_id_is_write_once_within_a_mode_root(tmp_path: Path) -> None:
    land_archives([_input()], tmp_path, run_id="fixed", source_mode="snapshot")
    with pytest.raises(WriteOnceError):
        land_archives([_input()], tmp_path, run_id="fixed", source_mode="snapshot")


def test_snapshot_and_live_can_coexist_below_one_volume_parent(tmp_path: Path) -> None:
    land_archives([_input()], tmp_path, run_id="snapshot-run", source_mode="snapshot")
    land_archives(
        [_input(mode="live")], tmp_path, run_id="live-run", source_mode="live"
    )

    assert (tmp_path / "snapshot" / ".nemweb-source-mode").read_text().strip() == "snapshot"
    assert (tmp_path / "live" / ".nemweb-source-mode").read_text().strip() == "live"
    assert list((tmp_path / "snapshot" / "raw").rglob("*.zip"))
    assert list((tmp_path / "live" / "raw").rglob("*.zip"))


def test_legacy_parent_marker_and_data_are_ignored_not_migrated(tmp_path: Path) -> None:
    (tmp_path / ".nemweb-source-mode").write_text("live\n")
    legacy = tmp_path / "raw" / "legacy.zip"
    legacy.parent.mkdir()
    legacy.write_bytes(b"legacy-audit-data")

    land_archives([_input()], tmp_path, run_id="new-snapshot", source_mode="snapshot")

    assert legacy.read_bytes() == b"legacy-audit-data"
    assert (tmp_path / ".nemweb-source-mode").read_text() == "live\n"
    assert list((tmp_path / "snapshot" / "raw").rglob("*.zip"))


def test_mode_marker_still_rejects_a_genuine_cross_mode_write(tmp_path: Path) -> None:
    # Simulate a corrupted/misrouted mode root. The parent-level resolver keeps
    # normal modes separate, while initialise_mode_root remains the final guard
    # within each resolved root.
    snapshot_root = tmp_path / "snapshot"
    initialise_mode_root(snapshot_root, "snapshot")
    with pytest.raises(ModeIsolationError):
        initialise_mode_root(snapshot_root, "live")


@pytest.mark.parametrize("incomplete", ["", "s", "snap"])
def test_incomplete_first_use_marker_is_completed_for_the_same_mode(
    tmp_path: Path, incomplete: str
) -> None:
    # Simulate the observable interleaving from the former open("x") writer: a
    # concurrent process saw the marker after creation but before its content was
    # completely written. It is incomplete initialisation, not a cross-mode
    # mismatch.
    root = tmp_path / "snapshot"
    root.mkdir()
    marker = root / ".nemweb-source-mode"
    marker.write_text(incomplete)

    initialise_mode_root(root, "snapshot")

    assert marker.read_text(encoding="utf-8") == "snapshot\n"
    assert not list(root.glob(".nemweb-source-mode.*.tmp"))
    assert not (root / ".nemweb-source-mode.lock").exists()


def test_already_scoped_landing_parent_fails_loudly(tmp_path: Path) -> None:
    scoped = tmp_path / "live"
    with pytest.raises(ContractError, match="already mode-scoped") as caught:
        mode_landing_root(scoped, "live")
    assert tmp_path.as_posix() in str(caught.value)

    # The public lander path must fail before silently creating live/live.
    with pytest.raises(ContractError, match="configure the unscoped parent"):
        land_archives([], scoped, run_id="misconfigured", source_mode="live")
    assert not (scoped / "live").exists()


def test_pipeline_rejects_an_already_scoped_landing_parent() -> None:
    from agentic_energy.common.config import PipelineConfig

    class Conf:
        values = {
            "nemweb.source_mode": "live",
            "nemweb.landing_path": "/Volumes/catalog/schema/landing/live",
            "nemweb.market_timezone": "Australia/Brisbane",
            "spark.sql.session.timeZone": "Australia/Brisbane",
        }

        def get(self, key: str) -> str:
            return self.values[key]

    with pytest.raises(ContractError, match="configure the unscoped parent"):
        PipelineConfig.from_spark(type("Spark", (), {"conf": Conf()})())


def test_required_report_failure_is_durable_and_observable(tmp_path: Path) -> None:
    bad = FIXTURE / "cases" / "missing_required_column" / "MISSING_REQUIRED.zip"
    source = ArchiveInput(
        "dispatchis", "202401010005", bad.name, bad.read_bytes(),
        "/REPORTS/CURRENT/DispatchIS_Reports/MISSING_REQUIRED.zip",
        "snapshot", "2026-09-02T11:30:00+10:00", True,
    )
    with pytest.raises(RequiredReportError) as caught:
        land_archives(
            [source], tmp_path, run_id="bad-cycle", source_mode="snapshot",
            required_families=["dispatchis"],
        )
    manifest = json.loads(caught.value.manifest_path.read_text())
    assert manifest["status"] == "failure"
    assert {error["error_type"] for error in manifest["errors"]} == {
        "LanderError", "MissingRequiredReports"
    }


def test_schema_drift_record_routes_to_rescued_quarantine(tmp_path: Path) -> None:
    changed = FIXTURE / "cases" / "unknown_column" / "UNKNOWN_COLUMN.zip"
    source = ArchiveInput(
        "dispatch_scada", "202401010005", changed.name, changed.read_bytes(),
        "/REPORTS/CURRENT/Dispatch_SCADA/UNKNOWN_COLUMN.zip", "snapshot",
        "2026-09-02T11:30:00+10:00", True,
    )
    land_archives([source], tmp_path, run_id="drift-visible", source_mode="snapshot")
    payloads = [json.loads(line) for path in (tmp_path / "snapshot" / "parsed").rglob("*.jsonl")
                for line in path.read_text().splitlines()]
    assert payloads and all("SCHEMA_DRIFT_QUARANTINE" in item.get("_rescued_data", "")
                            for item in payloads)


def test_parser_reject_and_schema_drift_are_queryable_jsonl(tmp_path: Path) -> None:
    malformed = FIXTURE / "cases" / "malformed_row" / "MALFORMED_ROW.zip"
    source = ArchiveInput(
        "dispatch_scada", "202401010005", malformed.name, malformed.read_bytes(),
        "/REPORTS/CURRENT/Dispatch_SCADA/MALFORMED_ROW.zip", "snapshot",
        "2026-09-02T11:30:00+10:00", True,
    )
    result = land_archives(
        [source], tmp_path, run_id="reject-visible", source_mode="snapshot",
        raise_on_failure=False,
    )
    payloads = [json.loads(line) for path in (tmp_path / "snapshot" / "parsed").rglob("*.jsonl")
                for line in path.read_text().splitlines()]
    assert any(item.get("_rescued_data") and "COLUMN_COUNT_MISMATCH" in item["_rescued_data"]
               for item in payloads)
    assert result.quarantine_count >= 1


def _zip_with(name: str, content: bytes, *, mode: int = 0o100644) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        info = zipfile.ZipInfo(name)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = mode << 16
        archive.writestr(info, content)
    return out.getvalue()


@pytest.mark.parametrize("name,mode", [
    ("../escape.CSV", 0o100644),
    ("/absolute.CSV", 0o100644),
    ("link.CSV", stat.S_IFLNK | 0o777),
    ("not_csv.txt", 0o100644),
])
def test_zip_member_path_and_type_attacks_are_rejected(name: str, mode: int) -> None:
    with pytest.raises(UnsafeArchiveError):
        parse_zip_bytes(_zip_with(name, b"F,END\n", mode=mode), "dispatchis")


def test_zip_bomb_ratio_and_expanded_size_are_bounded() -> None:
    compressed = _zip_with("bomb.CSV", b"A" * 100_000)
    with pytest.raises(UnsafeArchiveError):
        parse_zip_bytes(compressed, "dispatchis", ZipLimits(max_compression_ratio=2))
    with pytest.raises(UnsafeArchiveError):
        parse_zip_bytes(compressed, "dispatchis", ZipLimits(max_member_bytes=100))


def test_network_retries_are_bounded_without_leaking_url(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    client = NemwebClient(
        LanderLimits(retry_count=2, retry_backoff_seconds=0.01), sleep=sleeps.append
    )

    class BrokenOpener:
        def open(self, *args, **kwargs):
            raise urllib.error.URLError("private diagnostic must not escape")

    client._opener = BrokenOpener()  # type: ignore[assignment]
    with pytest.raises(Exception) as caught:
        client._get("https://www.nemweb.com.au/REPORTS/CURRENT/DispatchIS_Reports/")
    assert sleeps == [0.01, 0.02]
    assert "private diagnostic" not in str(caught.value)
    assert "www.nemweb" not in str(caught.value)
