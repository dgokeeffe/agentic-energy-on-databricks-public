# App-first NEMWEB Delta landing migration manifest

This manifest bounds the implementation to the two `nemweb_app` contracts and
records provenance separately from the dirty reference worktrees.

## Reference provenance

| Reference | Committed revision and source | Destination | Use | Reference status | Licence result |
|---|---|---|---|---|---|
| `australian-energy-nemweb-analytics` | `4c66923b3d3887117ed5dc20cb694f3e1652cc72`; committed folder data-source parser and NEMWEB pipeline resources | `agentic_energy/nemweb/parser.py`, `lander.py`, `source_registry.py`, and bundle resources | Adapted concepts: section-aware MMS rows, direct/nested archives, and external landing separated from Lakeflow | The dispatch chain is disabled at that revision; dirty worktree changes were not used | Databricks DB licence and NOTICE are already reproduced in repository `NOTICE.md`; modified files retain notices where direct adaptation exists |
| `8-gridsense-intelligence-hub` | `33aef7dd75b0abfedd0ea9188f2e11f22a0af680`; committed job/pipeline separation | Architecture only | Conceptual-only HTTP landing Job followed by Lakeflow | Demo-oriented; dirty worktree was not used | No clear repository licence was located, so no code, fixture, or text was copied |
| AEMO NEMWEB | Public Current and MMSDM contracts listed in `DATA_LICENSES.md` | Snapshot/live raw archives and eight typed Delta landing tables | Source data and section contracts | Public source; snapshot remains non-live | AEMO attribution and conditions remain authoritative in `DATA_LICENSES.md` |

## Eight app-critical subjects

The central registry in `source_registry.py` owns discovery, exact MMS identity,
typed fields, natural key, correction order, cadence, Delta destination, and app
dependency for PRICE, REGIONSUM, CONSTRAINT, INTERCONNECTORRES, UNIT_SCADA,
DUDETAILSUMMARY, DUALLOC, and GENUNITS.

## Behavioural migration

Immutable raw ZIPs remain on the mode-scoped managed Volume. The Spark Python
landing task parses each downloaded archive once, inserts immutable source rows
and run associations into Delta, and marks a run visible only after every
required subject reconciles. App-critical Bronze streaming tables retain their
names and dataset types, but stream successful run associations and join the
immutable subject table. Silver and Gold remain materialised views. The critical
orchestration publishes both isolated serving tables only after the exact
pipeline task succeeds; schedules remain paused and pipeline tasks are non-full.

Bids, trading, settlement, market notices, Next Day Dispatch, ML, dashboards,
Genie, and Lakebase are not migrated by this change.
