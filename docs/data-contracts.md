# Data contracts

Raw archives are immutable. Bronze retains all source versions. Silver selects the latest correction by report version/run number, source publication time, landing order, and deterministic row sequence. Missing publication metadata is explicitly labelled as retrieval fallback.

Market timestamps are interval-ending fixed AEST (UTC+10, Australia/Brisbane). Publication, landing, and processing timestamps represent UTC instants. Keep timezone offsets in API values. Never reinterpret a market timestamp as UTC or subtract clocks after dropping their offsets.

Regional, constraint, and interconnector Gold retain both intervention flags. Effective runs select the highest intervention flag present for each key excluding intervention. The app's regional source includes only effective rows and preserves `price_source_run_no` and `demand_source_run_no`.

SCADA reports actual generation, including negative battery charging. Registered capacity is reference data, not availability. Current reports do not establish five-minute availability, curtailment, causation, or trading advice. Fuel attribution uses registration with deterministic effective-date selection. Missing attribution stays visible as UNKNOWN rather than disappearing. Registration coverage is a signed, nullable UTC publication-time delta; missing coverage is not zero.

| Delta source in serving schema | Key | Lakebase `app_read` table | API | Maximum rows |
|---|---|---|---|---:|
| `gold_nem_app_region_status` | `serving_key` (region and interval) | `nem_region_status_synced` | `/api/region-status` | 100 |
| `gold_nem_scada_generation_5min` | interval, region, fuel | `nem_fuel_generation_synced` | `/api/fuel-generation` | 1000 |
| `gold_nem_unit_dispatch_5min` | interval, DUID | `nem_unit_dispatch_synced` | `/api/unit-dispatch` | 1800 |

SQL sources use `interval_end`, `region_id`, `fuel_type`, and `duid` for the keys above. `resources/lakebase/datasets.json` records exact sync keys. Publication checks nonempty sources and unique nonnull keys before merging. CDF remains enabled, history is additive, and changed values update their existing keys. Publication does not delete rows absent from a later source read.

Regional status includes `source_mode` (snapshot or live), price, demand, both source run numbers, source watermark/publication, Gold publication, and market-wide constraint/interconnector aggregates. Market-wide values are repeated on regional rows; they are not regional allocations. Interconnector flow retains AEMO source sign without invented direction.

Fuel and unit API values are parsed independently with finite numeric validation and offset-bearing timestamps. Fuel coverage and unit capacity may be null. A malformed optional panel does not erase regional status. Row bounds can truncate the oldest interval; the app's existing coverage reporting remains essential.

Native investigation writes use trusted application identity and optimistic version checks. They are independent of read-only synced data. No prediction fields or investigation CDC are part of this contract.

The retained synthetic ZIP fixtures cover parser behavior, corrections, timestamps, and registration. Extra report sections in parser fixtures do not imply deployed products. Snapshot observations are not current market evidence.
