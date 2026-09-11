import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('verify_sync', Path(__file__).resolve().parents[2] / 'scripts/verify-sync.py')
verify_sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_sync)


def test_sync_comparison_normalizes_offsets_and_postgres_numeric_strings():
    source = [{'duid': 'TEST1', 'interval_end': '2026-07-01T12:00:00+10:00', 'mw': -15.5, 'capacity': None}]
    synced = [{'duid': 'TEST1', 'interval_end': '2026-07-01T02:00:00Z', 'mw': '-15.50', 'capacity': None}]
    assert verify_sync.compare(source, synced, ['interval_end', 'duid']) == 1


@pytest.mark.parametrize('synced', [[], [{'duid': 'A', 'mw': 2}], [{'duid': 'A'}], [{'duid': 'A', 'mw': 1}, {'duid': 'A', 'mw': 1}]])
def test_sync_comparison_rejects_missing_changed_or_duplicate_data(synced):
    with pytest.raises(ValueError):
        verify_sync.compare([{'duid': 'A', 'mw': 1}], synced, ['duid'])


def test_sync_comparison_rejects_naive_timestamp_exports():
    with pytest.raises(ValueError):
        verify_sync.canonical('2026-07-01T02:00:00')
