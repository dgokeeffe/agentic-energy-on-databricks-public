# Agent instructions

This repository uses **Beads** for workshop task tracking. Beads is part of the
participant workflow and must be used for all implementation work.

## Start here

From a fresh clone, initialize the local participant graph:

```bash
scripts/bootstrap-participant-beads.sh
bd ready
```

Each participant laptop has its own local Beads database. There is no shared
Beads server in the workshop execution environment, so do not assume that a
claim or status update is visible to another laptop.

Read `.beads/README.md` for the participant Beads model.

## Beads workflow

1. Select an unblocked issue with `bd ready`.
2. Inspect it with `bd show <issue-id>`.
3. Claim it atomically:
   ```bash
   bd update <issue-id> --claim
   ```
4. Create a Git branch containing the Beads ID.
5. Implement the change and add or update tests.
6. Run the relevant deterministic checks.
7. Record evidence and the pull request URL in Beads:
   ```bash
   bd update <issue-id> --notes "Tests: <commands/results>. PR: <url>"
   ```
8. Do not close issues until the human review/merge gate is complete.

Git and Beads are separate, and Beads is local in the workshop:

- `git push` publishes code branches and pull requests.
- `bd update` records claims and evidence on the participant laptop only.
- The stable Beads ID must be included in the Git branch and pull request.
- The facilitator is the source of truth for team assignment and completion.
- `bd dolt push/pull` is optional organizer maintenance only, not a participant
  dependency.

## Safety boundaries

- Do not put credentials, tokens, workspace-specific secrets, or private tenant
  details in Git or Beads.
- Do not enable live data acquisition without facilitator approval.
- Do not create a source-specific Databricks Job or pipeline; extend the generic
  metadata-driven package instead.
- Do not merge or deploy workshop changes automatically.
- Do not close human review, merge, or deployment gates as an agent.

## Validation

For the local ETL package, run:

```bash
uv run --extra test python -m pytest
rm -rf dist && uv build --wheel --out-dir dist
```

For Databricks changes, use the direct-engine bundle and validate before
requesting deployment:

```bash
databricks bundle validate --strict -t dev
```

Use only an explicitly selected authenticated workspace/profile for deployment.
