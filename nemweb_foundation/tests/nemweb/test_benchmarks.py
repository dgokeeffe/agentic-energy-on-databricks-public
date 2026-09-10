from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("validate_nemweb_genie", SCRIPTS / "validate_nemweb_genie.py")
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

BENCHMARK_DOC = json.loads((ROOT / "genie/benchmark_questions.json").read_text())
BENCHMARKS = BENCHMARK_DOC["benchmarks"]
REFUSALS = BENCHMARK_DOC["refusals"]
BENCHMARK_IDS = {item["id"] for item in BENCHMARKS}

# The six governed assets Genie is allowed to see. A benchmark may only depend on
# one of these, so the answerable side of every near-miss pair resolves against
# governed Gold or a metric view rather than an ungoverned table.
GOVERNED_GENIE_ASSETS = {
    "gold_nem_region_dispatch_5min",
    "nem_region_dispatch_metrics",
    "nem_scada_generation_metrics",
    "nem_binding_constraint_metrics",
    "nem_interconnector_flow_metrics",
    "nem_unit_availability_t1_metrics",
}
# Tables with zero rows in the checked-in snapshot. A benchmark or refusal that
# named one of these would be unprovable locally: bids, trading, settlement and
# market notices are all empty, so nothing may depend on them. Matched as table
# identifiers only -- the prose word "trading" legitimately appears in the
# licence disclaimer a refusal quotes.
EMPTY_SNAPSHOT_TABLES = frozenset(
    {
        "bronze_nem_bid_day_offer",
        "bronze_nem_bid_period_offer",
        "silver_nem_bid_day_offer",
        "silver_nem_bid_period_offer",
        "gold_nem_bid_stack",
        "nem_bid_availability_metrics",
        "bronze_nem_trading_price",
        "silver_nem_trading_price",
        "gold_nem_trading_price",
        "bronze_nem_settlement_fcas_recovery",
        "bronze_nem_settlement_irsurplus",
        "silver_nem_settlement_fcas_recovery",
        "silver_nem_settlement_irsurplus",
        "gold_nem_settlement_fcas_recovery",
        "gold_nem_interregional_settlement_surplus",
        "bronze_nem_market_notice",
        "silver_nem_market_notice",
        "gold_nem_market_notice",
    }
)
TABLE_IDENTIFIER = re.compile(r"\b(?:bronze|silver|gold)_nem_[a-z0-9_]+|\bnem_[a-z0-9_]+_metrics\b")


def test_benchmark_catalog_covers_every_required_question() -> None:
    assert {item["id"] for item in BENCHMARKS} == validator.REQUIRED_TOPICS
    assert len(BENCHMARKS) == 6
    for item in BENCHMARKS:
        assert item["question"]
        assert item["expected_columns"]
        assert item["explanation"]
        assert "result_expectation" in item
        sql = (ROOT / item["sql_file"]).read_text()
        assert "{{catalog}}.{{schema}}." in sql
        assert ";" not in sql.rstrip().rstrip(";")


def test_benchmarks_encode_semantics_not_only_table_presence() -> None:
    sql_by_id = {item["id"]: (ROOT / item["sql_file"]).read_text().lower() for item in BENCHMARKS}
    assert "count_if(is_effective_run)" in sql_by_id["effective-intervention-uniqueness"]
    assert "having count_if(is_effective_run) <> 1" in sql_by_id["effective-intervention-uniqueness"]
    assert BENCHMARKS[0]["result_expectation"] == {"row_count": 0}
    assert "nem_region_dispatch_metrics" in sql_by_id["regional-price-demand"]
    assert "nem_scada_generation_metrics" in sql_by_id["generation-by-fuel"]
    assert "nem_binding_constraint_metrics" in sql_by_id["binding-constraints"]
    assert "source_sign" in sql_by_id["interconnector-source-sign"]
    assert "nem_unit_availability_t1_metrics" in sql_by_id["t1-unit-availability"]


