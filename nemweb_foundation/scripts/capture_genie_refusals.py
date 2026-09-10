#!/usr/bin/env python3
"""Ask a deployed Genie space the must-refuse questions and record what it said.

This is the only path that can produce a refusal transcript. It is separate from
``validate_nemweb_genie.py --execute``, which submits benchmark SQL to a
warehouse and therefore cannot exercise a refusal: a refusal is a
natural-language response from the space, not a SQL result. The refusal
catalogue deliberately carries no ``sql_file``, so no refusal can reach the SQL
executor.

The command is read-only in the workspace. It starts a conversation, posts each
question and polls it to a terminal state. It never creates, updates or deletes
a space, warehouse, job or schedule. Genie responses are **not deterministic**,
so the output is evidence of behaviour on one run and must never become a
required CI gate.

Every workspace call carries an explicit profile. Nothing here prints or stores
a host, token, account or workspace identifier.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "genie" / "benchmark_questions.json"

PROFILE_REQUIRED_MESSAGE = (
    "workspace-aware capture requires an explicit --profile <name>; "
    "no implicit default profile is permitted"
)
# COMPLETED/FAILED/CANCELLED end the message. QUERY_RESULT_EXPIRED is terminal
# for our purposes too: the text remains readable but the attachment is gone.
TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"}

# A pass needs all four. Refusing is not sufficient: the exercise exists because
# "I cannot answer that" is worth little next to a refusal that names its rule.
ACCEPTANCE = (
    "refused",
    "named_a_governed_reason",
    "cited_no_invented_rule",
    "offered_the_supported_near_miss",
)


class DatabricksCLI:
    """Small injectable CLI adapter; every workspace call carries a profile."""

    def __init__(self, profile: str, runner: Callable[[list[str]], dict[str, Any]] | None = None):
        # Reject only absence, not a particular name, so no operator's workspace
        # name is embedded in this repository.
        if not profile or not profile.strip():
            raise ValueError(PROFILE_REQUIRED_MESSAGE)
        self.profile = profile
        self._runner = runner or self._run

    @staticmethod
    def _run(args: list[str]) -> dict[str, Any]:
        import subprocess

        completed = subprocess.run(args, capture_output=True, text=True, check=False)
        if completed.returncode:
            raise RuntimeError(
                f"Databricks CLI transport failed ({completed.returncode}): {completed.stderr.strip()}"
            )
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Databricks CLI returned non-JSON output") from exc

    def call(self, args: Sequence[str]) -> dict[str, Any]:
        return self._runner(["databricks", *args, "--profile", self.profile])

    def api(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        args = ["api", method, path]
        if payload is not None:
            args += ["--json", json.dumps(payload)]
        return self.call(args)


def load_refusals(path: Path = BENCHMARKS) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    refusals = document.get("refusals")
    if not refusals:
        raise ValueError("benchmark catalogue carries no refusals")
    return refusals


def load_near_miss_questions(path: Path = BENCHMARKS) -> dict[str, str]:
    """Map benchmark id -> question, so the answerable twin can be asked too."""
    document = json.loads(path.read_text(encoding="utf-8"))
    return {item["id"]: item["question"] for item in document.get("benchmarks", [])}


def _message_state(message: dict[str, Any]) -> str:
    state = message.get("status") or message.get("state")
    if isinstance(state, dict):
        state = state.get("state")
    if not isinstance(state, str):
        raise RuntimeError("Genie message response carries no status")
    return state


def _message_text(message: dict[str, Any]) -> str:
    """Collect every text fragment Genie returned, in order."""
    parts: list[str] = []
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        parts.append(content.strip())
    for attachment in message.get("attachments") or []:
        text = attachment.get("text")
        if isinstance(text, dict):
            text = text.get("content")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
        query = attachment.get("query")
        if isinstance(query, dict):
            for key in ("description", "query"):
                value = query.get(key)
                if isinstance(value, str) and value.strip():
                    parts.append(f"[{key}] {value.strip()}")
    return "\n\n".join(parts)


def ask(
    cli: DatabricksCLI,
    space_id: str,
    question: str,
    *,
    timeout_seconds: int,
    poll_seconds: float = 3.0,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Start a conversation, post one question, poll to a terminal state."""
    started = cli.api(
        "post", f"/api/2.0/genie/spaces/{space_id}/start-conversation", {"content": question}
    )
    message = started.get("message", started)
    conversation_id = message.get("conversation_id") or started.get("conversation_id")
    message_id = message.get("message_id") or message.get("id")
    if not conversation_id or not message_id:
        raise RuntimeError("Genie start-conversation returned no conversation or message id")

    deadline = time.monotonic() + timeout_seconds
    state = _message_state(message)
    while state not in TERMINAL_STATES:
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Genie message {message_id} did not reach a terminal state within {timeout_seconds}s"
            )
        sleep(poll_seconds)
        message = cli.api(
            "get",
            f"/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}",
        )
        state = _message_state(message)

    # A non-COMPLETED terminal state is recorded, not raised: a FAILED message is
    # itself a finding about the space, and discarding it would hide the result.
    return {
        "conversation_id": conversation_id,
        "message_id": message_id,
        "state": state,
        "response_text": _message_text(message),
        "attachment_count": len(message.get("attachments") or []),
    }


