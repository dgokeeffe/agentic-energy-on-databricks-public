# NEMWEB data contract

The governed source-to-destination contract for the NEMWEB foundation. These are
the fixed data semantics that every track, query, and analyst asset must respect.

This page carries the contract sections recovered from the withdrawn migration
manifest on 2026-09-07. The wording is preserved verbatim, because tests and
analyst assets assert against it. Historical migration bookkeeping, reviewed
byte hashes, and dated disposition indexes were not retained.

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


## Deliberate omissions

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
