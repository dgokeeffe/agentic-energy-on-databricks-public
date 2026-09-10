-- NEMWEB Unity Catalog semantics and relationship checks.
-- Run as a SQL file task with the named :catalog and :schema parameters.
-- Lakeflow materialized views do not support declarative PRIMARY KEY / FOREIGN KEY
-- constraints. Therefore this file validates candidate keys first and records the
-- logical, nullable DUID relationship in governed comments instead of emitting
-- unsupported or misleading constraint DDL. UNKNOWN enrichment is intentional.

USE CATALOG IDENTIFIER(:catalog);
USE SCHEMA IDENTIFIER(:schema);

-- Candidate-key gates. Failure stops the semantics job before metadata is changed.
SELECT assert_true(COUNT(*) = 0, 'gold_nem_region_dispatch_5min candidate key is not unique')
FROM (
  SELECT interval_end, region_id, intervention
  FROM gold_nem_region_dispatch_5min
  GROUP BY ALL HAVING COUNT(*) > 1
);
-- The spike view is already filtered to effective runs, so intervention is not
-- part of its key: one row per region and interval is the contract.
SELECT assert_true(COUNT(*) = 0, 'gold_nem_dispatch_price_spike_5min candidate key is not unique')
FROM (
  SELECT interval_end, region_id
  FROM gold_nem_dispatch_price_spike_5min
  GROUP BY ALL HAVING COUNT(*) > 1
);
SELECT assert_true(COUNT(*) = 0, 'gold_nem_unit_dispatch_5min candidate key is not unique')
FROM (
  SELECT interval_end, duid FROM gold_nem_unit_dispatch_5min
  GROUP BY ALL HAVING COUNT(*) > 1
);
SELECT assert_true(COUNT(*) = 0, 'gold_nem_scada_generation_5min candidate key is not unique')
FROM (
  SELECT interval_end, region_id, fuel_type FROM gold_nem_scada_generation_5min
  GROUP BY ALL HAVING COUNT(*) > 1
);
SELECT assert_true(COUNT(*) = 0, 'gold_nem_binding_constraints_5min candidate key is not unique')
FROM (
  SELECT interval_end, constraint_id, intervention
  FROM gold_nem_binding_constraints_5min
  GROUP BY ALL HAVING COUNT(*) > 1
);
SELECT assert_true(COUNT(*) = 0, 'gold_nem_interconnector_flows_5min candidate key is not unique')
FROM (
  SELECT interval_end, interconnector_id, intervention
  FROM gold_nem_interconnector_flows_5min
  GROUP BY ALL HAVING COUNT(*) > 1
);
SELECT assert_true(COUNT(*) = 0, 'gold_nem_unit_dispatch_availability_t1 candidate key is not unique')
FROM (
  SELECT interval_end, duid, intervention
  FROM gold_nem_unit_dispatch_availability_t1
  GROUP BY ALL HAVING COUNT(*) > 1
);
SELECT assert_true(COUNT(*) = 0, 'silver_nem_facility_dimension candidate key is not unique')
FROM (
  SELECT duid FROM silver_nem_facility_dimension
  GROUP BY ALL HAVING COUNT(*) > 1
);
SELECT assert_true(COUNT(*) = 0, 'gold_nem_bid_stack candidate key is not unique')
FROM (
  SELECT settlement_date, duid, bid_type, direction, period_id
  FROM gold_nem_bid_stack
  GROUP BY ALL HAVING COUNT(*) > 1
);

-- Registration context must be present in aggregate while retaining individual
-- aggregate/pseudo DUIDs whose governed fuel or region remains UNKNOWN.
SELECT assert_true(COUNT(*) = 0, 'registration enrichment unhealthy: an interval has all regions UNKNOWN')
FROM (
  SELECT interval_end
  FROM gold_nem_unit_dispatch_5min
  GROUP BY interval_end
  HAVING COUNT_IF(region_id <> 'UNKNOWN') = 0
);
SELECT assert_true(COUNT(*) = 0, 'registration enrichment unhealthy: an interval has all fuels UNKNOWN')
FROM (
  SELECT interval_end
  FROM gold_nem_unit_dispatch_5min
  GROUP BY interval_end
  HAVING COUNT_IF(fuel_type <> 'UNKNOWN') = 0
);

