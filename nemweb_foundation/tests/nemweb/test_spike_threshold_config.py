"""The spike threshold must be stated, never defaulted.

The threshold is a market judgement rather than an engineering constant. If the
pipeline adopted a fallback value, a published measure would carry a number no
operator chose and no document supports.
"""

from __future__ import annotations

import pytest

from agentic_energy.nemweb.pipeline.config import (
    SPIKE_BASELINE_INTERVALS,
    spike_baseline_multiple,
)


def _spark(values: dict[str, str]):
    class Conf:
        def get(self, key: str) -> str:
            return values[key]  # KeyError when unset, as Spark does

    return type("Spark", (), {"conf": Conf()})()


def test_the_baseline_window_is_twenty_four_hours_of_five_minute_intervals() -> None:
    assert SPIKE_BASELINE_INTERVALS == 288
    assert SPIKE_BASELINE_INTERVALS == 24 * 60 // 5


def test_an_agreed_multiple_is_read() -> None:
    assert spike_baseline_multiple(_spark({"nemweb.spike_baseline_multiple": "3.5"})) == 3.5


def test_an_unset_threshold_refuses_rather_than_defaulting() -> None:
    with pytest.raises(ValueError, match="no default"):
        spike_baseline_multiple(_spark({}))


def test_an_empty_threshold_refuses() -> None:
    with pytest.raises(ValueError, match="no default"):
        spike_baseline_multiple(_spark({"nemweb.spike_baseline_multiple": "  "}))


def test_a_non_numeric_threshold_refuses() -> None:
    with pytest.raises(ValueError, match="must be a number"):
        spike_baseline_multiple(_spark({"nemweb.spike_baseline_multiple": "high"}))


@pytest.mark.parametrize("raw", ["0", "-2"])
def test_a_non_positive_threshold_refuses(raw: str) -> None:
    """A zero or negative multiple would flag every interval or none."""

    with pytest.raises(ValueError, match="greater than zero"):
        spike_baseline_multiple(_spark({"nemweb.spike_baseline_multiple": raw}))


def test_no_default_value_is_committed_anywhere_in_the_bundle() -> None:
    """A default in databricks.yml would silently re-enable the guessed number."""

    from pathlib import Path

    import yaml

    bundle = yaml.safe_load(
        (Path(__file__).parents[2] / "databricks.yml").read_text()
    )
    declared = bundle["variables"]["spike_baseline_multiple"]
    assert "default" not in declared, "the spike threshold must have no default"
