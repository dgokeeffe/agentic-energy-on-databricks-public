# NEMWEB ML starter

This starter supports participant issues #15–#17. The checked-in July 2026
fixture is deterministic prepared data derived from the workshop schema. It is
too small to establish historical completeness, class balance, calibration, or
predictive value. Passing its tests does not prove that a model is useful.

The contracts require one row per region and prediction time, features no newer
than prediction time, future labels, and strictly chronological train,
validation, and held-out test periods. Batch rows include immutable model
version, feature and scoring times, source freshness, and missing-feature
status. Missing or stale input cannot produce an apparently current score.

Training and scoring are manual serverless Databricks Job shells. Supply the
MLflow experiment, three-level Unity Catalog model name, historical table,
feature table, and prediction table through bundle variables. A real run must
pass historical completeness and leakage checks before registering an artifact
or setting `@challenger`. This starter never changes `@prod` and defines no
Model Serving endpoint.

## Participant ticket entry points

| Issue | Start with | Named deterministic checks |
|---|---|---|
| #15 leakage-safe training set | `src/nemweb_ml/features.py`, `src/nemweb_ml/split.py`, `tests/fixtures/history.json` | `test_leakage.py`, `test_split.py`, `test_schema.py` |
| #16 tracked challenger | `notebooks/train.py`, `src/nemweb_ml/train.py`, `resources/nemweb_training.job.yml` | `test_bundle_resources.py`; execution remains serverless-only |
| #17 governed batch scoring | `notebooks/batch_score.py`, `src/nemweb_ml/batch_score.py`, `sql/gold_nem_predictions.sql` | `test_batch_score.py`, `test_schema.py` |

```bash
uv sync --extra test
uv run python -m pytest tests -q
databricks bundle validate --strict -t dev --profile DEFAULT
```

Training, model registration, and scoring have not been run by the repository
fixture. Source history dates, completeness, and AEMO attribution must be
recorded before a facilitator authorises execution.
