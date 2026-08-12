"""Characterisation tests for the source metadata contract.

These tests pin the behaviour that the declared contract in
``agentic_energy/resources/metadata/sources.json`` is supposed to describe, so
that making a declared field actually drive the pipeline cannot silently change
what the pipeline does.

They are written to pass both before and after ``quality_checks`` becomes
executable: each expectation is derived from the contract, never from a
hardcoded per-source branch.
"""

import json
from pathlib import Path

import pytest

from agentic_energy.pipeline import (
    _parse_quality_check,
    _quality_check_reasons,
    run_pipeline,
)

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
SHIPPED_METADATA = REPOSITORY_ROOT / "agentic_energy/resources/metadata/sources.json"

# Reason code emitted when a declared quality check fails, keyed by the field the
# check constrains. The contract declares the rule; this table names the code.
EXPECTED_REASON_CODE = {
    "demand_mw": "INVALID_DEMAND",
    "price_per_mwh": "MISSING_PRICE",
    "temperature_c": "MISSING_TEMPERATURE",
    "region": "MISSING_REGION",
}

# A value that violates each declared check form.
VIOLATING_VALUE = {
    "demand_mw >= 0": -1,
    "price_per_mwh is not null": None,
    "temperature_c is not null": None,
    "region is not null": None,
}


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def contract():
    return json.loads(SHIPPED_METADATA.read_text())


def sources_by_id():
    return {source["source_id"]: source for source in contract()["sources"]}


def valid_row(source, **overrides):
    """A row that passes every declared check for ``source``."""
    row = {
        "region": "NSW1",
        source["event_timestamp_field"]: "2024-01-15T10:00:00",
        "ingestion_sequence": 1,
    }
    if source["dataset"] in {"DISPATCH_SCADA", "DISPATCHIS"}:
        row.update(demand_mw=8000, price_per_mwh=70.0)
    else:
        row.update(temperature_c=21.5)
    row.update(overrides)
    return row


def workspace(tmp_path, market_rows, weather_rows):
    """Build an isolated metadata + fixture tree and run the pipeline over it."""
    (tmp_path / "metadata").mkdir()
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "metadata/sources.json").write_text(json.dumps(contract()))
    for name, rows in (("aemo_dispatch", market_rows), ("weather", weather_rows)):
        (tmp_path / f"fixtures/{name}.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows)
        )
    counts = run_pipeline(tmp_path / "metadata/sources.json", tmp_path / "out")
    return counts, lines(tmp_path / "out/quarantine/rejected.jsonl")


def declared_checks():
    """Every (source_id, check expression) pair the contract declares."""
    return [
        (source["source_id"], check)
        for source in contract()["sources"]
        for check in source["quality_checks"]
    ]


def test_contract_declares_quality_checks_for_every_source():
    """The contract must not silently drop its quality rules."""
    for source in contract()["sources"]:
        assert source["quality_checks"], f"{source['source_id']} declares no quality_checks"
        assert source["quarantine_policy"] == "isolate_with_reason"


def test_every_declared_check_uses_a_supported_form():
    """Guards the evaluator's input space: only two expression forms exist."""
    for source_id, check in declared_checks():
        supported = check.endswith(" is not null") or " >= " in check
        assert supported, f"{source_id} declares unsupported check form: {check!r}"
        assert check in VIOLATING_VALUE, f"no violating value pinned for {check!r}"


@pytest.mark.parametrize("source_id,check", declared_checks())
def test_each_declared_quality_check_quarantines_a_violating_row(tmp_path, source_id, check):
    """A row violating a declared check must be quarantined with its reason code.

    This is the contract's whole purpose: the declaration must have teeth.
    """
    sources = sources_by_id()
    source = sources[source_id]
    field = check.split()[0]
    violating = valid_row(source, **{field: VIOLATING_VALUE[check]})

    market_rows = [valid_row(sources["aemo_dispatch_fixture"])]
    weather_rows = [valid_row(sources["weather_fixture"])]
    if source["dataset"] in {"DISPATCH_SCADA", "DISPATCHIS"}:
        market_rows.append(violating)
    else:
        weather_rows.append(violating)

    counts, rejected = workspace(tmp_path, market_rows, weather_rows)

    assert counts["quarantine"] == 1, "exactly the violating row should be quarantined"
    row = rejected[0]
    assert row["source_id"] == source_id
    assert EXPECTED_REASON_CODE[field] in row["reason_codes"]
    assert row["source_file"] and row["source_row_number"] and row["rejected_at"]


