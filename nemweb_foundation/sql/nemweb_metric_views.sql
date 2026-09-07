-- Governed NEMWEB metric views. This file is executed after nemweb_semantics.sql.
-- The job sets the target namespace through named SQL parameters so no workspace,
-- tenant or catalog identifier is committed in this repository.

USE CATALOG IDENTIFIER(:catalog);
USE SCHEMA IDENTIFIER(:schema);

CREATE OR REPLACE VIEW nem_region_dispatch_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: gold_nem_region_dispatch_5min
filter: is_effective_run = true
comment: "Effective-run regional DISPATCHIS metrics at interval-ending five-minute AEST (UTC+10, no DST) grain. Prices are dispatch AUD/MWh, not settlement; demand is MW. Source and Gold publication dimensions support freshness analysis."
dimensions:
  - name: interval_end
    expr: interval_end
    comment: "End of the five-minute NEM dispatch interval in fixed AEST, never interval start."
  - name: region_id
    expr: region_id
    comment: "AEMO NEM region."
  - name: intervention
    expr: intervention
    comment: "Retained for audit; global effective-run filter prevents intervention double counting."
  - name: source_publication_at
    expr: source_publication_at
    comment: "AEMO publication time; compare separately with Gold publication time for freshness."
  - name: gold_published_at
    expr: gold_published_at
    comment: "Lakeflow Gold publication time."
measures:
  - name: average_dispatch_price_aud_per_mwh
    expr: AVG(rrp_aud_per_mwh)
    comment: "Average regional dispatch price in AUD/MWh; never settlement price."
  - name: maximum_dispatch_price_aud_per_mwh
    expr: MAX(rrp_aud_per_mwh)
    comment: "Maximum regional dispatch price in AUD/MWh."
  - name: average_total_demand_mw
    expr: AVG(total_demand_mw)
    comment: "Average regional total demand in MW."
  - name: estimated_demand_energy_mwh
    expr: SUM(total_demand_mw) * 5.0 / 60.0
    comment: "Estimated demand energy in MWh: each effective five-minute MW observation times 5/60 hours."
  - name: five_minute_interval_count
    expr: COUNT(1)
    comment: "Effective regional five-minute observations."
$$;

CREATE OR REPLACE VIEW nem_unit_output_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: gold_nem_unit_dispatch_5min
comment: "Per-DUID Current SCADA actual-output metrics at interval-ending five-minute AEST grain. This is measured MW, never dispatch target or availability. UNKNOWN facility enrichment is retained."
joins:
  - name: facility
    source: silver_nem_facility_dimension
    "on": source.duid = facility.duid
dimensions:
  - name: interval_end
    expr: source.interval_end
    comment: "End of the five-minute NEM interval in fixed AEST (UTC+10, no DST)."
  - name: duid
    expr: source.duid
    comment: "AEMO DUID; nullable many-to-one join to the uniqueness-checked monthly facility dimension."
  - name: region_id
    expr: source.region_id
    comment: "Governed region or UNKNOWN; unknown rows remain in all measures."
  - name: fuel_type
    expr: source.fuel_type
    comment: "AEMO CO2E energy source or UNKNOWN; never inferred from GENSETTYPE."
  - name: station_id
    expr: facility.station_id
    comment: "Monthly NEMWEB station identifier when the optional facility relationship resolves."
  - name: dimension_match_status
    expr: source.dimension_match_status
    comment: "Measurable facility-enrichment result."
  - name: source_publication_at
    expr: source.source_publication_at
    comment: "AEMO SCADA source publication time for freshness."
  - name: gold_published_at
    expr: source.gold_published_at
    comment: "Lakeflow Gold publication time for processing lag."
measures:
  - name: average_actual_generation_mw
    expr: AVG(source.actual_generation_mw)
    comment: "Average signed SCADA actual output in MW, not a dispatch target."
  - name: maximum_actual_generation_mw
    expr: MAX(source.actual_generation_mw)
    comment: "Maximum signed SCADA actual output in MW."
  - name: estimated_actual_energy_mwh
    expr: SUM(source.actual_generation_mw) * 5.0 / 60.0
    comment: "Estimated signed actual energy in MWh from five-minute SCADA MW observations."
  - name: unit_interval_count
    expr: COUNT(1)
    comment: "DUID five-minute observations, including UNKNOWN enrichment."
$$;

