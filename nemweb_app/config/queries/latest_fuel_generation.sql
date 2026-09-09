-- AppKit Analytics read path for five-minute generation by region and fuel.
--
-- Keeping the identifier in reviewed SQL prevents callers from selecting another
-- object, exactly as latest_region_status.sql does. This is the only generation
-- read path in the application.
--
-- Grain is (interval_end, region_id, fuel_type). actual_generation_mw is a signed
-- sum, so a charging battery is negative and must not be treated as generation.
-- This is actual SCADA output only: AEMO Current publishes no five-minute
-- availability, so nothing here supports a curtailment or availability claim.
--
-- The LIMIT bounds the window to roughly two hours across five NEM regions at
-- five-minute grain with several fuels per region.
SELECT
  interval_end,
  region_id,
  fuel_type,
  actual_generation_mw,
  facility_count,
  partially_enriched_facility_count
FROM agentic_energy_workshop.agentic_energy_workshop_d4_serving.gold_nem_scada_generation_5min
ORDER BY interval_end DESC, region_id, fuel_type
LIMIT 1000
