# Single metadata-driven serverless ingestion architecture

## Decision

Maintain one generic Python ETL workflow through Silver. Do not create one
pipeline or job per source. Source-specific behavior is data in the metadata
contract and parser/adapter registries; orchestration is generic.

The installable `agentic_energy` package owns acquisition, validation,
Bronze/Silver/Quarantine/Gold transformation, reconciliation, and run
manifests. Databricks deployment is a serverless Python wheel Job managed by a
DAB. Lakeflow is optional for a later table-native refinement implementation;
it is not a prerequisite for the metadata framework or the workshop's core
ETL path.

The current local implementation proves the source-independent contract with
fixtures and a real NEMWEB DISPATCHIS adapter. The Databricks deployment target
uses the DAB direct deployment engine and the same package contract.

## Control plane and data plane

Lakebase is the control plane for source definitions. Unity Catalog Delta tables
and volumes are the data plane.

```text
Lakebase: source_metadata, parser versions, schedules, quality rules
                         │
                         ▼
             one serverless Python ETL job
                         │
        validates + snapshots metadata for run_id
                         │
              generic package execution
                         │
          Bronze ─► Quarantine ─► Silver ─► Gold
                         │
              governed Volume/UC output contract
                         │
             optional Delta projections / Genie One
```

### Why snapshot metadata

A live query to Lakebase during pipeline planning would make a run difficult to
reproduce and could change its contract halfway through execution. The
 dispatcher must:

1. read the active metadata rows from Lakebase;
2. validate versions, URLs, parser registrations, keys, watermarks, and quality
   rules;
3. write an immutable `metadata_snapshot` for `run_id` to a governed UC
   location;
4. pass only `run_id`, `metadata_snapshot_id`, source selection, and bounded
   time-window parameters to workers; and
5. record the snapshot ID in every Bronze/Silver run manifest.

Lakeflow refinement should read the immutable UC snapshot, not make an
untracked external Lakebase call at planning time.

## Lakebase metadata contract

The control-plane table should contain at least:

```text
source_id                    primary key
source_version
active
provider
dataset
url_or_fixture_path
extraction_mode              fixture | live
file_name_regex
format
compression
parser_key
schema_reference
source_timezone
event_timestamp_field
ingestion_timestamp_field
natural_key                   ordered array
watermark_field
deduplication_rule
quality_checks                JSON/array
quarantine_policy
schedule
serverless_worker_key
landing_volume_path
target_catalog
target_schema
licensing_provenance
updated_at
updated_by
```

Metadata changes need an approval/audit path. The dispatcher must reject an
unknown `parser_key`, unsupported source version, unsafe URL, invalid timezone,
missing natural-key component, or unapproved license/provenance before any
landing side effect.

## Serverless execution model

There are two acceptable execution shapes, with the same maintenance rule:

- **Preferred:** one Lakeflow Job with a generic `for_each` task. The dispatcher
  supplies a list of validated source snapshots; every iteration invokes the
  same worker entry point.
- **When isolation is needed:** one dispatcher invokes one generic serverless
  worker job through the Jobs API for each source snapshot. The worker job is
  still a single maintained definition; metadata supplies `source_id`, parser,
  and run parameters. The dispatcher waits for every child run and fails the
  parent if any selected source fails.

Do not store arbitrary executable code or Databricks job definitions in
Lakebase. Metadata selects a registered adapter/worker key; it does not become
an unreviewed code execution surface.

Every execution receives:

```text
run_id
metadata_snapshot_id
source_id
window_start
window_end
mode
landing_path
catalog
schema
```

Every execution emits:

```text
run_id
source_id
metadata_snapshot_id
adapter_version
parser_version
retrieval_uri
payload_sha256
bronze_count
accepted_count
quarantine_count
deduplicated_count
silver_count
watermark
freshness
status
failure_stage
failure_code
```

## NEMWEB source boundary

The local live adapter targets the public `DispatchIS_Reports` directory and
selects the latest matching `PUBLIC_DISPATCHIS_*.zip`. It parses:

- `PRICE`: regional `RRP`;
- `REGIONSUM`: regional `TOTALDEMAND`; and
- `SETTLEMENTDATE`, `REGIONID`, `DISPATCHINTERVAL`, and `INTERVENTION` as the
  join and lineage context.

The canonical Silver input is one row per `(region, interval_datetime)`. The
retrieval URL, archive name, source record types, and source line numbers remain
in Bronze/lineage evidence. A live run is not deterministic because NEMWEB
changes; deterministic fixtures remain the CI and workshop fallback.

## Workshop mapping

- **Business participants** use the governed Gold projection in Genie One,
  combining it with one preflighted SharePoint or Confluence context source
  during Brief → Research → Analysis stages.
- **Technical participants** change Lakebase metadata or a registered parser,
  then prove that the same dispatcher and worker produce correct Bronze/Silver
  results without a new source-specific workflow.

The shared gate is the run manifest and reconciliation evidence, not a screenshot
of a successful job.

## Deployment prerequisites

Before deploying the Databricks target, confirm:

- a UC catalog/schema and landing Volume;
- a Lakebase project/database and a read-only metadata access path for workers;
- secret/OAuth handling for Lakebase and any permitted source;
- serverless Jobs/Lakeflow availability and workspace permissions;
- source licensing/provenance approval for live NEMWEB retrieval; and
- Genie One and the selected SharePoint/Confluence connector and identity
  boundaries for the business lane, plus a curated cited fallback.
