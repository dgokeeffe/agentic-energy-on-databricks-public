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


def test_the_window_length_is_stated_identically_everywhere_it_appears() -> None:
    """288 is published in five places and they must not drift apart.

    The constant, the Gold view, the governed column comments, the metric view
    comment and DATA-CONTRACT.md all state the baseline length. If one is edited
    alone, analysts read a number the pipeline does not use.
    """

    from pathlib import Path

    root = Path(__file__).parents[2]
    surfaces = {
        "gold view": root / "agentic_energy/nemweb/pipeline/gold_additional_aggregates.py",
        "semantics": root / "sql/nemweb_semantics.sql",
        "data contract": root / "DATA-CONTRACT.md",
    }
    for name, path in surfaces.items():
        text = path.read_text()
        assert str(SPIKE_BASELINE_INTERVALS) in text, f"{name} does not state 288"
        # A stale window length is worse than none: it describes a rule that is
        # not the one running.
        for stale in (" 144 intervals", " 96 intervals", " 12 intervals"):
            assert stale not in text, f"{name} states a stale window {stale!r}"


def test_no_default_value_is_committed_anywhere_in_the_bundle() -> None:
    """A default in databricks.yml would silently re-enable the guessed number."""

    from pathlib import Path

    import yaml

    bundle = yaml.safe_load(
        (Path(__file__).parents[2] / "databricks.yml").read_text()
    )
    declared = bundle["variables"]["spike_baseline_multiple"]
    assert "default" not in declared, "the spike threshold must have no default"
