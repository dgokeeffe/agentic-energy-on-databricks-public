"""Deterministic contract for the governed regional dispatch-price spike rule.

The rule is carried in metadata, not code, so a threshold change is reviewable as
a metadata diff with a different fingerprint. These tests run offline against the
Spark-free helpers so boundary, correction, intervention, freshness and grain
semantics are proved without a warehouse.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from agentic_energy.nemweb.contracts import ContractError
from agentic_energy.nemweb.spike import (
    DEFAULT_SPIKE_RULE,
    SUPPORTED_METADATA_VERSION,
    SpikeRule,
    classify_interval,
    load_spike_rule,
    rule_fingerprint,
    spike_rows,
)

RULE = load_spike_rule()
# Processing instants are UTC. 2024-01-01T00:05:00+10:00 market time is published
# at 00:06:00+10:00, which is 2023-12-31T14:06:00Z.
AS_OF = "2023-12-31T14:10:00+00:00"


def row(**changes):
    """One effective-run regional dispatch row in governed Gold shape."""

    base = {
        "interval_end": "2024-01-01T00:05:00+10:00",
        "region_id": "NSW1",
        "intervention": 0,
        "rrp_aud_per_mwh": 55.0,
        "total_demand_mw": 7000.0,
        "administered_price_cap_flag": 0,
        "market_suspended_flag": 0,
        "report_version": "5",
        "source_run_no": 1,
        "source_publication_at": "2023-12-31T14:06:00+00:00",
        "ingestion_sequence": 1,
    }
    base.update(changes)
    return base


def only(rows, **kwargs):
    selected = spike_rows(rows, as_of=kwargs.pop("as_of", AS_OF), rule=kwargs.pop("rule", RULE))
    assert len(selected) == 1, selected
    return selected[0]


# --- Threshold and the documented boundary -------------------------------


def test_the_governed_default_is_the_reviewed_absolute_strict_rule() -> None:
    assert RULE.rule == "absolute"
    assert RULE.threshold_aud_per_mwh == 300.0
    assert RULE.boundary == "strict"
    # The threshold is a workshop-configured level with a recorded rationale, not
    # an AEMO-published spike definition. Saying otherwise would be a false claim.
    assert "not an AEMO" in RULE.rationale or "not an AEMO" in RULE.comment


def test_price_below_threshold_does_not_trigger() -> None:
    result = only([row(rrp_aud_per_mwh=299.99)])
    assert result["is_price_spike"] is False
    assert result["price_status"] == "PRESENT"


def test_value_exactly_at_the_documented_boundary_does_not_trigger() -> None:
    # The reviewed boundary is strict: rrp > threshold. Exactly at the threshold
    # is NOT a spike. This test is the record of that decision.
    result = only([row(rrp_aud_per_mwh=300.0)])
    assert result["is_price_spike"] is False
    assert result["spike_threshold_aud_per_mwh"] == 300.0


def test_price_above_threshold_triggers_and_carries_the_rule_that_fired() -> None:
    result = only([row(rrp_aud_per_mwh=300.01)])
    assert result["is_price_spike"] is True
    assert result["spike_rule"] == "absolute"
    assert result["spike_threshold_aud_per_mwh"] == 300.0
    assert result["spike_rule_fingerprint"] == rule_fingerprint(RULE)


def test_negative_and_null_prices_are_never_spikes() -> None:
    # Negative dispatch prices are valid NEM outcomes, not spikes.
    negative = only([row(rrp_aud_per_mwh=-1000.0)])
    assert negative["is_price_spike"] is False
    assert negative["price_status"] == "PRESENT"

    # A missing price must not become a silent spike or a silent non-spike; it is
    # labelled so an operator can see the measure was unavailable.
    unknown = only([row(rrp_aud_per_mwh=None)])
    assert unknown["is_price_spike"] is False
    assert unknown["price_status"] == "UNKNOWN_PRICE"


# --- Corrections ---------------------------------------------------------


def test_duplicate_intervals_use_the_governed_latest_value() -> None:
    duplicate = [row(rrp_aud_per_mwh=400.0), row(rrp_aud_per_mwh=400.0)]
    result = only(duplicate)
    assert result["is_price_spike"] is True
    assert len(duplicate) == 2, "the input rows must not be mutated or consumed"


def test_a_superseded_correction_cannot_create_a_spike() -> None:
    # A high price on an earlier run must not survive a later correction that
    # revises it down. The governed latest value decides, not the largest value.
    original = row(rrp_aud_per_mwh=5000.0, source_run_no=1)
    corrected = row(rrp_aud_per_mwh=90.0, source_run_no=2)
    result = only([original, corrected])
    assert result["rrp_aud_per_mwh"] == 90.0
    assert result["is_price_spike"] is False


def test_a_later_correction_can_also_reveal_a_spike() -> None:
    original = row(rrp_aud_per_mwh=90.0, source_run_no=1)
    corrected = row(rrp_aud_per_mwh=5000.0, source_run_no=2)
    assert only([original, corrected])["is_price_spike"] is True


# --- Intervention --------------------------------------------------------


def test_effective_intervention_run_is_the_default_and_both_runs_are_retained() -> None:
    # AEMO publishes a competing run for the same physical interval. The
    # effective run is the highest intervention flag; the other row is excluded
    # from the answer but is never deleted from the governed source.
    source = [
        row(intervention=0, rrp_aud_per_mwh=9999.0),
        row(intervention=1, rrp_aud_per_mwh=80.0),
    ]
    result = only(source)
    assert result["intervention"] == 1
    assert result["is_effective_run"] is True
    assert result["is_price_spike"] is False, (
        "the non-effective run's price must not leak into the spike answer"
    )
    assert len(source) == 2 and source[0]["intervention"] == 0


def test_a_non_intervened_interval_is_its_own_effective_run() -> None:
    assert only([row(intervention=0, rrp_aud_per_mwh=400.0)])["is_effective_run"] is True


# --- Freshness -----------------------------------------------------------


def test_stale_source_data_is_labelled_rather_than_presented_as_current() -> None:
    fresh = only([row(rrp_aud_per_mwh=400.0)])
    assert fresh["spike_freshness_status"] == "CURRENT"
    assert fresh["source_publication_lag_seconds"] == 240.0

    # Same row, read much later. The spike is still reported, but it is labelled
    # STALE rather than silently presented as actionable now.
    stale = only([row(rrp_aud_per_mwh=400.0)], as_of="2023-12-31T18:06:00+00:00")
    assert stale["spike_freshness_status"] == "STALE"
    assert stale["is_price_spike"] is True, "a stale row is labelled, never dropped"
    assert stale["source_publication_lag_seconds"] == 14400.0


def test_freshness_boundary_uses_the_recorded_stale_after_seconds() -> None:
    assert RULE.stale_after_seconds == 900
    at_limit = only([row()], as_of="2023-12-31T14:21:00+00:00")
    assert at_limit["source_publication_lag_seconds"] == 900.0
    assert at_limit["spike_freshness_status"] == "CURRENT", "strictly greater is stale"
    beyond = only([row()], as_of="2023-12-31T14:21:01+00:00")
    assert beyond["spike_freshness_status"] == "STALE"


def test_source_published_after_the_read_instant_is_not_reported_as_stale() -> None:
    ahead = only([row()], as_of="2023-12-31T14:00:00+00:00")
    assert ahead["source_publication_lag_seconds"] == -360.0
    assert ahead["spike_freshness_status"] == "CURRENT"


# --- Grain ---------------------------------------------------------------


def test_regional_and_five_minute_grain_are_preserved() -> None:
    source = [
        row(interval_end="2024-01-01T00:05:00+10:00", region_id="NSW1", rrp_aud_per_mwh=400.0),
        row(interval_end="2024-01-01T00:10:00+10:00", region_id="NSW1", rrp_aud_per_mwh=50.0),
        row(interval_end="2024-01-01T00:05:00+10:00", region_id="VIC1", rrp_aud_per_mwh=60.0),
    ]
    results = spike_rows(source, as_of=AS_OF, rule=RULE)
    keys = [(item["interval_end"], item["region_id"]) for item in results]
    assert len(keys) == len(set(keys)) == 3, "one row per region and five-minute interval"
    assert [item["is_price_spike"] for item in results] == [True, False, False]
    assert sum(item["is_price_spike"] for item in results) == 1


def test_an_interval_off_the_five_minute_grain_is_rejected_not_reported() -> None:
    with pytest.raises(ContractError, match="five-minute"):
        spike_rows([row(interval_end="2024-01-01T00:07:00+10:00")], as_of=AS_OF, rule=RULE)


def test_market_time_must_be_fixed_aest_never_utc() -> None:
    # A UTC market timestamp would silently shift every interval by ten hours.
    with pytest.raises(ContractError):
        spike_rows([row(interval_end="2023-12-31T14:05:00Z")], as_of=AS_OF, rule=RULE)


# --- Metadata fails closed before any classification ---------------------


def test_the_shipped_rule_metadata_is_the_reviewed_default() -> None:
    document = json.loads(DEFAULT_SPIKE_RULE.read_text(encoding="utf-8"))
    assert document["rule"] == "absolute"
    assert document["threshold_aud_per_mwh"] == 300.0
    assert document["boundary"] == "strict"
    assert document["metadata_version"] == SUPPORTED_METADATA_VERSION
    assert load_spike_rule() == RULE


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"rule": "relative"}, "rule"),
        ({"boundary": "inclusive"}, "boundary"),
        ({"threshold_aud_per_mwh": None}, "threshold"),
        ({"threshold_aud_per_mwh": "300"}, "threshold"),
        ({"threshold_aud_per_mwh": True}, "threshold"),
        # json.loads accepts these non-standard literals and returns floats, so an
        # isinstance check alone admits them. See the fail-open test below.
        ({"threshold_aud_per_mwh": float("nan")}, "finite"),
        ({"threshold_aud_per_mwh": float("inf")}, "finite"),
        ({"threshold_aud_per_mwh": float("-inf")}, "finite"),
        ({"stale_after_seconds": 0}, "stale_after_seconds"),
        ({"stale_after_seconds": -60}, "stale_after_seconds"),
        ({"rationale": ""}, "rationale"),
        # An unrecognised layout must be refused, not read on a best-effort basis.
        ({"metadata_version": 2}, "metadata_version"),
    ],
)
def test_malformed_rule_metadata_is_rejected_before_any_side_effect(
    tmp_path, changes, message
) -> None:
    document = json.loads(DEFAULT_SPIKE_RULE.read_text(encoding="utf-8"))
    document.update(changes)
    path = tmp_path / "spike_rule.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ContractError, match=message):
        load_spike_rule(path)


def test_a_missing_required_field_is_rejected(tmp_path) -> None:
    path = tmp_path / "spike_rule.json"
    path.write_text(json.dumps({"rule": "absolute"}), encoding="utf-8")
    with pytest.raises(ContractError, match="threshold_aud_per_mwh"):
        load_spike_rule(path)


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_a_non_finite_threshold_literal_in_the_json_is_rejected(tmp_path, literal) -> None:
    """These reach the loader as bare JSON text, not as a Python float.

    ``json.loads`` accepts NaN, Infinity and -Infinity even though they are not
    valid JSON, and returns ordinary floats that satisfy an isinstance check. The
    file therefore has to be rejected by content, not only by type.
    """

    document = json.loads(DEFAULT_SPIKE_RULE.read_text(encoding="utf-8"))
    document["threshold_aud_per_mwh"] = 300.0
    raw = json.dumps(document).replace("300.0", literal)
    path = tmp_path / "spike_rule.json"
    path.write_text(raw, encoding="utf-8")
    assert literal in path.read_text(encoding="utf-8")
    with pytest.raises(ContractError, match="finite"):
        load_spike_rule(path)


def test_a_non_finite_threshold_would_fail_open_which_is_why_it_is_rejected() -> None:
    """Prove the rejection above guards a real defect, not a theoretical one.

    A non-finite threshold does not raise and does not produce an obviously wrong
    row. It quietly inverts the detector, and the fingerprint still looks orderly,
    so nothing downstream reveals it. NaN makes every comparison false and reports
    a real spike as no spike; -Infinity flags every interval including a valid
    negative price. Both are worse than an error.
    """

    def rule_with(threshold: float) -> SpikeRule:
        return SpikeRule(
            rule=RULE.rule,
            threshold_aud_per_mwh=threshold,
            boundary=RULE.boundary,
            stale_after_seconds=RULE.stale_after_seconds,
            rationale=RULE.rationale,
            comment=RULE.comment,
        )

    # A genuine 99999 AUD/MWh spike disappears.
    silenced = only([row(rrp_aud_per_mwh=99999.0)], rule=rule_with(float("nan")))
    assert silenced["is_price_spike"] is False
    assert silenced["price_status"] == "PRESENT", "no error and no label: the gap is invisible"

    # A valid negative dispatch price becomes a spike.
    inverted = only([row(rrp_aud_per_mwh=-1000.0)], rule=rule_with(float("-inf")))
    assert inverted["is_price_spike"] is True


def test_threshold_change_alters_the_fingerprint_without_a_code_change() -> None:
    lowered = SpikeRule(
        rule=RULE.rule,
        threshold_aud_per_mwh=100.0,
        boundary=RULE.boundary,
        stale_after_seconds=RULE.stale_after_seconds,
        rationale=RULE.rationale,
        comment=RULE.comment,
    )
    assert rule_fingerprint(lowered) != rule_fingerprint(RULE)
    assert rule_fingerprint(RULE) == rule_fingerprint(load_spike_rule())
    # The lowered threshold changes the answer, and the flagged row records which
    # threshold fired, so a past result stays explainable after a rule change.
    result = only([row(rrp_aud_per_mwh=150.0)], rule=lowered)
    assert result["is_price_spike"] is True
    assert result["spike_threshold_aud_per_mwh"] == 100.0
    assert only([row(rrp_aud_per_mwh=150.0)])["is_price_spike"] is False


def test_classify_interval_requires_an_explicit_timezone_aware_read_instant() -> None:
    with pytest.raises(ContractError, match="as_of"):
        classify_interval(row(), as_of="2023-12-31T14:10:00", rule=RULE)


# --- The Lakeflow Gold view must apply the same reviewed rule ---------------
#
# The tests above prove the rule in Python. The published answer comes from the
# Spark module, so the two must not be allowed to drift: relaxing the boundary
# there once passed this suite untouched.

GOLD_SPIKE_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "agentic_energy/nemweb/pipeline/gold_price_spikes.py"
).read_text()


def _numeric_literals(source: str) -> list[float]:
    """Numeric constants in the module's code, ignoring comments and docstrings.

    Checked on the parse tree rather than the raw text. A substring ban on "300"
    also fires on a date, a row count, or a comment that happens to contain those
    digits, which makes the guard fail for reasons unrelated to the threshold.
    """

    return [
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    ]


def test_gold_view_reads_the_threshold_from_reviewed_metadata_not_a_literal() -> None:
    assert "load_spike_rule()" in GOLD_SPIKE_SOURCE
    assert "_RULE.threshold_aud_per_mwh" in GOLD_SPIKE_SOURCE
    assert "rule_fingerprint" in GOLD_SPIKE_SOURCE
    # A hard-coded threshold would let the published flag drift from the metadata.
    # The module carries no numeric constant at all, so any number appearing here
    # is a governed value that escaped the metadata.
    assert _numeric_literals(GOLD_SPIKE_SOURCE) == []


def test_the_numeric_literal_guard_would_catch_an_inlined_threshold() -> None:
    """A guard never shown to fail is indistinguishable from one that cannot fail."""

    assert _numeric_literals('F.col("rrp_aud_per_mwh") > F.lit(300.0)') == [300.0]
    # A comment or docstring mentioning the number is not a defect, and the
    # previous substring form of this check rejected it.
    assert _numeric_literals('# reviewed against the 300 AUD/MWh level\nx = _RULE.t') == []


def test_gold_view_applies_the_strict_boundary() -> None:
    assert (
        'F.col("rrp_aud_per_mwh") > F.lit(_RULE.threshold_aud_per_mwh)'
        in GOLD_SPIKE_SOURCE
    ), "the reviewed boundary is strict; >= would flag a price exactly at the threshold"
    assert 'F.col("rrp_aud_per_mwh") >= ' not in GOLD_SPIKE_SOURCE


def test_gold_view_defaults_to_the_effective_run_and_labels_freshness() -> None:
    assert 'spark.read.table("gold_nem_region_dispatch_5min")' in GOLD_SPIKE_SOURCE
    assert 'F.col("is_effective_run")' in GOLD_SPIKE_SOURCE
    assert '.alias("spike_freshness_status")' in GOLD_SPIKE_SOURCE
    assert '"STALE"' in GOLD_SPIKE_SOURCE and '"CURRENT"' in GOLD_SPIKE_SOURCE
    # Freshness labels the row; it must never filter rows out of the answer.
    assert 'where(F.col("spike_freshness_status")' not in GOLD_SPIKE_SOURCE
    # Non-spiking intervals are retained so no spikes stays distinguishable from
    # no data, which a .where(is_price_spike) filter would destroy.
    assert 'where(F.col("is_price_spike"))' not in GOLD_SPIKE_SOURCE


def test_gold_view_labels_staleness_in_the_direction_the_rule_intends() -> None:
    """Assert the comparison and both labels together, as the boundary check does.

    Presence of the strings "STALE" and "CURRENT" says nothing about which one a
    lagging row receives. Flipping the comparison, or swapping the two literals,
    inverts every freshness label while keeping both strings in the file: a stale
    spike would then be published as CURRENT, which is the exact failure this
    column exists to prevent.
    """

    assert (
        'lag_seconds > F.lit(_RULE.stale_after_seconds), F.lit("STALE")'
        in GOLD_SPIKE_SOURCE
    ), "lag beyond the recorded limit is STALE; < or swapped labels invert the answer"
    assert '.otherwise(F.lit("CURRENT")).alias("spike_freshness_status")' in GOLD_SPIKE_SOURCE
    # The limit is metadata like the threshold, never inlined.
    assert "_RULE.stale_after_seconds" in GOLD_SPIKE_SOURCE


def test_gold_view_labels_a_missing_price_instead_of_flagging_it() -> None:
    assert '"UNKNOWN_PRICE"' in GOLD_SPIKE_SOURCE
    assert 'F.coalesce(' in GOLD_SPIKE_SOURCE, (
        "a null price comparison is null, not false; it must be coalesced so a "
        "missing price can never read as a spike"
    )
