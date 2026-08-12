"""Bundle contract tests for many developers deploying `dev` at the same time.

These are cheap YAML contract assertions, not workspace calls, so they run in
the normal offline test suite. They lock in the two properties that let N
developers deploy the same bundle concurrently without stepping on each other:

1. `dev` must not pin `run_as` to a shared service principal. Binding an SP into
   `run_as` requires the `servicePrincipal.user` role on that SP, so a pinned SP
   makes the target undeployable by every other identity:

       Cannot bind the service principal provided in 'run_as' field ...
       (403 PERMISSION_DENIED)

   With no `run_as`, each deploy runs as its deployer and `mode: development`
   namespaces the job name and workspace root per identity.

2. Run outputs must be keyed by the unique `{{job.run_id}}`, so concurrent runs
   from different identities cannot overwrite each other in the shared Volume.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bundle():
    return yaml.safe_load((REPO_ROOT / "databricks.yml").read_text())


@pytest.fixture(scope="module")
def job():
    doc = yaml.safe_load(
        (REPO_ROOT / "resources" / "agentic_energy_job.job.yml").read_text()
    )
    return doc["resources"]["jobs"]["agentic_energy_etl"]


def test_job_does_not_pin_run_as(job):
    """run_as belongs to the target, never to the shared job definition."""
    assert "run_as" not in job


def test_dev_target_has_no_run_as(bundle):
    dev = bundle["targets"]["dev"]
    assert dev["mode"] == "development"
    assert "run_as" not in dev, (
        "pinning run_as on dev makes it deployable by exactly one identity"
    )


def test_workshop_target_pins_the_etl_service_principal(bundle):
    """The shared target still runs under one governed identity."""
    workshop = bundle["targets"]["workshop"]
    assert workshop["mode"] == "production"
    assert workshop["run_as"] == {
        "service_principal_name": "${var.runtime_service_principal}"
    }


def test_runtime_service_principal_is_optional_for_dev(bundle):
    """dev must validate with the variable unset, so it needs a default."""
    assert bundle["variables"]["runtime_service_principal"].get("default") == ""


def test_deploy_script_requires_the_sp_only_for_workshop():
    script = (REPO_ROOT / "scripts" / "deploy.sh").read_text()
    guard = "BUNDLE_VAR_runtime_service_principal:?"
    assert guard in script
    # The guard must sit inside a workshop-only branch, not at top level.
    before = script.split(guard)[0]
    assert 'if [ "$TARGET" = "workshop" ]; then' in before


def test_run_output_path_is_keyed_by_unique_run_id(job):
    params = job["tasks"][0]["python_wheel_task"]["parameters"]
    output = params[params.index("--output") + 1]
    assert output.endswith("/runs/{{job.run_id}}"), (
        "concurrent deployers share one Volume; only the unique run id keeps "
        "their outputs from colliding"
    )


def test_job_publishes_to_the_target_unity_catalog_schema(job):
    """The deployed run must land governed tables, not just Volume JSONL.

    A Volume of JSONL cannot be queried or granted, so without these the
    business has nothing to consume.
    """
    params = job["tasks"][0]["python_wheel_task"]["parameters"]
    assert params[params.index("--publish-catalog") + 1] == "${var.catalog}"
    assert params[params.index("--publish-schema") + 1] == "${var.schema}"


def test_published_tables_are_keyed_by_the_same_run_id_as_the_volume(job):
    """Publication idempotency depends on the run id the outputs are keyed by."""
    params = job["tasks"][0]["python_wheel_task"]["parameters"]
    assert params[params.index("--run-id") + 1] == "{{job.run_id}}"


def test_deployed_job_stays_in_fixture_mode(job):
    """Live NEMWEB requires PF-8 authorization and a human deployment gate."""
    params = job["tasks"][0]["python_wheel_task"]["parameters"]
    assert params[params.index("--mode") + 1] == "fixture"
