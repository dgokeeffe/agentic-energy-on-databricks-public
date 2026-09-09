from pathlib import Path

from agentic_energy.nemweb.delta_lander import (
    prepare_landing_batch,
    write_landing_batch_to_backend,
)
from agentic_energy.nemweb.lander import ArchiveInput

FIXTURE = Path(__file__).parents[1] / "fixtures" / "nemweb" / "v1" / "raw"


class MemoryBackend:
    def __init__(self):
        self.ids: dict[str, set[str]] = {}
        self.associations: set[tuple[str, str, str]] = set()
        self.metadata: dict[str, list[object]] = {}

    def insert_source(self, table, records):
        target = self.ids.setdefault(table, set())
        before = len(target)
        target.update(record.source_record_id for record in records)
        return len(target) - before

    def insert_run_records(self, batch):
        before = len(self.associations)
        for subject, records in batch.records_by_subject.items():
            for record in records:
                self.associations.add((batch.run_id, subject, record.source_record_id))
        return len(self.associations) - before

    def append_metadata(self, table, rows):
        self.metadata.setdefault(table, []).extend(rows)


def _archive(family: str, path: Path) -> ArchiveInput:
    return ArchiveInput(
        family,
        "202401010005",
        path.name,
        path.read_bytes(),
        f"/REPORTS/{path.name}",
        "snapshot",
        "2024-01-01T00:06:00+00:00",
        True,
    )


def _scada_archive() -> ArchiveInput:
    return _archive("dispatch_scada", next((FIXTURE / "dispatch_scada").glob("*.zip")))


def test_generation_critical_batch_needs_only_scada_and_retry_is_idempotent():
    archive = _scada_archive()
    first = prepare_landing_batch(
        [archive],
        run_id="one",
        source_mode="snapshot",
        scope="critical",
        landed_at="2024-01-01T00:07:00+00:00",
    )
    retry = prepare_landing_batch(
        [archive],
        run_id="two",
        source_mode="snapshot",
        scope="critical",
        landed_at="2024-01-01T00:08:00+00:00",
    )

    assert first.status == "COMPLETE_NEW_DATA"
    assert set(first.records_by_subject) == {"dispatch_unit_scada"}
    assert first.records_by_subject["dispatch_unit_scada"]
    assert [record.source_record_id for record in first.records_by_subject["dispatch_unit_scada"]] == [
        record.source_record_id for record in retry.records_by_subject["dispatch_unit_scada"]
    ]

    backend = MemoryBackend()
    status1, inserted1 = write_landing_batch_to_backend(backend, first)
    status2, inserted2 = write_landing_batch_to_backend(backend, retry)
    assert status1 == "COMPLETE_NEW_DATA"
    assert status2 == "COMPLETE_NO_NEW_SOURCE"
    assert inserted1 > 0
    assert inserted2 == 0
    assert {run_id for run_id, _, _ in backend.associations} == {"one", "two"}


def test_unrelated_dispatchis_archive_cannot_block_or_enter_generation_cycle():
    dispatch = _archive("dispatchis", next((FIXTURE / "dispatchis").glob("*.zip")))
    batch = prepare_landing_batch(
        [dispatch], run_id="wrong-family", source_mode="snapshot", scope="critical"
    )

    assert batch.status == "FAILED"
    assert set(batch.records_by_subject) == {"dispatch_unit_scada"}
    assert batch.records_by_subject["dispatch_unit_scada"] == ()


def test_context_batch_requires_all_three_registration_sections():
    registration = [
        _archive("registration", path)
        for path in sorted((FIXTURE / "registration").glob("*.zip"))
    ]
    batch = prepare_landing_batch(
        registration,
        run_id="registration",
        source_mode="snapshot",
        scope="context",
    )

    assert batch.status == "COMPLETE_NEW_DATA"
    assert set(batch.records_by_subject) == {"dudetail", "dualloc", "genunits"}
    assert all(batch.records_by_subject.values())


def test_regional_dispatch_has_an_explicit_non_critical_scope():
    dispatch = _archive("dispatchis", next((FIXTURE / "dispatchis").glob("*.zip")))
    batch = prepare_landing_batch(
        [dispatch], run_id="regional", source_mode="snapshot", scope="regional"
    )

    assert batch.status == "COMPLETE_NEW_DATA"
    assert set(batch.records_by_subject) == {
        "dispatch_price",
        "dispatch_region_sum",
        "dispatch_constraint",
        "dispatch_interconnector_res",
    }
    assert all(batch.records_by_subject.values())
