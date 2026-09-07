# NEMWEB source-to-destination migration manifest

Status: repository implementation and independent review fix pass complete; live deployment, analyst SQL execution and three-cycle closure remain external gates, 2 September 2026
Destination: `agentic-energy-challenge`
Reference: `australian-energy-nemweb-analytics`
Reference Git revision: `4c66923b3d3887117ed5dc20cb694f3e1652cc72`
Reference commit date: 17 July 2026

## Independent review fix-pass decisions (2 September 2026)

- The wheel lander now has an installed snapshot and executable `land` and
  `snapshot` commands. Live mode fails closed unless the deployment-controlled
  `allow_live_nemweb` gate is true. Critical Current discovery is bounded by
  lookback/files/bytes/timeouts; daily context raises ZIP expansion bounds to
  256 MiB only for measured context archives (about 134 MiB BIDMOVE and
  231 MiB SETFCASREGIONRECOVERY); the critical path remains at 64 MiB.
- UC Volume publication uses same-directory temporary files and atomic rename,
  never hard links or `fsync`. Parsed outputs are staged outside the Auto Loader
  prefix; the durable manifest is written first, then checksum-addressed files
  are published. Relisting identical bytes cannot create a second Auto Loader
  input. Symlink and snapshot traversal inputs fail closed.
- Parser errors and schema-drift additions are emitted as provenance-complete
  `_rescued_data` JSONL records so Bronze quarantine is queryable and layer
  counts reconcile; drift rows do not enter normal Bronze.
- Monthly DUDETAILSUMMARY, DUALLOC, GENUNITS, FCASREGIONRECOVERY and IRSURPLUS
  are separate MMSDM archives and are validated per expected section. Unproven
  STATION/network/interconnector-master tables were removed rather than left as
  permanently empty governed assets.
- `spark.sql.session.timeZone` is fixed to `Australia/Brisbane` and asserted by
  pipeline configuration. Five-minute Bronze records require an exact
  five-minute boundary. Open-ended DUDETAIL rows remain current; GENUNITS uses
  `LASTCHANGED` before landing metadata.
- Evidence SQL renders timezone offsets, filters landed/Bronze cycle counts by
  the nested lander run ID, sums exact-update microbatch expectation events and
  accepts drops only when no greater than queryable quarantine rows. Source
  listing timestamps are parsed without process-locale dependence.
- AEMO/IIS listing timestamps are treated as fixed NEM market time (AEST),
  consistent with report operation and the existing primary-source research.
  The exact server timezone is retained as a residual assumption to verify in
  the live evidence run; source publication lag is never inferred from the
  filename interval token.

## Review basis and provenance

This manifest is the gate for deliberate adaptation. It records reference
inputs, destination ownership, criticality, known failure state and required
remediation. File presence is not evidence that a reference component works.
The reference worktree was dirty when reviewed; in particular,
`utilities/nemweb_datasource_folder.py` differed from the recorded commit.
Content SHA-256 values below identify the exact bytes reviewed and prevent the
commit identifier from concealing a local change. No generated wheel, cache,
coverage output, log, deployment state or credential is migrated.

The destination's original material remains under `LICENSE`. Material adapted
from the reference is additionally governed by the Databricks source licence
reproduced verbatim in `NOTICE.md`. AEMO/NEMWEB attribution and snapshot rules
are in `DATA_LICENSES.md`. These terms are compatible for this Databricks
workshop because adapted material is used only with Databricks Services and the
more restrictive source terms remain attached. Any use outside those terms is
not granted.

## Fixed data semantics

- The primary runtime is governed NEMWEB Lakeflow; the original JSONL pipeline
  remains only as the explicit `agentic-energy-local-fixture` compatibility
  path.
- Raw ZIP archives are immutable provenance. Parsed typed files are Lakeflow
  inputs. Both live under mode-scoped sibling roots in the governed landing
  Volume (`snapshot/` and `live/`); each sibling retains its own write-once mode
  marker. Legacy parent-root data is ignored and not migrated automatically.
- Bronze is append-only and retains every report version. Silver selects the
  latest valid correction by report version/`RUNNO`, source listing/HTTP
  publication time, landing time/run ID, then deterministic row sequence. When
  listing metadata is absent the manifest labels retrieval time as a fallback.
  Late corrections may change Gold.
- NEM market time is AEST (UTC+10) without daylight saving; dispatch timestamps
  are interval-ending.
- Gold retains intervention and non-intervention rows. `is_effective_run`
  selects the highest intervention flag present for a key excluding
  intervention, otherwise intervention 0. Consumers must not aggregate runs
  blindly.
- Current reports do not publish five-minute unit availability. SCADA-based
  unit output is called `actual_generation_mw`; authoritative target and
  availability belong only in the daily T+1 unit-solution product.

## Report-to-subject contract

| Analyst subject | Source family and section | Source cadence | Destination Gold | Natural key before correction selection |
|---|---|---|---|---|
| Regional dispatch price and demand | `DispatchIS_Reports`: `PRICE`, `REGIONSUM` | Five minute | `gold_nem_region_dispatch_5min` | interval end, region, intervention |
| Unit/facility output | `Dispatch_SCADA`: `UNIT_SCADA`, enriched by NEMWEB registration | Five minute | `gold_nem_unit_dispatch_5min` | interval end, DUID |
| SCADA generation by region/fuel | `Dispatch_SCADA`: `UNIT_SCADA`, enriched by NEMWEB registration | Five minute | `gold_nem_scada_generation_5min` | interval end, DUID before aggregation |
| Binding constraints | `DispatchIS_Reports`: `CONSTRAINT` | Five minute | `gold_nem_binding_constraints_5min` | interval end, constraint ID, intervention |
| Interconnector flows | `DispatchIS_Reports`: `INTERCONNECTORRES` | Five minute | `gold_nem_interconnector_flows_5min` | interval end, interconnector ID, intervention |
| Authoritative unit target/availability | `Next_Day_Dispatch`: `UNIT_SOLUTION` | Daily T+1 | `gold_nem_unit_dispatch_availability_t1` | interval end, DUID, intervention |