def build_record(refusal: dict[str, Any], asked: dict[str, Any]) -> dict[str, Any]:
    """One transcript row. Acceptance is left null for a human to score."""
    return {
        "refusal_id": refusal["id"],
        "question": refusal["question"],
        "unsupported_because": refusal["unsupported_because"],
        "contract_source": refusal["contract_source"],
        "contract_section": refusal["contract_section"],
        "contract_quote": refusal["contract_quote"],
        "expected_refusal_reason": refusal["refusal_reason"],
        "near_miss_of": refusal["near_miss_of"],
        "state": asked["state"],
        "response_text": asked["response_text"],
        "attachment_count": asked["attachment_count"],
        "conversation_id": asked["conversation_id"],
        "message_id": asked["message_id"],
        # Scored by a human against the four criteria. Left null deliberately:
        # deciding automatically whether a reason was "named" would be the same
        # unproven inference this exercise exists to prevent.
        "acceptance": {key: None for key in ACCEPTANCE},
        "reviewer_note": "",
    }


def evidence_document(
    records: list[dict[str, Any]], near_miss_records: list[dict[str, Any]], *, space_id_supplied: bool
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "genie-refusal-transcript",
        # The status of the material, stated in the artefact itself. Genie output
        # is one non-deterministic sample against whatever data the space reads.
        "evidence_status": "captured-from-deployed-space",
        "determinism": "non-deterministic; one sample per question, not a CI gate",
        "space_id_supplied_by_operator": space_id_supplied,
        "must_refuse": records,
        "answerable_near_miss_controls": near_miss_records,
        "acceptance_criteria": list(ACCEPTANCE),
        "scoring_note": (
            "Every acceptance field is null until a human scores it. A response that "
            "declines without naming a governed reason is a fail, not a pass."
        ),
    }


def render_markdown(document: dict[str, Any]) -> str:
    lines = [
        "# Genie refusal transcript",
        "",
        f"Evidence status: **{document['evidence_status']}**. "
        f"Determinism: {document['determinism']}.",
        "",
        "Acceptance requires all four: " + ", ".join(f"`{key}`" for key in document["acceptance_criteria"]) + ".",
        "",
    ]
    for record in document["must_refuse"]:
        lines += [
            f"## {record['refusal_id']} (`{record['unsupported_because']}`)",
            "",
            f"**Question.** {record['question']}",
            "",
            f"**Governed rule cited by the benchmark.** {record['contract_source']} "
            f"{record['contract_section']} — {record['contract_quote']}",
            "",
            f"**Terminal state.** `{record['state']}`",
            "",
            "**Response.**",
            "",
            "```text",
            record["response_text"] or "(no text returned)",
            "```",
            "",
            f"**Answerable near-miss.** `{record['near_miss_of']}` — must NOT be refused.",
            "",
            "**Scored.** " + ", ".join(f"{key}: _unscored_" for key in document["acceptance_criteria"]),
            "",
        ]
    if document["answerable_near_miss_controls"]:
        lines += ["## Answerable controls", ""]
        for record in document["answerable_near_miss_controls"]:
            lines += [
                f"### {record['benchmark_id']}",
                "",
                f"**Question.** {record['question']}",
                "",
                f"**Terminal state.** `{record['state']}`",
                "",
                "```text",
                record["response_text"] or "(no text returned)",
                "```",
                "",
            ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="Databricks CLI profile name")
    parser.add_argument(
        "--space-id",
        required=True,
        help="Genie space id to interrogate. Supplied by the operator; never inferred.",
    )
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument(
        "--include-near-miss-controls",
        action="store_true",
        help="also ask each answerable twin, to prove the space is not refusing on keywords",
    )
    parser.add_argument(
        "--only",
        action="append",
        help="restrict to one refusal id; repeatable. Default asks every refusal.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the questions that would be asked and exit without contacting the workspace",
    )
    args = parser.parse_args()

    if not args.profile.strip():
        parser.error(PROFILE_REQUIRED_MESSAGE)

    refusals = load_refusals()
    if args.only:
        wanted = set(args.only)
        unknown = wanted - {item["id"] for item in refusals}
        if unknown:
            parser.error(f"unknown refusal id(s): {sorted(unknown)}")
        refusals = [item for item in refusals if item["id"] in wanted]

    near_miss_questions = load_near_miss_questions()

    if args.dry_run:
        print(f"Dry run. Would ask {len(refusals)} must-refuse question(s); no workspace contact.")
        for item in refusals:
            print(f"  [{item['id']}] {item['question']}")
            if args.include_near_miss_controls:
                twin = item["near_miss_of"]
                print(f"      control [{twin}] {near_miss_questions.get(twin, '(missing)')}")
        return 0

    cli = DatabricksCLI(args.profile)
    records = [
        build_record(item, ask(cli, args.space_id, item["question"], timeout_seconds=args.timeout_seconds))
        for item in refusals
    ]

    near_miss_records: list[dict[str, Any]] = []
    if args.include_near_miss_controls:
        for benchmark_id in sorted({item["near_miss_of"] for item in refusals}):
            question = near_miss_questions.get(benchmark_id)
            if not question:
                continue
            asked = ask(cli, args.space_id, question, timeout_seconds=args.timeout_seconds)
            near_miss_records.append({"benchmark_id": benchmark_id, "question": question, **asked})

    document = evidence_document(records, near_miss_records, space_id_supplied=bool(args.space_id))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    if args.output_markdown:
        args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.output_markdown.write_text(render_markdown(document), encoding="utf-8")

    print(
        f"Captured {len(records)} must-refuse response(s) and "
        f"{len(near_miss_records)} answerable control(s). Every acceptance field is unscored; "
        "a human must score all four criteria per question."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