def test_template_rendering_is_bounded_and_complete() -> None:
    rendered = validator.render_benchmark_sql(
        "SELECT * FROM {{catalog}}.{{schema}}.asset", "daveok", "nemweb_dev"
    )
    assert rendered == "SELECT * FROM daveok.nemweb_dev.asset"
    with pytest.raises(ValueError, match="simple Databricks identifiers"):
        validator.render_benchmark_sql("SELECT 1", "bad.catalog", "schema")


def test_sql_gate_rejects_failed_terminal_state_even_after_successful_transport() -> None:
    def fake_cli(_args: list[str]) -> dict:
        return {
            "statement_id": "statement-for-test",
            "status": {"state": "FAILED", "error": {"message": "analysis failed"}},
        }

    with pytest.raises(RuntimeError, match="ended in FAILED"):
        validator.execute_statement(
            "SELECT 1",
            profile="DEFAULT",
            warehouse_id="warehouse",
            catalog="catalog",
            schema="schema",
            timeout_seconds=1,
            cli_runner=fake_cli,
        )


def test_result_contract_checks_terminal_result_columns_and_counts() -> None:
    item = BENCHMARKS[0]
    response = {
        "statement_id": "statement-for-test",
        "status": {"state": "SUCCEEDED"},
        "manifest": {"schema": {"columns": [{"name": name} for name in item["expected_columns"]]}},
        "result": {"row_count": 0, "data_array": []},
    }
    validator._check_benchmark_result(item, response)
    response["result"]["row_count"] = 1
    with pytest.raises(RuntimeError, match="row count"):
        validator._check_benchmark_result(item, response)


def test_static_asset_validator_reconciles_all_files() -> None:
    # The validator no longer pins a profile name. It carries the explicit-profile
    # requirement as an error message instead, so no operator's workspace name is
    # embedded in this repository.
    assert not hasattr(validator, "REQUIRED_PROFILE")
    assert "explicit --profile" in validator.PROFILE_REQUIRED_MESSAGE
    result = validator.validate_assets()
    assert len(result["benchmarks"]) == 6
    assert len(result["dashboard_sql"]) == 6
    assert result["genie_asset_count"] == 6


def test_every_refusal_quotes_a_rule_that_exists_in_its_named_contract_section() -> None:
    # The quote is compared through the validator's own section splitter and
    # whitespace normaliser, so this test proves the shipped code rather than a
    # reimplementation of it. The contracts hard-wrap prose mid-sentence, so a raw
    # substring match against the file as written would fail on the longer quotes.
    assert len(REFUSALS) == 6
    for item in REFUSALS:
        source = item["contract_source"]
        assert source in validator.CONTRACT_SOURCES, source
        sections = validator.contract_sections(validator.CONTRACT_SOURCES[source])
        section = item["contract_section"]
        assert section in sections, f"{item['id']} cites missing section {section} in {source}"
        quote = validator._normalise_contract_text(item["contract_quote"])
        assert quote in sections[section], f"{item['id']} quote absent from {source} {section}"


def test_refusal_citing_an_invented_contract_rule_is_rejected() -> None:
    # This is the check the exercise exists for: a plausible-sounding rule nobody
    # wrote must fail. Operate on a deep copy so the on-disk catalogue is untouched.
    refusals = copy.deepcopy(REFUSALS)
    refusals[0]["contract_quote"] = (
        "Five-minute unit availability is published only for scheduled generators."
    )
    with pytest.raises(ValueError, match="quote is not present"):
        validator.validate_refusals(refusals, set(BENCHMARK_IDS))


def test_real_contract_quote_attributed_to_the_wrong_section_is_rejected() -> None:
    # Quote matching is scoped per section, so a genuine sentence cannot drift to a
    # section it does not belong to. Both sections below exist in DATA-CONTRACT.md.
    refusals = copy.deepcopy(REFUSALS)
    target = next(item for item in refusals if item["id"] == "snapshot-price-as-live-spot")
    assert target["contract_section"] == "## Fixed data semantics"
    target["contract_section"] = "## Deliberate omissions"
    with pytest.raises(ValueError, match="quote is not present"):
        validator.validate_refusals(refusals, set(BENCHMARK_IDS))


