import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

import agentic_energy.pipeline as pipeline_module
from agentic_energy.acquisition import parse_dispatchis_zip
from agentic_energy.pipeline import run_pipeline, _utc_timestamp


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def test_end_to_end_contract_and_idempotency(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    (first / "silver").mkdir(parents=True)
    (first / "silver/stale.jsonl").write_text("stale\n")
    assert run_pipeline(output_dir=first) == {"bronze": 11, "silver": 6, "quarantine": 3, "gold": 3}
    run_pipeline(output_dir=second)
    files1 = sorted(p.relative_to(first) for p in first.rglob("*" ) if p.is_file())
    files2 = sorted(p.relative_to(second) for p in second.rglob("*" ) if p.is_file())
    assert files1 == files2
    assert all((first / p).read_bytes() == (second / p).read_bytes() for p in files1)

    market = lines(first / "silver/aemo_dispatch_fixture.jsonl")
    assert [(r["region"], r["interval_utc"]) for r in market] == [
        ("NSW1", "2024-01-14T23:00:00Z"),
        ("NSW1", "2024-04-07T00:00:00Z"),
        ("VIC1", "2024-04-07T00:30:00Z"),
    ]
    assert market[1]["demand_mw"] == 8250  # duplicate keeps last ingestion sequence

    rejected = lines(first / "quarantine/rejected.jsonl")
    assert len(rejected) == 3
    assert {r["source_id"] for r in rejected} == {"aemo_dispatch_fixture", "weather_fixture"}
    assert all(r["source_file"] and r["source_row_number"] and r["reason_codes"] for r in rejected)

    gold = lines(first / "gold/market_weather.jsonl")
    assert [(r["region"], r["interval_utc"]) for r in gold] == [
        ("NSW1", "2024-01-14T23:00:00Z"),
        ("NSW1", "2024-04-07T00:00:00Z"),
        ("VIC1", "2024-04-07T00:30:00Z"),
    ]
    assert all(r["freshness"]["pipeline_ingested_at"] == "2024-04-07T00:00:00Z" for r in gold)
    assert all(r["lineage"]["source_ids"] == ["aemo_dispatch_fixture", "weather_fixture"] for r in gold)


def test_run_id_output_is_write_once(tmp_path):
    output = tmp_path / "output"
    run_pipeline(output_dir=output, run_id="job-run-1", mode="fixture")
    sentinel = output / "bronze" / "sentinel.txt"
    sentinel.write_text("preserve")
    with pytest.raises(FileExistsError, match="OUTPUT_ALREADY_EXISTS"):
        run_pipeline(output_dir=output, run_id="job-run-1", mode="fixture")
    assert sentinel.read_text() == "preserve"

    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "missing")
    with pytest.raises(FileExistsError, match="OUTPUT_ALREADY_EXISTS"):
        run_pipeline(output_dir=dangling, run_id="job-run-2", mode="fixture")


def test_manifest_reconciles_source_row_accounting(tmp_path):
    output = tmp_path / "output"
    run_pipeline(output_dir=output)
    manifest = json.loads((output / "manifest.json").read_text())

    assert manifest["source_definitions"] == {"read": 2, "selected": 2}
    assert set(manifest["sources"]) == set(manifest["source_ids"])
    for counts in manifest["sources"].values():
        assert counts["bronze"] == counts["accepted"] + counts["quarantine"]
        assert counts["accepted"] == counts["silver"] + counts["deduplicated"]
    assert sum(item["bronze"] for item in manifest["sources"].values()) == manifest["layers"]["bronze"]
    assert sum(item["silver"] for item in manifest["sources"].values()) == manifest["layers"]["silver"]
    assert sum(item["quarantine"] for item in manifest["sources"].values()) == manifest["layers"]["quarantine"]


def test_manifest_carries_orchestration_context(tmp_path):
    output = tmp_path / "output"
    run_pipeline(
        output_dir=output,
        mode="fixture",
        run_id="job-run-123",
        metadata_snapshot_id="snapshot-456",
    )
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["run_id"] == "job-run-123"
    assert manifest["metadata_snapshot_id"] == "snapshot-456"
    assert manifest["mode"] == "fixture"
    metadata_bytes = (Path(__file__).resolve().parent.parent / "agentic_energy/resources/metadata/sources.json").read_bytes()
    import hashlib
    assert manifest["metadata_sha256"] == hashlib.sha256(metadata_bytes).hexdigest()