def test_rows_satisfying_every_declared_check_are_accepted(tmp_path):
    """The negative control: no false quarantine when all checks pass."""
    sources = sources_by_id()
    counts, rejected = workspace(
        tmp_path,
        [valid_row(sources["aemo_dispatch_fixture"])],
        [valid_row(sources["weather_fixture"])],
    )
    assert rejected == []
    assert counts["quarantine"] == 0
    assert counts["silver"] == 2
    assert counts["gold"] == 1


def test_reason_codes_are_not_duplicated(tmp_path):
    """A field constrained both structurally and by a declared check reports once.

    ``weather_fixture`` declares ``region is not null`` while the pipeline also
    enforces region presence for every source. The row must not collect
    ``MISSING_REGION`` twice.
    """
    sources = sources_by_id()
    counts, rejected = workspace(
        tmp_path,
        [valid_row(sources["aemo_dispatch_fixture"])],
        [valid_row(sources["weather_fixture"]), valid_row(sources["weather_fixture"], region=None)],
    )
    assert counts["quarantine"] == 1
    codes = rejected[0]["reason_codes"]
    assert codes.count("MISSING_REGION") == 1
    assert len(codes) == len(set(codes)), f"duplicate reason codes: {codes}"


def test_structural_checks_apply_to_sources_that_do_not_declare_them(tmp_path):
    """Structural invariants are not delegated to ``quality_checks``.

    ``aemo_dispatch_fixture`` does not declare ``region is not null``, yet a
    market row with a non-string region must still be rejected. Contract-driven
    checks add to the structural floor; they do not replace it.
    """
    sources = sources_by_id()
    assert not any(
        check.startswith("region")
        for check in sources_by_id()["aemo_dispatch_fixture"]["quality_checks"]
    )
    counts, rejected = workspace(
        tmp_path,
        [valid_row(sources["aemo_dispatch_fixture"]),
         valid_row(sources["aemo_dispatch_fixture"], region=["NSW1"])],
        [valid_row(sources["weather_fixture"])],
    )
    assert counts["quarantine"] == 1
    assert "INVALID_REGION" in rejected[0]["reason_codes"]


def test_shipped_fixture_quarantine_is_exactly_pinned(tmp_path):
    """Byte-level expectation for the shipped fixture profile.

    Recorded in docs/evidence/foundation-run.md; any drift here means the
    foundation evidence has been invalidated.
    """
    counts = run_pipeline(SHIPPED_METADATA, tmp_path / "out")
    assert counts == {"bronze": 11, "silver": 6, "quarantine": 3, "gold": 3}
    rejected = lines(tmp_path / "out/quarantine/rejected.jsonl")
    assert [(r["source_id"], r["source_row_number"], r["reason_codes"]) for r in rejected] == [
        ("aemo_dispatch_fixture", 4, ["INVALID_DEMAND"]),
        ("aemo_dispatch_fixture", 5, ["MISSING_PRICE"]),
        ("weather_fixture", 4, ["MISSING_TEMPERATURE"]),
    ]


# --------------------------------------------------------------------------- #
# Evaluator unit tests: the parser's accepted language and the type floor.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "check,expected",
    [
        ("demand_mw >= 0", ("demand_mw", "at_least", 0.0)),
        ("demand_mw >= -10.5", ("demand_mw", "at_least", -10.5)),
        ("  demand_mw >= 0  ", ("demand_mw", "at_least", 0.0)),
        ("price_per_mwh is not null", ("price_per_mwh", "not_null", None)),
        ("temperature_c is not null", ("temperature_c", "not_null", None)),
        ("region is not null", ("region", "not_null", None)),
    ],
)
def test_parser_accepts_the_two_supported_forms(check, expected):
    assert _parse_quality_check(check) == expected


