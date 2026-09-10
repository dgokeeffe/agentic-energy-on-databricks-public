"""Behavioural proof of the governed dispatch-price spike rule.

The rule is relative: a five-minute price is a spike when it reaches a multiple
of the median of the immediately preceding intervals for the same region. These
tests fix the decisions recorded in ``miniwiki/features/price-spike-detector.md``
so a later change cannot quietly move a boundary.

The deployed PySpark window is pinned separately, by static assertions in
``test_gold_contracts.py``. Both halves are required: a well-tested pure function
whose deployed counterpart was reimplemented with a substituted clock call is the
exact defect recorded in ``miniwiki/decisions/facility-dimension-as-of.md``.
"""

from __future__ import annotations

import pytest

from agentic_energy.nemweb.contracts import ContractError
from agentic_energy.nemweb.corrections import mark_price_spikes, price_formation_basis


def _row(minute: int, price: float, *, region: str = "NSW1", **extra) -> dict:
    """One effective five-minute observation at interval-ending AEST."""

    hour, minute = divmod(minute, 60)
    return {
        "interval_end": f"2026-07-01T{hour:02d}:{minute:02d}:00+10:00",
        "region_id": region,
        "rrp_aud_per_mwh": price,
        "is_effective_run": True,
        **extra,
    }


def _flat_history(count: int, price: float = 50.0, **kwargs) -> list[dict]:
    return [_row(index * 5, price, **kwargs) for index in range(count)]


def _spike_flags(rows: list[dict], *, intervals: int = 4, multiple: float = 3.0):
    marked = mark_price_spikes(
        rows, baseline_intervals=intervals, baseline_multiple=multiple
    )
    return [row["is_price_spike"] for row in marked]


# --- insufficient history is not an absence of spikes -----------------------


def test_insufficient_history_withholds_the_flag_rather_than_returning_false() -> None:
    """NULL and False are different claims and must not be conflated.

    False asserts the comparison was made and failed. Before the window is full
    no comparison is possible, so the flag is withheld.
    """

    flags = _spike_flags(_flat_history(4), intervals=4)
    assert flags == [None, None, None, None]
    assert all(flag is not False for flag in flags)


def test_the_flag_appears_on_the_first_interval_with_a_full_baseline() -> None:
    marked = mark_price_spikes(
        _flat_history(5), baseline_intervals=4, baseline_multiple=3.0
    )
    assert [row["is_price_spike"] for row in marked] == [None, None, None, None, False]
    assert marked[4]["trailing_median_price_aud_per_mwh"] == 50.0


# --- boundary: the comparison is inclusive ---------------------------------


def test_a_price_exactly_on_the_multiple_is_a_spike() -> None:
    """The documented boundary is inclusive (>=). Both sides are tested."""

    rows = _flat_history(4, 50.0) + [_row(20, 150.0)]
    assert _spike_flags(rows, intervals=4, multiple=3.0)[4] is True


def test_a_price_just_below_the_multiple_is_not_a_spike() -> None:
    rows = _flat_history(4, 50.0) + [_row(20, 149.99)]
    assert _spike_flags(rows, intervals=4, multiple=3.0)[4] is False


# --- the interval never judges itself --------------------------------------


def test_the_judged_interval_is_excluded_from_its_own_baseline() -> None:
    """If the current price entered the median it would mask its own spike.

    With the current row included, a 4-row window of 50 plus a 10000 spike
    shifts the median upward and the ratio collapses. Excluding it keeps the
    baseline at 50 and the spike is detected.
    """

    rows = _flat_history(4, 50.0) + [_row(20, 10000.0)]
    marked = mark_price_spikes(rows, baseline_intervals=4, baseline_multiple=3.0)
    assert marked[4]["trailing_median_price_aud_per_mwh"] == 50.0
    assert marked[4]["is_price_spike"] is True


def test_a_sustained_plateau_stops_registering_once_it_becomes_the_baseline() -> None:
    """A spike is a departure from the recent level, not a high absolute price.

    Once elevated prices fill the trailing window they become the norm, and the
    rule must stop reporting them. Otherwise a long expensive period reads as
    hundreds of separate events.
    """

    rows = _flat_history(4, 50.0) + [
        _row(20 + index * 5, 500.0) for index in range(8)
    ]
    flags = _spike_flags(rows, intervals=4, multiple=3.0)
    assert flags[4] is True, "the step up is a spike"
    assert flags[-1] is False, "the plateau is the new baseline"


# --- negative and zero baselines ------------------------------------------


def test_a_negative_baseline_withholds_the_flag() -> None:
    """NEM prices go negative and a ratio against a negative median is nonsense.

    -500 >= 3 * -100 is arithmetically true, and would report the most extreme
    negative price in the window as a positive price spike.
    """

    rows = _flat_history(4, -100.0) + [_row(20, -500.0)]
    marked = mark_price_spikes(rows, baseline_intervals=4, baseline_multiple=3.0)
    assert marked[4]["is_price_spike"] is None
    assert marked[4]["trailing_median_price_aud_per_mwh"] == -100.0


def test_a_zero_baseline_withholds_the_flag() -> None:
    """Any positive price is an infinite multiple of zero; the ratio is undefined."""

    rows = _flat_history(4, 0.0) + [_row(20, 300.0)]
    assert _spike_flags(rows, intervals=4, multiple=3.0)[4] is None


