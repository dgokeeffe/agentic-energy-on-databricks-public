"""Serverless MLflow orchestration helpers; never run training on import."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .contracts import validate_training_rows
from .split import chronological_split


def validate_training_eligibility(rows: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    validated = validate_training_rows(rows)
    return chronological_split(validated)


def configure_mlflow(experiment_name: str) -> Any:
    if not experiment_name:
        raise ValueError("MLflow experiment name is mandatory")
    import mlflow

    mlflow.set_registry_uri("databricks-uc")
    mlflow.set_experiment(experiment_name)
    return mlflow


def register_challenger(*, model_uri: str, model_name: str, eligible_run_id: str) -> Any:
    if not all((model_uri, model_name, eligible_run_id)) or model_name.count(".") != 2:
        raise ValueError("an eligible run and three-level Unity Catalog model name are mandatory")
    mlflow = configure_mlflow(f"/Shared/nemweb/{eligible_run_id}")
    registered = mlflow.register_model(model_uri=model_uri, name=model_name)
    client = mlflow.MlflowClient()
    client.set_registered_model_alias(model_name, "challenger", registered.version)
    return registered
