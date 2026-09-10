"""Invariants of the spike rule over many generated price series.

The hand-written cases in ``test_price_spike_rule.py`` pin specific decisions.
These assert properties that must hold for *every* input, which is where
combinations the examples never thought of tend to surface -- a negative median
that only appears once the window slides, or a plateau that straddles the
boundary.

Randomness is seeded and the seeds are fixed, so a failure is reproducible and
the suite cannot pass or fail depending on the day. ``hypothesis`` is deliberately
not used: this project pins its test dependencies to pytest and pyyaml, and these
properties do not need a shrinking engine to be useful.
"""

from __future__ import annotations

import random

import pytest

from agentic_energy.nemweb.corrections import mark_price_spikes

BASELINE = 6
MULTIPLE = 3.0
SEEDS = list(range(25))


def _series(seed: int, length: int = 40) -> list[dict]:
    """A price series spanning negative, zero and positive prices."""

    rng = random.Random(seed)
    rows = []
    for index in range(length):
        # Deliberately includes negatives and exact zeros: both are real NEM
        # prices and both are where a ratio rule breaks down.
        price = rng.choice(
            [
                rng.uniform(-1000, -1),
                0.0,
                rng.uniform(0.01, 100),
                rng.uniform(100, 20000),
            ]
        )
        hour, minute = divmod(index * 5, 60)
        rows.append(
            {
                "interval_end": f"2026-07-01T{hour:02d}:{minute:02d}:00+10:00",
                "region_id": "NSW1",
                "rrp_aud_per_mwh": price,
                "is_effective_run": True,
            }
        )
    return rows


def _marked(seed: int) -> list[dict]:
    return mark_price_spikes(
        _series(seed), baseline_intervals=BASELINE, baseline_multiple=MULTIPLE
    )


@pytest.mark.parametrize("seed", SEEDS)
def test_the_flag_is_only_ever_true_false_or_withheld(seed: int) -> None:
    """No truthy stand-ins. A caller doing `is True` must not be surprised."""

    for row in _marked(seed):
        assert row["is_price_spike"] in (True, False, None)


@pytest.mark.parametrize("seed", SEEDS)
def test_an_incomplete_or_non_positive_baseline_always_withholds(seed: int) -> None:
    """The two undecidable cases are exhaustive and never yield False.

    This is the invariant that keeps "we could not tell" from being read as
    "we checked and found nothing".
    """

    marked = _marked(seed)
    for index, row in enumerate(marked):
        median = row["trailing_median_price_aud_per_mwh"]
        if index < BASELINE:
            assert row["is_price_spike"] is None, "incomplete baseline must withhold"
            assert median is None
        elif median is not None and median <= 0:
            assert row["is_price_spike"] is None, "non-positive baseline must withhold"


@pytest.mark.parametrize("seed", SEEDS)
def test_a_decided_verdict_agrees_with_recomputing_the_rule(seed: int) -> None:
    """Every decided row is reproducible from its own recorded baseline.

    Recomputing from the published median catches a verdict drifting away from
    the number the row claims it was measured against.
    """

    for row in _marked(seed):
        verdict = row["is_price_spike"]
        if verdict is None:
            continue
        median = row["trailing_median_price_aud_per_mwh"]
        assert median is not None and median > 0
        assert verdict == (row["rrp_aud_per_mwh"] >= median * MULTIPLE)


@pytest.mark.parametrize("seed", SEEDS)
def test_the_recorded_rule_travels_with_every_row(seed: int) -> None:
    """A flagged interval must always carry the parameters that judged it."""

    for row in _marked(seed):
        assert row["spike_baseline_intervals"] == BASELINE
        assert row["spike_baseline_multiple"] == MULTIPLE
        assert row["price_formation_basis"] in ("MARKET", "ADMINISTERED", "SUSPENDED")


@pytest.mark.parametrize("seed", SEEDS)
def test_input_order_never_changes_the_verdicts(seed: int) -> None:
    """Bronze row order is not guaranteed, so the rule must not depend on it."""

    rows = _series(seed)
    shuffled = rows[:]
    random.Random(seed + 9999).shuffle(shuffled)
    assert mark_price_spikes(
        shuffled, baseline_intervals=BASELINE, baseline_multiple=MULTIPLE
    ) == mark_price_spikes(
        rows, baseline_intervals=BASELINE, baseline_multiple=MULTIPLE
    )


@pytest.mark.parametrize("seed", SEEDS)
def test_scaling_every_price_leaves_the_verdicts_unchanged(seed: int) -> None:
    """The rule is a ratio, so it must be invariant under a positive rescale.

    A rule that changed verdicts when prices were expressed in different units
    would be an absolute threshold wearing a relative disguise.
    """

    rows = _series(seed)
    scaled = [dict(row, rrp_aud_per_mwh=row["rrp_aud_per_mwh"] * 7.0) for row in rows]
    original = [
        row["is_price_spike"]
        for row in mark_price_spikes(
            rows, baseline_intervals=BASELINE, baseline_multiple=MULTIPLE
        )
    ]
    rescaled = [
        row["is_price_spike"]
        for row in mark_price_spikes(
            scaled, baseline_intervals=BASELINE, baseline_multiple=MULTIPLE
        )
    ]
    assert original == rescaled


@pytest.mark.parametrize("seed", SEEDS)
def test_regions_are_never_influenced_by_one_another(seed: int) -> None:
    """Adding a second region must not alter the first region's verdicts."""

    nsw = _series(seed)
    vic = [dict(row, region_id="VIC1", rrp_aud_per_mwh=row["rrp_aud_per_mwh"] * -3.0) for row in nsw]
    alone = [
        row["is_price_spike"]
        for row in mark_price_spikes(
            nsw, baseline_intervals=BASELINE, baseline_multiple=MULTIPLE
        )
    ]
    together = [
        row["is_price_spike"]
        for row in mark_price_spikes(
            nsw + vic, baseline_intervals=BASELINE, baseline_multiple=MULTIPLE
        )
        if row["region_id"] == "NSW1"
    ]
    assert alone == together
