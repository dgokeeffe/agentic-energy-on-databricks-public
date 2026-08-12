"""Metadata-driven, deterministic Bronze/Silver/Quarantine/Gold workflow."""
from __future__ import annotations
try:
    import fcntl
except ImportError:  # pragma: no cover - Windows local development fallback
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover - POSIX runtime
    msvcrt = None

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import math
import os
import re
import shutil
import tempfile
import uuid

from .acquisition import acquire_live_dispatchis

UTC = timezone.utc
_PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_METADATA = _PACKAGE_ROOT / "resources" / "metadata" / "sources.json"
DEFAULT_LIVE_METADATA = _PACKAGE_ROOT / "resources" / "metadata" / "sources.live.json"


def _reject_json_constant(value: str):
    raise json.JSONDecodeError(f"non-standard JSON constant: {value}", "", 0)


def _read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for row_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                yield row_number, line.rstrip("\n"), json.loads(line, parse_constant=_reject_json_constant), None
            except json.JSONDecodeError as exc:
                yield row_number, line.rstrip("\n"), None, f"INVALID_JSON:{exc.msg}"


def _evaluate_quality_check(check: str, row: dict) -> bool:
    """Evaluate a simple quality check expression against a row.
    
    Supports patterns like:
      - "field >= 0"
      - "field is not null"
      - "field is null"
    
    Returns True if the check passes (row is acceptable).
    """
    check = check.strip()
    
    # Handle "field is not null" / "field is null"
    if " is not null" in check:
        field = check.replace(" is not null", "").strip()
        return field in row and row[field] is not None
    elif " is null" in check:
        field = check.replace(" is null", "").strip()
        return field not in row or row[field] is None
    
    # Handle "field op value" patterns (e.g., "demand_mw >= 0")
    for op in ["<=", ">=", "<", ">", "==", "!="]:
        if f" {op} " in check:
            field, value_str = check.split(f" {op} ", 1)
            field = field.strip()
            value_str = value_str.strip()
            if field not in row:
                return False
            val = row[field]
            if val is None:
                return False
            try:
                value = float(value_str)
                if op == ">=":
                    return val >= value
                elif op == "<=":
                    return val <= value
                elif op == ">":
                    return val > value
                elif op == "<":
                    return val < value
                elif op == "==":
                    return val == value
                elif op == "!=":
                    return val != value
            except (ValueError, TypeError):
                return False
    
    return True


def _utc_timestamp(value: str, source_timezone: str) -> str:
    # Convert local wall-clock timestamps to UTC, handling DST boundaries gracefully.
    # For ambiguous times (fall-back): use fold=0 (earlier occurrence, pre-DST offset)
    # For non-existent times (spring-forward): use fold=0 (pre-DST offset)
    # This ensures deterministic, predictable behavior across DST transitions.
    parsed = datetime.fromisoformat(value)
    if "T" not in value and " " not in value:
        raise ValueError("INVALID_EVENT_TIMESTAMP")
    if parsed.tzinfo is not None:
        raise ValueError("OFFSET_NOT_ALLOWED")
    zone = ZoneInfo(source_timezone)
    # Always use fold=0 for DST boundaries (canonical choice)
    local = parsed.replace(tzinfo=zone, fold=0)
    return local.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _strict_json_value(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _strict_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_strict_json_value(item) for item in value]
    return value


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(_strict_json_value(row), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def _promote_output(staging: Path, output: Path, *, allow_replace: bool) -> None:
    lock_handle = None
    if not allow_replace:
        lock_path = output.parent / f".{output.name}.lock"
        lock_handle = lock_path.open("a+")
        if fcntl is not None:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        elif msvcrt is not None:  # pragma: no cover - Windows only
            lock_handle.seek(0)
            lock_handle.write("0")
            lock_handle.flush()
            lock_handle.seek(0)
            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_LOCK, 1)
        else:  # pragma: no cover - unsupported runtime
            lock_handle.close()
            raise RuntimeError("WRITE_ONCE_LOCK_UNSUPPORTED")
    try:
        if (output.exists() or output.is_symlink()) and not allow_replace:
            raise FileExistsError("OUTPUT_ALREADY_EXISTS")
        backup = output.parent / f".{output.name}.backup-{uuid.uuid4().hex}"
        _remove_path(backup)
        try:
            if output.exists() or output.is_symlink():
                os.replace(output, backup)
            os.replace(staging, output)
        except BaseException:
            if output.exists() or output.is_symlink():
                _remove_path(output)
            if backup.exists() or backup.is_symlink():
                os.replace(backup, output)
            raise
        else:
            _remove_path(backup)
    finally:
        if lock_handle is not None:
            if fcntl is not None:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            elif msvcrt is not None:  # pragma: no cover - Windows only
                lock_handle.seek(0)
                msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
            lock_handle.close()


