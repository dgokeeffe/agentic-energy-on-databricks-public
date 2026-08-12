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

from agentic_energy.pipeline import run_pipeline

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
