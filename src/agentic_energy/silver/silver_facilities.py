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

from agentic_energy.common.quality import (
    BASIS_DEGRADED_RETRIEVAL_FALLBACK,
    BASIS_LISTING_OR_HTTP,
    BASIS_UNKNOWN,
    MINIMUM_PUBLICATION_TO_LANDING_SECONDS,
)

# The three registration sources the dimension is built from. Coverage is
# governed by the weakest of them, so they are named once and iterated rather
# than listed again per aggregate.
_REGISTRATION_TABLES = ("bronze_nem_dudetail", "bronze_nem_dualloc", "bronze_nem_genunits")


def _registration_publication(table: str):
    """One row summarising how recent, and how trustworthy, a registration load is.

    Measured on the **unfiltered** Bronze frame. Computing it after the
    ``_rank == 1`` window below would describe the one surviving row rather than
    the load, and coverage is a property of the load.

    ``degraded`` carries both legs of the provenance guard described in
    ``quality.registration_coverage``: the declared basis, and the heuristic that
    a publication instant sitting implausibly close to ``landed_at`` was probably
    fabricated from our own retrieval. The second leg exists because
    ``io.section_stream`` currently stamps every row ``listing_or_http``, which
    makes the first leg inert for these tables.
    """

    frame = spark.read.table(table)
    publication_to_landing = F.abs(
        F.unix_timestamp("landed_at") - F.unix_timestamp("source_publication_at")
    )
    return frame.select(
        F.max("source_publication_at").alias("published_at"),
        F.max(
            F.when(
                (F.col("source_publication_basis") == "retrieval_fallback")
                | (publication_to_landing < MINIMUM_PUBLICATION_TO_LANDING_SECONDS),
                1,
            ).otherwise(0)
        ).alias("degraded"),
    )


def _registration_coverage(scada):
    """Publication-time distance between the SCADA priced and the registration held.

    Both operands are UTC lineage instants, so the subtraction never crosses the
    fixed-AEST market domain. ``registration_effective_at`` is market time and is
    deliberately **not** an operand here; differencing the two is the defect class
    this pipeline separates by convention.

    The behavioural contract, its rejected alternatives and its tests live in
    ``agentic_energy.common.quality.registration_coverage``. This is the Spark
    expression of the same rule, and ``test_facility_dimension_determinism.py``
    binds the two together so they cannot drift.
    """

    legs = None
    for table in _REGISTRATION_TABLES:
        leg = _registration_publication(table)
        legs = leg if legs is None else legs.unionByName(leg)

    weakest = legs.select(
        # The oldest publication wins: GENUNITS alone supplies fuel, so a stalled
        # GENUNITS load must not be masked by a fresh DUDETAILSUMMARY.
        F.min("published_at").alias("registration_publication_at"),
        # count() skips NULLs, so a source that produced no publication instant at
        # all is detected here rather than silently dropping out of the min above.
        F.count("published_at").alias("_legs_with_publication"),
        F.max("degraded").alias("_degraded"),
    )

    unassessable = (
        F.col("scada_publication_at").isNull()
        | F.col("registration_publication_at").isNull()
    )
    return scada.select(F.max("source_publication_at").alias("scada_publication_at")).crossJoin(weakest).select(
        F.col("registration_publication_at"),
        # NULL, never 0, on a cold schema: zero would read as perfect coverage on
        # a schema holding nothing, exactly as the COALESCE floor below avoids
        # reading an empty dimension as a missing table.
        F.when(unassessable, F.lit(None).cast("long"))
        .otherwise(
            F.unix_timestamp("scada_publication_at") - F.unix_timestamp("registration_publication_at")
        )
        .alias("registration_coverage_seconds"),
        F.when(unassessable, F.lit(BASIS_UNKNOWN))
        .when(
            (F.col("_degraded") == 1) | (F.col("_legs_with_publication") < len(_REGISTRATION_TABLES)),
            F.lit(BASIS_DEGRADED_RETRIEVAL_FALLBACK),
        )
        .otherwise(F.lit(BASIS_LISTING_OR_HTTP))
        .alias("registration_coverage_basis"),
    )


@dp.materialized_view(
    name="silver_nem_facility_dimension",
    comment="NEMWEB MMSDM facility dimension, effective at the maximum SCADA interval in Bronze rather than at wall-clock time, so a refresh is reproducible from its inputs. Region comes from DUDETAILSUMMARY; DUID-to-GENSETID from DUALLOC (fallback GENSETID=DUID); fuel comes from GENUNITS.CO2E_ENERGY_SOURCE. Unknown SCADA DUIDs survive with explicit dimension_match_status. registration_coverage_seconds is the UTC publication-time distance from the SCADA being attributed to the weakest of the three monthly registration loads; it is signed, is NULL when either instant is absent, and is attribution provenance only, never an availability or curtailment claim.",
    table_properties={"quality": "silver", "source.cadence": "monthly", "registration.effective_at": "max_bronze_scada_interval", "registration.coverage": "utc_publication_delta", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
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
        # Publish how stale the registration context itself is. The pinned instant
        # above says which window was used; it cannot say whether the registration
        # data describing that window is current, because it is derived from SCADA
        # rather than from the monthly registration load.
        .crossJoin(_registration_coverage(scada))
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
        # Attribution provenance: how far the registration context lags the SCADA
        # being attributed, in UTC publication time. Says nothing about output,
        # availability or curtailment.
        F.col("registration_publication_at"),
        F.col("registration_coverage_seconds"),
        F.col("registration_coverage_basis"),
        # Processing time, not a filter. Unlike the effective instant above, this
        # only labels when the row was written and never decides which rows exist.
        F.current_timestamp().alias("silver_published_at"),
    )