-- Informational relationship checks. Missing facility rows are allowed because the
-- five-minute path must retain unknown DUIDs instead of blocking publication.
SELECT
  COUNT_IF(f.duid IS NULL) AS unit_rows_without_facility_dimension,
  COUNT_IF(u.region_id = 'UNKNOWN' OR u.fuel_type = 'UNKNOWN') AS unit_rows_with_unknown_enrichment
FROM gold_nem_unit_dispatch_5min u
LEFT JOIN silver_nem_facility_dimension f USING (duid);
SELECT COUNT_IF(f.duid IS NULL) AS t1_rows_without_facility_dimension
FROM gold_nem_unit_dispatch_availability_t1 t
LEFT JOIN silver_nem_facility_dimension f USING (duid);

COMMENT ON TABLE gold_nem_region_dispatch_5min IS
  'Governed DISPATCHIS regional dispatch price and demand at five-minute interval-ending NEM market grain. Timestamps are AEST (UTC+10) with no daylight saving. Prices are AUD/MWh and demand/capacity values are MW. This is dispatch, not settlement. Both intervention runs are retained; default analytics use is_effective_run and must never aggregate runs blindly. source_publication_at and gold_published_at support freshness measurement.';
COMMENT ON COLUMN gold_nem_region_dispatch_5min.interval_end IS
  'End of the five-minute dispatch interval in NEM market time (AEST, UTC+10, no DST), not the interval start.';
COMMENT ON COLUMN gold_nem_region_dispatch_5min.intervention IS
  'AEMO intervention flag. Both values remain queryable; do not combine them without applying effective-run semantics.';
COMMENT ON COLUMN gold_nem_region_dispatch_5min.is_effective_run IS
  'True for the highest intervention flag present for interval and region, otherwise intervention 0. Governed metrics filter to true.';
COMMENT ON COLUMN gold_nem_region_dispatch_5min.rrp_aud_per_mwh IS
  'Regional reference dispatch price in Australian dollars per megawatt-hour; not a settlement price.';
COMMENT ON COLUMN gold_nem_region_dispatch_5min.total_demand_mw IS
  'Regional total demand in megawatts. Estimated interval energy is MW multiplied by 5/60 hours.';
COMMENT ON COLUMN gold_nem_region_dispatch_5min.source_publication_at IS
  'NEMWEB listing/HTTP publication timestamp captured by the lander; retrieval time is retained as an explicitly labelled fallback when the listing supplies no timestamp.';
COMMENT ON COLUMN gold_nem_region_dispatch_5min.gold_published_at IS
  'Timestamp when Lakeflow published this Gold row; compare with source_publication_at while respecting its source_publication_basis lineage.';

COMMENT ON TABLE gold_nem_dispatch_price_spike_5min IS
  'Governed relative dispatch-price spike flag at five-minute interval-ending AEST (UTC+10, no DST) grain, derived from effective runs of gold_nem_region_dispatch_5min. A spike is a price at or above spike_baseline_multiple times the median of the 288 intervals immediately preceding it for the same region; the judged interval is excluded from its own baseline. This is dispatch, not settlement. The threshold is an operator-supplied market judgement, not an AEMO market setting, and must not be cited as one. is_price_spike is NULL, never false, wherever no comparison could be made.';
COMMENT ON COLUMN gold_nem_dispatch_price_spike_5min.interval_end IS
  'End of the five-minute dispatch interval in NEM market time (AEST, UTC+10, no DST), not the interval start.';
COMMENT ON COLUMN gold_nem_dispatch_price_spike_5min.rrp_aud_per_mwh IS
  'Regional reference dispatch price in Australian dollars per megawatt-hour; not a settlement price.';
COMMENT ON COLUMN gold_nem_dispatch_price_spike_5min.is_price_spike IS
  'True when rrp_aud_per_mwh is at or above the trailing median times spike_baseline_multiple; the comparison is inclusive. NULL means no comparison was made, either because fewer than spike_baseline_intervals prior intervals exist for the region or because the trailing median is zero or negative, where the ratio is undefined or inverts. NULL is not false: do not read it as the absence of a spike, and do not coalesce it to false in aggregation.';