@pytest.mark.parametrize(
    "check",
    [
        "demand_mw > 0",                          # unsupported operator
        "demand_mw <= 0",
        "demand_mw == 0",
        "demand_mw >= abc",                       # non-numeric bound
        "demand_mw >= ",
        "demand_mw >= nan",                       # nan bound: comparison always false
        "demand_mw >= inf",
        "unknown_field >= 0",                     # field not in the registry
        "unknown_field is not null",
        "demand_mw >= 0 and price_per_mwh >= 0",  # composed expressions
        "demand_mw >= 0 or price_per_mwh >= 0",
        "demand_mw is null",                      # inverted predicate
        "region is not NULL",                     # case-sensitive by design
        "region >= 0",                            # numeric bound on a string field
        "__import__('os').system('boom') is not null",
        "",
        "   ",
        None,
        42,
        ["demand_mw >= 0"],
    ],
)
def test_parser_rejects_everything_outside_the_supported_forms(check):
    """A check that cannot be parsed must raise, never be silently skipped.

    A quietly-ignored rule is worse than an absent one: the contract would claim
    a guarantee the pipeline does not provide.
    """
    with pytest.raises(ValueError, match="UNSUPPORTED_QUALITY_CHECK"):
        _parse_quality_check(check)


@pytest.mark.parametrize(
    "value,expected",
    [
        (21.5, []),
        (0, []),
        (-40, []),                              # cold, but a real measurement
        (None, ["MISSING_TEMPERATURE"]),
        ("abc", ["MISSING_TEMPERATURE"]),        # a nullness check alone would admit this
        ("21.5", ["MISSING_TEMPERATURE"]),       # numeric string is not a number
        (True, ["MISSING_TEMPERATURE"]),         # bool is an int subclass in Python
        ([1], ["MISSING_TEMPERATURE"]),
        ({}, ["MISSING_TEMPERATURE"]),
        (float("nan"), ["MISSING_TEMPERATURE"]),
        (float("inf"), ["MISSING_TEMPERATURE"]),
    ],
)
def test_numeric_type_floor_applies_even_to_a_nullness_check(value, expected):
    """``temperature_c is not null`` still demands a finite number.

    The declared predicate constrains nullness only, but a non-numeric measure is
    not a usable measurement. Without this floor the contract-driven path would be
    weaker than the hardcoded validation it replaced.
    """
    checks = [_parse_quality_check("temperature_c is not null")]
    assert _quality_check_reasons({"temperature_c": value}, checks) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, []),                        # boundary: >= is inclusive
        (0.0, []),
        (0.001, []),
        (-0.001, ["INVALID_DEMAND"]),   # boundary: just below fails
        (-1, ["INVALID_DEMAND"]),
    ],
)
def test_at_least_boundary_is_inclusive(value, expected):
    checks = [_parse_quality_check("demand_mw >= 0")]
    assert _quality_check_reasons({"demand_mw": value}, checks) == expected


def test_missing_field_violates_any_declared_check():
    """An absent field cannot satisfy a check that constrains it."""
    checks = [_parse_quality_check("demand_mw >= 0")]
    assert _quality_check_reasons({}, checks) == ["INVALID_DEMAND"]


def test_reasons_follow_declared_order_and_deduplicate():
    checks = [_parse_quality_check(c) for c in ("demand_mw >= 0", "price_per_mwh is not null")]
    assert _quality_check_reasons({"demand_mw": -1, "price_per_mwh": None}, checks) == [
        "INVALID_DEMAND",
        "MISSING_PRICE",
    ]
    twice = [_parse_quality_check(c) for c in ("demand_mw >= 0", "demand_mw >= 100")]
    assert _quality_check_reasons({"demand_mw": -1}, twice) == ["INVALID_DEMAND"]


