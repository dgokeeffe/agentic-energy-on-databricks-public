# Databricks notebook source
# Serverless starter only. Resolve an immutable challenger model version at runtime.
import mlflow

mlflow.set_registry_uri("databricks-uc")
model_name = dbutils.widgets.get("model_name")
feature_table = dbutils.widgets.get("feature_table")
prediction_table = dbutils.widgets.get("prediction_table")

raise NotImplementedError(
    "Participant starter: resolve the challenger alias to a version, score the governed "
    "feature table, and MERGE idempotent rows into the parameterised prediction table."
)
