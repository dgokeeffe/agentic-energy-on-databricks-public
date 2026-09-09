from agentic_energy.nemweb.source_registry import (
    APP_CRITICAL_SUBJECTS,
    GENERATION_APP_GOLD_TABLES,
    GENERATION_APP_SUBJECT_KEYS,
    MARKET_CONTEXT_GOLD_TABLES,
    MARKET_CONTEXT_SUBJECT_KEYS,
    get_subject_by_section,
    landing_tables,
    subjects_for_family,
    subjects_for_scope,
)


def test_app_registry_has_exactly_eight_complete_unique_subjects():
    assert len(APP_CRITICAL_SUBJECTS) == 8
    assert len({s.key for s in APP_CRITICAL_SUBJECTS}) == 8
    assert len({(s.report_family, *s.section_identity) for s in APP_CRITICAL_SUBJECTS}) == 8
    assert len(set(landing_tables())) == 8
    for subject in APP_CRITICAL_SUBJECTS:
        assert subject.natural_key and subject.correction_order
        assert subject.expected_cadence in {"five_minutes", "monthly"}
        assert subject.app_dependencies
        assert any(field.required for field in subject.fields)
        assert get_subject_by_section(subject.report_family, *subject.section_identity) is subject


def test_bronze_modules_do_not_duplicate_registry_projection_maps():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "agentic_energy/nemweb/pipeline"
    for name in ("bronze_dispatchis.py", "bronze_scada.py", "bronze_registration.py"):
        text = (root / name).read_text()
        assert "_COLUMNS =" not in text
        assert "subject_key=" in text


def test_generation_app_scope_is_only_scada_plus_registration():
    assert GENERATION_APP_GOLD_TABLES == (
        "gold_nem_unit_dispatch_5min",
        "gold_nem_scada_generation_5min",
    )
    critical = subjects_for_scope("critical")
    context = subjects_for_scope("context")
    generation_critical = tuple(
        subject for subject in critical if subject.key == "dispatch_unit_scada"
    )
    assert {
        subject.key for subject in (*generation_critical, *context)
    } == GENERATION_APP_SUBJECT_KEYS
    assert {subject.section_name for subject in context} == {
        "DUDETAILSUMMARY",
        "DUALLOC",
        "GENUNITS",
    }
    assert all(
        set(subject.app_dependencies) == set(GENERATION_APP_GOLD_TABLES)
        for subject in (*generation_critical, *context)
    )


def test_market_context_adds_only_price_and_region_sum_to_critical_scope():
    critical = subjects_for_scope("critical")
    market = tuple(
        subject for subject in critical if subject.key in MARKET_CONTEXT_SUBJECT_KEYS
    )
    assert {subject.key for subject in market} == MARKET_CONTEXT_SUBJECT_KEYS
    assert MARKET_CONTEXT_GOLD_TABLES == ("gold_nem_region_dispatch_5min",)
    assert all(subject.app_dependencies == MARKET_CONTEXT_GOLD_TABLES for subject in market)


def test_regional_dispatch_remains_a_separate_compatible_scope():
    dispatch = subjects_for_family("dispatchis")
    assert len(dispatch) == 4
    assert {subject.key for subject in subjects_for_scope("regional")} == {
        "dispatch_constraint",
        "dispatch_interconnector_res",
    }
    assert {s.current_folder for s in dispatch} == {"DispatchIS_Reports"}
    assert {s.filename_prefix for s in dispatch} == {"PUBLIC_DISPATCHIS_"}
    assert len({s.filename_prefix for s in subjects_for_scope("context")}) == 3
