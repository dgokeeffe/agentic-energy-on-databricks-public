from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
SPACE = json.loads((ROOT / "genie/nemweb_space.json").read_text())
RESOURCE = yaml.safe_load((ROOT / "resources/nemweb_genie.genie_space.yml").read_text())
BENCHMARK_DOC = json.loads((ROOT / "genie/benchmark_questions.json").read_text())
REFUSALS = BENCHMARK_DOC["refusals"]


def test_genie_resource_is_bundle_managed_and_parameterised() -> None:
    resource = RESOURCE["resources"]["genie_spaces"]["nemweb_analyst"]
    # The space body must be inlined, not referenced by file_path. A file_path
    # body is inlined verbatim by the CLI, so bundle ${var.*} references inside
    # it are never interpolated and the Genie API receives a literal
    # "${var.catalog}" table identifier, which fails deployment.
    assert "file_path" not in resource
    assert resource["warehouse_id"] == "${var.warehouse_id}"
    inlined = json.loads(resource["serialized_space"])
    assert inlined == SPACE, (
        "resources/nemweb_genie.genie_space.yml serialized_space has drifted from "
        "genie/nemweb_space.json, which is the reviewed source of record"
    )
    assert "${var.catalog}" in resource["serialized_space"]
    assert resource["parent_path"] == "${workspace.root_path}"
    assert "schedule" not in resource and "trigger" not in resource
    assert {item["level"] for item in resource["permissions"]} == {"CAN_RUN", "CAN_MANAGE"}


def test_genie_has_exactly_one_text_instruction_block() -> None:
    # The Genie spaces API rejects multiple blocks with
    # "instructions.text_instructions must contain at most one item"
    # (400 INVALID_PARAMETER_VALUE), observed on deploy 2026-09-02. All guidance
    # is merged into a single headed block.
    blocks = SPACE["instructions"]["text_instructions"]
    assert len(blocks) == 1
    merged = "\n".join(blocks[0]["content"]).lower()
    for heading in ("market and time semantics", "intervention", "query guidance"):
        assert heading in merged


def test_genie_column_configs_are_sorted_by_column_name() -> None:
    # The Genie spaces API rejects an unsorted export with
    # "column_configs must be sorted by column_name" (400
    # INVALID_PARAMETER_VALUE), observed on deploy 2026-09-02.
    for table in SPACE["data_sources"]["tables"]:
        names = [item["column_name"] for item in table.get("column_configs", [])]
        assert names == sorted(names), (
            f"{table['identifier']} column_configs must be sorted by column_name"
        )


def test_genie_exposes_only_a_small_governed_asset_set() -> None:
    identifiers = [item["identifier"] for item in SPACE["data_sources"]["tables"]]
    assert 5 <= len(identifiers) <= 8
    assert len(identifiers) == len(set(identifiers))
    assert all(value.startswith("${var.catalog}.${var.schema}.") for value in identifiers)
    assert not any("bronze_" in value or "silver_" in value for value in identifiers)
    assert set(value.rsplit(".", 1)[-1] for value in identifiers) == {
        "gold_nem_region_dispatch_5min",
        "nem_region_dispatch_metrics",
        "nem_scada_generation_metrics",
        "nem_binding_constraint_metrics",
        "nem_interconnector_flow_metrics",
        "nem_unit_availability_t1_metrics",
    }


def test_genie_instructions_define_market_and_source_limitations() -> None:
    text = json.dumps(SPACE["instructions"]).lower()
    for phrase in (
        "interval-ending",
        "aest (utc+10)",
        "effective",
        "never aggregate",
        "measure()",
        "actual_generation_mw",
        "daily t+1",
        "source sign",
        "unknown",
        "dispatch aud/mwh",
    ):
        assert phrase in text, phrase


def test_genie_samples_and_examples_are_deterministic_and_complete() -> None:
    samples = SPACE["config"]["sample_questions"]
    examples = SPACE["instructions"]["example_question_sqls"]
    # Samples and example SQL are deliberately no longer 1:1. The six answerable
    # questions each have example SQL; the six must-refuse questions are surfaced as
    # sample questions but carry no example SQL by design, because a must-refuse
    # question must never reach the SQL executor.
    assert len(samples) == 12
    assert len(examples) == 6
    # The Genie API requires every id to be a lowercase 32-hex UUID without
    # hyphens (400 INVALID_PARAMETER_VALUE otherwise, observed 2026-09-02). They
    # are generated deterministically with uuid5 from a stable slug, so they are
    # reproducible across deploys but are no longer human-sortable.
    all_ids = [item["id"] for item in samples] + [item["id"] for item in examples]
    all_ids += [item["id"] for item in SPACE["instructions"]["text_instructions"]]
    for value in all_ids:
        assert re.fullmatch(r"[0-9a-f]{32}", value), value
    assert len({item["id"] for item in samples}) == 12
    assert len({item["id"] for item in examples}) == 6
    # The API additionally requires these lists to be sorted by id
    # ("example_question_sqls must be sorted by id", 400, observed 2026-09-02).
    assert [item["id"] for item in samples] == sorted(item["id"] for item in samples)
    assert [item["id"] for item in examples] == sorted(item["id"] for item in examples)
    assert all(item["question"] and isinstance(item["question"][0], str) for item in samples)
    assert all("${var.catalog}.${var.schema}." in "".join(item["sql"]) for item in examples)


def test_genie_refusal_policy_requires_naming_the_reason_and_covers_every_class() -> None:
    # The refusal guidance lives in the single permitted text-instruction block, so a
    # deployed space carries it; a separate block would be rejected by the API.
    blocks = SPACE["instructions"]["text_instructions"]
    assert len(blocks) == 1
    merged = "\n".join(blocks[0]["content"])
    lowered = merged.lower()
    assert "## refusal policy" in lowered
    # It must instruct naming the reason rather than merely declining.
    assert "name the specific reason" in lowered
    assert "i cannot answer that" in lowered and "not an adequate refusal" in lowered
    assert "refuse rather than infer" in lowered
    flattened = re.sub(r"[^a-z0-9]+", " ", lowered)
    for item in REFUSALS:
        # Each unsupported_because class is discoverable as prose, e.g. the class
        # "no_published_field" appears as the heading "No published field:".
        phrase = re.sub(r"[^a-z0-9]+", " ", item["unsupported_because"].lower())
        assert phrase in flattened, item["unsupported_because"]


def test_every_must_refuse_question_is_a_sample_question_with_no_example_sql() -> None:
    samples = {item["id"]: "".join(item["question"]) for item in SPACE["config"]["sample_questions"]}
    example_ids = {item["id"] for item in SPACE["instructions"]["example_question_sqls"]}
    assert len(REFUSALS) == 6
    for item in REFUSALS:
        question_id = item["space_question_id"]
        assert question_id in samples, item["id"]
        assert samples[question_id] == item["question"], item["id"]
        # A must-refuse question with example SQL would hand the executor a query.
        assert question_id not in example_ids, item["id"]
    # The API-required invariants still hold across the enlarged sample list.
    sample_ids = [item["id"] for item in SPACE["config"]["sample_questions"]]
    assert all(re.fullmatch(r"[0-9a-f]{32}", value) for value in sample_ids)
    assert sample_ids == sorted(sample_ids)
    assert len(set(sample_ids)) == len(sample_ids)
    assert len(SPACE["instructions"]["text_instructions"]) == 1
