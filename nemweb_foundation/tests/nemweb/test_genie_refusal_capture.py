from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("capture_genie_refusals", SCRIPTS / "capture_genie_refusals.py")
assert spec and spec.loader
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)

SPACE = "0" * 32


def _fake_cli(script: dict[str, dict], calls: list[list[str]] | None = None) -> capture.DatabricksCLI:
    """A CLI whose responses are scripted by REST path fragment."""

    def runner(args: list[str]) -> dict:
        if calls is not None:
            calls.append(args)
        path = args[3]
        for fragment, response in script.items():
            if fragment in path:
                return response
        raise AssertionError(f"unscripted call: {path}")

    return capture.DatabricksCLI("TESTPROFILE", runner=runner)


def test_profile_absence_is_rejected_without_pinning_a_name() -> None:
    # The repository must not embed an operator's profile name; it requires only
    # that one is named explicitly.
    assert not hasattr(capture, "REQUIRED_PROFILE")
    assert "explicit --profile" in capture.PROFILE_REQUIRED_MESSAGE
    for bad in ("", "   "):
        with pytest.raises(ValueError, match="explicit --profile"):
            capture.DatabricksCLI(bad)
    assert capture.DatabricksCLI("DEFAULT").profile == "DEFAULT"


def test_every_workspace_call_carries_the_profile_and_never_a_default() -> None:
    calls: list[list[str]] = []
    cli = _fake_cli(
        {
            "start-conversation": {
                "conversation_id": "c1",
                "message_id": "m1",
                "status": "COMPLETED",
                "content": "refused",
            }
        },
        calls,
    )
    capture.ask(cli, SPACE, "q", timeout_seconds=5, sleep=lambda _s: None)
    assert calls, "no workspace call was made"
    for args in calls:
        assert "--profile" in args and args[args.index("--profile") + 1] == "TESTPROFILE"


def test_ask_polls_until_a_terminal_state_and_returns_the_text() -> None:
    states = iter(
        [
            {"status": "FILTERING_CONTEXT", "conversation_id": "c1", "message_id": "m1"},
            {"status": "ASKING_AI", "conversation_id": "c1", "message_id": "m1"},
            {
                "status": "COMPLETED",
                "conversation_id": "c1",
                "message_id": "m1",
                "attachments": [{"text": {"content": "AEMO Current publishes no five-minute availability."}}],
            },
        ]
    )

    def runner(args: list[str]) -> dict:
        if "start-conversation" in args[3]:
            return {"conversation_id": "c1", "message_id": "m1", "status": "SUBMITTED"}
        return next(states)

    cli = capture.DatabricksCLI("TESTPROFILE", runner=runner)
    result = capture.ask(cli, SPACE, "q", timeout_seconds=30, sleep=lambda _s: None)
    assert result["state"] == "COMPLETED"
    assert "no five-minute availability" in result["response_text"]


def test_a_message_that_never_terminates_raises_rather_than_hanging() -> None:
    cli = _fake_cli(
        {
            "start-conversation": {"conversation_id": "c1", "message_id": "m1", "status": "SUBMITTED"},
            "messages/": {"status": "ASKING_AI"},
        }
    )
    with pytest.raises(TimeoutError, match="did not reach a terminal state"):
        capture.ask(cli, SPACE, "q", timeout_seconds=0, sleep=lambda _s: None)


def test_a_failed_message_is_recorded_not_discarded() -> None:
    # A FAILED response is itself a finding about the space. Raising here would
    # hide the very result the exercise wants to see.
    cli = _fake_cli(
        {
            "start-conversation": {
                "conversation_id": "c1",
                "message_id": "m1",
                "status": "FAILED",
                "content": "could not answer",
            }
        }
    )
    result = capture.ask(cli, SPACE, "q", timeout_seconds=5, sleep=lambda _s: None)
    assert result["state"] == "FAILED"
    assert result["response_text"] == "could not answer"