def test_near_miss_pairing_is_sound_and_never_marks_an_answerable_question_refusable() -> None:
    refusal_ids = {item["id"] for item in REFUSALS}
    assert len(refusal_ids) == len(REFUSALS)
    assert not (refusal_ids & BENCHMARK_IDS)
    near_misses = {item["near_miss_of"] for item in REFUSALS}
    assert near_misses <= BENCHMARK_IDS
    assert len(near_misses) >= 4
    assert len(near_misses) >= validator.MINIMUM_REFUSAL_NEAR_MISS_COVERAGE
    space_ids = [item["space_question_id"] for item in REFUSALS]
    assert len(set(space_ids)) == len(space_ids)


def test_refusals_can_never_reach_the_sql_executor() -> None:
    for item in REFUSALS:
        for field in validator.REFUSAL_FORBIDDEN_FIELDS:
            assert field not in item, f"refusal {item['id']} carries executable key {field}"
        assert not any(key.endswith("sql") for key in item)
    # Source-level guard: even if a refusal somehow acquired those keys, main()'s
    # --execute region must not iterate refusals. Located by marker text rather
    # than line numbers so the guard survives unrelated edits.
    source = (SCRIPTS / "validate_nemweb_genie.py").read_text()
    main_source = source[source.index("def main("):]
    execute_region = main_source[main_source.index("if not args.execute:"):]
    assert "refusal" not in execute_region.lower(), (
        "the --execute region of main() references refusals; a must-refuse question "
        "must never be submitted to the SQL Statement Execution API"
    )


def test_vacuous_result_expectation_is_rejected_but_empty_valid_grain_contract_is_kept() -> None:
    item = copy.deepcopy(BENCHMARKS[1])
    item["result_expectation"] = {"minimum_row_count": 0}
    with pytest.raises(ValueError, match="asserts nothing"):
        validator._check_expectation_asserts_something(item)
    # The shipped binding-constraints expectation is row-count independent yet still
    # asserts a grain, so it must stay acceptable.
    binding = next(entry for entry in BENCHMARKS if entry["id"] == "binding-constraints")
    assert binding["result_expectation"]["empty_result_is_valid"] is True
    assert binding["result_expectation"]["distinct_key_columns"] == ["constraint_id"]
    validator._check_expectation_asserts_something(binding)
    for entry in BENCHMARKS:
        validator._check_expectation_asserts_something(entry)


def test_result_grain_contract_rejects_a_duplicate_key_tuple() -> None:
    item = next(entry for entry in BENCHMARKS if entry["id"] == "generation-by-fuel")
    key_columns = item["result_expectation"]["distinct_key_columns"]
    assert key_columns == ["region_id", "fuel_type"]

    def response_for(rows: list[list[str]]) -> dict:
        return {
            "statement_id": "statement-for-test",
            "status": {"state": "SUCCEEDED"},
            "manifest": {"schema": {"columns": [{"name": name} for name in item["expected_columns"]]}},
            "result": {"row_count": len(rows), "data_array": rows},
        }

    width = len(item["expected_columns"])
    duplicate = [["NSW1", "Coal"] + ["1"] * (width - 2), ["NSW1", "Coal"] + ["2"] * (width - 2)]
    unique = [["NSW1", "Coal"] + ["1"] * (width - 2), ["NSW1", "Wind"] + ["2"] * (width - 2)]
    with pytest.raises(RuntimeError, match="declared grain is not unique"):
        validator._check_benchmark_result(item, response_for(duplicate))
    validator._check_benchmark_result(item, response_for(unique))


