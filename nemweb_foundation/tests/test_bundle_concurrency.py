"""Offline bundle contracts for safe concurrent developer deployments.

Development mode namespaces resources by deploying identity. No resource may
pin a shared identity, and all writing jobs are single-run/queued so one
identity cannot overlap its own landing or publication cycles.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bundle():
    return yaml.safe_load((REPO_ROOT / "databricks.yml").read_text())


@pytest.fixture(scope="module")
def jobs():
    resources = {}
    for path in (REPO_ROOT / "resources").glob("*.yml"):
        document = yaml.safe_load(path.read_text()) or {}
        resources.update(document.get("resources", {}).get("jobs", {}))
    return resources


def test_jobs_do_not_pin_run_as(jobs):
    """run_as belongs to the target, never to a shared job definition."""
    assert jobs
    assert all("run_as" not in job for job in jobs.values())


def test_dev_target_has_no_run_as(bundle):
    dev = bundle["targets"]["dev"]
    assert dev["mode"] == "development"
    assert "run_as" not in dev, (
        "pinning run_as on dev makes it deployable by exactly one identity"
    )


def test_workshop_target_does_not_pin_run_as_by_default(bundle):
    workshop = bundle["targets"]["workshop"]
    assert workshop["mode"] == "production"
    assert "run_as" not in workshop


def test_runtime_service_principal_is_optional_for_dev(bundle):
    assert bundle["variables"]["runtime_service_principal"].get("default") == ""


def test_deploy_script_uses_profile_and_optional_overrides():
    script = (REPO_ROOT / "scripts" / "deploy.sh").read_text()
    assert "RUNTIME_SERVICE_PRINCIPAL" in script
    assert "BUNDLE_VAR_" not in script
    assert "--profile \"$PROFILE\"" in script


def test_writing_jobs_are_single_run_and_queued(jobs):
    expected = {
        "agentic_energy_local_fixture",
        "nemweb_lander",
        "nemweb_refresh",
        "nemweb_context_refresh",
    }
    assert expected <= jobs.keys()
    for key in expected:
        assert jobs[key]["queue"] == {"enabled": True}
        if key == "nemweb_lander":
            # Deliberately concurrent: this one Job is called by both the
            # five-minute critical orchestration and the daily context
            # orchestration. Serialising it made a critical cycle queue behind
            # another caller and time out. Landing is content-addressed and
            # write-once, so concurrent runs cannot corrupt the landing zone.
            assert jobs[key]["max_concurrent_runs"] > 1
        else:
            # Orchestrators stay single-run so cycles cannot overlap.
            assert jobs[key]["max_concurrent_runs"] == 1


def test_development_resource_names_use_the_run_specific_workshop_prefix(jobs):
    for job in jobs.values():
        assert job["name"].startswith("${var.resource_prefix}-")


def test_legacy_output_and_lander_cycle_are_keyed_by_unique_run_id(jobs):
    legacy_parameters = jobs["agentic_energy_local_fixture"]["tasks"][0][
        "python_wheel_task"
    ]["parameters"]
    output = legacy_parameters[legacy_parameters.index("--output") + 1]
    assert output.endswith("/legacy-fixture/runs/{{job.run_id}}")

    lander_task = jobs["nemweb_lander"]["tasks"][0]
    assert lander_task["spark_python_task"]["python_file"] == "../scripts/land_nemweb_delta.py"
    lander_parameters = lander_task["spark_python_task"]["parameters"]
    assert lander_parameters[lander_parameters.index("--cycle-id") + 1] == (
        "{{job.run_id}}"
    )