`DISPATCHIS` is fetched once per cycle and all interleaved sections in every CSV
member are parsed. The old first-member `parse_dispatchis_zip()` implementation
is diagnostic only and must not be reused for the governed path.

## Silver natural-key and enrichment proof (2 September 2026)

The natural keys are evidenced directly by the checked-in versioned `I` header
rows and representative `D` rows: `PRICE.v5` and `REGIONSUM.v9` identify
`SETTLEMENTDATE`, `RUNNO`, `REGIONID`, `INTERVENTION`; `CONSTRAINT.v5` identifies
`SETTLEMENTDATE`, `RUNNO`, `CONSTRAINTID`, `INTERVENTION`;
`INTERCONNECTORRES.v3` identifies `SETTLEMENTDATE`, `RUNNO`,
`INTERCONNECTORID`, `INTERVENTION`; `UNIT_SCADA.v1` identifies
`SETTLEMENTDATE`, `DUID`; and T+1 `UNIT_SOLUTION.v6` identifies
`SETTLEMENTDATE`, `RUNNO`, `DUID`, `INTERVENTION`. Section version, then
`RUNNO`, captured listing/HTTP publication time, landing time/run identity and
source row sequence form the correction order. Tests prove duplicate archives,
higher `RUNNO`, bid/settlement-specific revisions, equal-version later
publication and cross-run deterministic ties. Bronze remains unchanged.

The facility join is proven from these AEMO NEMWEB MMSDM July 2026 monthly
SQLLoader archives, retrieved and parsed on 2 September 2026 (literal `#` in
filenames is URL-encoded as `%23`):

- `PUBLIC_ARCHIVE#DUDETAILSUMMARY#FILE01#202607010000.zip`, SHA-256
  `c87e888dbae6e65fba3b07aba89c04c1f3e3a17f38e811cfe0b1ee6833139b1e`;
- `PUBLIC_ARCHIVE#DUALLOC#FILE01#202607010000.zip`, SHA-256
  `7aa9fabcf18c9c5cb1e280bf7aa333b4384709e90a4c5a58ffa4bf8db7bee845`;
- `PUBLIC_ARCHIVE#GENUNITS#FILE01#202607010000.zip`, SHA-256
  `847de568b04902b6472df16cff89c4abce643323566cd79f966848500a29cc03`.

Their common base URL is
`https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/2026/MMSDM_2026_07/MMSDM_Historical_Data_SQLLoader/DATA/`.
Real headers are `DUDETAILSUMMARY.v7` (DUID/effective start and end/region/
station/classification), `DUALLOC.v1` (effective date/version/DUID/GENSETID),
and `GENUNITS.v3` (GENSETID/capacities/name/`CO2E_ENERGY_SOURCE`). Fuel is
**GENUNITS.CO2E_ENERGY_SOURCE**, not `GENSETTYPE`. The latter is a dispatchable
unit class, not fuel. The join selects the effective DUDETAILSUMMARY row,
selects latest DUALLOC by effective date/version, and joins GENUNITS; missing
DUALLOC falls back to `GENSETID = DUID`. All joins are left joins.

Measured against 514 DUIDs in a real Current DISPATCHSCADA file, this join gave
514/514 region matches (100.0%) and 478/514 fuel matches (93.0%). The 36 missing
fuels were aggregate/pseudo units such as `RT_*`, `DG_*` and `SNOWYP`; they stay
published with `fuel_type = 'UNKNOWN'` and a precise `dimension_match_status`.
Observed populated energy sources included Solar (153), Wind (119), Natural Gas
(Pipeline) (100), Hydro (98), Battery Storage (96), Black coal (67), Diesel oil
(46), Landfill biogas methane (37), Brown coal (37), Coal seam methane (12) and
smaller categories. Casing is normalised while `fuel_type_raw` remains.

Constraint binding is not thresholded or filtered. The AEMO MMS Data Model
Report for `DISPATCHCONSTRAINT` describes `MARGINALVALUE` as the “$ Value of
binding constraint” (`MMS_126.htm`, retrieved 2 September 2026):
`https://visualisations.aemo.com.au/aemo/nemweb/MMSDataModelReport/Electricity/MMS%20Data%20Model%20Report_files/MMS_126.htm`.
Accordingly `is_binding` is the explicitly documented derived interpretation
`MARGINALVALUE <> 0`; zero and null are false. Raw RHS, LHS, marginal value and
violation degree remain available, and no row is silently removed.

## Foundation/resource migration

