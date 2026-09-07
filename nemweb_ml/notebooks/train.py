# Databricks notebook source
# Serverless starter only. Historical completeness and leakage gates run before registration.
from nemweb_ml.train import configure_mlflow, validate_training_eligibility

experiment_name = dbutils.widgets.get("experiment_name")
model_name = dbutils.widgets.get("model_name")
training_table = dbutils.widgets.get("training_table")

mlflow = configure_mlflow(experiment_name)
rows = [row.asDict(recursive=True) for row in spark.read.table(training_table).collect()]
train_rows, validation_rows, test_rows = validate_training_eligibility(rows)

raise NotImplementedError(
    "Participant starter: train and compare an interpretable baseline on the approved "
    "chronological splits before registering model_name with the challenger alias."
)