# --------------------------------------------------------------------------- #
# The contract drives behaviour: end-to-end, in both directions.
# --------------------------------------------------------------------------- #


def mutated_run(tmp_path, mutate):
    """Run the shipped fixtures under a mutated contract."""
    (tmp_path / "metadata").mkdir()
    (tmp_path / "fixtures").mkdir()
    metadata = contract()
    mutate(metadata)
    (tmp_path / "metadata/sources.json").write_text(json.dumps(metadata))
    for name in ("aemo_dispatch", "weather"):
        (tmp_path / f"fixtures/{name}.jsonl").write_text(
            (REPOSITORY_ROOT / f"agentic_energy/resources/fixtures/{name}.jsonl").read_text()
        )
    counts = run_pipeline(tmp_path / "metadata/sources.json", tmp_path / "out")
    return counts, lines(tmp_path / "out/quarantine/rejected.jsonl")


def test_tightening_a_declared_check_quarantines_more(tmp_path):
    """A stricter contract must reject more rows: the declaration is not decorative."""

    def tighten(metadata):
        for source in metadata["sources"]:
            if source["dataset"] == "DISPATCH_SCADA":
                source["quality_checks"].append("demand_mw >= 999999")

    counts, rejected = mutated_run(tmp_path, tighten)
    assert counts["quarantine"] == 7, "every market row violates the tightened bound"
    assert counts["silver"] == 3
    assert counts["gold"] == 0
    assert all(
        "INVALID_DEMAND" in row["reason_codes"]
        for row in rejected
        if row["source_id"] == "aemo_dispatch_fixture"
    )


@pytest.mark.parametrize(
    "source_index,check,surviving_codes",
    [
        (0, "demand_mw >= 0", {"MISSING_PRICE", "MISSING_TEMPERATURE"}),
        (0, "price_per_mwh is not null", {"INVALID_DEMAND", "MISSING_TEMPERATURE"}),
        (1, "temperature_c is not null", {"INVALID_DEMAND", "MISSING_PRICE"}),
    ],
)
def test_removing_a_declared_check_loosens_behaviour(tmp_path, source_index, check, surviving_codes):
    """Deleting a rule from the contract must stop it being enforced.

    Together with the tightening test this shows the contract, not the code,
    decides which rows are quarantined.
    """
    counts, rejected = mutated_run(
        tmp_path, lambda metadata: metadata["sources"][source_index]["quality_checks"].remove(check)
    )
    assert counts["quarantine"] == 2
    assert {code for row in rejected for code in row["reason_codes"]} == surviving_codes


def test_unsupported_check_aborts_the_run_and_writes_no_output(tmp_path):
    """A typo in the contract must fail the run, not degrade it silently."""

    def typo(metadata):
        metadata["sources"][0]["quality_checks"].append("demand_mw > 0")

    with pytest.raises(ValueError, match="UNSUPPORTED_QUALITY_CHECK"):
        mutated_run(tmp_path, typo)
    assert not (tmp_path / "out").exists(), "failed validation must leave no partial output"


# --------------------------------------------------------------------------- #
# watermark_field: declared, validated, and reported in the run manifest.
# --------------------------------------------------------------------------- #


def test_contract_declares_a_watermark_field_for_every_source():
    for source in contract()["sources"]:
        assert source["watermark_field"], f"{source['source_id']} declares no watermark_field"


def test_manifest_reports_the_declared_watermark_field_and_its_high_water_mark(tmp_path):
    """Acceptance requires counts *and* a watermark in the run manifest."""
    run_pipeline(SHIPPED_METADATA, tmp_path / "out")
    manifest = json.loads((tmp_path / "out/manifest.json").read_text())
    for source in contract()["sources"]:
        reported = manifest["sources"][source["source_id"]]
        assert reported["watermark_field"] == source["watermark_field"]
        silver = lines(tmp_path / f"out/silver/{source['source_id']}.jsonl")
        assert reported["watermark"] == max(row["interval_utc"] for row in silver)