CREATE OR REPLACE VIEW nem_scada_generation_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: gold_nem_scada_generation_5min
comment: "Signed actual SCADA output grouped by region and AEMO fuel at interval-ending five-minute AEST grain. UNKNOWN dimensions remain; output is not dispatch target, availability or settlement energy."
dimensions:
  - name: interval_end
    expr: interval_end
    comment: "End of the five-minute NEM interval in fixed AEST (UTC+10, no DST)."
  - name: region_id
    expr: region_id
    comment: "AEMO region or UNKNOWN."
  - name: fuel_type
    expr: fuel_type
    comment: "AEMO CO2E energy source or UNKNOWN."
  - name: source_publication_at
    expr: source_publication_at
    comment: "Latest AEMO SCADA publication for the grouped row."
  - name: gold_published_at
    expr: gold_published_at
    comment: "Lakeflow Gold publication time for freshness lag."
measures:
  - name: average_actual_generation_mw
    expr: AVG(actual_generation_mw)
    comment: "Average signed actual output in MW across selected grouped observations."
  - name: estimated_actual_energy_mwh
    expr: SUM(actual_generation_mw) * 5.0 / 60.0
    comment: "Estimated signed MWh: five-minute actual MW times 5/60 hours."
  - name: partially_enriched_observation_count
    expr: SUM(CASE WHEN partially_enriched_facility_count > 0 THEN 1 ELSE 0 END)
    comment: "Grouped observations containing at least one facility without both region and fuel mappings."
$$;

CREATE OR REPLACE VIEW nem_binding_constraint_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: gold_nem_binding_constraints_5min
filter: is_effective_run = true
comment: "Effective-run binding DISPATCHIS constraint metrics at interval-ending five-minute AEST grain. Binding is the documented MARGINALVALUE <> 0 derivation; raw values remain available."
dimensions:
  - name: interval_end
    expr: interval_end
    comment: "End of the five-minute dispatch interval in fixed AEST."
  - name: constraint_id
    expr: constraint_id
    comment: "AEMO generic constraint identifier."
  - name: intervention
    expr: intervention
    comment: "Retained for audit; effective-run filter prevents duplicate physical intervals."
  - name: source_publication_at
    expr: source_publication_at
    comment: "AEMO publication time for source freshness."
  - name: gold_published_at
    expr: gold_published_at
    comment: "Lakeflow Gold publication time."
measures:
  - name: binding_constraint_interval_count
    expr: COUNT(1)
    comment: "Effective rows where derived is_binding is true."
  - name: distinct_binding_constraint_count
    expr: COUNT(DISTINCT constraint_id)
    comment: "Distinct AEMO constraints binding in the selected interval range."
  - name: average_marginal_value
    expr: AVG(marginal_value)
    comment: "Average raw AEMO marginal value; not an additive price or energy measure."
  - name: maximum_violation_degree
    expr: MAX(violation_degree)
    comment: "Maximum raw constraint violation degree in the selection."
$$;

CREATE OR REPLACE VIEW nem_interconnector_flow_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: gold_nem_interconnector_flows_5min
filter: is_effective_run = true
comment: "Effective-run DISPATCHIS interconnector flow at interval-ending five-minute AEST grain. MW flow preserves AEMO source sign; no import/export direction is inferred."
dimensions:
  - name: interval_end
    expr: interval_end
    comment: "End of the five-minute dispatch interval in fixed AEST."
  - name: interconnector_id
    expr: interconnector_id
    comment: "AEMO interconnector identifier needed to interpret source-sign direction."
  - name: intervention
    expr: intervention
    comment: "Retained for audit; effective-run filter prevents double counting."
  - name: source_publication_at
    expr: source_publication_at
    comment: "AEMO publication time for freshness."
  - name: gold_published_at
    expr: gold_published_at
    comment: "Lakeflow Gold publication time."
measures:
  - name: average_source_sign_flow_mw
    expr: AVG(mw_flow)
    comment: "Average MW flow preserving AEMO source sign."
  - name: estimated_source_sign_flow_mwh
    expr: SUM(mw_flow) * 5.0 / 60.0
    comment: "Estimated signed MWh: five-minute source-sign MW times 5/60 hours."
  - name: average_losses_mw
    expr: AVG(mw_losses)
    comment: "Average AEMO interconnector losses in MW."
  - name: estimated_losses_mwh
    expr: SUM(mw_losses) * 5.0 / 60.0
    comment: "Estimated loss energy in MWh from five-minute loss MW observations."
$$;