def test_external_metadata_root_and_fixture_mode_are_enforced(tmp_path):
    root = tmp_path / "contract-root"
    metadata_dir = root / "metadata"
    fixture_dir = root / "fixtures"
    metadata_dir.mkdir(parents=True)
    fixture_dir.mkdir()
    repository_root = Path(__file__).resolve().parent.parent
    metadata = json.loads((repository_root / "agentic_energy/resources/metadata/sources.json").read_text())
    for fixture in (repository_root / "agentic_energy/resources/fixtures").glob("*.jsonl"):
        (fixture_dir / fixture.name).write_bytes(fixture.read_bytes())
    metadata_path = metadata_dir / "snapshot.json"
    metadata_path.write_text(json.dumps(metadata))
    output = tmp_path / "output"
    run_pipeline(metadata_path, output, metadata_root=root, mode="fixture", metadata_snapshot_id="snapshot-1")
    assert json.loads((output / "manifest.json").read_text())["layers"]["gold"] == 3
    with pytest.raises(ValueError, match="OUTPUT_PATH_CONFLICTS_WITH_METADATA_ROOT"):
        run_pipeline(metadata_path, root, metadata_root=root, mode="fixture", metadata_snapshot_id="snapshot-1")

    metadata["sources"][0]["natural_key"] = ["region", "unknown_field"]
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="INVALID_NATURAL_KEY"):
        run_pipeline(metadata_path, tmp_path / "invalid-key-output", metadata_root=root, mode="fixture", metadata_snapshot_id="snapshot-1")

    live_metadata = json.loads((repository_root / "agentic_energy/resources/metadata/sources.live.json").read_text())
    live_path = metadata_dir / "live.json"
    live_path.write_text(json.dumps(live_metadata))
    with pytest.raises(ValueError, match="LIVE_MODE_NOT_ALLOWED"):
        run_pipeline(live_path, tmp_path / "live-output", metadata_root=root, mode="fixture", metadata_snapshot_id="snapshot-2")
    with pytest.raises(ValueError, match="METADATA_PATH_OUTSIDE_ROOT"):
        run_pipeline(live_path, tmp_path / "outside-output", metadata_root=tmp_path / "other", mode="fixture", metadata_snapshot_id="snapshot-3")


def test_metadata_rejects_non_standard_json_constants(tmp_path):
    metadata = (Path(__file__).resolve().parent.parent / "agentic_energy/resources/metadata/sources.json").read_text()
    metadata = metadata.replace('"pipeline_ingestion_timestamp": "2024-04-07T00:00:00Z"', '"pipeline_ingestion_timestamp": NaN')
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(metadata)
    with pytest.raises(json.JSONDecodeError, match="non-standard JSON constant"):
        run_pipeline(metadata_path, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_aest_and_aedt_are_normalized_using_source_timezone():
    assert _utc_timestamp("2024-04-07T10:00:00", "Australia/Sydney") == "2024-04-07T00:00:00Z"
    assert _utc_timestamp("2024-01-15T10:00:00", "Australia/Sydney") == "2024-01-14T23:00:00Z"


def test_failed_run_preserves_previous_output_and_rejects_unsafe_metadata(tmp_path):
    output = tmp_path / "output"
    run_pipeline(output_dir=output)
    manifest_before = (output / "manifest.json").read_bytes()

    metadata = json.loads((Path(__file__).resolve().parent.parent / "agentic_energy/resources/metadata/sources.json").read_text())
    metadata_dir = tmp_path / "metadata"
    fixture_dir = tmp_path / "fixtures"
    metadata_dir.mkdir()
    fixture_dir.mkdir()
    repository_fixtures = Path(__file__).resolve().parent.parent / "agentic_energy/resources/fixtures"
    for fixture in repository_fixtures.glob("*.jsonl"):
        (fixture_dir / fixture.name).write_bytes(fixture.read_bytes())
    metadata["sources"][0]["fixture_path"] = "fixtures/missing.jsonl"
    metadata_path = metadata_dir / "sources.json"
    metadata_path.write_text(json.dumps(metadata))

    with pytest.raises(FileNotFoundError):
        run_pipeline(metadata_path, output)
    assert (output / "manifest.json").read_bytes() == manifest_before

    metadata["sources"][0]["fixture_path"] = "../outside.jsonl"
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="FIXTURE_PATH_OUTSIDE_ROOT"):
        run_pipeline(metadata_path, output)
    assert (output / "manifest.json").read_bytes() == manifest_before

    metadata["sources"][0]["fixture_path"] = "fixtures/aemo_dispatch.jsonl"
    metadata["sources"][1]["fixture_path"] = "fixtures/weather.jsonl"
    metadata["sources"][1]["source_id"] = metadata["sources"][0]["source_id"]
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="DUPLICATE_SOURCE_ID"):
        run_pipeline(metadata_path, output)
    assert (output / "manifest.json").read_bytes() == manifest_before