def test_required_refusal_topics_leave_the_optional_one_optional_and_name_reasons() -> None:
    refusal_ids = {item["id"] for item in REFUSALS}
    assert validator.REQUIRED_REFUSAL_TOPICS <= refusal_ids
    # The exercise documents market-notice-cause as the "cut if time runs short"
    # refusal, so removing it must validate without editing the validator.
    assert "market-notice-cause" not in validator.REQUIRED_REFUSAL_TOPICS
    trimmed = [item for item in copy.deepcopy(REFUSALS) if item["id"] != "market-notice-cause"]
    assert len(trimmed) == 5
    validator.validate_refusals(trimmed, set(BENCHMARK_IDS))

    for item in REFUSALS:
        assert item["unsupported_because"] in validator.REFUSAL_CLASSES
        reason = item["refusal_reason"]
        assert len(reason) >= validator.MINIMUM_REFUSAL_REASON_CHARS
        lowered = reason.lower()
        # A reason explains; a decline does not. Require an explanatory connective
        # and vocabulary shared with the cited rule, so the reason is attributed.
        assert any(
            marker in lowered
            for marker in ("because", "so ", "rather than", "without", " no ", "not ")
        ), item["id"]
        quote_words = set(re.findall(r"[a-z0-9_-]{5,}", item["contract_quote"].lower()))
        assert len(quote_words & set(re.findall(r"[a-z0-9_-]{5,}", lowered))) >= 3, item["id"]

    bare = copy.deepcopy(REFUSALS)
    bare[0]["refusal_reason"] = "I cannot answer that."
    with pytest.raises(ValueError, match="must name a reason"):
        validator.validate_refusals(bare, set(BENCHMARK_IDS))


def test_no_benchmark_or_refusal_depends_on_a_table_that_is_empty_in_the_snapshot() -> None:
    for item in BENCHMARKS:
        assets = item["assets"]
        assert assets
        assert set(assets) <= GOVERNED_GENIE_ASSETS, item["id"]
        assert not set(assets) & EMPTY_SNAPSHOT_TABLES, item["id"]
        sql = (ROOT / item["sql_file"]).read_text().lower()
        assert not EMPTY_SNAPSHOT_TABLES & set(TABLE_IDENTIFIER.findall(sql)), item["id"]
    for item in REFUSALS:
        text = " ".join(str(value) for value in item.values()).lower()
        assert not EMPTY_SNAPSHOT_TABLES & set(TABLE_IDENTIFIER.findall(text)), item["id"]
        # A refusal explains what is missing; it must not name an empty table as if
        # it were queryable, nor carry an assets list that the executor could use.
        assert "assets" not in item


# ---------------------------------------------------------------------------
# Mutation resistance.
#
# Everything above this line describes properties of the *shipped* catalogue.
# Those assertions are necessary but not sufficient: a contributor who deletes a
# guard from validate_nemweb_genie.py leaves the shipped catalogue valid, so a
# data-only assertion still passes and the deletion ships silently. An
# independent review demonstrated exactly that for twelve guards.
#
# The tests below therefore feed a VIOLATING input through the shipped function
# and require it to raise, with a `match` that is specific to the guard under
# test so a case cannot pass because an unrelated check happened to fire first.
# Every mutation is applied to a deep copy; the on-disk JSON is never written.
# ---------------------------------------------------------------------------

REQUIRED_REFUSAL_TOPIC_IDS = frozenset(
    {
        "five-minute-curtailment",
        "constraint-marginal-value-by-region",
        "interconnector-import-export-direction",
        "snapshot-price-as-live-spot",
        "bid-recommendation",
    }
)
# `market-notice-cause` is deliberately absent above and must stay absent: the
# exercise documents it as the "cut if time runs short" refusal.
OPTIONAL_REFUSAL_TOPIC_ID = "market-notice-cause"
# A refusal that is NOT a required topic, so blanking or renaming its `id` in a
# copy cannot trip the required-topics check before the guard under test.
MUTABLE_REFUSAL_ID = OPTIONAL_REFUSAL_TOPIC_ID


def _refusals_copy() -> list[dict]:
    """A deep copy of the refusal catalogue. Never hand REFUSALS itself out."""
    return copy.deepcopy(REFUSALS)


def _find(refusals: list[dict], refusal_id: str) -> dict:
    return next(item for item in refusals if item["id"] == refusal_id)