CREATE OR REPLACE VIEW nem_unit_availability_t1_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: gold_nem_unit_dispatch_availability_t1
filter: is_effective_run = true
comment: "Effective-run authoritative daily T+1 UNIT_SOLUTION target and availability metrics at interval-ending AEST grain. This asset must never be described as Current five-minute availability; SCADA actual is present only for reconciliation."
dimensions:
  - name: interval_end
    expr: interval_end
    comment: "Five-minute interval end represented in the daily T+1 publication, fixed AEST."
  - name: duid
    expr: duid
    comment: "AEMO Dispatchable Unit Identifier."
  - name: region_id
    expr: region_id
    comment: "Monthly facility region or UNKNOWN."
  - name: fuel_type
    expr: fuel_type
    comment: "AEMO CO2E energy source or UNKNOWN."
  - name: intervention
    expr: intervention
    comment: "Retained for audit; effective-run filter prevents target double counting."
  - name: source_publication_at
    expr: source_publication_at
    comment: "Daily T+1 source publication time; source lag is separate from pipeline cadence."
  - name: gold_published_at
    expr: gold_published_at
    comment: "Lakeflow Gold publication time."
measures:
  - name: average_dispatch_target_mw
    expr: AVG(total_cleared_mw)
    comment: "Average authoritative T+1 TOTALCLEARED dispatch target in MW."
  - name: average_availability_mw
    expr: AVG(availability_mw)
    comment: "Average authoritative T+1 availability in MW, never Current availability."
  - name: estimated_dispatched_energy_mwh
    expr: SUM(total_cleared_mw) * 5.0 / 60.0
    comment: "Estimated target energy in MWh from T+1 five-minute targets."
  - name: mean_absolute_scada_target_variance_mw
    expr: AVG(absolute_scada_dispatch_variance_mw)
    comment: "Mean absolute difference in MW between overlapping SCADA actual and T+1 target."
$$;

CREATE OR REPLACE VIEW nem_bid_availability_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: gold_nem_bid_stack
comment: "Daily BIDMOVE_COMPLETE bid availability context. Price bands are AUD/MWh and availability bands are MW. This is offered context, not five-minute dispatch, SCADA actual, T+1 availability or settlement."
dimensions:
  - name: settlement_date
    expr: settlement_date
    comment: "AEMO bid settlement date; daily source cadence."
  - name: offer_interval_end
    expr: offer_interval_end
    comment: "Interval end in fixed NEM AEST (UTC+10, no DST) when supplied."
  - name: duid
    expr: duid
    comment: "AEMO Dispatchable Unit Identifier."
  - name: bid_type
    expr: bid_type
    comment: "AEMO bid service/type."
  - name: direction
    expr: direction
    comment: "AEMO offer direction."
  - name: source_publication_at
    expr: source_publication_at
    comment: "Latest source publication across joined day and period offers."
  - name: gold_published_at
    expr: gold_published_at
    comment: "Lakeflow Gold publication time for freshness."
measures:
  - name: average_maximum_offer_availability_mw
    expr: AVG(maximum_availability_mw)
    comment: "Average offered maximum availability in MW; not UNIT_SOLUTION availability."
  - name: average_total_band_availability_mw
    expr: AVG(COALESCE(band_availability_1_mw, 0) + COALESCE(band_availability_2_mw, 0) + COALESCE(band_availability_3_mw, 0) + COALESCE(band_availability_4_mw, 0) + COALESCE(band_availability_5_mw, 0) + COALESCE(band_availability_6_mw, 0) + COALESCE(band_availability_7_mw, 0) + COALESCE(band_availability_8_mw, 0) + COALESCE(band_availability_9_mw, 0) + COALESCE(band_availability_10_mw, 0))
    comment: "Average sum of the ten offered availability bands in MW per bid-period row."
  - name: minimum_price_band_aud_per_mwh
    expr: MIN(LEAST(price_band_1_aud_per_mwh, price_band_2_aud_per_mwh, price_band_3_aud_per_mwh, price_band_4_aud_per_mwh, price_band_5_aud_per_mwh, price_band_6_aud_per_mwh, price_band_7_aud_per_mwh, price_band_8_aud_per_mwh, price_band_9_aud_per_mwh, price_band_10_aud_per_mwh))
    comment: "Minimum offered price band in AUD/MWh across selected rows."
  - name: bid_period_row_count
    expr: COUNT(1)
    comment: "Daily bid-period rows at DUID, type and direction grain."
$$;