def test_failed_promotion_cleans_staging_and_restores_output(tmp_path, monkeypatch):
    output = tmp_path / "output"
    run_pipeline(output_dir=output)
    manifest_before = (output / "manifest.json").read_bytes()
    real_replace = pipeline_module.os.replace
    failed = False

    def fail_staging_promotion(source, destination):
        nonlocal failed
        if Path(source).name.startswith(".output.staging-") and Path(destination) == output and not failed:
            failed = True
            raise OSError("simulated promotion failure")
        return real_replace(source, destination)

    monkeypatch.setattr(pipeline_module.os, "replace", fail_staging_promotion)
    with pytest.raises(OSError, match="simulated promotion failure"):
        run_pipeline(output_dir=output)
    assert (output / "manifest.json").read_bytes() == manifest_before
    assert not list(tmp_path.glob(".output.staging-*"))
    assert not list(tmp_path.glob(".output.backup-*"))


def test_malformed_rows_are_quarantined_without_aborting(tmp_path):
    root = tmp_path
    (root / "metadata").mkdir()
    (root / "fixtures").mkdir()
    repository_root = Path(__file__).resolve().parent.parent
    metadata = json.loads((repository_root / "agentic_energy/resources/metadata/sources.json").read_text())
    (root / "metadata/sources.json").write_text(json.dumps(metadata))
    (root / "fixtures/aemo_dispatch.jsonl").write_text(
        '{bad json}\n'
        'null\n'
        '{"region":"NSW1","interval_datetime":"not-a-time","demand_mw":1,"price_per_mwh":2}\n'
        '{"region":["NSW1"],"interval_datetime":"2024-01-15T10:00:00","demand_mw":1,"price_per_mwh":2}\n'
        '{"region":"NSW1","interval_datetime":"2024-01-15T10:00:00","demand_mw":1,"price_per_mwh":2,"ingestion_sequence":"bad"}\n'
        '{"region":"NSW1","interval_datetime":"2024-01-15","demand_mw":1,"price_per_mwh":2}\n'
    )
    (root / "fixtures/weather.jsonl").write_text(
        '{"region":"NSW1","observed_at":"2024-01-15T10:00:00","temperature_c":25,"ingestion_sequence":1}\n'
    )
    counts = run_pipeline(root / "metadata/sources.json", root / "out")
    assert counts["quarantine"] == 6
    rejected = lines(root / "out/quarantine/rejected.jsonl")
    assert all(r["source_id"] and r["source_row_number"] and r["reason_codes"] for r in rejected)
    codes = {code for row in rejected for code in row["reason_codes"]}
    assert "INVALID_RECORD_SHAPE" in codes
    assert "INVALID_EVENT_TIMESTAMP" in codes
    assert "INVALID_REGION" in codes
    assert "INVALID_INGESTION_SEQUENCE" in codes
    assert any(code.startswith("INVALID_JSON:") for code in codes)