def test_constants_the_mutation_tests_rely_on_state_their_required_content() -> None:
    # Guards 4 and 5. `frozenset() <= anything` is True and `len(x) >= 0` is
    # True, so a membership/floor assertion alone is vacuous once the constant is
    # emptied or zeroed. Pin the content instead: emptying either constant must
    # fail here as well as in the behavioural tests below.
    assert validator.REQUIRED_REFUSAL_TOPICS == REQUIRED_REFUSAL_TOPIC_IDS
    assert OPTIONAL_REFUSAL_TOPIC_ID not in validator.REQUIRED_REFUSAL_TOPICS
    assert validator.MINIMUM_REFUSAL_COUNT >= 4
    assert validator.MINIMUM_REFUSAL_NEAR_MISS_COVERAGE >= 4
    assert validator.MINIMUM_REFUSAL_REASON_CHARS >= 80
    assert validator.REFUSAL_REQUIRED_FIELDS == (
        "id",
        "space_question_id",
        "question",
        "contract_source",
        "contract_section",
        "contract_quote",
        "unsupported_because",
        "refusal_reason",
        "near_miss_of",
    )
    assert validator.REFUSAL_FORBIDDEN_FIELDS == (
        "sql_file",
        "expected_columns",
        "result_expectation",
    )


@pytest.mark.parametrize("required_topic", sorted(REQUIRED_REFUSAL_TOPIC_IDS))
def test_dropping_any_required_refusal_topic_is_rejected(required_topic: str) -> None:
    # Guard 4, behaviourally: REQUIRED_REFUSAL_TOPICS must actually be enforced.
    # The topics check runs before the per-item loop, so this message is the one
    # a missing required topic produces even when the shortened catalogue would
    # also fail a later coverage check.
    refusals = [item for item in _refusals_copy() if item["id"] != required_topic]
    assert len(refusals) == len(REFUSALS) - 1
    with pytest.raises(
        ValueError, match=rf"omits required topics: \['{re.escape(required_topic)}'\]"
    ):
        validator.validate_refusals(refusals, set(BENCHMARK_IDS))


def test_dropping_the_optional_refusal_topic_is_still_accepted() -> None:
    # The other half of guard 4: the floor must not creep upward and make the
    # documented optional refusal mandatory.
    refusals = [item for item in _refusals_copy() if item["id"] != OPTIONAL_REFUSAL_TOPIC_ID]
    assert len(refusals) == 5
    assert validator.validate_refusals(refusals, set(BENCHMARK_IDS)) == refusals


def test_a_catalogue_below_the_minimum_refusal_count_is_rejected() -> None:
    # Guard 5a. The literal count in the message is emitted only by the count
    # floor, so zeroing MINIMUM_REFUSAL_COUNT cannot satisfy this match.
    refusals = _refusals_copy()[:3]
    with pytest.raises(ValueError, match=r"at least 4 refusal questions are required"):
        validator.validate_refusals(refusals, set(BENCHMARK_IDS))


def test_refusals_all_crowded_onto_one_benchmark_fail_near_miss_coverage() -> None:
    # Guard 5b. Every near_miss_of below is a real benchmark ID, so guard 9
    # cannot fire instead; only the distinct-coverage floor can raise.
    refusals = _refusals_copy()
    for item in refusals:
        item["near_miss_of"] = "binding-constraints"
    with pytest.raises(
        ValueError,
        match=r"must sit adjacent to at least 4 distinct benchmarks; only 1 covered",
    ):
        validator.validate_refusals(refusals, set(BENCHMARK_IDS))


@pytest.mark.parametrize("forbidden_field", ["sql_file", "expected_columns", "result_expectation"])
def test_a_refusal_carrying_an_executable_benchmark_key_is_rejected(forbidden_field: str) -> None:
    # Guard 1. Nothing else in the pipeline looks at these keys on a refusal, so
    # neutering `present_forbidden` would let an executable refusal through.
    refusals = _refusals_copy()
    payload = {
        "sql_file": "genie/sql/regional_price_demand.sql",
        "expected_columns": ["region_id"],
        "result_expectation": {"minimum_row_count": 1},
    }[forbidden_field]
    _find(refusals, MUTABLE_REFUSAL_ID)[forbidden_field] = payload
    with pytest.raises(
        ValueError,
        match=rf"must not carry executable benchmark keys: \['{forbidden_field}'\]",
    ):
        validator.validate_refusals(refusals, set(BENCHMARK_IDS))


