-- AppKit Analytics read path for five-minute per-unit SCADA output.
--
-- Keeping the identifier in reviewed SQL prevents callers from selecting another
-- object, exactly as latest_region_status.sql and latest_fuel_generation.sql do.
-- This is the only per-unit read path in the application.
--
-- Grain is (interval_end, duid). actual_generation_mw is signed, so a charging
-- battery is negative and must not be treated as generation. This is actual
-- SCADA output only: AEMO Current publishes no five-minute unit availability,
-- so nothing here supports a curtailment or availability claim, and
-- registered_capacity_mw is registration reference data rather than an
-- availability figure for the interval.
--
-- duid is the join key to the static facility coordinate reference in
-- client/src/data/topology/nemFacilities.json. A DUID absent from that file is
-- reported on screen as uncovered rather than dropped.
--
-- dimension_match_status is retained rather than filtered: an UNMATCHED row has
-- no governed region or fuel enrichment, and hiding it would understate the
-- fleet while appearing complete.
--
-- The LIMIT bounds the window to roughly three intervals across the ~570
-- registered DUIDs, which is enough for the map to reduce to a single latest
-- interval while remaining a bounded read.
SELECT
  interval_end,
  duid,
  actual_generation_mw,
  region_id,
  fuel_type,
  registered_capacity_mw,
  dimension_match_status
FROM agentic_energy_workshop.agentic_energy_workshop_d4_serving.gold_nem_unit_dispatch_5min
ORDER BY interval_end DESC, duid
LIMIT 1800
