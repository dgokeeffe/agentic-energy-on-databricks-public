from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
ROOT = Path(__file__).resolve().parents[1]


def test_jobs_are_serverless_manual_shells_and_parameterised():
    resources = {}
    for path in (ROOT / "resources").glob("*.yml"):
        jobs = (yaml.safe_load(path.read_text()) or {}).get("resources", {}).get("jobs")
        if jobs:
            resources.update(jobs)
    assert set(resources) == {"nemweb_training", "nemweb_batch_scoring"}
    for job in resources.values():
        assert "schedule" not in job and "trigger" not in job and "continuous" not in job
        assert job["max_concurrent_runs"] == 1
        task = job["tasks"][0]
        assert task["environment_key"] == "default"
        assert "notebook_task" in task
        assert "existing_cluster_id" not in task and "new_cluster" not in task


def test_registry_and_alias_safety_contracts():
    source = "\n".join(path.read_text() for path in (ROOT / "src").rglob("*.py"))
    resources = "\n".join(path.read_text() for path in (ROOT / "resources").glob("*.yml"))
    assert 'mlflow.set_registry_uri("databricks-uc")' in source
    assert '"challenger"' in source
    assert '"prod"' not in source.lower()
    assert "serving_endpoint" not in resources
    variables = yaml.safe_load((ROOT / "databricks.yml").read_text())["variables"]
    assert {"mlflow_experiment_name", "uc_model_name", "training_table", "feature_table", "prediction_table"} <= variables.keys()
    assert variables["catalog"]["default"] == "${workspace.current_user.short_name}"
    assert variables["schema"]["default"] == "agentic_energy_workshop"
    assert variables["mlflow_experiment_name"]["default"] == "${resources.experiments.nemweb.name}"
    assert variables["uc_model_name"]["default"] == "${resources.registered_models.price_model.full_name}"


def test_fixture_is_explicitly_not_a_useful_performance_claim():
    readme = (ROOT / "README.md").read_text()
    assert "prepared" in readme.lower()
    assert "does not prove" in readme.lower()