@pytest.mark.parametrize(
    "required_field",
    [
        "id",
        "space_question_id",
        "question",
        "contract_source",
        "contract_section",
        "contract_quote",
        "unsupported_because",
        "refusal_reason",
        "near_miss_of",
    ],
)
def test_a_refusal_with_a_blank_required_field_is_rejected(required_field: str) -> None:
    # Guard 12. Whitespace-only, so this proves the `.strip()` arm too. The
    # mutated refusal is the non-required topic, so blanking `id` cannot trip the
    # required-topics check first.
    refusals = _refusals_copy()
    _find(refusals, MUTABLE_REFUSAL_ID)[required_field] = "   "
    with pytest.raises(ValueError, match=rf"lacks a non-empty {required_field}$"):
        validator.validate_refusals(refusals, set(BENCHMARK_IDS))


def test_a_refusal_space_question_id_that_is_not_32_hex_is_rejected() -> None:
    # Guard 6. Non-empty and unique, so only the hex-shape check can raise; the
    # Genie API rejects any other shape at deploy time.
    refusals = _refusals_copy()
    _find(refusals, MUTABLE_REFUSAL_ID)["space_question_id"] = "209e1c8a-663c-56fb-9bf3-3f427e45"
    with pytest.raises(
        ValueError, match=r"space_question_id is not a 32-character hex ID"
    ):
        validator.validate_refusals(refusals, set(BENCHMARK_IDS))


def test_a_refusal_inventing_an_unsupported_because_class_is_rejected() -> None:
    # Guard 8. A new refusal class must be added to REFUSAL_CLASSES consciously,
    # not invented in JSON, because the Genie refusal policy prose is checked
    # against that enum in test_genie_assets.py.
    refusals = _refusals_copy()
    _find(refusals, MUTABLE_REFUSAL_ID)["unsupported_because"] = "no_governed_notice_text"
    with pytest.raises(
        ValueError,
        match=r"uses unknown unsupported_because 'no_governed_notice_text'",
    ):
        validator.validate_refusals(refusals, set(BENCHMARK_IDS))


def test_a_refusal_citing_a_contract_source_outside_the_registry_is_rejected() -> None:
    # Guard 11. The registry is what keeps a refusal from naming an arbitrary
    # path, exactly as `sql_file` may not contain `..`.
    refusals = _refusals_copy()
    _find(refusals, MUTABLE_REFUSAL_ID)["contract_source"] = "../DATA-CONTRACT.md"
    with pytest.raises(
        ValueError, match=r"cites unknown contract source '\.\./DATA-CONTRACT\.md'"
    ):
        validator.validate_refusals(refusals, set(BENCHMARK_IDS))


def test_a_refusal_citing_a_section_that_does_not_exist_is_rejected() -> None:
    # Guard 10, distinct from the existing wrong-section test: there the section
    # exists and the quote does not belong to it; here the section itself is
    # invented, which must be named as a missing section rather than a bad quote.
    refusals = _refusals_copy()
    target = _find(refusals, MUTABLE_REFUSAL_ID)
    assert target["contract_section"] == "## Deliberate omissions"
    target["contract_section"] = "## Market notice semantics"
    with pytest.raises(
        ValueError,
        match=r"cites missing section '## Market notice semantics' in DATA-CONTRACT\.md",
    ):
        validator.validate_refusals(refusals, set(BENCHMARK_IDS))


