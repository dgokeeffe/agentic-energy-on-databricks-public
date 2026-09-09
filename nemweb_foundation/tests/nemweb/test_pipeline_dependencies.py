"""Static dependency and API checks for the NEMWEB pipeline source graph."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


yaml = pytest.importorskip("yaml")
ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "agentic_energy" / "nemweb" / "pipeline"

# Helper modules are imported by the dataset modules and must NOT be listed as
# pipeline libraries. Listing io.py evaluated its @dp.temporary_view decorator
# both as a library and again on import, failing the deployed update with
# "Found duplicate dataset `_nemweb_parsed_records`". Verified against pipeline
# update e8456591 on 2026-09-02.
# Helpers and sources owned by a separate pipeline are not libraries in the
# primary NEMWEB medallion graph.
HELPER_SOURCES = {"config.py", "io.py", "silver_common.py", "lakebase_investigations.py"}

EXPLICIT_SOURCES = {
    "parsed_records.py", "bronze_dispatchis.py", "bronze_scada.py",
    "bronze_unit_solution.py", "bronze_registration.py",
    "silver_region_dispatch.py", "silver_scada.py", "silver_constraints.py",
    "silver_interconnectors.py", "silver_unit_solution.py", "silver_facilities.py",
    "gold_region_dispatch.py", "gold_unit_dispatch.py", "gold_scada_generation.py",
    "gold_constraints.py", "gold_interconnectors.py", "gold_unit_solution.py",
    "gold_app_region_status.py", "gold_additional_aggregates.py",
    "bronze_bids.py", "silver_bids.py", "gold_bids.py",
    "bronze_trading.py", "silver_trading.py", "gold_trading.py",
    "bronze_settlement.py", "silver_settlement.py", "gold_settlement.py",
}


def _pipeline() -> dict:
    document = yaml.safe_load((ROOT / "resources" / "nemweb.pipeline.yml").read_text())
    return document["resources"]["pipelines"]["nemweb"]


def _read_stream_dependencies(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    dependencies: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "table" or not node.args:
            continue
        owner = node.func.value
        if not (
            isinstance(owner, ast.Attribute)
            and owner.attr == "readStream"
            and isinstance(owner.value, ast.Name)
            and owner.value.id == "spark"
        ):
            continue
        if isinstance(node.args[0], ast.Constant):
            dependencies.add(node.args[0].value)
    return dependencies


def test_every_current_pipeline_source_is_explicitly_included() -> None:
    pipeline = _pipeline()
    listed = {
        Path(library["file"]["path"]).name
        for library in pipeline["libraries"]
    }
    current = {
        path.name
        for path in PIPELINE.glob("*.py")
        if path.name != "__init__.py" and path.name not in HELPER_SOURCES
    }
    assert listed == current == EXPLICIT_SOURCES
    assert not (listed & HELPER_SOURCES), (
        "helper modules must not be pipeline libraries: a decorator in a helper "
        "would register its dataset twice and fail the update"
    )
    assert all("glob" not in library and "notebook" not in library for library in pipeline["libraries"])
    assert pipeline["root_path"] == ".."


def test_dependency_graph_has_one_auto_loader_source_and_no_unresolved_reads() -> None:
    io_source = (PIPELINE / "io.py").read_text()
    assert io_source.count('.format("cloudFiles")') == 1
    # The view is declared exactly once, in its own dataset module, because a
    # decorator inside the widely-imported io.py helper registers the dataset
    # once per importer and fails the update as a duplicate.
    declarations = [
        path
        for path in PIPELINE.glob("*.py")
        if 'name="_nemweb_parsed_records"' in path.read_text()
    ]
    assert [path.name for path in declarations] == ["parsed_records.py"]
    assert 'name="_nemweb_parsed_records"' not in io_source

    bronze_dependencies = set()
    for path in PIPELINE.glob("bronze_*.py"):
        bronze_dependencies |= _read_stream_dependencies(path)
    bronze_source = "\n".join(
        path.read_text() for path in PIPELINE.glob("bronze_*.py")
    )
    assert "section_stream(" in bronze_source
    assert 'readStream.table("_nemweb_parsed_records")' in io_source
    assert bronze_dependencies
    assert all(name.startswith("_raw_nem_") for name in bronze_dependencies)


def test_app_critical_bronze_uses_delta_association_bridge():
    io_source = (PIPELINE / "io.py").read_text()
    delta_source = (ROOT / "agentic_energy/nemweb/delta_lander.py").read_text()
    assert "successful_run_records(" in io_source
    assert "landing_nem_run_records" in delta_source
    assert "COMPLETE_NEW_DATA" in delta_source and "COMPLETE_NO_NEW_SOURCE" in delta_source
    for filename in ("bronze_dispatchis.py", "bronze_scada.py", "bronze_registration.py"):
        source = (PIPELINE / filename).read_text()
        assert "subject_key=" in source
        assert "_COLUMNS =" not in source


def test_pipeline_sources_do_not_hide_critical_files_or_perform_side_effects() -> None:
    resource = (ROOT / "resources" / "nemweb.pipeline.yml").read_text()
    for source in EXPLICIT_SOURCES:
        assert f"path: ../agentic_energy/nemweb/pipeline/{source}" in resource
        assert f"# path: ../agentic_energy/nemweb/pipeline/{source}" not in resource

    source_text = "\n".join(path.read_text() for path in PIPELINE.glob("*.py"))
    for forbidden in (
        "import dlt",
        "dlt.read",
        "dp.read(",
        "dp.read_stream",
        "LIVE.",
        "input_file_name(",
        ".writeStream",
        ".start(",
        "requests.",
        "urllib.",
    ):
        assert forbidden not in source_text
