# Facilitator reference solution

This directory contains the completed NEMWEB implementation. The app-first
Delta landing provenance and exact eight-subject scope are recorded in
[`MIGRATION_MANIFEST.md`](MIGRATION_MANIFEST.md).

It is the
authoritative Python project and Databricks Asset Bundle for facilitator
validation and deployment. Workshop participants use `QUICKSTART.md` and their
assigned track; they do not work in this directory.

## Local checks

Run these commands from `nemweb_foundation/`:

```bash
uv run --extra test python -m pytest
uv build --wheel --out-dir dist
uv run python scripts/validate_nemweb_snapshot.py
python3 scripts/check_modern_pipeline_apis.py
```

The repository root also provides a small validation facade so facilitators and
CI can run the full suite with `uv run --extra test python -m pytest` from the
root.

## Bundle validation

Supply approved values through `BUNDLE_VAR_*` environment variables, then run:

```bash
databricks bundle validate --strict -t dev --profile DEFAULT
```

Do not guess workspace identifiers or principal names. Validation does not
authorise deployment, a job run, or a schedule change.
