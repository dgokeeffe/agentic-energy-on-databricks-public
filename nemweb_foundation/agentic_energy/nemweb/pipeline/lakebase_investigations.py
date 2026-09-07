"""Lakeflow current state over immutable Lakebase CDF investigation history."""

from pyspark import pipelines as dp
from pyspark.sql import Window
from pyspark.sql import functions as F

_HISTORY_TABLE = spark.conf.get("nemweb.lakebase_cdf_history_table")


@dp.materialized_view(
    name="silver_nem_investigations_current",
    comment=(
        "Deterministic current state derived from immutable Lakebase CDF history. "
        "Update preimages remain in source audit history, and deletes remove only current rows."
    ),
    table_properties={"quality": "silver", "source.system": "lakebase_cdf"},
)
@dp.expect_or_drop(
    "valid_investigation_current_key",
    "investigation_id IS NOT NULL AND region_id IS NOT NULL AND interval_end IS NOT NULL",
)
def silver_nem_investigations_current():
    history = spark.read.table(_HISTORY_TABLE)
    change_rank = (
        F.when(F.col("_pg_change_type") == "update_preimage", F.lit(0))
        .when(F.col("_pg_change_type") == "insert", F.lit(1))
        .when(F.col("_pg_change_type") == "update_postimage", F.lit(2))
        .when(F.col("_pg_change_type") == "delete", F.lit(3))
        .otherwise(F.lit(-1))
    )
    lsn_text = F.col("_pg_lsn").cast("string")
    lsn_parts = F.split(lsn_text, "/")
    lsn_order = F.when(
        F.instr(lsn_text, "/") > 0,
        F.conv(lsn_parts.getItem(0), 16, 10).cast("decimal(38,0)") * F.lit(4294967296)
        + F.conv(lsn_parts.getItem(1), 16, 10).cast("decimal(38,0)"),
    ).otherwise(lsn_text.cast("decimal(38,0)"))
    stable_tie_breaker = F.sha2(
        F.concat_ws(
            "|",
            F.col("investigation_id").cast("string"),
            F.col("version").cast("string"),
            F.col("status").cast("string"),
            F.col("decision").cast("string"),
            F.col("evidence_reference").cast("string"),
        ),
        256,
    )
    latest = Window.partitionBy("investigation_id").orderBy(
        F.col("_sort_by").desc(),
        lsn_order.desc(),
        F.col("_timestamp").desc(),
        F.col("_pg_xid").desc(),
        change_rank.desc(),
        stable_tie_breaker.desc(),
    )
    return (
        history.withColumn("_timestamp", F.col("_timestamp").cast("timestamp"))
        .withColumn("_current_rank", F.row_number().over(latest))
        .where(F.col("_current_rank") == 1)
        .where(~F.col("_pg_change_type").isin("delete", "update_preimage"))
        .drop("_current_rank")
    )
