from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_required_foundation_app_ml_and_lakebase_structures_exist():
    for relative in ("nemweb_foundation", "nemweb_app", "nemweb_ml", "workshop/lakebase"):
        assert (ROOT / relative).is_dir(), relative


def test_no_tracked_retired_foundation_paths_or_content_references():
    retired = "reference" + "_solution"
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    assert not [path for path in tracked if path.startswith(f"{retired}/")]
    completed = subprocess.run(
        ["git", "grep", "-n", retired, "--", "."],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert completed.returncode == 1, completed.stdout


def test_app_analytics_identifier_is_fixed_to_the_regular_serving_table():
    query = (ROOT / "nemweb_app/config/queries/latest_region_status.sql").read_text()
    table = "agentic_energy_workshop.agentic_energy_workshop_d4_serving.gold_nem_app_region_status"
    assert f"FROM {table}" in query
    assert "FROM daveok." not in query
    assert "IDENTIFIER(" not in query
    assert ":serving_table" not in query
    assert "SERVING_TABLE" not in (ROOT / "nemweb_app/app.yaml").read_text()

    bundle = (ROOT / "nemweb_app/databricks.yml").read_text()
    assert f"securable_full_name: {table}" in bundle
    assert "securable_type: TABLE" in bundle
    assert "permission: SELECT" in bundle


def test_app_fuel_generation_read_is_fixed_and_separately_granted():
    """The value-capture read must be as constrained as the region-status read.

    It is a second governed surface with its own Unity Catalog grant, so a caller
    must not be able to choose the object and the privilege must be declared
    explicitly rather than inherited by widening an existing grant to the schema.
    """
    query = (ROOT / "nemweb_app/config/queries/latest_fuel_generation.sql").read_text()
    table = (
        "agentic_energy_workshop.agentic_energy_workshop_d4_serving"
        ".gold_nem_scada_generation_5min"
    )
    assert f"FROM {table}" in query
    assert "FROM daveok." not in query
    assert "IDENTIFIER(" not in query
    assert ":serving_table" not in query

    bundle = (ROOT / "nemweb_app/databricks.yml").read_text()
    assert f"securable_full_name: {table}" in bundle
    # A schema-level grant would hand the app every table in the serving schema.
    assert "securable_type: SCHEMA" not in bundle


def test_app_states_the_availability_and_settlement_boundaries_on_screen():
    """A capture screen invites a curtailment reading, so the denial must be visible.

    AEMO Current publishes no five-minute availability, and the revenue figure is
    an indicative energy value rather than a settlement figure. Both boundaries are
    asserted here so they cannot be lost to a later copy edit.
    """
    purpose = (ROOT / "nemweb_app/client/src/components/AppPurpose.tsx").read_text()
    shell = (ROOT / "nemweb_app/client/src/components/RegionalOperationsShell.tsx").read_text()
    assert "no five-minute availability" in purpose
    # JSX prose is line-wrapped, so assert fragments that survive the wrapping
    # rather than a sentence that spans a newline and two indents.
    assert "Curtailment is not" in shell
    assert "AEMO Current publishes no five-minute availability" in shell
    assert "excluding FCAS, loss factors, contracts, and settlement adjustment" in shell
    # The borrowed design system is MIT licensed and must stay attributed.
    assert "Open Electricity" in shell
    assert "MIT licensed" in shell


def test_app_mock_smoke_does_not_start_workspace_plugins():
    playwright = (ROOT / "nemweb_app/playwright.config.ts").read_text()
    makefile = (ROOT / "Makefile").read_text()
    assert "vite preview" in playwright
    assert "npm start" not in playwright
    assert "VITE_DATA_MODE=mock npx vite" in makefile


def test_app_analytics_query_parameters_are_referentially_stable():
    app = (ROOT / "nemweb_app/client/src/App.tsx").read_text()
    assert "const EMPTY_QUERY_PARAMETERS" in app
    for query in ("latest_region_status", "latest_fuel_generation"):
        assert f"useAnalyticsQuery('{query}', EMPTY_QUERY_PARAMETERS)" in app
        assert f"useAnalyticsQuery('{query}', {{}})" not in app