def test_dispatchis_zip_parser_joins_price_and_region_summary():
    csv_text = "\n".join([
        "C,NEMP.WORLD,DISPATCHIS,AEMO,PUBLIC",
        "I,DISPATCH,PRICE,5,SETTLEMENTDATE,RUNNO,REGIONID,DISPATCHINTERVAL,INTERVENTION,RRP",
        'D,DISPATCH,PRICE,5,"2024/04/07 10:00:00",1,NSW1,20240407120,0,123.45',
        "I,DISPATCH,REGIONSUM,9,SETTLEMENTDATE,RUNNO,REGIONID,DISPATCHINTERVAL,INTERVENTION,TOTALDEMAND",
        'D,DISPATCH,REGIONSUM,9,"2024/04/07 10:00:00",1,NSW1,20240407120,0,9876.5',
    ])
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr("PUBLIC_DISPATCHIS_test.CSV", csv_text)

    rows = parse_dispatchis_zip(payload.getvalue(), "https://example.test/dispatch.zip")

    assert rows == [{
        "region": "NSW1",
        "interval_datetime": "2024-04-07T10:00:00",
        "demand_mw": 9876.5,
        "price_per_mwh": 123.45,
        "ingestion_sequence": 20240407120,
        "source_record_types": ["PRICE", "REGIONSUM"],
        "source_line_numbers": [3, 5],
        "source_file": "https://example.test/dispatch.zip",
    }]


def test_live_metadata_path_uses_generic_pipeline(monkeypatch, tmp_path):
    live_metadata = Path(__file__).resolve().parent.parent / "agentic_energy/resources/metadata/sources.live.json"
    monkeypatch.setattr(
        pipeline_module,
        "acquire_live_dispatchis",
        lambda source: ([{
            "region": "NSW1",
            "interval_datetime": "2024-04-07T10:00:00",
            "demand_mw": 9876.5,
            "price_per_mwh": 123.45,
            "ingestion_sequence": 20240407120,
        }], "https://nemweb.com.au/Reports/Current/DispatchIS_Reports/PUBLIC_DISPATCHIS_test.zip"),
    )

    counts = run_pipeline(live_metadata, tmp_path / "out", mode="live")

    assert counts == {"bronze": 6, "silver": 4, "quarantine": 1, "gold": 1}
    gold = lines(tmp_path / "out/gold/market_weather.jsonl")
    assert gold[0]["demand_mw"] == 9876.5
    assert gold[0]["price_per_mwh"] == 123.45
    assert gold[0]["temperature_c"] == 24.5
    assert gold[0]["lineage"]["market"]["source_file"].endswith("PUBLIC_DISPATCHIS_test.zip")


def test_fixture_mode_uses_declared_ingestion_timestamp(tmp_path):
    """The scored baseline must stay reproducible, so no wall clock in fixture mode."""
    out = tmp_path / "fixture"
    run_pipeline(output_dir=out)
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["pipeline_ingested_at"] == "2024-04-07T00:00:00Z"
    bronze = lines(out / "bronze/aemo_dispatch_fixture.jsonl")
    assert {row["_ingested_at"] for row in bronze} == {"2024-04-07T00:00:00Z"}


def test_live_mode_stamps_the_real_ingestion_instant(monkeypatch, tmp_path):
    """Live freshness must be real.

    Reusing the contract's fixed timestamp made a live run claim it ingested data
    on 2024-04-07 seconds after fetching it, silently invalidating every freshness
    and lineage marker. Freshness is part of the acceptance gate, and
    stale-by-construction freshness is worse than none because it looks
    authoritative.

    Uses the packaged fixture contract so no network access is needed: `--mode live`
    permits fixture-backed sources, and the clock is what is under test.
    """
    from datetime import datetime, timezone

    fixed = datetime(2026, 8, 12, 3, 4, 5, tzinfo=timezone.utc)

    class _Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed

    monkeypatch.setattr(pipeline_module, "datetime", _Clock)

    out = tmp_path / "live"
    run_pipeline(output_dir=out, mode="live")

    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["mode"] == "live"
    assert manifest["pipeline_ingested_at"] == "2026-08-12T03:04:05Z"
    assert manifest["pipeline_ingested_at"] != "2024-04-07T00:00:00Z"

    bronze = lines(out / "bronze/aemo_dispatch_fixture.jsonl")
    assert {row["_ingested_at"] for row in bronze} == {"2026-08-12T03:04:05Z"}
    gold = lines(out / "gold/market_weather.jsonl")
    assert {row["freshness"]["pipeline_ingested_at"] for row in gold} == {
        "2026-08-12T03:04:05Z"
    }



