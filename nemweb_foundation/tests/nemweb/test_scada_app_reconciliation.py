from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL = (ROOT / "sql/scada_app_reconciliation.sql").read_text()


def test_scada_reconciliation_is_read_only_and_scoped_to_two_app_gold_tables():
    upper = SQL.upper()
    for mutation in ("CREATE ", "MERGE ", "UPDATE ", "DELETE ", "INSERT ", "DROP ", "ALTER "):
        assert mutation not in upper
    assert "gold_nem_unit_dispatch_5min" in SQL
    assert "gold_nem_scada_generation_5min" in SQL
    assert "silver_nem_dispatch_unit_scada" in SQL
    assert "gold_nem_region_dispatch_5min" not in SQL
    assert "is_effective_run" not in SQL
    assert "intervention" in SQL  # explicit comment: not a SCADA dimension


def test_scada_reconciliation_proves_duid_mw_and_enrichment_contracts():
    for failure in (
        "SCADA DUID coverage does not reconcile between Silver and unit Gold",
        "SCADA signed MW does not reconcile between unit and fuel Gold",
        "SCADA partial-enrichment counts do not reconcile",
    ):
        assert failure in SQL
    assert "FULL OUTER JOIN gold_nem_unit_dispatch_5min" in SQL
    assert "ABS(u.unit_mw - g.generation_mw) > 0.000001" in SQL
    assert "dimension_match_status <> 'REGION_AND_FUEL'" in SQL
    for status in ("REGION_AND_FUEL", "REGION_ONLY", "FUEL_ONLY", "UNMATCHED"):
        assert status in SQL