def test_a_negative_price_against_a_positive_baseline_is_not_a_spike() -> None:
    rows = _flat_history(4, 50.0) + [_row(20, -1000.0)]
    assert _spike_flags(rows, intervals=4, multiple=3.0)[4] is False


# --- regions are independent ----------------------------------------------


def test_each_region_carries_its_own_baseline() -> None:
    """A cheap region must not borrow an expensive region's baseline."""

    rows = _flat_history(4, 50.0, region="NSW1") + _flat_history(4, 500.0, region="VIC1")
    rows += [_row(20, 200.0, region="NSW1"), _row(20, 200.0, region="VIC1")]
    marked = mark_price_spikes(rows, baseline_intervals=4, baseline_multiple=3.0)
    verdicts = {
        (row["region_id"], row["rrp_aud_per_mwh"]): row["is_price_spike"]
        for row in marked
        if row["is_price_spike"] is not None
    }
    assert verdicts[("NSW1", 200.0)] is True, "4x a $50 baseline"
    assert verdicts[("VIC1", 200.0)] is False, "below a $500 baseline"


# --- effective-run and price-formation semantics --------------------------


def test_non_effective_runs_are_excluded_entirely() -> None:
    """Intervention pairs must not double count, matching every other default."""

    rows = _flat_history(4, 50.0) + [
        _row(20, 9999.0, is_effective_run=False),
        _row(20, 60.0),
    ]
    marked = mark_price_spikes(rows, baseline_intervals=4, baseline_multiple=3.0)
    assert len(marked) == 5
    assert 9999.0 not in [row["rrp_aud_per_mwh"] for row in marked]


def test_price_formation_basis_separates_intervention_from_market() -> None:
    """An administered price is a governed artefact, not a scarcity signal."""

    assert price_formation_basis({}) == "MARKET"
    assert price_formation_basis({"administered_price_cap_flag": 1}) == "ADMINISTERED"
    assert price_formation_basis({"market_suspended_flag": 1}) == "SUSPENDED"
    # A suspended market can carry both flags; suspension is the stronger claim.
    assert (
        price_formation_basis(
            {"market_suspended_flag": 1, "administered_price_cap_flag": 1}
        )
        == "SUSPENDED"
    )


def test_an_administered_price_is_still_flagged_but_labelled() -> None:
    """The decision was to expose the basis, not to exclude the interval."""

    rows = _flat_history(4, 50.0) + [_row(20, 5000.0, administered_price_cap_flag=1)]
    marked = mark_price_spikes(rows, baseline_intervals=4, baseline_multiple=3.0)
    assert marked[4]["is_price_spike"] is True
    assert marked[4]["price_formation_basis"] == "ADMINISTERED"


# --- determinism and input safety -----------------------------------------


def test_the_same_inputs_reproduce_exactly() -> None:
    rows = _flat_history(4, 50.0) + [_row(20, 400.0)]
    first = mark_price_spikes(rows, baseline_intervals=4, baseline_multiple=3.0)
    second = mark_price_spikes(rows, baseline_intervals=4, baseline_multiple=3.0)
    assert first == second


def test_input_rows_are_not_modified() -> None:
    rows = _flat_history(5, 50.0)
    before = [dict(row) for row in rows]
    mark_price_spikes(rows, baseline_intervals=4, baseline_multiple=3.0)
    assert rows == before


def test_unordered_input_is_sorted_before_the_window_is_applied() -> None:
    """Row order in Bronze is not guaranteed; the baseline must not depend on it."""

    ordered = _flat_history(4, 50.0) + [_row(20, 400.0)]
    shuffled = [ordered[3], ordered[0], ordered[4], ordered[2], ordered[1]]
    assert mark_price_spikes(
        shuffled, baseline_intervals=4, baseline_multiple=3.0
    ) == mark_price_spikes(ordered, baseline_intervals=4, baseline_multiple=3.0)


def test_the_declared_parameters_travel_with_every_row() -> None:
    """A flagged interval must carry the rule that fired, for audit."""

    marked = mark_price_spikes(
        _flat_history(5), baseline_intervals=4, baseline_multiple=3.5
    )
    assert {row["spike_baseline_intervals"] for row in marked} == {4}
    assert {row["spike_baseline_multiple"] for row in marked} == {3.5}


# --- refused inputs -------------------------------------------------------


@pytest.mark.parametrize("multiple", [0.0, -1.0])
def test_a_non_positive_multiple_is_refused(multiple: float) -> None:
    with pytest.raises(ContractError):
        mark_price_spikes(
            _flat_history(5), baseline_intervals=4, baseline_multiple=multiple
        )


def test_a_zero_window_is_refused() -> None:
    with pytest.raises(ContractError):
        mark_price_spikes(
            _flat_history(5), baseline_intervals=0, baseline_multiple=3.0
        )


def test_a_missing_price_is_refused_rather_than_read_as_zero() -> None:
    """A null price silently treated as 0 would corrupt every later baseline."""

    rows = _flat_history(4, 50.0) + [_row(20, None)]
    with pytest.raises(ContractError):
        mark_price_spikes(rows, baseline_intervals=4, baseline_multiple=3.0)
