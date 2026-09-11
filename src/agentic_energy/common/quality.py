"""Pure fail-closed quality contracts for NEMWEB enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, Any

from agentic_energy.common.contracts import UTC, ContractError


@dataclass(frozen=True)
class RegistrationEnrichmentQuality:
    """Aggregate quality for rows expected to use registration context."""

    total_rows: int
    known_region_rows: int
    known_fuel_rows: int

    @property
    def known_region_ratio(self) -> float:
        return self.known_region_rows / self.total_rows if self.total_rows else 0.0

    @property
    def known_fuel_ratio(self) -> float:
        return self.known_fuel_rows / self.total_rows if self.total_rows else 0.0

    def validate(self, *, registration_context_expected: bool) -> None:
        if not registration_context_expected:
            return
        if self.total_rows < 1:
            raise ValueError("registration context was expected but no enriched rows were present")
        if self.known_region_rows < 1:
            raise ValueError("registration enrichment is unhealthy: all regions are UNKNOWN")
        if self.known_fuel_rows < 1:
            raise ValueError("registration enrichment is unhealthy: all fuels are UNKNOWN")


def registration_enrichment_quality(
    rows: Iterable[Mapping[str, Any]],
) -> RegistrationEnrichmentQuality:
    """Summarise enrichment without rejecting valid individual pseudo units."""

    materialised = list(rows)
    return RegistrationEnrichmentQuality(
        total_rows=len(materialised),
        known_region_rows=sum(str(row.get("region_id", "UNKNOWN")).upper() != "UNKNOWN" for row in materialised),
        known_fuel_rows=sum(str(row.get("fuel_type", "UNKNOWN")).upper() != "UNKNOWN" for row in materialised),
    )


def validate_registration_enrichment_counts(
    *,
    total_rows: int,
    known_region_rows: int,
    known_fuel_rows: int,
    registration_context_expected: bool,
) -> RegistrationEnrichmentQuality:
    quality = RegistrationEnrichmentQuality(total_rows, known_region_rows, known_fuel_rows)
    quality.validate(registration_context_expected=registration_context_expected)
    return quality


# --- Registration coverage -------------------------------------------------
#
# How old is the registration context we hold, relative to the SCADA we are
# pricing with it?
#
# The facility dimension attributes five-minute generation to a region and fuel
# using **monthly** MMSDM registration. If a monthly load stalls, generation is
# attributed from out-of-date registration and every downstream revenue and
# capture figure moves while staying entirely plausible. Nothing detected that
# before this contract existed.
#
# Two rejected formulations, recorded so they are not retried:
#
# 1. ``MAX(interval_end) - registration_effective_at``, which issue #7 asked
#    for, is **identically zero**. ``registration_effective_at`` is defined as
#    ``MAX(interval_end)`` over Bronze SCADA, and the Gold product aggregates a
#    correction-dedup of that same table, which never moves the maximum. It
#    would have shipped an indicator that could never fire.
# 2. ``MAX(interval_end) - MAX(dudetail.start_date)`` conflates two different
#    things. ``start_date`` only advances when a registration actually
#    *changes*, so a stable fleet drifts toward "stale" on a perfectly fresh
#    load. It also goes negative whenever AEMO ships future-effective
#    registrations, which the governed snapshot does.
#
# What remains is publication time: compare when the SCADA was published with
# when the registration we hold was published. Both are UTC instants, so the
# subtraction never crosses the fixed-AEST market domain.

BASIS_LISTING_OR_HTTP = "LISTING_OR_HTTP"
BASIS_DEGRADED_RETRIEVAL_FALLBACK = "DEGRADED_RETRIEVAL_FALLBACK"
BASIS_UNKNOWN = "UNKNOWN"

#: Coverage beyond this is stale. The MMSDM archive is monthly, so the gap
#: between publications is up to 31 days by definition; AEMO then publishes a
#: month's archive partway through the following month, and the lander itself
#: deliberately reaches back a further 35 days. A threshold under ~35 days
#: therefore alarms during every normal month, and one beyond ~60 lets a wholly
#: skipped archive pass unnoticed for two cycles. 45 days catches one missed
#: monthly publication while staying quiet through the ordinary cadence.
STALE_REGISTRATION_AFTER_SECONDS = 45 * 24 * 60 * 60

#: Minimum plausible gap between a genuine AEMO publication instant and our own
#: landing of it. See ``RegistrationCoverage`` on why this is a heuristic.
MINIMUM_PUBLICATION_TO_LANDING_SECONDS = 60


@dataclass(frozen=True)
class RegistrationCoverage:
    """How far the registration context lags the SCADA being attributed.

    ``coverage_seconds`` is **signed and never clamped**. Negative means the
    registration we hold was published *after* the SCADA, which is ordinary for
    a monthly source landing behind five-minute intervals; clamping it to zero
    would hide that the two are unrelated cadences.

    ``is_assessable`` is the fail-closed gate. When it is false the caller must
    report "not assessable" and must never report "fresh", because a small
    ``coverage_seconds`` is then evidence of nothing.
    """

    scada_publication_at: str | None
    registration_publication_at: str | None
    basis: str
    coverage_seconds: int | None
    is_assessable: bool

    @property
    def is_stale(self) -> bool:
        """True only when coverage is assessable *and* beyond the threshold.

        Unassessable coverage is not stale and not fresh. Collapsing those two
        states is the whole failure this contract exists to prevent.
        """

        if not self.is_assessable or self.coverage_seconds is None:
            return False
        return self.coverage_seconds > STALE_REGISTRATION_AFTER_SECONDS


def _parse_utc_instant(value: str | None, *, field: str) -> datetime | None:
    """Parse a UTC lineage instant, refusing anything carrying another offset.

    This is where the market-versus-processing rule is mechanically enforced.
    Market timestamps are fixed AEST and processing timestamps are UTC, and the
    defect class this guards against is subtracting one from the other. Passing
    a ``+10:00`` value here raises rather than silently producing a result ten
    hours wrong.
    """

    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise ContractError(f"{field} is not an ISO-8601 instant: {value!r}") from error
    if parsed.tzinfo is None:
        raise ContractError(f"{field} must carry an explicit UTC offset: {value!r}")
    if parsed.utcoffset() != UTC.utcoffset(None):
        raise ContractError(
            f"{field} must be a UTC processing instant, not {parsed.utcoffset()}: {value!r}. "
            "Market time is fixed AEST and must never be differenced against a UTC instant."
        )
    return parsed


def registration_coverage(
    *,
    scada_publication_at: str | None,
    registration_publications: Iterable[Mapping[str, Any]],
) -> RegistrationCoverage:
    """Summarise how stale the held registration context is.

    ``registration_publications`` carries one mapping per registration source
    (DUDETAILSUMMARY, DUALLOC, GENUNITS), each with ``source_publication_at``,
    ``source_publication_basis`` and ``landed_at``.

    Coverage is governed by the **weakest** source, so the oldest publication
    instant wins. GENUNITS is the only supplier of fuel, so a stalled GENUNITS
    load with a fresh DUDETAILSUMMARY must read stale rather than being masked.

    Degradation is detected two ways, because one of them is currently inert:

    * ``source_publication_basis == 'retrieval_fallback'`` marks a publication
      instant the lander had to invent from its own download time. This is the
      correct signal, but ``section_stream`` presently overwrites the basis with
      a hardcoded ``listing_or_http`` for every row, so it never fires for the
      registration tables today.
    * A publication instant sitting implausibly close to ``landed_at`` is
      therefore used as well. This is a **heuristic, not proof of provenance**:
      when the publication timestamp is fabricated from the retrieval event, the
      two collapse together. It is what actually protects the metric until the
      basis passthrough is repaired.
    """

    scada = _parse_utc_instant(scada_publication_at, field="scada source_publication_at")

    oldest: datetime | None = None
    oldest_text: str | None = None
    degraded = False
    saw_source = False

    for entry in registration_publications:
        saw_source = True
        raw = entry.get("source_publication_at")
        published = _parse_utc_instant(raw, field="registration source_publication_at")
        if published is None:
            # A source with no publication instant cannot be vouched for, and it
            # is the weakest leg by definition. Fail closed.
            degraded = True
            continue

        basis = str(entry.get("source_publication_basis") or "").strip().lower()
        if basis == "retrieval_fallback":
            degraded = True

        landed = _parse_utc_instant(entry.get("landed_at"), field="registration landed_at")
        if landed is not None:
            gap = (landed - published).total_seconds()
            if abs(gap) < MINIMUM_PUBLICATION_TO_LANDING_SECONDS:
                degraded = True

        if oldest is None or published < oldest:
            oldest = published
            oldest_text = str(raw)

    if not saw_source:
        degraded = True

    if scada is None or oldest is None:
        # A cold or SCADA-empty schema. Deliberately NOT zero seconds: zero
        # would read as perfect coverage on a schema holding nothing at all.
        return RegistrationCoverage(
            scada_publication_at=None if scada is None else str(scada_publication_at),
            registration_publication_at=oldest_text,
            basis=BASIS_UNKNOWN,
            coverage_seconds=None,
            is_assessable=False,
        )

    return RegistrationCoverage(
        scada_publication_at=str(scada_publication_at),
        registration_publication_at=oldest_text,
        basis=BASIS_DEGRADED_RETRIEVAL_FALLBACK if degraded else BASIS_LISTING_OR_HTTP,
        coverage_seconds=int((scada - oldest).total_seconds()),
        is_assessable=not degraded,
    )
