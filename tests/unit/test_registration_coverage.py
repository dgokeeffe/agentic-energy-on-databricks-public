"""Registration coverage must fire on a stalled monthly load, and stay quiet otherwise.

The facility dimension attributes five-minute generation using **monthly**
registration. A stalled monthly load re-attributes generation to the wrong region
or fuel, moving every revenue and capture figure downstream while each value stays
plausible. These tests are what make the detector real rather than decorative.

Two formulations were rejected before this one, and two tests below exist
specifically to stop a future change from silently reverting to them:

``test_a_fresh_load_of_an_unchanged_fleet_reads_healthy`` fails under
"``MAX(interval_end) - MAX(start_date)``", and
``test_coverage_is_not_the_difference_of_a_column_with_itself`` documents why the
formulation issue #7 literally asked for could never fire.
"""

from __future__ import annotations

import pytest

from agentic_energy.common.contracts import ContractError
from agentic_energy.common.quality import (
    BASIS_DEGRADED_RETRIEVAL_FALLBACK,
    BASIS_LISTING_OR_HTTP,
    BASIS_UNKNOWN,
    STALE_REGISTRATION_AFTER_SECONDS,
    registration_coverage,
)

DAY = 24 * 60 * 60


def _source(published: str | None, *, landed: str | None = None, basis: str = "listing_or_http"):
    """One registration source's publication lineage.

    ``landed`` defaults to a day after publication, which is the ordinary
    healthy shape: AEMO publishes, and we land it some time later.
    """

    return {
        "source_publication_at": published,
        "source_publication_basis": basis,
        "landed_at": landed if landed is not None else "2026-09-02T00:00:00+00:00",
    }


def _healthy_sources(published: str = "2026-08-20T03:00:00+00:00"):
    return [_source(published, landed="2026-08-21T03:00:00+00:00") for _ in range(3)]


def test_a_stalled_monthly_load_is_reported_stale() -> None:
    """The case the contract exists for: registration months behind the SCADA."""

    coverage = registration_coverage(
        scada_publication_at="2026-09-10T05:00:00+00:00",
        registration_publications=[_source("2026-06-01T03:00:00+00:00", landed="2026-06-02T03:00:00+00:00")],
    )
    assert coverage.is_assessable
    assert coverage.basis == BASIS_LISTING_OR_HTTP
    assert coverage.coverage_seconds > STALE_REGISTRATION_AFTER_SECONDS
    assert coverage.is_stale


def test_a_recent_monthly_load_is_not_stale() -> None:
    """Ordinary cadence must not alarm, or operators learn to ignore the badge."""

    coverage = registration_coverage(
        scada_publication_at="2026-09-10T05:00:00+00:00",
        registration_publications=_healthy_sources(),
    )
    assert coverage.is_assessable
    assert not coverage.is_stale
    assert 0 < coverage.coverage_seconds < STALE_REGISTRATION_AFTER_SECONDS


def test_a_fresh_load_of_an_unchanged_fleet_reads_healthy() -> None:
    """A stable fleet must not drift toward "stale" merely by not changing.

    This is the refutation of the rejected market-time formulation
    ``MAX(interval_end) - MAX(dudetail.start_date)``. A generator registered in
    2019 that has never changed has a ``start_date`` seven years old, so that
    formulation would report seven years of staleness on a registration load
    published yesterday. Coverage measures the *load*, so it reads healthy.

    If this test is ever changed to accept a stale verdict, the metric has
    reverted to measuring registration churn instead of registration freshness.
    """

    coverage = registration_coverage(
        scada_publication_at="2026-09-10T05:00:00+00:00",
        # Published yesterday, describing registrations effective years ago.
        registration_publications=_healthy_sources("2026-09-09T03:00:00+00:00"),
    )
    assert coverage.is_assessable
    assert not coverage.is_stale


