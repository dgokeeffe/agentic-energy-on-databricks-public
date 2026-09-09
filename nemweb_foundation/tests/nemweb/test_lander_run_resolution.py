"""Regression tests for resolving the Bronze ``ingestion_run_id``.

``land_current`` is a ``run_job_task``, so the task's own ``run_id`` belongs to
the orchestrating refresh job while the lander stamps the *inner* lander job run
ID into Bronze. Scoping evidence queries by the task run ID silently matches no
Bronze rows, which makes ``cycle.interval_end`` NULL and reports every critical
Gold subject as empty even when the tables hold data. These tests pin the
resolution so that false negative cannot return unnoticed.
"""

from __future__ import annotations

import pytest

from agentic_energy.nemweb.evidence import job_outcomes, resolve_lander_run_id, resolve_pipeline_update_id


class _Client:
    """Minimal stand-in exposing only ``list_job_runs``."""

    def __init__(self, runs):
        self.runs = runs
        self.calls = []

    def list_job_runs(self, job_id, limit=25):
        self.calls.append((job_id, limit))
        return self.runs

    def list_pipeline_updates(self, pipeline_id, max_results=25):
        self.calls.append((pipeline_id, max_results))
        return self.runs


def _parent_run(task, **overrides):
    run = {
        "run_id": 660002388315155,
        "start_time": 1788346444000,
        "end_time": 1788346825000,
        "state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"},
        "tasks": [
            task,
            {"task_key": "publish_medallion", "state": {"result_state": "SUCCESS"}},
        ],
    }
    run.update(overrides)
    return run


def _run_job_task(**overrides):
    task = {
        "task_key": "land_current",
        "run_id": 1045367671248243,  # task run ID, NOT the ingestion run ID
        "start_time": 1788346444663,
        "end_time": 1788346824468,
        "state": {"result_state": "SUCCESS"},
        "run_job_task": {"job_id": 980288191176099},
    }
    task.update(overrides)
    return task


def test_resolves_inner_lander_run_not_task_run():
    """The inner lander job run inside the task window wins."""
    client = _Client([
        {"run_id": 209073032136172, "start_time": 1788347579000},  # later cycle
        {"run_id": 195921727520845, "start_time": 1788346691000},  # in window
        {"run_id": 445319079708068, "start_time": 1788345956000},  # earlier cycle
    ])
    run = _parent_run(_run_job_task())

    resolved = resolve_lander_run_id(client, run)

    assert resolved == "195921727520845"
    # The task run ID must never be used to scope Bronze queries.
    assert resolved != "1045367671248243"
    assert client.calls == [("980288191176099", 25)]


def test_task_run_id_used_when_not_a_run_job_task():
    """A direct lander task stamps its own run ID, so no lookup is needed."""
    client = _Client([])
    task = _run_job_task()
    del task["run_job_task"]

    assert resolve_lander_run_id(client, _parent_run(task)) == "1045367671248243"
    assert client.calls == []


def test_trigger_info_link_wins_when_scheduled_windows_overlap():
    client = _Client([
        {
            "run_id": 111111111111111,
            "start_time": 1788346500000,
            "trigger_info": {"run_id": 1045367671248243},
        },
        {
            "run_id": 222222222222222,
            "start_time": 1788346600000,
            "trigger_info": {"run_id": 999999999999999},
        },
    ])

    assert resolve_lander_run_id(client, _parent_run(_run_job_task())) == "111111111111111"


def test_ambiguous_window_is_raised_not_guessed():
    """Two candidate runs must fail loudly rather than silently pick one."""
    client = _Client([
        {"run_id": 111111111111111, "start_time": 1788346500000},
        {"run_id": 222222222222222, "start_time": 1788346600000},
    ])

    with pytest.raises(RuntimeError, match="multiple lander runs"):
        resolve_lander_run_id(client, _parent_run(_run_job_task()))


def test_empty_window_is_raised():
    """No candidate means the cycle cannot be evidenced."""
    client = _Client([{"run_id": 333333333333333, "start_time": 1788300000000}])

    with pytest.raises(RuntimeError, match="no run of lander job"):
        resolve_lander_run_id(client, _parent_run(_run_job_task()))


def test_missing_land_current_task_is_raised():
    client = _Client([])
    run = {"tasks": [{"task_key": "publish_medallion", "state": {}}]}

    with pytest.raises(RuntimeError, match="no land_current task"):
        resolve_lander_run_id(client, run)


def test_open_ended_window_accepts_later_run():
    """A still-running task has no end time; later runs stay eligible."""
    client = _Client([{"run_id": 444444444444444, "start_time": 1788346900000}])
    task = _run_job_task()
    del task["end_time"]

    assert resolve_lander_run_id(client, _parent_run(task)) == "444444444444444"


def test_exact_pipeline_update_resolution_prefers_exposed_id_and_fails_ambiguous_window():
    client = _Client([])
    assert resolve_pipeline_update_id(client, "p", {"pipeline_task": {"update_id": "u-exact"}}) == "u-exact"
    client = _Client([{"update_id": "u1", "creation_time": 150}, {"update_id": "u2", "creation_time": 160}])
    with pytest.raises(RuntimeError, match="2 updates"):
        resolve_pipeline_update_id(client, "p", {"start_time": 100, "end_time": 200})
    client = _Client([{"update_id": "u1", "creation_time": 150}])
    assert resolve_pipeline_update_id(client, "p", {"start_time": 100, "end_time": 200}) == "u1"


def test_job_outcomes_still_reports_task_run_id():
    """job_outcomes keeps its documented task-run-ID contract."""
    started, ended, lander, pipeline, overall, task_run_id = job_outcomes(
        _parent_run(_run_job_task())
    )

    assert task_run_id == "1045367671248243"
    assert lander == "SUCCESS"
    assert pipeline == "SUCCESS"
    assert overall == "SUCCESS"
    assert started.startswith("2026-")
    assert ended.startswith("2026-")
