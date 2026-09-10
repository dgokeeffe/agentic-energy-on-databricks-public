-- AppKit Analytics read path for five-minute generation by region and fuel.
-- @param fuel_generation_table STRING = agentic_energy_workshop.agentic_energy_workshop_d4_serving.gold_nem_scada_generation_5min
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
-- interval_end is interval-ending fixed AEST. registration_coverage_seconds is a
-- UTC publication-time delta. The two clocks must never be differenced.
--
-- registration_coverage_seconds is signed and nullable: negative means the
-- registration load was published after the dispatch data it describes, and NULL
-- means the distance is not assessable rather than zero. Read it together with
-- registration_coverage_basis, because a small coverage under
-- DEGRADED_RETRIEVAL_FALLBACK establishes nothing about the registration's age.
--
-- The LIMIT bounds the window to roughly two hours across five NEM regions at
-- five-minute grain with several fuels per region.
SELECT
  interval_end,
  region_id,
  fuel_type,
  actual_generation_mw,
  facility_count,
  partially_enriched_facility_count,
  registration_publication_at,
  registration_coverage_seconds,
  registration_coverage_basis
FROM IDENTIFIER(:fuel_generation_table)
ORDER BY interval_end DESC, region_id, fuel_type
LIMIT 1000
