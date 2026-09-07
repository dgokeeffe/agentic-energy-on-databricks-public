"""Chronological train, validation, and held-out test splitting."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .contracts import parse_timestamp, validate_training_rows


def chronological_split(
    rows: Iterable[Mapping[str, Any]], *, train_fraction: float = 0.6, validation_fraction: float = 0.2
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    validated = validate_training_rows(rows)
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("split fractions must be between zero and one")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train and validation fractions must leave a test period")
    times = sorted({parse_timestamp(row["prediction_time"], "prediction_time") for row in validated})
    if len(times) < 3:
        raise ValueError("at least three distinct prediction times are required")
    train_end = max(1, int(len(times) * train_fraction))
    validation_end = max(train_end + 1, int(len(times) * (train_fraction + validation_fraction)))
    validation_end = min(validation_end, len(times) - 1)
    train_times = set(times[:train_end])
    validation_times = set(times[train_end:validation_end])
    test_times = set(times[validation_end:])

    def select(wanted: set) -> list[dict[str, Any]]:
        return [row for row in validated if parse_timestamp(row["prediction_time"], "prediction_time") in wanted]

    train, validation, test = select(train_times), select(validation_times), select(test_times)
    if not train or not validation or not test:
        raise ValueError("every chronological split must be non-empty")
    if max(train_times) >= min(validation_times) or max(validation_times) >= min(test_times):
        raise AssertionError("chronological split periods overlap")
    return train, validation, test
