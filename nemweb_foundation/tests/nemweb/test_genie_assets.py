from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
SPACE = json.loads((ROOT / "genie/nemweb_space.json").read_text())
RESOURCE = yaml.safe_load((ROOT / "resources/nemweb_genie.genie_space.yml").read_text())


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
        "nem_dispatch_price_spike_metrics",
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
    assert len(samples) == len(examples) == 6
    # The Genie API requires every id to be a lowercase 32-hex UUID without
    # hyphens (400 INVALID_PARAMETER_VALUE otherwise, observed 2026-09-02). They
    # are generated deterministically with uuid5 from a stable slug, so they are
    # reproducible across deploys but are no longer human-sortable.
    all_ids = [item["id"] for item in samples] + [item["id"] for item in examples]
    all_ids += [item["id"] for item in SPACE["instructions"]["text_instructions"]]
    for value in all_ids:
        assert re.fullmatch(r"[0-9a-f]{32}", value), value
    assert len({item["id"] for item in samples}) == 6
    assert len({item["id"] for item in examples}) == 6
    # The API additionally requires these lists to be sorted by id
    # ("example_question_sqls must be sorted by id", 400, observed 2026-09-02).
    assert [item["id"] for item in samples] == sorted(item["id"] for item in samples)
    assert [item["id"] for item in examples] == sorted(item["id"] for item in examples)
    assert all(item["question"] and isinstance(item["question"][0], str) for item in samples)
    assert all("${var.catalog}.${var.schema}." in "".join(item["sql"]) for item in examples)
