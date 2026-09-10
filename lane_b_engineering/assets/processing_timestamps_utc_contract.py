"""Workshop entry point for the canonical UTC processing-time contract test."""

from __future__ import annotations

import importlib.util
from pathlib import Path

TEST_PATH = (
    Path(__file__).resolve().parents[4]
    / "nemweb_foundation"
    / "tests"
    / "nemweb"
    / "test_processing_timestamps_utc.py"
)
SPEC = importlib.util.spec_from_file_location("nemweb_foundation_utc_contract", TEST_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

test_pipeline_processing_timestamps_preserve_utc_instants = (
    MODULE.test_pipeline_processing_timestamps_preserve_utc_instants
)
