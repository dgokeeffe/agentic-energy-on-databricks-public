"""NEMWEB-only facility dimension from monthly MMSDM registration tables."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.window import Window


@dp.materialized_view(
    name="silver_nem_facility_dimension",
    comment="Current NEMWEB MMSDM facility dimension. Region comes from DUDETAILSUMMARY; DUID-to-GENSETID from DUALLOC (fallback GENSETID=DUID); fuel comes from GENUNITS.CO2E_ENERGY_SOURCE. Unknown SCADA DUIDs survive with explicit dimension_match_status.",
    table_properties={"quality": "silver", "source.cadence": "monthly", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_facility_duid", "duid IS NOT NULL")
def silver_nem_facility_dimension():
    now = F.current_timestamp()
    detail_window = Window.partitionBy("duid").orderBy(
        F.col("start_date").desc_nulls_last(),
        F.col("source_publication_at").desc_nulls_last(),
        F.col("ingestion_sequence").desc_nulls_last(),
    )
    details = (
        spark.read.table("bronze_nem_dudetail")
        .where(
            (F.col("start_date") <= now)
            & (F.col("end_date").isNull() | (F.col("end_date") > now))
        )
        .withColumn("_rank", F.row_number().over(detail_window)).where(F.col("_rank") == 1).drop("_rank")
    )
    allocation_window = Window.partitionBy("duid").orderBy(
        F.col("effective_at").desc_nulls_last(), F.col("source_version_no").desc_nulls_last(),
        F.col("source_publication_at").desc_nulls_last(), F.col("ingestion_sequence").desc_nulls_last(),
    )
    allocations = (
        spark.read.table("bronze_nem_dualloc").where(F.col("effective_at") <= now)
        .withColumn("_rank", F.row_number().over(allocation_window)).where(F.col("_rank") == 1).drop("_rank")
    )
    generator_window = Window.partitionBy("genset_id").orderBy(
        F.col("source_last_changed").desc_nulls_last(),
        F.col("source_publication_at").desc_nulls_last(),
        F.col("landed_at").desc_nulls_last(),
        F.col("ingestion_sequence").desc_nulls_last(),
    )
    generators = (
        spark.read.table("bronze_nem_genunits")
        .withColumn("_rank", F.row_number().over(generator_window))
        .where(F.col("_rank") == 1).drop("_rank")
    )
    scada_duids = spark.read.table("bronze_nem_dispatch_unit_scada").select("duid").distinct()
    all_duids = scada_duids.unionByName(details.select("duid")).distinct().alias("base")
    joined = (
        all_duids.join(details.alias("d"), "duid", "left")
        .join(allocations.select("duid", "genset_id").alias("a"), "duid", "left")
        .withColumn("resolved_genset_id", F.coalesce(F.col("a.genset_id"), F.col("duid")))
        .join(generators.alias("g"), F.col("resolved_genset_id") == F.col("g.genset_id"), "left")
    )
    raw_fuel = F.trim(F.col("g.fuel_type_raw"))
    fuel = F.when(raw_fuel.isNull() | (raw_fuel == ""), F.lit("UNKNOWN")).otherwise(F.initcap(F.lower(raw_fuel)))
    region = F.coalesce(F.col("d.region_id"), F.lit("UNKNOWN"))
    return joined.select(
        F.col("duid"), region.alias("region_id"), F.col("d.station_id"),
        F.col("d.dispatch_type"), F.col("d.schedule_type"),
        F.col("resolved_genset_id").alias("genset_id"),
        F.col("g.genset_name"), raw_fuel.alias("fuel_type_raw"), fuel.alias("fuel_type"),
        F.col("g.registered_capacity_mw"), F.col("g.maximum_capacity_mw"),
        F.col("d.transmission_loss_factor"), F.col("d.distribution_loss_factor"),
        F.when((region != "UNKNOWN") & (fuel != "UNKNOWN"), "REGION_AND_FUEL")
        .when(region != "UNKNOWN", "REGION_ONLY")
        .when(fuel != "UNKNOWN", "FUEL_ONLY").otherwise("UNMATCHED").alias("dimension_match_status"),
        F.current_timestamp().alias("silver_published_at"),
    )
