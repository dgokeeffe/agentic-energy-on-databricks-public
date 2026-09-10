# Facilitator reference solution

This directory contains the completed NEMWEB implementation. The app-first
Delta landing provenance and exact eight-subject scope are recorded in
[`MIGRATION_MANIFEST.md`](MIGRATION_MANIFEST.md).

It is the authoritative Python project and Databricks Asset Bundle for
validation and deployment. Run the local checks below from this directory or
use the corresponding root Makefile targets.

## Local checks

Run these commands from `nemweb_foundation/`:

```bash
uv run --extra test python -m pytest
uv build --wheel --out-dir dist
uv run python scripts/validate_nemweb_snapshot.py
python3 scripts/check_modern_pipeline_apis.py
```

The repository root also provides Makefile targets for running the full suite
with `uv run --extra test python -m pytest` from the root.

## Bundle validation

The `dev` target creates the SQL warehouse and UC schemas and names them from
the authenticated CLI identity. Override with `BUNDLE_VAR_*` only when those
defaults are wrong, then run:

```bash
databricks bundle validate --strict -t dev --profile DEFAULT
```

Do not guess workspace identifiers or principal names. Validation does not
authorise deployment, a job run, or a schedule change.
