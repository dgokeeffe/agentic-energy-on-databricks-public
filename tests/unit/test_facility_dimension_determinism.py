"""The facility dimension must be reproducible from its inputs alone.

This suite exists because 290 foundation tests passed while
``silver_nem_facility_dimension`` was non-deterministic. The tested code and the
deployed code had diverged: ``build_facility_dimension`` takes an explicit
``as_of`` and every test pinned it, while the Spark view reimplemented the same
three-way join with ``F.current_timestamp()`` in the ``WHERE`` clause that decides
which registration rows survive.

Nothing crashed. Row counts held. Every value stayed plausible. The suite was green
because it exercised the other implementation.

Two levels of check, because either alone is insufficient:

1. A **behavioural** check on the shared pure function, proving that registration
   selection genuinely depends on the effective instant. This is what makes the
   defect real rather than theoretical.
2. A **structural** check on the deployed PySpark, proving the view derives its
   instant from data and never calls a clock function in a row-selecting filter.
   The behavioural check cannot reach the Spark view without a cluster, so this is
   the guard that keeps the two implementations from drifting apart again.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from agentic_energy.common.corrections import build_facility_dimension

ROOT = Path(__file__).resolve().parents[2]
FACILITIES = ROOT / "src" / "agentic_energy" / "silver" / "silver_facilities.py"

# A DUID whose registration moves it between regions at a period boundary. This is
# the shape every DUID in the governed snapshot has: two periods, one boundary.
MOVED_REGION = [
    {
        "duid": "MOVER1",
        "start_date": "2026/01/01 00:00:00",
        "end_date": "2026/07/13 00:00:00",
        "region_id": "VIC1",
        "source_version_no": 1,
    },
    {
        "duid": "MOVER1",
        "start_date": "2026/07/13 00:00:00",
        "end_date": "2999/12/31 00:00:00",
        "region_id": "NSW1",
        "source_version_no": 1,
    },
]


def test_registration_selection_depends_on_the_effective_instant() -> None:
    """The defect is real: the same rows resolve differently across a boundary.

    If this ever stops holding, the pinned instant has stopped mattering and the
    rest of this suite is guarding nothing.
    """
    before = build_facility_dimension(["MOVER1"], MOVED_REGION, [], [], as_of="2026/07/05 00:00:00")[0]
    after = build_facility_dimension(["MOVER1"], MOVED_REGION, [], [], as_of="2026/07/20 00:00:00")[0]
    assert before["region_id"] == "VIC1"
    assert after["region_id"] == "NSW1"


def test_the_same_inputs_and_instant_reproduce_exactly() -> None:
    """Reproducibility is a property of (inputs, instant), not of the wall clock."""
    first = build_facility_dimension(["MOVER1"], MOVED_REGION, [], [], as_of="2026/07/20 00:00:00")
    second = build_facility_dimension(["MOVER1"], MOVED_REGION, [], [], as_of="2026/07/20 00:00:00")
    assert first == second


def test_an_expired_registration_degrades_visibly_rather_than_silently() -> None:
    """A DUID with no period covering the instant must be inspectable, not absent.

    UNKNOWN with UNMATCHED status is a reportable state. Dropping the row would
    remove its generation from every regional and fuel aggregate instead.
    """
    expired = [{
        "duid": "GONE1",
        "start_date": "2020/01/01 00:00:00",
        "end_date": "2021/01/01 00:00:00",
        "region_id": "SA1",
        "source_version_no": 1,
    }]
    row = build_facility_dimension(["GONE1"], expired, [], [], as_of="2026/07/20 00:00:00")[0]
    assert row["region_id"] == "UNKNOWN"
    assert row["dimension_match_status"] == "UNMATCHED"


CLOCK_FUNCTIONS = {"current_timestamp", "current_date", "now"}


def _names_bound_to_a_clock(tree: ast.AST) -> set[str]:
    """Local names assigned directly from a clock call, e.g. ``now = F.current_timestamp()``.

    Tracking these is the whole point. The original defect did not write the clock
    call inside the filter; it bound it to ``now`` on one line and used ``now`` in
    the ``where`` two lines later. A checker that only inspected the filter
    expression walked straight past the bug it existed to find.
    """
    bound = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        call = node.value.func
        if isinstance(call, ast.Attribute) and call.attr in CLOCK_FUNCTIONS:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bound.add(target.id)
    return bound


def _row_selecting_clock_calls(source: str) -> list[str]:
    """Find wall-clock time used inside a ``.where(...)`` or ``.filter(...)``.

    Detects both the direct call and any local name bound to one.

    A clock call is only a defect when it decides which rows exist. The same call
    in a ``select`` is an ordinary processing-time label, and this pipeline uses it
    that way 21 times, so a blanket ban would be wrong.
    """
    tree = ast.parse(source)
    clock_names = _names_bound_to_a_clock(tree)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if not isinstance(function, ast.Attribute) or function.attr not in {"where", "filter"}:
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute):
                if inner.func.attr in CLOCK_FUNCTIONS:
                    found.append(inner.func.attr)
            elif isinstance(inner, ast.Name) and inner.id in clock_names:
                found.append(inner.id)
    return found


def test_the_deployed_view_never_selects_rows_by_the_wall_clock() -> None:
    source = FACILITIES.read_text()
    assert _row_selecting_clock_calls(source) == []


def test_the_guard_would_catch_the_original_defect() -> None:
    """Prove the structural check is capable of failing, in the shape it really had.

    A guard that has never been shown to fail is indistinguishable from one that
    cannot fail. The first version of this checker only inspected the filter
    expression and therefore passed against the genuine defect, because the clock
    call was bound to a variable first. Both shapes are asserted here.
    """
    inline = "frame.where(F.col('start_date') <= F.current_timestamp())"
    assert _row_selecting_clock_calls(inline) == ["current_timestamp"]

    # The exact shape of the original defect, reconstructed.
    via_variable = (
        "now = F.current_timestamp()\n"
        "frame.where((F.col('start_date') <= now) & (F.col('end_date') > now))\n"
    )
    assert _row_selecting_clock_calls(via_variable) == ["now", "now"]

    # A clock call that only labels a row must not be reported.
    label_only = "frame.select(F.current_timestamp().alias('published_at'))"
    assert _row_selecting_clock_calls(label_only) == []


def test_the_effective_instant_is_derived_from_the_data_and_published() -> None:
    """The instant must come from Bronze and be visible on the row.

    Derived rather than configured, so it cannot go stale; published, so an
    operator can read which registration window a refresh used instead of
    inferring it from when the job happened to run.
    """
    source = FACILITIES.read_text()
    assert 'F.max("interval_end")' in source
    assert "registration_effective_at" in source
    # A NULL max on a cold or SCADA-empty schema would make every comparison NULL
    # and silently empty the dimension, so the floor is part of the contract.
    assert "F.coalesce(F.max(" in source


@pytest.mark.parametrize("dependency", ["bronze_nem_dispatch_unit_scada", "bronze_nem_dudetail", "bronze_nem_dualloc"])
def test_the_view_reads_only_governed_bronze_dependencies(dependency: str) -> None:
    assert f'spark.read.table("{dependency}")' in FACILITIES.read_text()


# --- Registration coverage -------------------------------------------------
#
# Coverage has the same divergence hazard as the effective instant, for the same
# reason: the rule is tested behaviourally in ``quality.registration_coverage``,
# but the deployed expression is PySpark that no local test can execute because
# pyspark is not a test dependency. These checks are what stop the two from
# drifting, and each is shown capable of failing below.

GOLD_GENERATION = ROOT / "src" / "agentic_energy" / "gold" / "gold_scada_generation.py"

#: Market-domain columns. Fixed AEST, interval-ending, no daylight saving.
MARKET_COLUMNS = {"interval_end", "registration_effective_at", "start_date", "end_date"}
#: Processing-domain columns. UTC instants.
UTC_COLUMNS = {"source_publication_at", "landed_at", "registration_publication_at"}


def test_the_view_derives_coverage_from_the_shared_contract() -> None:
    """The deployed view must import the tested contract, not restate its constants.

    A literal ``60`` or ``"LISTING_OR_HTTP"`` copied into the pipeline would pass
    every test here while silently disagreeing with the function whose behaviour
    is actually proven.
    """
    source = FACILITIES.read_text()
    assert "from agentic_energy.common.quality import" in source
    for name in (
        "BASIS_DEGRADED_RETRIEVAL_FALLBACK",
        "BASIS_LISTING_OR_HTTP",
        "BASIS_UNKNOWN",
        "MINIMUM_PUBLICATION_TO_LANDING_SECONDS",
    ):
        assert name in source, f"{name} must come from quality.py, not be restated"


def test_coverage_is_measured_across_every_registration_source() -> None:
    """All three loads, and the oldest governs.

    GENUNITS is the only supplier of fuel, so a stalled GENUNITS load with a fresh
    DUDETAILSUMMARY must read stale. ``F.min`` on the publication instant is what
    makes the weakest leg govern; ``F.max`` would let one fresh source mask two
    stale ones.

    The tuple is read from the AST rather than grepped. An earlier version of this
    test asserted only that each table name appeared *somewhere* in the file, and
    a mutation removing GENUNITS from the coverage tuple passed it — the name still
    occurred in the unrelated generators window. Substring presence is not
    membership.
    """
    source = FACILITIES.read_text()
    assert 'F.min("published_at")' in source, "the oldest publication must govern coverage"

    tables: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "_REGISTRATION_TABLES" for t in node.targets):
            continue
        assert isinstance(node.value, ast.Tuple), "_REGISTRATION_TABLES must stay a literal tuple"
        tables = {e.value for e in node.value.elts if isinstance(e, ast.Constant)}
    assert tables == {"bronze_nem_dudetail", "bronze_nem_dualloc", "bronze_nem_genunits"}, (
        f"coverage must span all three registration loads, found {sorted(tables)}"
    )


def test_the_degraded_basis_dominates_in_the_gold_aggregate() -> None:
    """One healthy row must not mask a degraded refresh.

    ``DEGRADED_RETRIEVAL_FALLBACK`` sorts before ``LISTING_OR_HTTP``, so the
    aggregate has to be ``F.min``. ``F.max`` would report the healthy label and
    the screen would read "assessable" on unassessable provenance.
    """
    source = GOLD_GENERATION.read_text()
    assert 'F.min("registration_coverage_basis")' in source
    assert 'F.max("registration_coverage_basis")' not in source


def test_coverage_is_aggregated_without_widening_the_gold_grain() -> None:
    """Per-refresh scalars must be aggregated, never grouped.

    Grouping by a scalar makes it grain-defining. If a refresh ever produced two
    coverage values the grain would split, ``facility_count`` would fragment, and
    the app-serving MERGE — keyed on only the three real columns — would collide.
    """
    source = GOLD_GENERATION.read_text()
    assert 'groupBy("interval_end", "region_id", "fuel_type")' in source
    group_by_call = source.split("groupBy(")[1].split(")")[0]
    for column in ("registration_coverage_seconds", "registration_coverage_basis", "registration_effective_at"):
        assert column not in group_by_call, f"{column} is a scalar and must not define the grain"


def _crossed_timezone_subtractions(source: str) -> list[str]:
    """Find any subtraction mixing fixed-AEST market time with a UTC instant.

    Freshness computed across that boundary is ten hours wrong — the defect class
    issue #22 exists for. The rule is mechanised here rather than left to a
    comment, because a comment cannot fail a build.
    """
    findings = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Sub):
            continue
        names = {
            inner.value
            for inner in ast.walk(node)
            if isinstance(inner, ast.Constant) and isinstance(inner.value, str)
        }
        market = names & MARKET_COLUMNS
        utc = names & UTC_COLUMNS
        if market and utc:
            findings.append(f"{sorted(market)} - {sorted(utc)}")
    return findings


@pytest.mark.parametrize("path", [FACILITIES, GOLD_GENERATION])
def test_market_time_is_never_differenced_against_a_utc_instant(path: Path) -> None:
    assert _crossed_timezone_subtractions(path.read_text()) == []


def test_the_timezone_guard_would_catch_a_crossed_subtraction() -> None:
    """Prove this guard can fail, in the shape the mistake would really take.

    A guard never shown to fail is indistinguishable from one that cannot fail —
    the lesson already recorded above for the wall-clock checker.
    """
    # The most tempting wrong version of coverage: issue #7's literal ask, which
    # differences market time against a processing instant.
    crossed = (
        'frame.select(F.unix_timestamp("interval_end") '
        '- F.unix_timestamp("source_publication_at"))'
    )
    assert _crossed_timezone_subtractions(crossed) != []

    # And the same mistake via the published effective instant.
    via_effective_at = (
        'frame.select(F.unix_timestamp("registration_effective_at") '
        '- F.unix_timestamp("landed_at"))'
    )
    assert _crossed_timezone_subtractions(via_effective_at) != []

    # Both operands in the same domain must not be reported. This is the real
    # coverage expression and it must stay legal.
    same_domain = (
        'frame.select(F.unix_timestamp("source_publication_at") '
        '- F.unix_timestamp("registration_publication_at"))'
    )
    assert _crossed_timezone_subtractions(same_domain) == []


def test_coverage_never_decides_which_rows_exist() -> None:
    """Coverage labels a row; it must never filter one.

    Dropping rows on stale registration would delete real generation from every
    regional and fuel aggregate — the opposite of reporting the staleness, and a
    breach of the retain-unmatched-DUIDs contract.
    """
    source = FACILITIES.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if not isinstance(function, ast.Attribute) or function.attr not in {"where", "filter"}:
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
                assert not inner.value.startswith("registration_coverage"), (
                    f"coverage appears in a row-selecting {function.attr}()"
                )
