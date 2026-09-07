"""Validation and deterministic ordering for Lakebase CDF events."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Mapping

CHANGE_RANK = {"update_preimage": 0, "insert": 1, "update_postimage": 2, "delete": 3}
REQUIRED_METADATA = {"_pg_change_type", "_pg_lsn", "_pg_xid", "_timestamp", "_sort_by"}


def validate_event(event: Mapping[str, Any], *, key: str = "investigation_id") -> None:
    missing = REQUIRED_METADATA - event.keys()
    if missing:
        raise ValueError(f"CDF event missing metadata: {sorted(missing)}")
    if key not in event:
        raise ValueError(f"CDF event missing key: {key}")
    if event["_pg_change_type"] not in CHANGE_RANK:
        raise ValueError(f"unsupported CDF change type: {event['_pg_change_type']}")


def _integerish(value: Any) -> tuple[int, str]:
    text = str(value or "")
    try:
        return int(text), text
    except ValueError:
        return 0, text


def _lsn(value: Any) -> tuple[int, int]:
    if isinstance(value, int):
        return 0, value
    text = str(value or "0")
    if "/" not in text:
        try:
            return 0, int(text)
        except ValueError:
            return 0, 0
    parts = text.split("/", 1)
    try:
        return int(parts[0], 16), int(parts[1], 16)
    except (ValueError, IndexError):
        return 0, 0


def _timestamp(value: Any) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc)


def event_order(event: Mapping[str, Any]) -> tuple[Any, ...]:
    """Order by monotonic feed key, LSN, time, change rank, and canonical bytes."""

    canonical = json.dumps(dict(event), sort_keys=True, separators=(",", ":"), default=str)
    return (
        _integerish(event.get("_sort_by")),
        _lsn(event.get("_pg_lsn")),
        _timestamp(event.get("_timestamp")),
        CHANGE_RANK.get(str(event.get("_pg_change_type", "")), -1),
        canonical,
    )


def validate_update_pairs(events: list[Mapping[str, Any]], *, key: str = "investigation_id") -> None:
    """Require balanced preimages and postimages per key and transaction."""

    pairs: dict[tuple[str, str], dict[str, set[str]]] = {}
    for event in events:
        validate_event(event, key=key)
        change = str(event["_pg_change_type"])
        if change not in {"update_preimage", "update_postimage"}:
            continue
        pair_key = (str(event[key]), str(event["_pg_xid"]))
        canonical = json.dumps(dict(event), sort_keys=True, separators=(",", ":"), default=str)
        pairs.setdefault(
            pair_key,
            {"update_preimage": set(), "update_postimage": set()},
        )[change].add(canonical)
    unpaired = sorted(
        pair
        for pair, images in pairs.items()
        if len(images["update_preimage"]) != len(images["update_postimage"])
    )
    if unpaired:
        raise ValueError(f"unpaired Lakebase CDF update events: {unpaired}")