| Reference | Destination | Class | Disposition and required repair |
|---|---|---|---|
| `LICENSE.md`, `NOTICE.md` | `NOTICE.md`, this manifest | Provenance | Reproduce source licence and notice; mark adapted files modified. |
| `DATA_LICENSES.md` | `DATA_LICENSES.md` | Provenance | Keep only AEMO terms; remove unrelated source licences and unsupported non-commercial claims. |
| `nemweb_file_lander.job.yml` | `nemweb_foundation/resources/nemweb_lander.job.yml` | Critical | Replace continuous/notebook/uploaded-wheel design with bounded destination wheel task and no independent trigger. |
| `open_electricity.pipeline.yml` | `nemweb_foundation/resources/nemweb.pipeline.yml` | Critical | Rewrite; include the whole modern pipeline source glob, serverless compute and no commented-out critical libraries or pipeline continuous setting. |
| `open_electricity.job.yml` | `nemweb_foundation/resources/nemweb_refresh.job.yml`, `nemweb_foundation/resources/nemweb_context_refresh.job.yml` | Critical/context | Replace fan-out and external feeds with one queued five-minute DAG and one daily context DAG; both deploy paused. |
| `metric_views.job.yml` | `nemweb_foundation/resources/nemweb_semantics.job.yml` (later slice) | Analyst | Resource pattern only; no metric SQL copied before stable Gold contracts. |
| `ml_pipeline.yml` | — | Excluded | ML is outside scope. |
| `AustralianOpenNEMElectricityDashboard.lvdash.json` | `nemweb_foundation/dashboards/nemweb_overview.lvdash.json` (later slice) | Analyst | Structural reference only; rebuild against governed five-minute assets. |
| Genie/metric-view notebooks and scripts | versioned Genie/SQL assets (later slices) | Analyst | Adapt serialisation/resource concepts only; no custom-app dependency. |

Bundle variables are `catalog`, `schema`, `landing_volume`, `warehouse_id`,
`nemweb_mode`, `critical_lookback_hours`, `context_lookback_days`,
`max_files_per_cycle`, `network_timeout_seconds`, `network_retry_count`, and the
existing governed principals. No host, credential, token, tenant identifier or
fixed private URL is committed.

## Utility and schema migration

| Reference | Destination | Class | Disposition |
|---|---|---|---|
| `utilities/nemweb_lander.py` | `nemweb_foundation/agentic_energy/nemweb/lander.py` | Critical | Redesign: HTTPS allowlist, redirect validation, bounded retries/bytes/files/ZIP expansion, checksum identity, atomic promotion, immutable versions, durable status and write-once cycle ID. |
| `utilities/nemweb_utils.py` | `parser.py`, `schemas.py`, `contracts.py` | Critical | Split parser and typed contracts; retain `C/I/D/F`, every member/section and observable drift. |
| `utilities/nemweb_ingest.py` | `lander.py` | Critical | Adapt deterministic ingestion/manifest concepts only; remove custom-source coupling. |
| `utilities/nemweb_etl.py` | `contracts.py`, transformations | Critical/context | Adapt only mappings proven against a fixture or MMS evidence. |
| `utilities/nemweb_schema_tracker.py` | `schema_drift.py` | Critical | Required-column failure, rescued additions and measurable drift. |
| `utilities/nemweb_datasource_folder.py` | `pipeline/bronze*.py` | Diagnostic only | Do not port custom data source; use supported Volume/Auto Loader reads. Reviewed worktree bytes were locally modified. |
| `utilities/nemweb_dispatch.py` | `contracts.py` | Diagnostic only | Mapping hints require representative-file proof. |
| `utilities/nem_registry.py` | `schemas.py` | Critical dependency | Adapt NEMWEB section registry only. |
| `utilities/nemweb_backfill.py` | — | Deferred | Archive history cannot delay Current reports. |
| `utilities/nemweb_datasource_stream.py` | — | Excluded | Replace custom stream source with supported Spark reads. |
| `utilities/ml_utils.py` | — | Excluded | ML is outside scope. |
| utility test runners | evidence tooling (later slice) | Diagnostic | Rewrite to query watermarks and exact update events. |

## Transformation/table migration

All destination pipeline Python must use `from pyspark import pipelines as dp`,
`@dp.table`/`@dp.materialized_view`, `spark.read.table` and
`spark.readStream.table`. A static test rejects `import dlt`, `dlt.read`,
`dp.read`, `LIVE.*`, `CREATE LIVE`, old `apply_changes` and deprecated file-name
metadata APIs.

| Reference input | Destination tables | Class | Disposition |
|---|---|---|---|
| `bronze_nemweb_dispatch.py`, `bronze_nemweb_dispatch_extended.py` | dispatch price, region summary, constraint and interconnector-result Bronze | Critical five minute | Rewrite with append-only source/version metadata and one all-section DISPATCHIS parse. |
| `bronze_nemweb_registration.py` | DUID, generating-unit, station, region and interconnector Bronze; facility dimensions | Mandatory dependency | Rewrite; prove DUID-to-region/fuel joins from NEMWEB rather than OpenElectricity. |
| No working Current reference | unit-solution T+1 Bronze/Silver/Gold | Daily context | Implement from `Next_Day_Dispatch UNIT_SOLUTION`; never present as five-minute availability. |
| `silver_nemweb_markets.py` | `silver_nem_region_dispatch` | Critical five minute | Rewrite correction-aware at intervention grain. |
| `silver_nemweb_scada.py` | `silver_nem_dispatch_unit_scada` | Critical five minute | Rewrite; preserve legitimate negative values and unknown DUIDs. |
| `silver_nemweb_constraints.py` | `silver_nem_dispatch_constraint` | Critical five minute | Rewrite; binding semantics remain a stop gate until proven from MMS/sample fields. |
| disabled `silver_nemweb_interconnector.py` | `silver_nem_interconnector_flow` | Critical five minute | Diagnostic input only; repair from `INTERCONNECTORRES` contract and prove independently. |
| `gold_nemweb_markets.py` | regional five-minute Gold plus optional 30-minute/daily views | Critical | Do not carry forward a 30-minute-only product. |
| `gold_nemweb_generation.py` | unit and enriched SCADA five-minute Gold | Critical | Replace 30-minute window and excluded OpenElectricity join with proven NEMWEB dimensions. |
| `gold_nemweb_constraints.py` | binding-constraint five-minute Gold | Critical | Do not port arbitrary thresholds or inferred regions without proof. |
| disabled `gold_nemweb_interconnector.py` | interconnector-flow five-minute Gold | Critical | Repair; disabled file is not operational evidence. |
| bids transformations | bid Bronze/Silver/Gold | Slower context | Include only after report and key tests pass. |
| trading transformations | trading Bronze/Silver/Gold | Slower context | Include only after report and key tests pass. |
| settlement transformations | settlement Bronze/Silver/Gold | Slower context | Include only where a current/archive source contract is proven. |
| market-notice transformations | one canonical notice Bronze/Silver/Gold path | Event-driven context | Reconcile duplicate reference Gold implementations; include only proven path. |