def test_a_refusal_paired_with_a_question_that_is_not_a_benchmark_is_rejected() -> None:
    # Guard 9. Four other refusals still cover four distinct benchmarks, so the
    # coverage floor cannot fire instead of the near-miss identity check.
    refusals = _refusals_copy()
    _find(refusals, MUTABLE_REFUSAL_ID)["near_miss_of"] = "market-notice-explanation"
    with pytest.raises(
        ValueError, match=r"near_miss_of 'market-notice-explanation' is not a benchmark ID"
    ):
        validator.validate_refusals(refusals, set(BENCHMARK_IDS))


def test_declared_grain_columns_must_be_columns_the_benchmark_returns() -> None:
    # Guard 7. A key column that is not in expected_columns cannot be located in
    # a result row, so _check_result_grain would silently assert nothing.
    item = copy.deepcopy(next(entry for entry in BENCHMARKS if entry["id"] == "regional-price-demand"))
    item["result_expectation"] = {
        "minimum_row_count": 1,
        "distinct_key_columns": ["region_id", "settlement_date"],
    }
    with pytest.raises(
        ValueError,
        match=r"distinct_key_columns \['settlement_date'\] are not expected columns",
    ):
        validator._check_expectation_asserts_something(item)


def _validate_assets_with_catalogue(doc: dict, tmp_path: Path) -> dict:
    """Run the real validate_assets() against a temp benchmark catalogue.

    The module constant is repointed and restored in `finally`, and the temp file
    is inside pytest's tmp_path, so the shipped JSON is never written.
    """
    temp = tmp_path / "benchmark_questions.json"
    temp.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    original = validator.BENCHMARKS
    assert original == ROOT / "genie/benchmark_questions.json"
    try:
        validator.BENCHMARKS = temp
        return validator.validate_assets()
    finally:
        validator.BENCHMARKS = original


def test_validate_assets_is_wired_to_the_refusal_validator(tmp_path: Path) -> None:
    # Guard 2. A validator whose refusal checks are never called is decorative,
    # so prove the end-to-end entry point rejects a bad refusal, not just
    # validate_refusals() called directly.
    doc = copy.deepcopy(BENCHMARK_DOC)
    _find(doc["refusals"], MUTABLE_REFUSAL_ID)["contract_quote"] = (
        "Market notice reason codes are published only for constraint violations."
    )
    with pytest.raises(
        ValueError,
        match=rf"refusal {MUTABLE_REFUSAL_ID} quote is not present",
    ):
        _validate_assets_with_catalogue(doc, tmp_path)


def test_validate_assets_is_wired_to_the_anti_vacuity_expectation_check(tmp_path: Path) -> None:
    # Guard 3. Same wiring argument for the result-contract check.
    doc = copy.deepcopy(BENCHMARK_DOC)
    target = next(item for item in doc["benchmarks"] if item["id"] == "regional-price-demand")
    target["result_expectation"] = {"minimum_row_count": 0}
    with pytest.raises(
        ValueError,
        match=r"benchmark regional-price-demand result_expectation .*asserts nothing",
    ):
        _validate_assets_with_catalogue(doc, tmp_path)


def test_validate_assets_still_accepts_the_shipped_catalogue_through_a_temp_copy(
    tmp_path: Path,
) -> None:
    # Control for the two wiring tests: the harness itself must not be what makes
    # them raise, and validator.BENCHMARKS must be restored afterwards.
    result = _validate_assets_with_catalogue(copy.deepcopy(BENCHMARK_DOC), tmp_path)
    assert len(result["benchmarks"]) == 6
    assert len(result["refusals"]) == 6
    assert validator.BENCHMARKS == ROOT / "genie/benchmark_questions.json"


def test_no_mutation_test_wrote_to_the_shipped_catalogue() -> None:
    # Every mutation above is applied to a deep copy, and the one test that
    # repoints validator.BENCHMARKS writes only inside pytest's tmp_path. This is
    # the backstop: the reviewed JSON on disk must still parse to exactly what
    # this module read at import time.
    on_disk = json.loads((ROOT / "genie/benchmark_questions.json").read_text())
    assert on_disk == BENCHMARK_DOC, "the shipped catalogue was mutated on disk by a test"
    assert on_disk["refusals"] == REFUSALS
    assert on_disk["benchmarks"] == BENCHMARKS
