---
name: agentic-verification
description: Use when implementing or reviewing non-trivial changes that need deterministic tests, adversarial subagent review, generated edge-case tests, regression analysis, or verification gates. Trigger for requests about verification, test generation, fuzzing, review loops, quality gates, or proving an agent-produced change is correct.
---

# Agentic verification

Use layered evidence. A model's confidence, a passing happy-path test, or a reviewer saying "looks good" is not proof.

## Verification contract

Before implementation, define:

- user-visible outcome
- invariants and non-goals
- deterministic commands and expected evidence
- representative end-to-end behaviour
- likely malformed, boundary, security, ordering, timezone, retry, and idempotency cases
- what must be reproduced before a fuzzy finding becomes blocking

Attach the contract to the pull request, the applicable miniwiki page, or
another committed Markdown artifact.

## Verification sequence

Use direct prompts for short work, async subagents for parallel work or long
waits, and start a fresh goal at milestone boundaries when context or cache
cost requires it. Keep the sequence visible in the pull request or named
Markdown artifact:

```text
acceptance contract → impact map → deterministic test plan → implementation
→ deterministic validation → independent reviews → finding reproduction
→ finding resolution → final adjudication
```

The parent or orchestrator owns the sequence. Children report evidence and do
not redefine completion. Git and committed Markdown carry continuation state;
no local issue database is required.

## Deterministic lane

The deterministic verifier must run real commands and capture:

- exact command
- exit code
- raw or saved output
- test/lint/type-check/build counts
- environment or fixture assumptions
- artifact path

Prefer property-based, mutation, golden-fixture, differential, contract, malformed-input, concurrency, and idempotency tests when ordinary examples are insufficient. A test-generation agent may write tests, but a separate deterministic run is the verdict.

## Fuzzy lane

Use a review squad scaled to change size, not a fixed swarm:

- small change: 2 reviewers
- normal feature: 3-5 reviewers
- high-risk or cross-cutting change: 6-9 reviewers

Choose one primary reviewer/adjudicator. Do not request a crowd of reviewers for a small diff. Keep the change scoped; mixed refactors, formatting churn, unrelated features, or multiple languages make both human and agent review less reliable. Require a test plan and security impact analysis when applicable.

Use fresh-context reviewers with distinct prompts and, when useful, different models/providers:

1. **Requirements adversary** — find ways the implementation can pass tests while violating intent.
2. **Edge-case generator** — propose executable tests for boundaries, malformed inputs, partial failures, retries, duplicates, and empty data.
3. **Security/data reviewer** — inspect identity, authorization, leakage, silent data loss, ordering, timezone, and idempotency.
4. **Regression-impact reviewer** — trace callers, dependants, fixtures, and affected tests.

Every finding must include severity, file/line evidence, why it matters, and a proposed reproduction. A fuzzy finding is a hypothesis until a deterministic reproduction succeeds, except when the strong adjudicator marks it as a human-decision risk.

Dispatch the squad in one parallel subagent call so the reviewers remain independent. Prefer the named roles `requirements-reviewer`, `edge-case-reviewer`, `security-data-reviewer`, and `regression-reviewer`; use the generic `reviewer` only when a custom lens is needed. Give every reviewer the same acceptance contract and diff scope, but a different lens. Request structured findings, not general commentary. Save each result to an artifact, deduplicate by file/line and claim, then record
surviving findings in the pull request or applicable miniwiki page. Re-request
review after fixes rather than treating the first pass as final.

## PR and human-review gate

For repositories with a PR workflow, create or update the PR only after
deterministic validation and the fuzzy findings have been reduced. The PR
description must link the acceptance contract, test plan, command results,
review artifacts, reproduced findings, and remaining risks. Request a primary
human reviewer, wait for approval or requested changes, then address comments
and re-run affected checks. Do not merge until the human review gate is
satisfied. If the repository has no remote or PR workflow, produce the
equivalent branch/diff and evidence pack for explicit human review instead.

## Adjudication

Use `verification-adjudicator` for final reduction and acceptance decisions; it is pinned to Opus. Escalate directly to Sol/Opus for architecture, security, data correctness, conflicting reviews, failed review rounds, or final acceptance of high-risk work. Do not use majority vote between identical prompts; independent angles are more valuable than agent count.

Finish the verification sequence only when the evidence is recorded and no
reproducible high-severity finding remains open. Keep the limitation explicit:
every verifier is a proxy for intent, so combine requirement evidence,
execution evidence, independent challenge, reproduction, and adjudication.

## Handoff format

Return:

```text
Verification status: pass | fail | blocked | conditional
Deterministic commands and results:
Fuzzy findings and reproduction status:
Open risks:
Follow-up items recorded:
Artifacts:
Recommended next action:
```