Every Bronze table retains: `source_mode`, `source_url_path`, `source_archive`,
`source_archive_sha256`, `source_csv_member`, `report_family`, `section_name`,
`report_version`, `run_no`, `source_publication_at`, `interval_end`, `landed_at`,
`ingested_at`, `ingestion_run_id`, `ingestion_sequence`, and `_rescued_data`.
Bronze counts may exceed Silver because prior corrections are retained; that is
not a duplicate-key defect.

## Explicit exclusions and deferred inputs

Not migrated because they are out of scope, disabled/unproven, duplicate or
replaced:

- non-NEMWEB weather, BOM, ABS, CER, OpenElectricity and public-holiday files;
- affordability, PASA, rooftop PV, predispatch, demand forecast, FCAS,
  curtailment, monitoring and ML transformations;
- disabled P5MIN, extended constraint, network, settlement duplicate and schema
  monitor transformations;
- P5MIN notebooks (the Current family has no unit solution), predispatch,
  STPASA/MTPASA, rooftop-PV, network, operational-demand and forecast notebooks;
- reference facility-power and OpenElectricity facility notebooks;
- custom application code and ML resources;
- `dist/`, `htmlcov/`, `.coverage`, `coverage.xml`, logs, caches, compiled
  frontend assets, `.databricks` state, local lock/environment files and any
  credential material.

The following consolidated notebook concepts may inform the destination lander
or contracts but are not copied as notebooks: Current listing/extraction,
dispatch region/constraint/interconnector/load, registration/facility, bids,
trading, market notices, interconnector and generic-constraint landers.

## Reference checks disposition

No reference check is copied as proof. Each is classified explicitly:

| Reference check | Destination disposition |
|---|---|
| `checks/CONSTRAINTS_VERIFIED.md` | Diagnostic only; re-prove binding fields and semantics from current MMS/sample data. |
| `checks/checks.sql` | Query-pattern input for later reconciliation checks; rewrite against governed destination names. |
| `checks/silver_nem_markets_scd_1__checks.yml` | Rewrite as region-dispatch correction and natural-key tests. |
| `checks/gold_nem_markets_10min_aggregates_checks.yml` | Exclude; destination critical contract is five-minute, not ten-minute. |
| `checks/gold_nem_markets_30min_aggregates_checks.yml` | Optional additional-product reconciliation only. |
| `checks/gold_facility_energy_totals_checks.yml` and summary | Diagnostic; exclude OpenElectricity dependencies and re-prove NEMWEB facility joins. |
| `checks/silver_facility_energy__checks.yml` | Diagnostic only; rewrite for SCADA actual-MW semantics. |
| `checks/gold_nem_facilities_30min_aggregates_checks.yml` | Optional additional-product input after five-minute Gold works. |
| `checks/silver_nem_network_scd_1__checks.yml` | Deferred; network history is outside the critical path. |
| `checks/gold_nem_network_aggregates_checks.yml` | Deferred with network history. |
| `checks/gold_nem_network_fuel_type_aggregates_checks.yml` | Diagnostic join input; do not copy excluded dimensions. |
| `checks/gold_nem_curtailment_30min_aggregates_checks.yml` | Excluded with curtailment. |
| `checks/backfill_nem.sql` | Deferred with archive backfill. |

## Complete transformation disposition index

- **Critical inputs to rewrite:** `bronze_nemweb_dispatch.py`,
  `bronze_nemweb_dispatch_extended.py`, `bronze_nemweb_registration.py`,
  `silver_nemweb_markets.py`, `silver_nemweb_scada.py`,
  `silver_nemweb_constraints.py`, `silver_nemweb_facilities.py`,
  `gold_nemweb_markets.py`, `gold_nemweb_generation.py`,
  `gold_nemweb_constraints.py`, `gold_nemweb_facilities.py`, and
  `gold_nemweb_facility_aggregates.py`.
- **Slower context, migrate only after source proof:**
  `bronze_nemweb_trading.py`, `bronze_nemweb_settlement.py`,
  `bronze_nemweb_market_notice.py`, `silver_nemweb_bids.py`,
  `silver_nemweb_market_notice.py`, `gold_nemweb_bids.py`,
  `gold_nemweb_settlement.py`, and exactly one reconciled implementation from
  `gold_nemweb_market_notice.py` / `gold_nemweb_market_notices.py`.
- **Enabled but excluded:** `bronze_nemweb_affordability.py`,
  `silver_nemweb_affordability.py`, `gold_nemweb_affordability.py`,
  `gold_nemweb_pasa.py`, and `gold_nemweb_ml_aggregates.py`.
- **Disabled, diagnostic only or excluded:** `bronze_nemweb_p5min.py`,
  `bronze_nemweb_p5min_extended.py`, `bronze_nemweb_fcas.py`,
  `bronze_nemweb_constraints_bids.py`, `bronze_nemweb_constraints_extended.py`,
  `bronze_nemweb_settlement.py` (disabled duplicate),
  `bronze_nemweb_file_manifest.py`, `bronze_nemweb_predispatch.py`,
  `bronze_nemweb_predispatch_extended.py`,
  `bronze_nemweb_demand_forecast.py`, `bronze_nemweb_network_extended.py`,
  `bronze_nemweb_rooftop_pv.py`, `bronze_nemweb_pasa.py`,
  `bronze_nemweb_mtpasa_extended.py`, `bronze_nemweb_stpasa_extended.py`,
  `silver_nemweb_interconnector.py`, `gold_nemweb_interconnector.py`,
  `silver_nemweb_curtailment.py`, `gold_nemweb_curtailment.py`,
  `silver_nemweb_monitoring.py`, and `schema_evolution_monitor.py`.
