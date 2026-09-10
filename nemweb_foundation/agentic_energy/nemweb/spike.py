"""Governed regional dispatch-price spike rule, independent of Spark.

The rule itself lives in ``resources/metadata/spike_rule.json`` so a threshold
change is a reviewable metadata diff with a different fingerprint and no code
change.  This module mirrors the semantics the Lakeflow Gold module applies, in
the same spirit as ``corrections.py``, so boundary, correction, intervention,
freshness and grain behaviour can be proved in fast offline tests.

The measure is dispatch price (RRP) in AUD/MWh, never settlement price.  Negative
prices are valid NEM outcomes and are never spikes.  A missing price is labelled
rather than silently treated as either a spike or a normal interval.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from agentic_energy.nemweb.contracts import ContractError, parse_market_time
from agentic_energy.nemweb.corrections import (
    latest_by_natural_key,
    mark_effective_intervention,
)

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPIKE_RULE = _PACKAGE_ROOT / "resources" / "metadata" / "spike_rule.json"

# The natural key of the governed regional dispatch subject. Intervention is part
# of the key because AEMO publishes a competing run for the same physical
# interval; both are retained and the effective run is selected afterwards.
NATURAL_KEY = ("interval_end", "region_id", "intervention")

SUPPORTED_RULES = frozenset({"absolute"})
SUPPORTED_BOUNDARIES = frozenset({"strict"})
_REQUIRED_FIELDS = (
    "rule",
    "threshold_aud_per_mwh",
    "boundary",
    "stale_after_seconds",
    "rationale",
)


@dataclass(frozen=True)
class SpikeRule:
    """The reviewed spike definition, loaded from metadata."""

    rule: str
    threshold_aud_per_mwh: float
    boundary: str
    stale_after_seconds: int
    rationale: str
    comment: str = ""


def load_spike_rule(path: Path | None = None) -> SpikeRule:
    """Read and validate the spike rule, failing closed before any classification.

    A malformed rule is rejected here so an unreviewed threshold can never reach a
    Gold row or an operator's answer.
    """

    source = Path(path) if path is not None else DEFAULT_SPIKE_RULE
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"spike rule metadata is missing: {source}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"spike rule metadata is not valid JSON: {source}") from exc
    if not isinstance(document, Mapping):
        raise ContractError("spike rule metadata must be a JSON object")

    missing = [name for name in _REQUIRED_FIELDS if name not in document]
    if missing:
        raise ContractError(f"spike rule metadata is missing fields: {sorted(missing)}")

    rule = document["rule"]
    if rule not in SUPPORTED_RULES:
        raise ContractError(
            f"unsupported spike rule {rule!r}; the reviewed rule is 'absolute'. A "
            "relative or trailing-median rule needs its own definition review."
        )
    boundary = document["boundary"]
    if boundary not in SUPPORTED_BOUNDARIES:
        raise ContractError(
            f"unsupported spike boundary {boundary!r}; the reviewed boundary is "
            "'strict', meaning a price exactly at the threshold is not a spike"
        )

    threshold = document["threshold_aud_per_mwh"]
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ContractError("threshold_aud_per_mwh must be a number in AUD/MWh")

    stale_after_seconds = document["stale_after_seconds"]
    if (
        isinstance(stale_after_seconds, bool)
        or not isinstance(stale_after_seconds, int)
        or stale_after_seconds <= 0
    ):
        raise ContractError("stale_after_seconds must be a positive whole number of seconds")

    rationale = document["rationale"]
    if not isinstance(rationale, str) or not rationale.strip():
        raise ContractError(
            "rationale must record why this threshold was chosen; an unexplained "
            "threshold is not reviewable"
        )
    comment = document.get("comment", "")
    if not isinstance(comment, str):
        raise ContractError("comment must be a string when present")

    return SpikeRule(
        rule=rule,
        threshold_aud_per_mwh=float(threshold),
        boundary=boundary,
        stale_after_seconds=stale_after_seconds,
        rationale=rationale,
        comment=comment,
    )


def rule_fingerprint(rule: SpikeRule) -> str:
    """Fingerprint the operative rule so a threshold change is visible in evidence.

    Only the fields that change the answer are hashed. Rewording the rationale
    does not alter a published result, so it must not alter the fingerprint.
    """

    operative = {
        "rule": rule.rule,
        "threshold_aud_per_mwh": rule.threshold_aud_per_mwh,
        "boundary": rule.boundary,
        "stale_after_seconds": rule.stale_after_seconds,
    }
    canonical = json.dumps(operative, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _read_instant(value: Any, name: str) -> datetime:
    """Parse a UTC processing instant. Market time is handled separately."""

    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ContractError(f"{name} must be timezone-aware")
        return value.astimezone(timezone.utc)
    if value is None or not str(value).strip():
        raise ContractError(f"{name} is empty")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{name} is not an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{name} must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def _five_minute_interval_end(value: Any) -> datetime:
    """Parse interval_end as fixed AEST and hold it to the five-minute grain."""

    parsed = parse_market_time(str(value))
    if parsed.minute % 5 or parsed.second or parsed.microsecond:
        raise ContractError(
            f"interval_end {value!r} is not on the five-minute interval-ending grain"
        )
    return parsed


def classify_interval(
    row: Mapping[str, Any], *, as_of: Any, rule: SpikeRule
) -> dict[str, Any]:
    """Apply the governed rule to one already-selected effective regional row."""

    result = dict(row)
    read_at = _read_instant(as_of, "as_of")
    _five_minute_interval_end(result.get("interval_end"))

    price = result.get("rrp_aud_per_mwh")
    if price is None or (isinstance(price, str) and not price.strip()):
        # A missing price is not a spike, and it is not an ordinary interval
        # either. Labelling it keeps the gap visible to the operator.
        result["price_status"] = "UNKNOWN_PRICE"
        result["is_price_spike"] = False
    else:
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise ContractError("rrp_aud_per_mwh must be a number in AUD/MWh")
        result["price_status"] = "PRESENT"
        # Strict boundary: exactly at the threshold is not a spike.
        result["is_price_spike"] = float(price) > rule.threshold_aud_per_mwh

    published_at = _read_instant(result.get("source_publication_at"), "source_publication_at")
    lag_seconds = (read_at - published_at).total_seconds()
    result["source_publication_lag_seconds"] = lag_seconds
    # Freshness is a label on the answer, never a filter. A stale spike is still
    # reported so it cannot be mistaken for an absence of spikes.
    result["spike_freshness_status"] = (
        "STALE" if lag_seconds > rule.stale_after_seconds else "CURRENT"
    )

    result["spike_rule"] = rule.rule
    result["spike_threshold_aud_per_mwh"] = rule.threshold_aud_per_mwh
    result["spike_boundary"] = rule.boundary
    result["spike_rule_fingerprint"] = rule_fingerprint(rule)
    return result


def spike_rows(
    rows: Iterable[Mapping[str, Any]], *, as_of: Any, rule: SpikeRule
) -> list[dict[str, Any]]:
    """Classify governed regional dispatch rows at region and five-minute grain.

    Corrections are resolved first, then the effective intervention run is
    selected, and only then is the rule applied. Doing it in that order is what
    stops a superseded value or a non-effective run from creating a spike. The
    input rows are never mutated; Bronze and Gold history is unchanged.
    """

    materialised = [dict(row) for row in rows]
    for row in materialised:
        _five_minute_interval_end(row.get("interval_end"))

    corrected = latest_by_natural_key(materialised, NATURAL_KEY)
    labelled = mark_effective_intervention(corrected, ("interval_end", "region_id"))
    effective = [row for row in labelled if row["is_effective_run"]]
    classified = [classify_interval(row, as_of=as_of, rule=rule) for row in effective]
    return sorted(classified, key=lambda row: (row["interval_end"], row["region_id"]))


def rule_document(rule: SpikeRule) -> dict[str, Any]:
    """The rule and its fingerprint, for an evidence record."""

    return {**asdict(rule), "fingerprint": rule_fingerprint(rule)}
