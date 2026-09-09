"""NEMWEB-only facility dimension from monthly MMSDM registration tables.

Registration validity is evaluated at a **pinned instant derived from the data**,
never at wall-clock time.

This view previously used ``F.current_timestamp()`` inside the ``WHERE`` clause
that selects the effective DUDETAILSUMMARY and DUALLOC rows. That made the view
non-reproducible: the same Bronze data yielded different Silver rows depending on
when the refresh happened to run. Every DUID in the governed snapshot carries two
registration periods, so a refresh either side of a period boundary silently
re-attributed five-minute generation to a different region or fuel, with no code
change, no new source file, and no failing expectation.

That matters downstream because ``gold_nem_scada_generation_5min`` groups by
``region_id`` and ``fuel_type``. Moving a DUID between buckets moves revenue and
capture figures computed from it, while every value stays plausible.

The pinned instant is the **maximum SCADA interval present in Bronze**, so the
dimension answers "which registration applied to the market intervals this data
describes", which is the correct semantics as well as a reproducible one. It is
derived rather than configured so it cannot go stale, and it keeps the view a pure
function of its inputs.

See ``miniwiki/decisions/facility-dimension-as-of.md``.
"""

from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.window import Window


@dp.materialized_view(
    name="silver_nem_facility_dimension",
    comment="NEMWEB MMSDM facility dimension, effective at the maximum SCADA interval in Bronze rather than at wall-clock time, so a refresh is reproducible from its inputs. Region comes from DUDETAILSUMMARY; DUID-to-GENSETID from DUALLOC (fallback GENSETID=DUID); fuel comes from GENUNITS.CO2E_ENERGY_SOURCE. Unknown SCADA DUIDs survive with explicit dimension_match_status.",
    table_properties={"quality": "silver", "source.cadence": "monthly", "registration.effective_at": "max_bronze_scada_interval", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_facility_duid", "duid IS NOT NULL")
def silver_nem_facility_dimension():
    scada = spark.read.table("bronze_nem_dispatch_unit_scada")
    # Pinned, data-derived effective instant. Cross-joining one row keeps this a
    # scalar in the plan without collecting to the driver.
    #
    # The COALESCE floor matters: on a cold or SCADA-empty schema the max is NULL,
    # which would make every `start_date <= NULL` comparison NULL and silently
    # empty the dimension. Falling back to the earliest representable instant
    # instead yields UNKNOWN enrichment, which is visible in
    # dimension_match_status rather than appearing as a missing table.
    as_of = scada.select(
        F.coalesce(F.max("interval_end"), F.lit("1900-01-01").cast("timestamp")).alias("as_of")
    )
    now = F.col("as_of")
    detail_window = Window.partitionBy("duid").orderBy(
        F.col("start_date").desc_nulls_last(),
        F.col("source_publication_at").desc_nulls_last(),
        F.col("ingestion_sequence").desc_nulls_last(),
    )
    details = (
        spark.read.table("bronze_nem_dudetail")
        .crossJoin(as_of)
        .where(
            (F.col("start_date") <= now)
            & (F.col("end_date").isNull() | (F.col("end_date") > now))
        )
        .drop("as_of")
        .withColumn("_rank", F.row_number().over(detail_window)).where(F.col("_rank") == 1).drop("_rank")
    )
    allocation_window = Window.partitionBy("duid").orderBy(
        F.col("effective_at").desc_nulls_last(), F.col("source_version_no").desc_nulls_last(),
        F.col("source_publication_at").desc_nulls_last(), F.col("ingestion_sequence").desc_nulls_last(),
    )
    allocations = (
        spark.read.table("bronze_nem_dualloc")
        .crossJoin(as_of)
        .where(F.col("effective_at") <= now)
        .drop("as_of")
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
    scada_duids = scada.select("duid").distinct()
    all_duids = scada_duids.unionByName(details.select("duid")).distinct().alias("base")
    joined = (
        all_duids.join(details.alias("d"), "duid", "left")
        .join(allocations.select("duid", "genset_id").alias("a"), "duid", "left")
        .withColumn("resolved_genset_id", F.coalesce(F.col("a.genset_id"), F.col("duid")))
        .join(generators.alias("g"), F.col("resolved_genset_id") == F.col("g.genset_id"), "left")
        # Publish the pinned instant so an operator can read which registration
        # window a refresh actually used, instead of inferring it from the clock.
        .crossJoin(as_of.withColumnRenamed("as_of", "registration_effective_at"))
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
        F.col("registration_effective_at"),
        # Processing time, not a filter. Unlike the effective instant above, this
        # only labels when the row was written and never decides which rows exist.
        F.current_timestamp().alias("silver_published_at"),
    )