- **Configuration utilities to replace, not extend:** `dlt_config.py` and
  `dlt_streaming_utils.py`; destination names remove DLT terminology and legacy
  read APIs.

## Test migration

| Reference test family | Destination tests | Disposition |
|---|---|---|
| `test_nemweb_utils.py`, registry tests | parser/schema tests | Adapt all-member, all-section, version and typed-schema cases. |
| `test_nemweb_etl.py` | contract/correction tests | Replace ingestion-time-only dedupe with approved correction ordering. |
| `test_nemweb_schema_tracker.py` | drift tests | Adapt additions, required-column loss and acknowledgement cases. |
| folder-data-source gates AC1–AC10 | lander/parser/snapshot tests | Preserve applicable safety outcomes; remove custom-source assumptions. |
| job YAML and selective-refresh tests | `test_bundle_resources.py` and live evidence | Assert paused five-minute trigger, dependencies, no full refresh and included sources. |
| backfill/custom-stream/ML tests | — | Deferred or excluded with their implementations. |
| reference deployment/e2e harness | evidence scripts and dated evidence | Rewrite around exact job runs, update IDs, watermarks and terminal errors. |

Exact reference test index: adapt `test_nemweb_utils.py`, `test_nem_registry.py`,
`test_nemweb_etl.py`, `test_nemweb_schema_tracker.py`, `test_schema_inference.py`,
`test_job_yaml.py`, `test_selective_refresh.py`, `test_lsdp_pipeline.py` and gates
`test_nemweb_folder_datasource_ac1.py` through `ac10.py` as described above;
rewrite `test_e2e_deployment.py`; defer `test_nemweb_backfill.py`; exclude
`test_streaming_data_source.py`, `test_ml_utils.py` and
`test_ml_utils_feature_store.py` with their non-migrated implementations.

The deterministic snapshot will contain critical families plus duplicate,
correction, multi-section, malformed footer/row, unknown/missing-column and
timezone cases. Its manifest carries source URL, date, checksum, report
version, attribution and synthetic-mutation labels. The registration component
is a row-preserving excerpt of the three real MMSDM archives identified above;
dispatch edge cases remain explicitly synthetic and are never live evidence.

## Exact reviewed reference-byte hashes

| Reference path | SHA-256 |
|---|---|
| `LICENSE.md` | `dde5a48bcf8c3179a7a5a3a00d51a638d93da35083a2467277643c2f60fc9ae2` |
| `NOTICE.md` | `b30a7ecf7b0a8d7ca2613f996f0561e48934750ea608f2b11140e98133e30d72` |
| `DATA_LICENSES.md` | `7f277379094cc25144f791006fb0e1280a910031b710474862a8539f9d1b0d77` |
| `resources/open_electricity_pipeline/nemweb_file_lander.job.yml` | `ab0413ed721c2013acd7e44f7470381ed22b6e9f764ca7bbf4813f2338f7409d` |
| `resources/open_electricity_pipeline/open_electricity.pipeline.yml` | `ded6bf63683e68072b3fa9366fe56c53e8a13959e34d2a57ba40cbb609692273` |
| `resources/open_electricity_pipeline/open_electricity.job.yml` | `5bdf8b047cf7d5a23a14a8530c1ea7d8c0835f7b6596b048cdb3fc58ef62cf8d` |
| `resources/open_electricity_pipeline/metric_views.job.yml` | `51a306c2e5f1b4d870dc3829ac3dfc4a7f1113da9b971000357aa11f9c2b9cb0` |
| `utilities/nemweb_lander.py` | `9562566a18b65da2c7196df7aff37a2e086f49fc5ccac73eb879f47badeac141` |
| `utilities/nemweb_utils.py` | `379555a9b18d7db2d9d358db873cd434768319c2e865d6bbc7f1d1bcf609dfb1` |
| `utilities/nemweb_ingest.py` | `f2bea5e54018824dafe07aa1ad8aec676516f07671e775220f485e8f04c8c487` |
| `utilities/nemweb_etl.py` | `8af798ba40682b101e5b5fa73fa168e43d51b204cb30670358d5625397d8b00` |
| `utilities/nemweb_schema_tracker.py` | `8f22d0ec27c26cf8750cb11fe27c2cd182569241f5cafa1cd0f9f8ef53847b0a` |
| `utilities/nemweb_datasource_folder.py` (dirty reference bytes; diagnostic only) | `79da44652622e5e2cb23ff2697d9c03e3a213cf47863ac6b1274c4588322e85b` |
| `utilities/nem_registry.py` | `5f1ce0892cd04107c70f7a3ae5e4671ae94d406db73427d432faf9a77c8a02aa` |
| `transformations/bronze_nemweb_dispatch.py` | `d086d2a38a95a0e41e15381ac70abb772d6da934e17f5b301ef3ae15f0a97d0a` |
| `transformations/bronze_nemweb_dispatch_extended.py` | `4aa91d31d87809a5529e8f27faacba7e6aac043aa08886096807dcc6cf4a079a` |
| `transformations/bronze_nemweb_registration.py` | `bee8e66544796047cc8362cbd749cceaf196e8b7d977acfc6fef070565997661` |
| `transformations/silver_nemweb_markets.py` | `7c0bf745ac6b6a46f4136c32264558cfad261eee80a9e3b4b1751a8fc4908e85` |
| `transformations/silver_nemweb_scada.py` | `fa8b34ae30dd9f13fe0bbb6ed2b56c8b09b53a8a0dba15e3c0c94f7a4b973144` |
| `transformations/silver_nemweb_constraints.py` | `7a69c0e84545cc3a888f9ed9c173e64bea1b2458a0fa0667a6a38c1a442493db` |
| `transformations/gold_nemweb_markets.py` | `79a8a2aca5d272060df03ef0d0760201c37786c7e68a1c6284ccf85fe73c5abc` |
| `transformations/gold_nemweb_generation.py` | `649ed3519414552ee50f7ba7d2eac969c026fa08131c71bff80b738b502c9736` |
| `transformations/gold_nemweb_constraints.py` | `9dd0a3b29065cc8d56b3c343f2e84e7184f7f7ec88d6f3a3cab3c76a94d7a59b` |
| `transformations/disabled/silver_nemweb_interconnector.py` | `681cc871280c05be43ca692a99c4bd10fb310247aa069de97988d0f46203e855` |
| `transformations/disabled/gold_nemweb_interconnector.py` | `e3b432b1dacc162ec053c7c9761ea6baf74075c2612fe6f81b764b99814992c0` |