def _validate_source(source: dict, root: Path) -> Path | None:
    source_id = source.get("source_id")
    if not isinstance(source_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", source_id):
        raise ValueError("INVALID_SOURCE_ID")
    natural_key = source.get("natural_key")
    if (not isinstance(natural_key, list) or not natural_key or
            any(not isinstance(field, str) or not field for field in natural_key)):
        raise ValueError("INVALID_NATURAL_KEY")
    dataset = source.get("dataset")
    allowed_key_fields = {"region", "interval_utc", "ingestion_sequence"}
    if dataset in {"DISPATCH_SCADA", "DISPATCHIS"}:
        allowed_key_fields.update({"demand_mw", "price_per_mwh"})
    elif dataset == "HOURLY_WEATHER":
        allowed_key_fields.add("temperature_c")
    event_field = source.get("event_timestamp_field")
    if not isinstance(event_field, str) or any(
        field not in allowed_key_fields and field != event_field for field in natural_key
    ):
        raise ValueError("INVALID_NATURAL_KEY")
    mode = source.get("extraction_mode", "fixture")
    if mode == "live":
        if not isinstance(source.get("url_or_fixture_path"), str) or not source["url_or_fixture_path"].startswith(("http://", "https://")):
            raise ValueError("INVALID_LIVE_SOURCE_URL")
        return None
    if mode != "fixture":
        raise ValueError("INVALID_EXTRACTION_MODE")
    configured_path = source.get("fixture_path")
    if not isinstance(configured_path, str):
        raise ValueError("INVALID_FIXTURE_PATH")
    relative_path = Path(configured_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("FIXTURE_PATH_OUTSIDE_ROOT")
    fixture = (root / relative_path).resolve()
    try:
        fixture.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("FIXTURE_PATH_OUTSIDE_ROOT") from exc
    return fixture

def _source_rows(source: dict, root: Path):
    if source.get("extraction_mode", "fixture") == "live":
        live_rows, source_file = acquire_live_dispatchis(source)
        for row_number, row in enumerate(live_rows, 1):
            raw_line = json.dumps(row, sort_keys=True, separators=(",", ":"))
            yield row_number, raw_line, row, None, source_file
        return
    fixture = _validate_source(source, root)
    assert fixture is not None
    for row_number, raw_line, row, parse_error in _read_jsonl(fixture):
        yield row_number, raw_line, row, parse_error, str(source["fixture_path"])


def run_pipeline(
    metadata_path: str | Path = DEFAULT_METADATA,
    output_dir: str | Path = "output",
    *,
    metadata_root: str | Path | None = None,
    mode: str = "fixture",
    run_id: str | None = None,
    metadata_snapshot_id: str | None = None,
) -> dict[str, int]:
    metadata_path = Path(metadata_path).resolve()
    output_input = Path(output_dir)
    output = output_input if output_input.is_symlink() else output_input.resolve()
    if metadata_root is not None:
        root = Path(metadata_root).resolve()
        try:
            metadata_path.relative_to(root)
        except ValueError as exc:
            raise ValueError("METADATA_PATH_OUTSIDE_ROOT") from exc
        if metadata_snapshot_id is None or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", metadata_snapshot_id):
            raise ValueError("INVALID_METADATA_SNAPSHOT_ID")
        if metadata_path.is_relative_to(output):
            raise ValueError("OUTPUT_PATH_CONFLICTS_WITH_METADATA_ROOT")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        counts = _run_pipeline_in_place(
            Path(metadata_path).resolve(),
            staging,
            metadata_root=Path(metadata_root).resolve() if metadata_root is not None else None,
            mode=mode,
            run_id=run_id,
            metadata_snapshot_id=metadata_snapshot_id,
        )
        _promote_output(staging, output, allow_replace=run_id is None)
    except BaseException:
        _remove_path(staging)
        raise
    return counts


def _ingestion_timestamp(metadata: dict, mode: str) -> str:
    """Resolve the run's ingestion instant.

    Fixture mode uses the timestamp declared in the metadata contract, because
    the scored baseline must be byte-for-byte reproducible on replay — a wall
    clock there would break determinism.

    Live mode must use the real instant. Reusing the contract's fixed timestamp
    made a live run report ``pipeline_ingested_at`` and ``_ingested_at`` of
    2024-04-07 for data fetched seconds earlier, so every freshness marker and
    piece of lineage evidence was wrong by years. Freshness is part of the
    acceptance gate, and stale-by-construction freshness is worse than none: it
    looks authoritative.
    """
    if mode == "live":
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return metadata["pipeline_ingestion_timestamp"]


def _run_pipeline_in_place(
    metadata_path: Path,
    output_dir: Path,
    *,
    metadata_root: Path | None = None,
    mode: str = "fixture",
    run_id: str | None = None,
    metadata_snapshot_id: str | None = None,
) -> dict[str, int]:
    metadata_path = Path(metadata_path).resolve()
    if mode is None:
        mode = "fixture"
    root = (metadata_root or metadata_path.parent.parent).resolve()
    if metadata_root is not None:
        try:
            metadata_path.relative_to(root)
        except ValueError as exc:
            raise ValueError("METADATA_PATH_OUTSIDE_ROOT") from exc
    metadata_bytes = metadata_path.read_bytes()
    metadata_hash = hashlib.sha256(metadata_bytes).hexdigest()
    metadata = json.loads(metadata_bytes.decode("utf-8"), parse_constant=_reject_json_constant)
    if mode not in (None, "fixture", "live"):
        raise ValueError("INVALID_RUN_MODE")
    for source in metadata["sources"]:
        if mode == "fixture" and source.get("extraction_mode", "fixture") == "live":
            raise ValueError("LIVE_MODE_NOT_ALLOWED")
        _validate_source(source, root)
    source_ids = [source["source_id"] for source in metadata["sources"]]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("DUPLICATE_SOURCE_ID")
    out = Path(output_dir)
    for layer in ("bronze", "silver", "quarantine", "gold"):
        shutil.rmtree(out / layer, ignore_errors=True)
    (out / "manifest.json").unlink(missing_ok=True)
    sources = {source["source_id"]: source for source in metadata["sources"]}
    bronze, quarantine, silver_by_source = [], [], {}
    source_reconciliation: dict[str, dict[str, int]] = {}
    ingested_at = _ingestion_timestamp(metadata, mode)
    rejection_at = ingested_at

    for source in metadata["sources"]:
        source_id = source["source_id"]
        raw_rows = []
        quarantine_before = len(quarantine)
        time_field = source["event_timestamp_field"]
        is_market = source["dataset"] in {"DISPATCH_SCADA", "DISPATCHIS"}
        for row_number, raw_line, row, parse_error, source_file in _source_rows(source, root):
            raw_rows.append({"source_id": source_id, "source_file": source_file,
                             "source_row_number": row_number, "raw_line": raw_line,
                             "raw_record": row, "_ingested_at": ingested_at})
            reasons = [parse_error] if parse_error else []
            raw_record = row
            if not isinstance(row, dict):
                reasons.append("INVALID_RECORD_SHAPE")
                row = {}
            region = row.get("region")
            if not region:
                reasons.append("MISSING_REGION")
            elif not isinstance(region, str):
                reasons.append("INVALID_REGION")
            sequence = row.get("ingestion_sequence", 0)
            if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
                reasons.append("INVALID_INGESTION_SEQUENCE")
            # Apply quality checks from metadata
            for check in source.get("quality_checks", []):
                if not _evaluate_quality_check(check, row):
                    # Map check to a reason code
                    if "demand_mw" in check and ">= 0" in check:
                        reasons.append("INVALID_DEMAND")
                    elif "price_per_mwh" in check and "is not null" in check:
                        reasons.append("MISSING_PRICE")
                    elif "temperature_c" in check and "is not null" in check:
                        reasons.append("MISSING_TEMPERATURE")
                    else:
                        # Generic quality check failure
                        reasons.append(f"QUALITY_CHECK_FAILED:{check}")
            if not row.get(time_field):
                reasons.append("MISSING_EVENT_TIMESTAMP")
            if not reasons:
                try:
                    interval_utc = _utc_timestamp(row[time_field], source["source_timezone"])
                except (TypeError, ValueError) as exc:
                    code = str(exc)
                    reasons.append(code if code in {"OFFSET_NOT_ALLOWED", "NONEXISTENT_OR_AMBIGUOUS_LOCAL_TIME"} else "INVALID_EVENT_TIMESTAMP")
            if reasons:
                quarantine.append({"source_id": source_id, "source_file": source_file,
                                   "source_row_number": row_number, "reason_codes": reasons,
                                   "rejected_at": rejection_at, "raw_record": raw_record})
                continue
            normalized = {"source_id": source_id, "source_file": source_file,
                          "source_row_number": row_number, "region": row["region"],
                          "interval_utc": interval_utc,
                          "ingestion_sequence": sequence,
                          "lineage": {"source_id": source_id, "source_version": source["source_version"],
                                      "provider": source["provider"], "dataset": source["dataset"],
                                      "licensing_provenance": source["licensing_provenance"],
                                      "source_file": source_file,
                                      "source_row_number": row_number}}
            if is_market:
                normalized.update(demand_mw=row["demand_mw"], price_per_mwh=row["price_per_mwh"])
            else:
                normalized.update(temperature_c=row["temperature_c"])
            silver_by_source.setdefault(source_id, []).append(normalized)
        source_reconciliation[source_id] = {
            "bronze": len(raw_rows),
            "accepted": len(silver_by_source.get(source_id, [])),
            "quarantine": len(quarantine) - quarantine_before,
        }
        bronze.extend(raw_rows)
        _write_jsonl(out / "bronze" / f"{source_id}.jsonl", raw_rows)

    # Metadata natural keys are evaluated after event timestamps are normalized.
    for source_id in sorted(sources):
        rows = silver_by_source.get(source_id, [])
        source = sources[source_id]
        if source["deduplication_rule"] != "last_by_ingestion_sequence":
            raise ValueError(f"Unsupported deduplication_rule for {source_id}")
        deduped = {}
        for row in rows:
            key = tuple(row["interval_utc"] if field == source["event_timestamp_field"] else row[field]
                        for field in source["natural_key"])
            if key not in deduped or row["ingestion_sequence"] >= deduped[key]["ingestion_sequence"]:
                deduped[key] = row
        silver_by_source[source_id] = sorted(deduped.values(), key=lambda r: (r["region"], r["interval_utc"]))
        row_counts = source_reconciliation[source_id]
        row_counts["silver"] = len(silver_by_source[source_id])
        row_counts["deduplicated"] = row_counts["accepted"] - row_counts["silver"]
        if row_counts["bronze"] != row_counts["accepted"] + row_counts["quarantine"]:
            raise RuntimeError(f"BRONZE_RECONCILIATION_FAILED:{source_id}")
        if row_counts["accepted"] != row_counts["silver"] + row_counts["deduplicated"]:
            raise RuntimeError(f"SILVER_RECONCILIATION_FAILED:{source_id}")
        _write_jsonl(out / "silver" / f"{source_id}.jsonl", silver_by_source[source_id])
    _write_jsonl(out / "quarantine" / "rejected.jsonl", sorted(quarantine, key=lambda r: (r["source_id"], r["source_row_number"])))

    market_sources = [source for source in metadata["sources"] if source["dataset"] in {"DISPATCH_SCADA", "DISPATCHIS"}]
    weather_sources = [source for source in metadata["sources"] if source["dataset"] == "HOURLY_WEATHER"]
    if len(market_sources) != 1 or len(weather_sources) != 1:
        raise ValueError("Metadata must define exactly one DISPATCH_SCADA and one HOURLY_WEATHER source")
    market_source, weather_source = market_sources[0], weather_sources[0]
    weather = {(r["region"], r["interval_utc"]): r
               for r in silver_by_source.get(weather_source["source_id"], [])}
    gold = []
    for market in silver_by_source.get(market_source["source_id"], []):
        key = (market["region"], market["interval_utc"])
        weather_row = weather.get(key)
        gold.append({"region": market["region"], "interval_utc": market["interval_utc"],
                     "demand_mw": market["demand_mw"], "price_per_mwh": market["price_per_mwh"],
                     "temperature_c": weather_row["temperature_c"] if weather_row else None,
                     "freshness": {"pipeline_ingested_at": ingested_at,
                                   "latest_event_utc": market["interval_utc"]},
                     "lineage": {"market": market["lineage"],
                                 "weather": weather_row["lineage"] if weather_row else None,
                                 "source_ids": [market_source["source_id"], weather_source["source_id"]]}})
    gold.sort(key=lambda r: (r["region"], r["interval_utc"]))
    _write_jsonl(out / "gold" / "market_weather.jsonl", gold)
    manifest = {"layers": {"bronze": len(bronze), "silver": sum(map(len, silver_by_source.values())),
                            "quarantine": len(quarantine), "gold": len(gold)},
                "source_definitions": {"read": len(source_ids), "selected": len(metadata["sources"])},
                "sources": {source_id: source_reconciliation[source_id] for source_id in sorted(source_reconciliation)},
                "source_ids": sorted(sources), "pipeline_ingested_at": ingested_at,
                "metadata_sha256": metadata_hash}
    if run_id is not None:
        manifest["run_id"] = run_id
    if metadata_snapshot_id is not None:
        manifest["metadata_snapshot_id"] = metadata_snapshot_id
    if mode is not None:
        manifest["mode"] = mode
    (out / "manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return dict(manifest["layers"])