COMMENT ON COLUMN gold_nem_dispatch_price_spike_5min.trailing_median_price_aud_per_mwh IS
  'Median dispatch price over the 288 intervals immediately preceding this one for the same region, excluding this interval. NULL until the window is complete.';
COMMENT ON COLUMN gold_nem_dispatch_price_spike_5min.spike_baseline_intervals IS
  'Number of preceding intervals forming the baseline; 288 is 24 hours at five-minute grain. Recorded on every row so a flagged interval carries the rule that fired.';
COMMENT ON COLUMN gold_nem_dispatch_price_spike_5min.spike_baseline_multiple IS
  'Operator-supplied multiple of the trailing median at which a price is flagged. Sourced from the nemweb.spike_baseline_multiple pipeline setting, which has no default. Not an AEMO market setting.';
COMMENT ON COLUMN gold_nem_dispatch_price_spike_5min.price_formation_basis IS
  'How the price was formed: ADMINISTERED when an administered price cap applied, SUSPENDED when the market was suspended, otherwise MARKET. Administered and suspended prices are intervention artefacts, not market scarcity signals; separate them before reading a spike count as price risk.';
COMMENT ON COLUMN gold_nem_dispatch_price_spike_5min.is_effective_run IS
  'Always true. The view is filtered to effective runs, so its key is interval_end and region_id without intervention.';

COMMENT ON TABLE gold_nem_unit_dispatch_5min IS
  'Per-DUID actual SCADA output at five-minute interval-ending AEST grain. actual_generation_mw is measured output, never dispatch target or availability; Current NEMWEB publishes no five-minute unit availability. DUID has a logical nullable many-to-one relationship to silver_nem_facility_dimension. UNKNOWN region/fuel is retained by design. Estimated energy uses MW times 5/60 hours.';
COMMENT ON COLUMN gold_nem_unit_dispatch_5min.duid IS
  'AEMO Dispatchable Unit Identifier; logical nullable foreign key to silver_nem_facility_dimension.duid after uniqueness checking.';
COMMENT ON COLUMN gold_nem_unit_dispatch_5min.actual_generation_mw IS
  'Signed SCADA actual output in MW. Negative values can represent load or charging; this is not a dispatch target.';
COMMENT ON COLUMN gold_nem_unit_dispatch_5min.dimension_match_status IS
  'Facility enrichment status. UNKNOWN/UNMATCHED values are measurable quality context and rows are never dropped.';
COMMENT ON COLUMN gold_nem_unit_dispatch_5min.source_publication_at IS
  'NEMWEB listing/HTTP publication timestamp (or labelled retrieval fallback) for freshness and source-to-Gold lag.';

COMMENT ON TABLE gold_nem_scada_generation_5min IS
  'Signed actual SCADA MW aggregated by interval-ending five-minute AEST interval, region and AEMO fuel source. UNKNOWN dimensions are retained. This is actual output rather than dispatch target, availability or settlement energy. Energy measures multiply signed MW by 5/60 hours.';
COMMENT ON COLUMN gold_nem_scada_generation_5min.actual_generation_mw IS
  'Signed sum of per-DUID SCADA actual MW for the region/fuel group; storage/load values may be negative.';
COMMENT ON COLUMN gold_nem_scada_generation_5min.partially_enriched_facility_count IS
  'Count of source facilities without both governed region and fuel enrichment; non-zero values are visible quality context.';

COMMENT ON TABLE gold_nem_binding_constraints_5min IS
  'Binding DISPATCHIS constraints at interval-ending five-minute AEST grain. is_binding is explicitly derived as MARGINALVALUE <> 0 from the AEMO field meaning value of binding constraint. Both intervention runs remain; governed metrics filter is_effective_run.';
COMMENT ON COLUMN gold_nem_binding_constraints_5min.is_binding IS
  'Derived flag MARGINALVALUE <> 0; raw marginal_value, RHS, LHS and violation degree remain available.';