## Foundation review disposition

- **Licence:** compatible only with the additional source restrictions retained
  in `NOTICE.md`; satisfied for this Databricks workshop scope.
- **Disabled files:** diagnostic only; none is represented as working.
- **Five-minute Gold:** mandatory; 30-minute/daily products are additional only.
- **Pipeline API:** destination source glob is active and contains no legacy
  DLT API. Dataset files arrive in later slices; no placeholder table or fake
  data is declared.
- **Schedules:** critical periodic trigger is five minutes and paused; daily
  context is paused; the legacy JSONL fixture has no schedule.
- **Resolved Silver stop gates:** the NEMWEB-only MMSDM registration join and
  exact non-zero `MARGINALVALUE` binding interpretation are evidenced above.
- **Open stop gates:** slower-context contracts still require representative
  source data/MMS proof before their later slice.

## Critical Gold publication contract (Slice 5, 2026-09-02)

The primary analyst products preserve the source five-minute interval ending;
none is derived only at 30-minute or daily grain:

| Gold product | Natural key | Source and measure semantics |
|---|---|---|
| `gold_nem_region_dispatch_5min` | interval end, region, intervention | DISPATCHIS PRICE + REGIONSUM; $/MWh and MW |
| `gold_nem_unit_dispatch_5min` | interval end, DUID | Current UNIT_SCADA `actual_generation_mw`; explicitly not target or availability |
| `gold_nem_scada_generation_5min` | interval end, region, fuel type | signed sum of UNIT_SCADA actual MW; missing dimension values remain `UNKNOWN` |
| `gold_nem_binding_constraints_5min` | interval end, constraint ID, intervention | only Silver rows with the documented derived `MARGINALVALUE <> 0` flag; raw values retained |
| `gold_nem_interconnector_flows_5min` | interval end, interconnector ID, intervention | AEMO source-sign MW flow retained unchanged |
| `gold_nem_unit_dispatch_availability_t1` | interval end, DUID, intervention | daily T+1 UNIT_SOLUTION target/availability, with separately labelled overlapping SCADA reconciliation |

Every primary product carries the row's `source_interval_watermark`, latest
source publication timestamp and Gold publication timestamp. Products with an
intervention field retain all selected intervention rows and expose
`is_effective_run`; only the additional 30-minute/daily products default to the
effective row.

The deterministic Next_Day_Dispatch fixture remains synthetic and is not live
evidence. In this slice its two DUID/interval keys were deliberately aligned to
the already-attributed synthetic SCADA fixture so the reconciliation itself is
executable: ARWF1 compares 20 MW actual with 21 MW target, and ADPBA1 compares
-5 MW actual with -6 MW target. The T+1 `LASTCHANGED` remains the following day,
and availability remains solely on the T+1 product. The fixture manifest
records this mutation and its replacement checksum; no live cadence claim is
made from it.

## Slower NEMWEB analyst context (Slice 6, 2026-09-02)

The source contracts below were confirmed directly from public Current files.
This inspection was read-only and no downloaded source row is checked into the
repository.

| Domain | Public source inspected | Exact section/version | Natural key and correction order | Cadence and purpose |
|---|---|---|---|---|
| bids | `REPORTS/CURRENT/Bidmove_Complete/PUBLIC_BIDMOVE_COMPLETE_20260901_0000000535637491.zip` | `BID.BIDDAYOFFER_D.v3`, `BID.BIDPEROFFER_D.v4` | day: settlement date, DUID, bid type, direction; period adds PERIODID; latest section version, VERSIONNO, publication, ingestion sequence | daily after trading day; analyst bid price/availability context |
| trading | `REPORTS/CURRENT/TradingIS_Reports/PUBLIC_TRADINGIS_202609021230_0000000535691330.zip` | `TRADING.PRICE.v3` | interval end, region; latest section version, RUNNO, publication, ingestion sequence | source publishes approximately every five minutes; settlement-price context, never a dispatch-price substitute |
| settlement | `REPORTS/CURRENT/Settlements/PUBLIC_SETTLEMENTS_20260902102926_0000000535675941.zip` | `SETTLEMENTS.FCASREGIONRECOVERY.v6`, `SETTLEMENTS.IRSURPLUS.v6` | FCAS: settlement date, region, period, bid type using VERSIONNO; IRSR: settlement date, period, interconnector, region using SETTLEMENTRUNNO; publication/ingestion break ties | issued per settlement run and refreshed by the daily context job; financial context only |

