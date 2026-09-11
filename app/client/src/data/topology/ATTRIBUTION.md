# Facility coordinate attribution

`nemFacilities.json` is derived from the OpenElectricity facilities export:
[github.com/opennem/openelectricity](https://github.com/opennem/openelectricity),
MIT licensed, © 2023–2026 Open Electricity.

**435 facilities, 572 DUIDs, five NEM regions** (NSW1, QLD1, SA1, TAS1, VIC1).

## What this file is

Static public reference data only: facility code, facility name, NEM region,
WGS84 latitude and longitude, and the DUIDs registered at each facility.

`duid` is the join key to `gold_nem_unit_dispatch_5min`. All output shown on the
map comes from that governed read; **no generation value is stored here**.

## What this file is not

- Not a governed data contract. The workshop's contracts are the `gold_nem_*`
  tables, and this file must not be treated as one.
- Not electrical topology. There are no lines, no transformers, no substations
  and no connection points, so nothing here supports a power-flow, contingency,
  or electrical-distance claim.
- Not authoritative registration data. AEMO's monthly registration export is
  authoritative for region and fuel; that enrichment already reaches the app
  through `gold_nem_unit_dispatch_5min`. Where the two disagree, the governed
  read wins and this file is only used for position.

## Regeneration

Derived from `data/nem_facility_coordinates.csv` in the GridSense reference
repository, grouped by `facility_code`, with DUIDs collected per facility and
facilities sorted by code for a stable diff.

Coordinates are recorded to source precision. A facility appearing in the
governed dispatch read but absent here is reported on screen as an uncovered
DUID rather than being dropped silently — see `MapCoverage` in
`client/src/domain/facilityMap.ts`.
