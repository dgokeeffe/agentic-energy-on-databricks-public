"""Deterministic Silver contract helpers independent of Spark.

These helpers mirror the window ordering used by the Lakeflow Silver modules so
correction, intervention and NEMWEB-only dimension semantics can be proved in
fast local tests. Bronze is never changed by these functions.
"""

from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

from agentic_energy.nemweb.contracts import ContractError, parse_market_time


def _required_text(row: Mapping[str, Any], name: str) -> str:
    value = row.get(name)
    if value is None or not str(value).strip():
        raise ContractError(f"natural-key field {name!r} is empty")
    return str(value).strip()


def _integer(row: Mapping[str, Any], name: str, default: int = 0) -> int:
    value = row.get(name)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"ordering field {name!r} is not an integer") from exc


def _price(row: Mapping[str, Any], name: str) -> float:
    """Read a required price. A missing price is never treated as zero."""

    value = row.get(name)
    if value is None or str(value).strip() == "":
        raise ContractError(f"price field {name!r} is empty")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"price field {name!r} is not a number") from exc


def _instant(value: Any, name: str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ContractError(f"ordering field {name!r} must be timezone-aware")
        return value
    if value is None or not str(value).strip():
        raise ContractError(f"ordering field {name!r} is empty")
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise ContractError(f"ordering field {name!r} is not an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"ordering field {name!r} must be timezone-aware")
    return parsed


def correction_order(
    row: Mapping[str, Any], source_revision: str | None = None
) -> tuple[Any, ...]:
    """Return the approved latest-correction order.

    RUNNO is the report-specific version when present. ``report_version`` is
    retained as the first component because AEMO may publish concurrent section
    versions. Publication and ingestion sequence are deterministic tie-breaks.
    """

    revision = _integer(row, source_revision) if source_revision else 0
    return (
        _integer(row, "report_version"),
        revision,
        _integer(row, "source_run_no")
        if row.get("source_run_no") not in (None, "")
        else _integer(row, "run_no"),
        _instant(row.get("source_publication_at"), "source_publication_at"),
        _instant(row.get("landed_at"), "landed_at")
        if row.get("landed_at") not in (None, "")
        else _instant(row.get("source_publication_at"), "source_publication_at"),
        str(row.get("ingestion_run_id") or ""),
        _integer(row, "ingestion_sequence"),
    )


def latest_by_natural_key(
    rows: Iterable[Mapping[str, Any]], key_fields: Sequence[str],
    *, source_revision: str | None = None,
) -> list[dict[str, Any]]:
    """Select one latest correction for every valid natural key."""

    latest: dict[tuple[str, ...], tuple[tuple[Any, ...], dict[str, Any]]] = {}
    for source in rows:
        row = dict(source)
        key = tuple(_required_text(row, field) for field in key_fields)
        order = correction_order(row, source_revision)
        existing = latest.get(key)
        if existing is None or order > existing[0]:
            latest[key] = (order, row)
    return [latest[key][1] for key in sorted(latest)]


def mark_effective_intervention(
    rows: Iterable[Mapping[str, Any]], key_fields_without_intervention: Sequence[str]
) -> list[dict[str, Any]]:
    """Label the highest available intervention flag for each business key.

    Both intervention rows remain present. Consumers can default to the row
    labelled ``is_effective_run`` without double counting the pair.
    """

    materialised = [dict(row) for row in rows]
    highest: dict[tuple[str, ...], int] = {}
    for row in materialised:
        key = tuple(_required_text(row, field) for field in key_fields_without_intervention)
        flag = _integer(row, "intervention")
        highest[key] = max(highest.get(key, flag), flag)
    for row in materialised:
        key = tuple(str(row[field]).strip() for field in key_fields_without_intervention)
        row["is_effective_run"] = _integer(row, "intervention") == highest[key]
    return materialised


def price_formation_basis(row: Mapping[str, Any]) -> str:
    """Classify how a dispatch price was formed.

    A price pinned at an administered cap, or set while the market is suspended,
    is an intervention artefact rather than a market scarcity signal. Callers
    must be able to separate the two; adding them together overstates genuine
    price risk. Suspension is reported ahead of the administered cap because a
    suspended market can carry both flags.
    """

    if _integer(row, "market_suspended_flag") == 1:
        return "SUSPENDED"
    if _integer(row, "administered_price_cap_flag") == 1:
        return "ADMINISTERED"
    return "MARKET"


def _spike_verdict(
    price: float, baseline: list[float], baseline_intervals: int, baseline_multiple: float
) -> tuple[float | None, bool | None]:
    """Resolve the trailing median and spike flag, or withhold both.

    The flag is ``None`` rather than ``False`` whenever the comparison cannot be
    made, so "not yet known" is never read as "checked, no spike".
    """

    if len(baseline) < baseline_intervals:
        return None, None
    median_price = median(baseline)
    # NEM prices go negative. A ratio against a zero or negative baseline is
    # meaningless: -500 > 2 * -100 is arithmetically true and market nonsense.
    if median_price <= 0:
        return median_price, None
    return median_price, price >= median_price * baseline_multiple


def mark_price_spikes(
    rows: Iterable[Mapping[str, Any]],
    *,
    baseline_intervals: int,
    baseline_multiple: float,
) -> list[dict[str, Any]]:
    """Flag five-minute dispatch prices above a trailing regional baseline.

    The baseline is the median of the ``baseline_intervals`` rows immediately
    preceding each interval for the same region, and strictly excludes the
    interval being judged so a spike can never inflate the baseline it is
    measured against. The comparison is inclusive (``>=``): a price exactly on
    the multiple is a spike.

    Only effective runs are considered, matching every other default regional
    aggregation. Rows are returned in region and interval order; inputs are not
    modified.
    """

    if baseline_intervals < 1:
        raise ContractError("baseline_intervals must be at least 1")
    if baseline_multiple <= 0:
        raise ContractError("baseline_multiple must be greater than zero")

    effective = [dict(row) for row in rows if row.get("is_effective_run")]
    effective.sort(
        key=lambda row: (
            _required_text(row, "region_id"),
            _instant(row.get("interval_end"), "interval_end"),
        )
    )

    history: dict[str, list[float]] = {}
    for row in effective:
        region = _required_text(row, "region_id")
        price = _price(row, "rrp_aud_per_mwh")
        baseline = history.setdefault(region, [])
        median_price, is_spike = _spike_verdict(
            price, baseline, baseline_intervals, baseline_multiple
        )
        row["trailing_median_price_aud_per_mwh"] = median_price
        row["is_price_spike"] = is_spike
        row["spike_baseline_intervals"] = baseline_intervals
        row["spike_baseline_multiple"] = baseline_multiple
        row["price_formation_basis"] = price_formation_basis(row)
        baseline.append(price)
        del baseline[:-baseline_intervals]
    return effective


def canonical_fuel_type(raw: Any) -> str:
    """Normalise AEMO GENUNITS.CO2E_ENERGY_SOURCE without inventing a fuel."""

    if raw is None or not str(raw).strip():
        return "UNKNOWN"
    text = " ".join(str(raw).strip().split())
    return text.casefold().capitalize()


def _latest_effective(
    rows: Iterable[Mapping[str, Any]], key: str, value: str, as_of: str,
    start: str, version: str, end: str | None = None,
) -> dict[str, Any] | None:
    candidates = []
    point = parse_market_time(as_of)
    for source in rows:
        row = dict(source)
        if str(row.get(key, "")).strip() != value:
            continue
        begins = parse_market_time(str(row[start]))
        if begins > point:
            continue
        if end and row.get(end) and parse_market_time(str(row[end])) <= point:
            continue
        candidates.append((begins, _integer(row, version), row))
    return max(candidates, default=(None, None, None), key=lambda item: item[:2])[2]


def build_facility_dimension(
    duids: Iterable[str],
    dudetail: Iterable[Mapping[str, Any]],
    allocations: Iterable[Mapping[str, Any]],
    genunits: Iterable[Mapping[str, Any]],
    *,
    as_of: str,
) -> list[dict[str, Any]]:
    """Build the proven MMSDM DUDETAILSUMMARY→DUALLOC→GENUNITS dimension.

    Every input DUID survives. DUALLOC falls back to ``GENSETID == DUID`` for
    common single-unit registrations. Missing fuel is explicitly UNKNOWN.
    """

    dudetail_rows = list(dudetail)
    allocation_rows = list(allocations)
    gen_by_id = {str(row.get("genset_id", "")).strip(): dict(row) for row in genunits}
    result = []
    for raw_duid in duids:
        duid = str(raw_duid).strip()
        if not duid:
            raise ContractError("natural-key field 'duid' is empty")
        detail = _latest_effective(
            dudetail_rows, "duid", duid, as_of, "start_date", "source_version_no", "end_date"
        )
        allocation = _latest_effective(
            allocation_rows, "duid", duid, as_of, "effective_at", "source_version_no"
        )
        genset_id = str((allocation or {}).get("genset_id") or duid).strip()
        generator = gen_by_id.get(genset_id) or gen_by_id.get(duid)
        region = (detail or {}).get("region_id") or "UNKNOWN"
        raw_fuel = (generator or {}).get("fuel_type_raw")
        fuel = canonical_fuel_type(raw_fuel)
        result.append(
            {
                "duid": duid,
                "region_id": region,
                "station_id": (detail or {}).get("station_id"),
                "dispatch_type": (detail or {}).get("dispatch_type"),
                "schedule_type": (detail or {}).get("schedule_type"),
                "genset_id": genset_id,
                "fuel_type_raw": raw_fuel,
                "fuel_type": fuel,
                "registered_capacity_mw": (generator or {}).get("registered_capacity_mw"),
                "maximum_capacity_mw": (generator or {}).get("maximum_capacity_mw"),
                "dimension_match_status": (
                    "REGION_AND_FUEL" if region != "UNKNOWN" and fuel != "UNKNOWN"
                    else "REGION_ONLY" if region != "UNKNOWN"
                    else "FUEL_ONLY" if fuel != "UNKNOWN"
                    else "UNMATCHED"
                ),
            }
        )
    return result


def constraint_is_binding(marginal_value: Any) -> bool:
    """Derived interpretation: any non-zero marginal value is binding."""

    return marginal_value is not None and float(marginal_value) != 0.0
