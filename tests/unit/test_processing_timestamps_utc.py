"""Source contract for UTC processing timestamps in the Lakeflow pipeline.

Spark ``current_timestamp()`` represents an instant. Converting it to a local
wall-clock string and parsing it back would discard that UTC-instant contract,
so this test rejects local-time conversion in processing/publication columns.
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).parents[2]
PIPELINE = ROOT / "src" / "agentic_energy"
PROCESSING_COLUMNS = {"ingested_at", "silver_published_at", "gold_published_at"}
LOCALISING_CALLS = {"date_format", "from_utc_timestamp", "to_timestamp"}


def _call_names(expression: ast.AST) -> set[str]:
    return {
        node.func.attr
        for node in ast.walk(expression)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def _processing_expressions(path: Path) -> list[tuple[str, ast.AST]]:
    expressions: list[tuple[str, ast.AST]] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "alias"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value in PROCESSING_COLUMNS
        ):
            expressions.append((str(node.args[0].value), node.func.value))
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "withColumn"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value in PROCESSING_COLUMNS
        ):
            expressions.append((str(node.args[0].value), node.args[1]))
    return expressions


def test_pipeline_processing_timestamps_preserve_utc_instants() -> None:
    observed: set[str] = set()
    for path in sorted(PIPELINE.rglob("*.py")):
        for column, expression in _processing_expressions(path):
            calls = _call_names(expression)
            # Gold tables may carry a Silver publication timestamp through as
            # lineage. Inspect only expressions that create a processing time;
            # the workshop defect still contains current_timestamp and is
            # therefore checked here.
            if "current_timestamp" not in calls:
                assert calls.intersection({"col", "max"}) and calls <= {
                    "col",
                    "greatest",
                    "max",
                }, (
                    f"{path.name}:{column} must either carry lineage through "
                    "or be written from Spark's current UTC instant"
                )
                continue
            observed.add(column)
            assert not calls.intersection(LOCALISING_CALLS), (
                f"{path.name}:{column} must not be converted to a local, naive "
                "wall-clock timestamp"
            )

    assert observed == PROCESSING_COLUMNS