def test_every_shipped_refusal_becomes_a_record_carrying_its_cited_rule() -> None:
    refusals = capture.load_refusals()
    assert len(refusals) >= 4
    for item in refusals:
        record = capture.build_record(
            item,
            {
                "conversation_id": "c",
                "message_id": "m",
                "state": "COMPLETED",
                "response_text": "text",
                "attachment_count": 0,
            },
        )
        # The transcript must carry the rule the refusal claims, so a reviewer can
        # check the response against it without opening another file.
        assert record["contract_quote"] == item["contract_quote"]
        assert record["contract_section"] == item["contract_section"]
        assert record["expected_refusal_reason"] == item["refusal_reason"]
        assert record["near_miss_of"] == item["near_miss_of"]


def test_acceptance_is_unscored_so_no_automated_pass_is_implied() -> None:
    # Deciding automatically whether a reason was "named" would be the same
    # unproven inference this exercise exists to prevent.
    record = capture.build_record(
        capture.load_refusals()[0],
        {
            "conversation_id": "c",
            "message_id": "m",
            "state": "COMPLETED",
            "response_text": "I cannot answer that.",
            "attachment_count": 0,
        },
    )
    assert set(record["acceptance"]) == set(capture.ACCEPTANCE)
    assert all(value is None for value in record["acceptance"].values())
    assert len(capture.ACCEPTANCE) == 4
    assert "refused" in capture.ACCEPTANCE
    assert "named_a_governed_reason" in capture.ACCEPTANCE


def test_evidence_document_labels_its_own_status_and_non_determinism() -> None:
    document = capture.evidence_document([], [], space_id_supplied=True)
    assert "non-deterministic" in document["determinism"]
    assert "not a CI gate" in document["determinism"]
    assert document["evidence_status"] == "captured-from-deployed-space"
    # Prepared or snapshot material must never be labelled live.
    assert "live" not in document["evidence_status"]


def test_markdown_renders_the_rule_and_marks_every_case_unscored() -> None:
    refusal = capture.load_refusals()[0]
    document = capture.evidence_document(
        [
            capture.build_record(
                refusal,
                {
                    "conversation_id": "c",
                    "message_id": "m",
                    "state": "COMPLETED",
                    "response_text": "some answer",
                    "attachment_count": 0,
                },
            )
        ],
        [],
        space_id_supplied=True,
    )
    text = capture.render_markdown(document)
    assert refusal["contract_quote"][:40] in text
    assert "_unscored_" in text
    assert "must NOT be refused" in text


def test_dry_run_contacts_nothing(monkeypatch, capsys, tmp_path) -> None:
    # The guard that lets an operator see the questions before spending compute.
    def explode(*_args, **_kwargs):
        raise AssertionError("dry run must not construct a workspace client")

    monkeypatch.setattr(capture, "DatabricksCLI", explode)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "capture_genie_refusals.py",
            "--profile",
            "DEFAULT",
            "--space-id",
            SPACE,
            "--output-json",
            str(tmp_path / "out.json"),
            "--dry-run",
            "--include-near-miss-controls",
        ],
    )
    assert capture.main() == 0
    out = capsys.readouterr().out
    assert "no workspace contact" in out
    assert not (tmp_path / "out.json").exists()
    for item in capture.load_refusals():
        assert item["id"] in out


def test_near_miss_controls_ask_the_answerable_twin() -> None:
    # Without this, a space that refuses on keywords alone would look correct.
    questions = capture.load_near_miss_questions()
    refusals = capture.load_refusals()
    for item in refusals:
        assert item["near_miss_of"] in questions, item["id"]
        assert questions[item["near_miss_of"]] != item["question"]


def test_refusal_catalogue_carries_no_sql_so_capture_cannot_execute_one() -> None:
    for item in capture.load_refusals():
        assert "sql_file" not in item
        assert "expected_columns" not in item
        assert "result_expectation" not in item
    source = (SCRIPTS / "capture_genie_refusals.py").read_text(encoding="utf-8")
    # This helper talks to the Genie conversation API only. It must never submit
    # SQL, start a warehouse, or mutate a workspace resource.
    for forbidden in ("/api/2.0/sql/statements", "warehouses start", "bundle deploy"):
        assert forbidden not in source
    for method in ('api("delete"', 'api("patch"', "'delete'", "spaces/create"):
        assert method not in source