def test_coverage_is_not_the_difference_of_a_column_with_itself() -> None:
    """Issue #7's literal formulation could never fire; this records why.

    It asked for ``registration_effective_at`` minus the priced intervals. But
    ``registration_effective_at`` *is* ``MAX(interval_end)`` over Bronze SCADA,
    and the priced intervals are a correction-dedup of that same table, so the
    difference is identically zero regardless of how stale registration is.

    Here the registration load is three months behind while the market interval
    and the effective instant coincide exactly, as they always do. The zero-lag
    formulation reports 0. Coverage reports the real problem.
    """

    market_interval = "2026-09-10T05:00:00+00:00"
    registration_effective_at = market_interval  # equal by construction, always

    assert (
        registration_effective_at == market_interval
    ), "if these ever differ, re-examine silver_facilities.py"

    coverage = registration_coverage(
        scada_publication_at=market_interval,
        registration_publications=[_source("2026-06-10T03:00:00+00:00", landed="2026-06-11T03:00:00+00:00")],
    )
    assert coverage.is_stale, "coverage must see what the zero-lag formulation cannot"


def test_the_weakest_source_governs_coverage() -> None:
    """A stalled GENUNITS load must not be masked by a fresh DUDETAILSUMMARY.

    GENUNITS is the only supplier of fuel, so if it stalls, fuel attribution is
    stale even when region attribution is current. Taking the newest publication
    instant would hide exactly that, which is why the oldest wins.
    """

    coverage = registration_coverage(
        scada_publication_at="2026-09-10T05:00:00+00:00",
        registration_publications=[
            _source("2026-09-09T03:00:00+00:00", landed="2026-09-09T09:00:00+00:00"),  # dudetail, fresh
            _source("2026-09-09T03:00:00+00:00", landed="2026-09-09T09:00:00+00:00"),  # dualloc, fresh
            _source("2026-05-01T03:00:00+00:00", landed="2026-05-02T03:00:00+00:00"),  # genunits, stalled
        ],
    )
    assert coverage.is_stale
    assert coverage.registration_publication_at.startswith("2026-05-01")


def test_a_retrieval_fallback_basis_is_not_reported_as_fresh() -> None:
    """Fabricated provenance must read "not assessable", never "fresh".

    Under ``retrieval_fallback`` the publication instant is our own download
    time, so a near-zero coverage says nothing about the registration content's
    age. Reporting that as healthy is the silent-plausible-value failure this
    repository has already shipped once.
    """

    coverage = registration_coverage(
        scada_publication_at="2026-09-10T05:00:00+00:00",
        registration_publications=[
            _source("2026-09-10T04:00:00+00:00", landed="2026-09-11T04:00:00+00:00", basis="retrieval_fallback")
        ],
    )
    assert not coverage.is_assessable
    assert coverage.basis == BASIS_DEGRADED_RETRIEVAL_FALLBACK
    assert not coverage.is_stale, "unassessable is neither fresh nor stale"


def test_a_publication_instant_collapsed_onto_landing_is_not_assessable() -> None:
    """The leg that actually fires today, because the basis field is overwritten.

    ``section_stream`` hardcodes ``listing_or_http`` for every row, so the basis
    leg above cannot fire for registration tables. When the lander had to invent
    the publication instant it derives from the same retrieval event as
    ``landed_at``, so the two collapse together — which is detectable even
    though the basis lies.

    This is a heuristic, not proof of provenance. It must not regress while the
    basis passthrough remains broken.
    """

    coverage = registration_coverage(
        scada_publication_at="2026-09-10T05:00:00+00:00",
        registration_publications=[
            _source(
                "2026-09-02T02:05:00+00:00",
                landed="2026-09-02T02:05:03+00:00",  # three seconds apart
                basis="listing_or_http",  # the field claims a real listing
            )
        ],
    )
    assert not coverage.is_assessable
    assert coverage.basis == BASIS_DEGRADED_RETRIEVAL_FALLBACK