Complete source-header fingerprints are versioned in `schemas.py`, so known
non-selected columns are not mistaken for drift while required-column loss or a
changed header remains observable. Bronze preserves every revision. Silver
uses the report-specific `VERSIONNO` or `SETTLEMENTRUNNO` where `RUNNO` is not
part of that source contract. Gold exposes units and the source cadence in UC
comments and does not join or aggregate unlike financial/dispatch concepts.

A source-size probe is also part of the operational contract. The inspected
BIDMOVE_COMPLETE ZIP was 9,196,328 compressed bytes but 134,365,549 expanded
bytes (2,261 day keys and 651,168 period rows); every period row matched the
approved day-offer join key in that file. TradingIS was 707/2,127 bytes and Settlements was
5,064,380/49,374,364 bytes. The default parser expansion bound is intentionally
64 MiB, so the later context-lander wiring must set a separately reviewed,
still-bounded context limit of at least 135 MB for bids. This slice does not
weaken the global ZIP-safety default or claim a live bid landing run.

**Market notices are deliberately omitted in this slice.** The current source
(`REPORTS/CURRENT/Market_Notice/NEMITWEB1_MKTNOTICE_20260902.R144966` inspected)
is a 1,344-byte unstructured plain-text notice with labelled fields and a
free-form reason body, not a NEM CSV ZIP. The destination's bounded parser only
accepts ZIP members with NEM `C/I/D/F` controls. The reference path writes a
separate Delta table and does not provide the same immutable parser/provenance
contract. Shipping Bronze/Silver/Gold definitions without a bounded text parser,
deterministic fixture and correction/version tests would falsely claim a
working source path, so notice assets remain omitted pending that explicit
parser slice. The daily context job remains paused and no external workspace
change was made.

## Operations and evidence contract (Slice 9, 2026-09-02)

`nemweb_foundation/agentic_energy/nemweb/evidence.py` defines a versioned row contract for every
critical subject and cycle. Capture is workspace read-only and requires the
explicit `daveok` profile, SQL warehouse, pipeline ID, exact pipeline update ID
and orchestration run ID. It polls that update to `COMPLETED`, filters pipeline
events with the CLI-supported `update_id = '<id>'` expression (maximum page size
250), extracts nested `error.exceptions[0].message`, and
fails closed on missing expectation metrics, failed expectations, duplicate Gold
natural keys, failed lander/orchestration outcomes, or a source listing ahead of
Bronze.

The source publication timestamp is taken from the public NEMWEB directory
listing's timestamp for the exact newest filename. It is not inferred from the
12-digit filename token, which is retained separately as the source interval.
Listing timestamps and filename intervals are interpreted as fixed NEM AEST.
This keeps source-publication lag separate from source-to-Gold and
landed-to-Gold processing lag.

The five subject mappings used by evidence are:

| Subject | Source | Bronze | Silver | Gold natural key |
|---|---|---|---|---|
| regional price/demand | DISPATCHIS | PRICE + REGIONSUM (including quarantine) | `silver_nem_region_dispatch` | `gold_nem_region_dispatch_5min`: interval, region, intervention |
| unit/facility actual | Dispatch SCADA | UNIT_SCADA (including quarantine) | `silver_nem_dispatch_unit_scada` | `gold_nem_unit_dispatch_5min`: interval, DUID |
| SCADA region/fuel | Dispatch SCADA | UNIT_SCADA (including quarantine) | `silver_nem_dispatch_unit_scada` | `gold_nem_scada_generation_5min`: interval, region, fuel |
| binding constraints | DISPATCHIS | CONSTRAINT (including quarantine) | `silver_nem_dispatch_constraint` | `gold_nem_binding_constraints_5min`: interval, constraint, intervention |
| interconnector flow | DISPATCHIS | INTERCONNECTORRES (including quarantine) | `silver_nem_interconnector_flow` | `gold_nem_interconnector_flows_5min`: interval, interconnector, intervention |

A no-new-source result requires the listing filename, publication timestamp,
source interval and checksum signature to match the preceding capture, with the
listing interval not ahead of Bronze. Gold change detection compares watermark,
row count and an order-independent SHA-256 over bounded aggregate hashes of each
subject's governed business columns, so same-interval corrections remain
observable without collecting whole tables in the client. A source-changed
DISPATCHIS cycle with no new binding Gold row is labelled
source-changed/no-Gold-change rather than “no new source”. Captures append
without overwriting prior cycles, and the live
validator requires all five subjects, one update per cycle, successful outcomes
and bounded five-minute spacing for at least three cycles.

The in-job `evidence` wheel callback records only Jobs-supplied run identifiers
and explicitly reports `capture_pending_exact_update_id`. It does not invent an
update ID or data result. The authoritative post-run capture is
`nemweb_foundation/scripts/capture_nemweb_evidence.py`, once the exact update ID is known. Live
deployment and the three-cycle proof remain external closure gates.

## Public commit 4b664ce reconciliation (2026-09-05)

The merge commit `4b664ce` was compared file by file with both parents (`6be7faa` and `ec87239`). No history was merged or cherry-picked. The historical deployment evidence below is copied byte-for-byte and proves the public deployment, not this newly packaged `nemweb_foundation/`.