def test_watermark_is_reported_in_normalized_utc(tmp_path):
    """The declared field holds local time; the watermark must be comparable.

    A high-water mark expressed in mixed local time cannot drive an incremental
    load, so the normalized UTC value is reported instead of the raw field.
    """
    run_pipeline(SHIPPED_METADATA, tmp_path / "out")
    manifest = json.loads((tmp_path / "out/manifest.json").read_text())
    for reported in manifest["sources"].values():
        assert reported["watermark"].endswith("Z")
        assert reported["watermark"] == "2024-04-07T00:30:00Z"


def test_watermark_tracks_the_data_rather_than_a_constant(tmp_path):
    """Dropping the latest interval must move the watermark back."""
    (tmp_path / "metadata").mkdir()
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "metadata/sources.json").write_text(json.dumps(contract()))
    sources = sources_by_id()
    market = sources["aemo_dispatch_fixture"]
    (tmp_path / "fixtures/aemo_dispatch.jsonl").write_text(
        json.dumps(valid_row(market, **{market["event_timestamp_field"]: "2024-04-07T10:00:00"})) + "\n"
    )
    weather = sources["weather_fixture"]
    (tmp_path / "fixtures/weather.jsonl").write_text(
        json.dumps(valid_row(weather, **{weather["event_timestamp_field"]: "2024-04-07T10:00:00"})) + "\n"
    )
    run_pipeline(tmp_path / "metadata/sources.json", tmp_path / "out")
    manifest = json.loads((tmp_path / "out/manifest.json").read_text())
    assert manifest["sources"]["aemo_dispatch_fixture"]["watermark"] == "2024-04-07T00:00:00Z"


def test_watermark_is_null_when_no_row_reaches_silver(tmp_path):
    """An empty Silver partition has no high-water mark, not a zero one.

    Reporting an epoch or empty string here would make an incremental load
    silently re-read from the beginning of time.
    """

    def tighten(metadata):
        for source in metadata["sources"]:
            if source["dataset"] == "DISPATCH_SCADA":
                source["quality_checks"].append("demand_mw >= 999999")

    counts, _ = mutated_run(tmp_path, tighten)
    assert counts["silver"] == 3, "only the weather source should survive"
    manifest = json.loads((tmp_path / "out/manifest.json").read_text())
    market = manifest["sources"]["aemo_dispatch_fixture"]
    assert market["silver"] == 0
    assert market["watermark"] is None
    assert market["watermark_field"] == "interval_datetime"
    assert manifest["sources"]["weather_fixture"]["watermark"] == "2024-04-07T00:30:00Z"


@pytest.mark.parametrize("value", [None, "", 42, ["interval_datetime"], "interval_utc", "region"])
def test_undeclared_or_unsupported_watermark_field_is_rejected(tmp_path, value):
    """The watermark must come from the normalized event timestamp, not any field."""
    (tmp_path / "metadata").mkdir()
    (tmp_path / "fixtures").mkdir()
    metadata = contract()
    metadata["sources"][0]["watermark_field"] = value
    (tmp_path / "metadata/sources.json").write_text(json.dumps(metadata))
    for name in ("aemo_dispatch", "weather"):
        (tmp_path / f"fixtures/{name}.jsonl").write_text(
            (REPOSITORY_ROOT / f"agentic_energy/resources/fixtures/{name}.jsonl").read_text()
        )
    with pytest.raises(ValueError, match="WATERMARK_FIELD"):
        run_pipeline(tmp_path / "metadata/sources.json", tmp_path / "out")


def test_row_accounting_still_reconciles_alongside_the_watermark(tmp_path):
    """Adding a watermark must not disturb the existing per-source counters."""
    run_pipeline(SHIPPED_METADATA, tmp_path / "out")
    manifest = json.loads((tmp_path / "out/manifest.json").read_text())
    for reported in manifest["sources"].values():
        assert reported["bronze"] == reported["accepted"] + reported["quarantine"]
        assert reported["accepted"] == reported["silver"] + reported["deduplicated"]
