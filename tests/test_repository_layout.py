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
    assert "FROM daveok.agentic_energy_workshop_d4_serving.gold_nem_app_region_status" in query
    assert "IDENTIFIER(" not in query
    assert ":serving_table" not in query
    assert "SERVING_TABLE" not in (ROOT / "nemweb_app/app.yaml").read_text()


def test_app_mock_smoke_does_not_start_workspace_plugins():
    playwright = (ROOT / "nemweb_app/playwright.config.ts").read_text()
    makefile = (ROOT / "Makefile").read_text()
    assert "vite preview" in playwright
    assert "npm start" not in playwright
    assert "VITE_DATA_MODE=mock npx vite" in makefile