| Public path | Disposition | Public SHA-256 | Destination SHA-256 |
|---|---|---|---|
| `agentic_energy/nemweb/pipeline/bronze_dispatchis.py` | identical | `1c61952caa23b5282235986f4b321e33e75b33912ef13c56dd4ae30ca97ef9f5` | `1c61952caa23b5282235986f4b321e33e75b33912ef13c56dd4ae30ca97ef9f5` |
| `agentic_energy/nemweb/pipeline/bronze_scada.py` | identical | `ab5369be21a322fb1dae2ec85c8bb157353222ca8792a4d90795a391ce714d10` | `ab5369be21a322fb1dae2ec85c8bb157353222ca8792a4d90795a391ce714d10` |
| `agentic_energy/nemweb/pipeline/bronze_unit_solution.py` | identical | `f532f4ba1293aeab22d60694c70f26e6ca0f67cb2404fac65441d4dd5e56b02f` | `f532f4ba1293aeab22d60694c70f26e6ca0f67cb2404fac65441d4dd5e56b02f` |
| `agentic_energy/nemweb/pipeline/bronze_registration.py` | identical | `c1f74e7fa51267467c645aeb4874ab196406261110e66f819a2603e3e21dfa30` | `c1f74e7fa51267467c645aeb4874ab196406261110e66f819a2603e3e21dfa30` |
| `agentic_energy/nemweb/pipeline/bronze_bids.py` | identical | `a1058c9fadf44e5cbf26446d0d5e9ebaeecee41bedaea0e9ad47214bc67b85e8` | `a1058c9fadf44e5cbf26446d0d5e9ebaeecee41bedaea0e9ad47214bc67b85e8` |
| `agentic_energy/nemweb/pipeline/bronze_trading.py` | identical | `fa7cf9a90168e1ab09e0edac0a3f6d2d380ce7d321c7bba6fdf2fda437dcbe0e` | `fa7cf9a90168e1ab09e0edac0a3f6d2d380ce7d321c7bba6fdf2fda437dcbe0e` |
| `agentic_energy/nemweb/pipeline/bronze_settlement.py` | identical | `f6fe47dccf0246c98e67e022d3eeb4905ff4032602c01ad1c66620b4bda07c0c` | `f6fe47dccf0246c98e67e022d3eeb4905ff4032602c01ad1c66620b4bda07c0c` |
| `agentic_energy/nemweb/pipeline/silver_region_dispatch.py` | adapt | `a011a7e20e4ae5d9c4502eb70b15b9020914c4d76fdcd0f3b2d061d42546a866` | `b8423c856b70929f4cf7fd626713f0bf9717a024501acb4d2a0f7a1a2070717f` |
| `agentic_energy/nemweb/pipeline/silver_scada.py` | identical | `d37363fffcf10b9cbf71df8a53b5258c8913e5e4ad3f1083196cdfdc6c6534f4` | `d37363fffcf10b9cbf71df8a53b5258c8913e5e4ad3f1083196cdfdc6c6534f4` |
| `agentic_energy/nemweb/pipeline/silver_constraints.py` | identical | `67c787c126b921801e3eb86aa62e6510c358d867cde9715d82e1328946563968` | `67c787c126b921801e3eb86aa62e6510c358d867cde9715d82e1328946563968` |
| `agentic_energy/nemweb/pipeline/silver_interconnectors.py` | identical | `3316fd91d2aad17883eac2e2876fe988639c871e47943bffb390a49338703acc` | `3316fd91d2aad17883eac2e2876fe988639c871e47943bffb390a49338703acc` |
| `agentic_energy/nemweb/pipeline/silver_unit_solution.py` | identical | `eedf62ee40b4545b50c859262e04c19c9ba7c4d642bb902e99721e8bc895eb40` | `eedf62ee40b4545b50c859262e04c19c9ba7c4d642bb902e99721e8bc895eb40` |
| `agentic_energy/nemweb/pipeline/silver_facilities.py` | identical | `0a4b593c6878dadc55f078a0b28977d3047623f15af619febb81c3d98c594e68` | `0a4b593c6878dadc55f078a0b28977d3047623f15af619febb81c3d98c594e68` |
| `agentic_energy/nemweb/pipeline/silver_bids.py` | identical | `973929bc794de22848334ee4f3f7dc6e41cf757b4d4b792d7b49be718f00cc30` | `973929bc794de22848334ee4f3f7dc6e41cf757b4d4b792d7b49be718f00cc30` |
| `agentic_energy/nemweb/pipeline/silver_trading.py` | identical | `c9dbc1d602b599d373866f6ed869fb8b04a0751bec3a8768ce43d12e670a29da` | `c9dbc1d602b599d373866f6ed869fb8b04a0751bec3a8768ce43d12e670a29da` |
| `agentic_energy/nemweb/pipeline/silver_settlement.py` | identical | `c87ecac844e9fc9253df77065e76a6a07a6a5208a9b032f66e204213dcca754f` | `c87ecac844e9fc9253df77065e76a6a07a6a5208a9b032f66e204213dcca754f` |
| `resources/nemweb_refresh.job.yml` | adapt | `a669b9174768fe0945a8dbb628b511f7e72c78e0f08f91d832dbbce21b572f05` | `baa31a6add5429f0bb7b3f2899305b9a735c1e40f178f0ecc7d1d8721813364f` |
| `docs/test-evidence/nemweb-e2e-2026-09-03.md` | identical public historical evidence | `4b99ea2cfaff116f32175c6826e7f661c658b99c07ef7a45eed568d84d35d6b1` | `4b99ea2cfaff116f32175c6826e7f661c658b99c07ef7a45eed568d84d35d6b1` |
| `docs/test-evidence/nemweb-e2e-evidence.json` | identical public historical evidence | `f86570da393940b53007f8904f8630c47467eeecf1d1dbd02b39f39e2a2dbb46` | `f86570da393940b53007f8904f8630c47467eeecf1d1dbd02b39f39e2a2dbb46` |

`utilities/nemweb_datasource_folder.py` and generated artifacts were excluded as non-operational or generated material. Existing implementation files not listed above were already superseded by the governed foundation.