def test_evaluate_quality_check_function():
    """Test the _evaluate_quality_check function directly."""
    from agentic_energy.pipeline import _evaluate_quality_check
    
    # Test >= operator
    assert _evaluate_quality_check("demand_mw >= 0", {"demand_mw": 100}) == True
    assert _evaluate_quality_check("demand_mw >= 0", {"demand_mw": -1}) == False
    assert _evaluate_quality_check("demand_mw >= 8000", {"demand_mw": 8250}) == True
    assert _evaluate_quality_check("demand_mw >= 8000", {"demand_mw": 7999}) == False
    
    # Test is not null
    assert _evaluate_quality_check("price_per_mwh is not null", {"price_per_mwh": 70.0}) == True
    assert _evaluate_quality_check("price_per_mwh is not null", {"price_per_mwh": None}) == False
    assert _evaluate_quality_check("price_per_mwh is not null", {}) == False
    
    # Test is null
    assert _evaluate_quality_check("temperature_c is null", {"temperature_c": None}) == True
    assert _evaluate_quality_check("temperature_c is null", {"temperature_c": 25.0}) == False
    assert _evaluate_quality_check("temperature_c is null", {}) == True
    
    # Test other operators
    assert _evaluate_quality_check("value <= 100", {"value": 50}) == True
    assert _evaluate_quality_check("value <= 100", {"value": 150}) == False
    assert _evaluate_quality_check("value > 0", {"value": 1}) == True
    assert _evaluate_quality_check("value > 0", {"value": -1}) == False


def test_utc_timestamp_handles_dst_boundaries():
    """Test that _utc_timestamp handles DST boundaries gracefully.
    
    - Ambiguous times (fall-back): use fold=0 (earlier occurrence, pre-DST offset)
    - Non-existent times (spring-forward): use fold=0 (pre-DST offset)
    - This ensures deterministic behavior across DST transitions.
    """
    from agentic_energy.pipeline import _utc_timestamp
    
    # Normal timestamp (no DST boundary)
    assert _utc_timestamp("2024-04-07T10:00:00", "Australia/Sydney") == "2024-04-07T00:00:00Z"
    
    # Ambiguous time (fall-back): 2024-04-07 02:00 occurs twice
    # fold=0 gives the earlier occurrence (AEDT, UTC+11)
    result = _utc_timestamp("2024-04-07T02:00:00", "Australia/Sydney")
    assert result == "2024-04-06T15:00:00Z", f"Expected 2024-04-06T15:00:00Z, got {result}"
    
    # Non-existent time (spring-forward): 2024-10-06 02:00 doesn't exist
    # fold=0 interprets as pre-DST (AEST, UTC+10)
    result = _utc_timestamp("2024-10-06T02:00:00", "Australia/Sydney")
    assert result == "2024-10-05T16:00:00Z", f"Expected 2024-10-05T16:00:00Z, got {result}"
    
    # Verify determinism: same input always gives same output
    result1 = _utc_timestamp("2024-04-07T02:00:00", "Australia/Sydney")
    result2 = _utc_timestamp("2024-04-07T02:00:00", "Australia/Sydney")
    assert result1 == result2, "DST boundary handling must be deterministic"


def test_utc_timestamp_rejects_explicit_offsets():
    """Test that _utc_timestamp rejects timestamps with explicit UTC offsets."""
    from agentic_energy.pipeline import _utc_timestamp
    
    with pytest.raises(ValueError, match="OFFSET_NOT_ALLOWED"):
        _utc_timestamp("2024-04-07T10:00:00+10:00", "Australia/Sydney")
    
    # Z suffix is rejected by fromisoformat before we can check
    with pytest.raises(ValueError):
        _utc_timestamp("2024-04-07T10:00:00Z", "Australia/Sydney")


def test_utc_timestamp_rejects_invalid_format():
    """Test that _utc_timestamp rejects invalid timestamp formats."""
    from agentic_energy.pipeline import _utc_timestamp
    
    with pytest.raises(ValueError, match="INVALID_EVENT_TIMESTAMP"):
        _utc_timestamp("2024-04-07", "Australia/Sydney")  # Missing time
    
    # Time-only format is rejected by fromisoformat before we can check
    with pytest.raises(ValueError):
        _utc_timestamp("10:00:00", "Australia/Sydney")  # Missing date