def test_a_cold_schema_yields_no_coverage_rather_than_zero() -> None:
    """Absent input must be NULL, never 0. Zero would read as perfect coverage."""

    no_scada = registration_coverage(
        scada_publication_at=None,
        registration_publications=_healthy_sources(),
    )
    assert no_scada.coverage_seconds is None
    assert no_scada.basis == BASIS_UNKNOWN
    assert not no_scada.is_assessable
    assert not no_scada.is_stale

    no_registration = registration_coverage(
        scada_publication_at="2026-09-10T05:00:00+00:00",
        registration_publications=[],
    )
    assert no_registration.coverage_seconds is None
    assert no_registration.basis == BASIS_UNKNOWN
    assert not no_registration.is_assessable


def test_a_registration_source_missing_its_publication_instant_fails_closed() -> None:
    """One vouchable source does not excuse another that cannot be vouched for."""

    coverage = registration_coverage(
        scada_publication_at="2026-09-10T05:00:00+00:00",
        registration_publications=[
            _source("2026-09-09T03:00:00+00:00", landed="2026-09-09T09:00:00+00:00"),
            _source(None),
        ],
    )
    assert not coverage.is_assessable


def test_negative_coverage_is_representable_and_not_clamped() -> None:
    """Registration published after the SCADA is ordinary, not an error.

    A monthly archive routinely lands after the five-minute intervals it
    describes. Clamping to zero would hide that the shipped snapshot's own
    timestamps sit in this state.
    """

    coverage = registration_coverage(
        scada_publication_at="2026-09-02T01:30:00+00:00",
        registration_publications=[_source("2026-09-02T02:05:00+00:00", landed="2026-09-03T02:05:00+00:00")],
    )
    assert coverage.coverage_seconds == -35 * 60
    assert not coverage.is_stale


@pytest.mark.parametrize(
    "bad",
    [
        "2026-09-10T15:00:00+10:00",  # fixed AEST market time
        "2026-09-10T15:00:00",  # naive, offset unknown
        "10/09/2026 15:00:00",  # NEM market text form
    ],
)
def test_a_non_utc_instant_is_refused(bad: str) -> None:
    """Market time must never be differenced against a processing instant.

    Converting a UTC instant to an AEST wall-clock string and parsing it back
    without an offset makes freshness ten hours wrong. The subtraction happens in
    exactly one place, so the guard belongs there rather than in a comment.
    """

    with pytest.raises(ContractError):
        registration_coverage(
            scada_publication_at=bad,
            registration_publications=_healthy_sources(),
        )

    with pytest.raises(ContractError):
        registration_coverage(
            scada_publication_at="2026-09-10T05:00:00+00:00",
            registration_publications=[_source(bad, landed="2026-09-11T03:00:00+00:00")],
        )


def test_zulu_notation_is_accepted_as_utc() -> None:
    """``Z`` and ``+00:00`` are the same instant and must behave identically."""

    zulu = registration_coverage(
        scada_publication_at="2026-09-10T05:00:00Z",
        registration_publications=[_source("2026-08-20T03:00:00Z", landed="2026-08-21T03:00:00Z")],
    )
    offset = registration_coverage(
        scada_publication_at="2026-09-10T05:00:00+00:00",
        registration_publications=[_source("2026-08-20T03:00:00+00:00", landed="2026-08-21T03:00:00+00:00")],
    )
    assert zulu.coverage_seconds == offset.coverage_seconds
    assert zulu.is_assessable and offset.is_assessable


def test_the_threshold_suits_a_monthly_source() -> None:
    """A monthly cadence must survive its own normal gap without alarming.

    31 days is the definitional worst case between two monthly publications, and
    AEMO adds delay into the following month on top. A threshold at or below
    31 days would alarm every ordinary month.
    """

    assert STALE_REGISTRATION_AFTER_SECONDS > 31 * DAY, "would alarm during normal monthly cadence"
    assert STALE_REGISTRATION_AFTER_SECONDS < 60 * DAY, "would let a wholly skipped archive pass for two cycles"