COMMENT ON COLUMN gold_nem_binding_constraints_5min.marginal_value IS
  'AEMO marginal value for the constraint; its source unit/interpretation is retained and it is not summed as energy or price.';

COMMENT ON TABLE gold_nem_interconnector_flows_5min IS
  'DISPATCHIS interconnector flow at interval-ending five-minute AEST grain. mw_flow preserves the AEMO source sign unchanged; positive and negative direction requires the interconnector definition and is never relabelled as import/export by inference. Both intervention runs remain; governed metrics filter is_effective_run.';
COMMENT ON COLUMN gold_nem_interconnector_flows_5min.mw_flow IS
  'Interconnector MW flow with AEMO source sign unchanged. Estimated signed energy is MW times 5/60 hours.';
COMMENT ON COLUMN gold_nem_interconnector_flows_5min.mw_losses IS
  'AEMO interconnector losses in MW at the dispatch interval.';
COMMENT ON COLUMN gold_nem_interconnector_flows_5min.is_effective_run IS
  'Effective intervention selection; use true by default to avoid duplicate physical intervals.';

COMMENT ON TABLE gold_nem_unit_dispatch_availability_t1 IS
  'Authoritative daily T+1 Next_Day_Dispatch UNIT_SOLUTION target and availability by five-minute interval end, DUID and intervention. It is not Current five-minute availability. Timestamps are NEM AEST (UTC+10, no DST). Both intervention rows remain and governed metrics filter is_effective_run. DUID has a logical nullable relationship to the monthly facility dimension.';
COMMENT ON COLUMN gold_nem_unit_dispatch_availability_t1.total_cleared_mw IS
  'Authoritative dispatch target (TOTALCLEARED) in MW, available only from daily T+1 source.';
COMMENT ON COLUMN gold_nem_unit_dispatch_availability_t1.availability_mw IS
  'Authoritative unit availability in MW from daily T+1 UNIT_SOLUTION; never present it as Current five-minute data.';
COMMENT ON COLUMN gold_nem_unit_dispatch_availability_t1.overlapping_scada_actual_mw IS
  'Five-minute SCADA actual MW joined only for reconciliation with the T+1 dispatch target.';
COMMENT ON COLUMN gold_nem_unit_dispatch_availability_t1.dimension_match_status IS
  'Monthly facility enrichment status. UNKNOWN enrichment remains queryable and does not block dispatch publication.';

COMMENT ON TABLE silver_nem_facility_dimension IS
  'Monthly NEMWEB MMSDM DUID dimension. Region is from DUDETAILSUMMARY; DUID-to-GENSETID from DUALLOC; fuel is GENUNITS.CO2E_ENERGY_SOURCE, never GENSETTYPE. One candidate row per DUID is checked before semantic publication; aggregate/pseudo DUIDs may retain UNKNOWN fuel.';
COMMENT ON COLUMN silver_nem_facility_dimension.duid IS
  'Candidate unique DUID used by logical, nullable Gold relationships; no FK is declared because unknown DUIDs must be retained.';
COMMENT ON COLUMN silver_nem_facility_dimension.fuel_type IS
  'Canonical AEMO CO2E_ENERGY_SOURCE classification, or UNKNOWN when the authoritative monthly source has no mapping.';

COMMENT ON TABLE gold_nem_bid_stack IS
  'Daily BIDMOVE_COMPLETE bid context at settlement date, DUID, bid type, direction and period. Price bands are AUD/MWh; band availability and maximum availability are MW. This slower context is not five-minute dispatch or settlement output and has independent source freshness.';
COMMENT ON COLUMN gold_nem_bid_stack.offer_interval_end IS
  'Interval-ending NEM market timestamp in AEST (UTC+10, no DST) when present.';
COMMENT ON COLUMN gold_nem_bid_stack.maximum_availability_mw IS
  'Offered maximum availability in MW from daily bid context; not actual SCADA output and not T+1 UNIT_SOLUTION availability.';
COMMENT ON COLUMN gold_nem_bid_stack.source_publication_at IS
  'Latest publication timestamp across joined day and period offers for source freshness.';
