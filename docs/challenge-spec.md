# Agentic Energy Data Workshop — Specification

> **Status:** Workshop contract with a local MVP and real NEMWEB DISPATCHIS
> acquisition adapter. Databricks Lakebase/serverless deployment remains an
> implementation exercise. This document defines the challenge contract,
> architecture, lane boundaries, validation requirements, and stop conditions.

---

## 1. Overview

This challenge gives participants a bounded, realistic energy-market data
foundation on Databricks and asks them to operate on it in one of two lanes:
a business-experience lane using Genie One plus one approved SharePoint or
Confluence context source, or a software-engineering lane using a coding/code-
review agent.

The shared foundation is a metadata-driven Lakeflow pipeline ingesting public
AEMO/NEMWEB market data and weather enrichment, refining it through
Bronze/Silver/Gold layers, and syncing curated Gold into Lakebase for
low-latency consumption. A native writable Lakebase table holds participant
annotations. Both lanes consume the same foundation; neither lane may define a
separate data store.

The challenge is designed for a single-day workshop with 20–30 senior
participants in teams of 2–3.

## 2. Learning outcomes

Participants who complete the challenge will have demonstrated:

- Metadata-driven multi-source ingestion with deterministic fixtures and live
  acquisition modes.
- Lakeflow Bronze/Silver/Gold refinement with deduplication, quarantine, and
  quality expectations.
- Lakebase synced-table read-only consumption alongside native writable
  application state.
- Governed natural-language data access through Genie One and Genie Agent, with
  identity-bound permissions and source/freshness context.
- Agent-assisted code review against a deliberately flawed pipeline, with
  evidence-based findings, proposed patches, and tests — without automatic
  merge or deployment.

## 3. Audience

| Lane | Audience | Primary surface |
|---|---|---|
| A | Business-facing analysts, operators, energy-market staff | Brief → Research → Analysis in Genie One + one approved SharePoint/Confluence source |
| B | Software engineers, data engineers | Lakebase metadata + one serverless ingestion workflow |

All participants complete the common data foundation first. Then each team
selects **one** lane. Completing both lanes is an optional stretch goal.

## 4. Challenge flow

```
1. Common foundation (all participants)
   ├── Understand the metadata contract and NEMWEB source grain
   ├── Run the facilitator's live NEMWEB run or deterministic fixtures
   ├── Verify Bronze/Silver/quarantine counts, keys, timezone, and freshness
   └── Read the shared governed projection in Genie One

2. Lane selection (one required)
   ├── Lane A: Business value
   │   ├── Write a decision brief and value hypothesis
   │   ├── Research NEMWEB plus permitted SharePoint/Confluence context
   │   ├── Analyze in Genie One with source/freshness evidence
   │   └── Produce a recommendation and next action
   └── Lane B: Metadata-driven engineering
       ├── Read the source contract and current run evidence
       ├── Add/change metadata in Lakebase, not orchestration code
       ├── Run the single generic serverless path through Silver
       ├── Prove replay, quarantine, deduplication, and timezone behavior
       └── Extend with a new source without a new pipeline

3. Stretch (optional)
   ├── Add a second live NEMWEB report family
   ├── Lakebase synced Gold and native annotations
   ├── Selected SharePoint or Confluence connector and identity-bound Genie One analysis
   └── Lakebase CDF back to Delta
```

## 5. Deliverables

### Common foundation

- A validated NEMWEB market metadata entry and weather enrichment entry.
- A facilitator run manifest with Bronze/Silver/quarantine reconciliation.
- A governed projection with source, freshness, and lineage context.

### Lane A — Business value

- A decision brief with a measurable value hypothesis.
- A research log citing NEMWEB and the selected SharePoint or Confluence source.
- A Genie One analysis with method, uncertainty, recommendation, and next action.

### Lane B — Engineering

- A metadata change or registered parser change, with no new source-specific
  orchestration.
- Evidence that the single serverless workflow reads Lakebase metadata and
  produces correct Bronze/Silver results.
- Tests or run evidence for replay, quarantine, deduplication, timezone, and
  failure handling.

## 6. Evaluation

| Dimension | Signal |
|---|---|
| Foundation | Metadata validates; fixtures ingest deterministically; Silver dedup/quarantine correct; Gold grain/freshness checks pass |
| Lakebase | Synced Gold key/row-count/freshness reconciles; synced relation is read-only to participants; annotation CRUD authorized; audit fields present; logical referential integrity holds |
| Lane A | Brief is decision-led; research cites NEMWEB and the selected context source; analysis is governed, explicit about uncertainty, and actionable |
| Lane B | Metadata drives the same worker path; Silver invariants and run evidence reconcile; no source-specific pipeline is introduced |

## 7. Shared data foundation

### 7.1 Data sources

| Source | Provider | Dataset | Role |
|---|---|---|---|
| AEMO NEMWEB | AEMO | Dispatch price/demand report family (bounded) | Market: region, interval, demand, price |
| Weather | Open-Meteo (workshop default) or Bureau of Meteorology | Observations for 1–2 stations mapped to NEM regions | Weather: region, interval, temperature |

Acquisition is a **scheduled Python task** that reads metadata-configured URLs,
preserves source files and retrieval metadata in a Unity Catalog volume, and
then hands off to Lakeflow for refinement. Lakeflow does not scrape sources
inside declarative table functions.

### 7.2 Fixture and live modes

- **Fixture mode:** checked-in deterministic sample files (ZIP/CSV) guarantee
  repeatable offline execution and CI evidence.
- **Live facilitator mode:** the current adapter reads the latest public AEMO
  NEMWEB DISPATCHIS ZIP/CSV, joins PRICE and REGIONSUM records, and emits the
  same canonical market rows. Confirm source terms and network policy before
  scheduling it; live tests must fail clearly when the endpoint is unavailable.

### 7.3 Metadata contract

Every data source is described by a metadata entry with at minimum:

| Field | Description |
|---|---|
| `source_id` | Unique source identifier |
| `source_version` | Source schema/version |
| `provider` | AEMO, BOM, Open-Meteo |
| `dataset` | Dataset name or report family |
| `region` | NEM region or station identifier |
| `url_or_fixture_path` | Live URL or fixture file path |
| `format` | ZIP, CSV, JSON |
| `compression` | none, gzip, zip |
| `extraction_mode` | fixture, live |
| `schedule` | Cron or interval |
| `event_timestamp_field` | Source event time field |
| `ingestion_timestamp_field` | Landing timestamp |
| `source_timezone` | Source TZ (AEST/AEDT for NEM) |
| `schema_reference` | Schema name and version |
| `natural_key` | Business key (e.g. region + interval) |
| `watermark_field` | Field for incremental watermark |
| `deduplication_rule` | How duplicates are resolved |
| `quality_checks` | Expectations or validation rules |
| `quarantine_policy` | Malformed-row handling |
| `licensing_provenance` | License and provenance notes |

Illustrative YAML:

```yaml
sources:
  - source_id: aemo_dispatch_scada
    source_version: "1.0"
    provider: AEMO
    dataset: DISPATCH_SCADA
    region: NEM
    url_or_fixture_path: fixtures/aemo/PREDISPATCHSCADA_*.zip
    format: zip
    compression: zip
    extraction_mode: fixture
    schedule: "0 */30 * * *"
    event_timestamp_field: INTERVAL_DATETIME
    ingestion_timestamp_field: _ingested_at
    source_timezone: Australia/Sydney
    schema_reference: mms_dispatch_scada_v1
    natural_key: [REGIONID, INTERVAL_DATETIME]
    watermark_field: INTERVAL_DATETIME
    deduplication_rule: last_by_ingestion_timestamp
    quality_checks:
      - demand_mw >= 0
      - price_per_mwh is not null
    quarantine_policy: isolate_with_reason
    licensing_provenance: "AEMO public NEMWEB data; workshop use only"
```

### 7.4 Lakeflow layers

| Layer | Responsibility | Key invariants |
|---|---|---|
| **Bronze** | Immutable landing of raw source files with retrieval metadata | Traceable to source file; no transformation; append-only |
| **Silver** | Typed, normalized, deduplicated conformed data | Explicit NEM timezone handling; dedup by natural key + last watermark; quarantine records with reason codes and source lineage |
| **Quarantine** | Malformed rows with reason codes | Reason code, source file, row identifier, rejection timestamp |
| **Gold** | Market/weather views or tables at a documented grain | Stable keys, freshness metadata, joined market + weather by region/interval |

Lakeflow owns refinement and quality enforcement. The acquisition Python task
owns retrieval and landing only.

### 7.5 DAB ownership

The future deployable repository will use Databricks Asset Bundles (DAB) to
declare:

- Jobs (acquisition task, refresh schedule)
- Lakeflow pipeline resources
- Permissions and variables
- Environment targets (dev, workshop)

All workspace IDs, catalog/schema names, endpoint names, principals, schedules,
and tenant-specific values are **TODO placeholders** in the specification and
must be filled during scaffold implementation — not fabricated now.

## 8. Lakebase contract

Lakebase is a required application-state component, not an optional checkbox.

### 8.1 Synced Gold (read-only)

Selected Gold projections are synced **read-only** into Lakebase for
low-latency consumption. The synced relation:

- Preserves stable source keys, freshness markers, and reconciliation counts.
- Is **read-only to participants.** Direct writes interfere with managed sync
  and may be overwritten. Participants must never update the synced Gold table.
- Supports Snapshot sync mode (Triggered/Continuous requires Delta Change Data
  Feed and is stretch-only).

### 8.2 Native annotations (writable)

A native Lakebase `operator_annotations` table is owned by the application:

| Column | Type | Description |
|---|---|---|
| `annotation_id` | UUID/serial | Stable annotation ID |
| `gold_entity_key` | text | Gold entity/business key (e.g. region + interval) |
| `note` | text | Annotation content |
| `status` | text | Status/category (e.g. reviewed, flagged, acknowledged) |
| `author_identity` | text | Author identity (UC principal or app SP) |
| `created_at` | timestamptz | Creation timestamp |
| `updated_at` | timestamptz | Last update timestamp |
| `audit_version` | int | Audit/version counter |

Cross-relation foreign-key enforcement is **capability-dependent**. If a
physical FK from the native table to the synced read-only relation is not
supported, logical referential validation is required instead.

### 8.3 Workflow

1. A user or agent reads the synced Gold context (market/weather briefing).
2. The user or agent creates or updates a native annotation under its own
   authorization boundary.
3. Subsequent lane output surfaces the annotation and its audit context.
4. Annotations do **not** mutate Gold and do **not** flow back to AEMO.

### 8.4 Role separation

| Role | Permissions |
|---|---|
| Sync owner | Write to synced-table sync process; participants do not have this role |
| Reader | SELECT on synced Gold table |
| Annotator | INSERT/UPDATE on native annotations table |

### 8.5 Lakebase CDF (stretch only)

Lakebase Change Data Feed can capture native Postgres table changes into Unity
Catalog Delta. This is **Public Preview** and is an instructor-pre-provisioned
optional extension. It is **not** reverse write-back into the synced Gold
source. The core challenge requires only transactional write/read in native
Postgres.

## 9. Lane A — Business experience

### 9.1 Capability boundary matrix

Four distinct integration boundaries must not be conflated:

| Component | Intended role | Control plane | Data/tool surface | Identity/auth boundary | Verification evidence | Prohibited assumptions |
|---|---|---|---|---|---|---|
| **Genie One** | Business-user shell / unified entry point over approved governed data and workflows | Databricks workspace | UC data, dashboards, queries, metric views, Genie Agents | Workspace auth + `genie` OAuth scope for MCP | TBD/preflight | Do not assert direct Lakebase access, M365 embedding, or tool support until verified |
| **Genie Agent** | Curated natural-language data agent over UC data, instructions, example SQL, trusted assets | Databricks workspace (per-agent) | UC objects in agent scope | SQL/consumer entitlement + Agent ACL + SELECT on underlying UC objects; author's embedded compute credential; end-user row filters/masks apply | TBD/preflight | Do not assert invocation method, supported assets, citation behavior, or permissions without current product docs |
| **Selected document connector** | Identity-bound access to one approved context source | Microsoft 365 tenant or Confluence site | Selected SharePoint or Confluence content only | Per-user OAuth or connector identity; tokens not shared | TBD/preflight | Select one source before the workshop; do not describe it as a Genie Agent, data sync bypass, or unrestricted document search |
| **Managed MCP** | Separately governed tool-exposure boundary | Databricks workspace (Managed MCP Servers preview) | Genie One MCP, Genie Agent MCP, AI Search, Databricks SQL, UC functions | Workspace auth + per-server OAuth scope | TBD/preflight | Do not imply MCP provides M365 connectivity, shares connector auth, bypasses UC/Lakebase permissions, or is automatically consumable by any client |

### 9.2 Provisional interaction diagram

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Genie One   │────▶│  Genie Agent │────▶│  UC Gold tables  │
│  (shell)     │     │  (curated)   │     │  (market/weather)│
└──────┬───────┘     └──────────────┘     └────────┬─────────┘
       │                                            │
       │ TBD/preflight                               │ sync (read-only)
       │                                            ▼
┌──────▼───────┐                           ┌──────────────────┐
│  Selected    │                           │  Lakebase        │
│  document    │                           │  synced Gold     │
│  connector   │                           │  (read-only)     │
│ (identity)   │                           └────────┬─────────┘
└──────────────┘                                    │
       │ TBD/preflight                               │ join in Postgres
       │                                            ▼
┌──────▼───────┐                           ┌──────────────────┐
│  Managed MCP │                           │  operator_       │
│  (governed   │                           │  annotations    │
│   tool edge) │                           │  (native, writable)│
└──────────────┘                           └──────────────────┘
```

All edges labeled `TBD/preflight` require confirmation against current product
and tenant documentation before implementation.

### 9.3 Business-lane output requirements

- Answers must include governed source and freshness context.
- The annotation workflow must be used without exceeding the caller's
  permissions.
- Genie Agent grounding SQL and example questions must be tuned to the shared
  Gold foundation.

## 10. Lane B — Software engineering

### 10.1 Agent task

The coding/code-review agent:

1. Reviews a deployable starter repository containing intentionally seeded
   defects.
2. Traces code against the metadata contract, data-quality expectations, and
   Lakebase contracts defined in this specification.
3. Produces prioritized findings with file/line evidence.
4. Proposes a patch.
5. Adds or updates tests.

Execution and merge remain **human-controlled**. The agent does not merge or
deploy.

### 10.2 Seeded defect categories

The future scaffold will contain intentional, bounded defects across
representative categories:

| Category | Example |
|---|---|
| Schema/metadata drift | Code assumes a field name or type that diverges from the metadata contract |
| Timezone or watermark/idempotency handling | NEM timestamps not converted from AEST/AEDT; watermark not applied; re-runs produce duplicates |
| Quarantine bypass | Malformed rows silently dropped instead of quarantined with reason codes |
| Unsafe annotation access or authorization | Annotation CRUD without identity check or role separation |
| Gold-to-Lakebase key/reconciliation handling | Synced key mismatch; reconciliation count not checked |

Participant-visible symptoms and evaluation signals are defined in this
specification. The **exact defect locations and answers** are kept in a
separate organizer-controlled artifact — not in this participant repository.

### 10.3 Authority boundaries

- Sandboxed credentials; least privilege.
- No arbitrary production writes.
- No secret exfiltration.
- No automatic merge or deployment.

## 11. Work orchestration (Beads)

The challenge uses [Beads](https://beads.gascity.com/) (`bd`) as the AI-native
work orchestrator. Beads replaces ad-hoc ticket lists and markdown plans with a
persistent, dependency-aware work graph backed by a Dolt version-controlled
database.

### 11.1 Why Beads

| Beads concept | Challenge role |
|---|---|
| **Beads (issues)** with hash IDs | Seeded defects in Lane B become beads; multiple teams/agents work concurrently without ID collisions |
| **`bd ready`** (dependency frontier) | Enforces "common foundation before lane work" — teams cannot claim lane beads until foundation beads are closed |
| **Gates** (`human`, `gh:pr`, `gh:run`) | Machine-enforced governance: agent can produce findings/patches, but a human gate blocks merge; a `gh:pr` gate blocks until CI passes |
| **Formulas → molecules** | The entire challenge flow (foundation → lane → stretch) declared as a TOML formula, poured per team |
| **Dolt sync** | Facilitators push new defects or updates to all teams mid-workshop; teams sync and pick up new ready work |
| **`bd prime`** | Agent context injection survives session death — the next agent pickup knows exactly where work stopped |
| **`.beads/issues.jsonl`** | Passive export for facilitator dashboards / scoring |

### 11.2 The challenge formula

The challenge flow is defined in `.beads/formulas/agentic-energy-challenge.formula.toml`.
A facilitator cooks the formula and pours one molecule per team:

```bash
bd cook agentic-energy-challenge
bd mol pour <proto-id> --var team=team01
```

Each molecule instantiates the full dependency graph:

```
foundation-metadata → foundation-ingest → foundation-lakeflow → foundation-lakebase
  → [human gate: foundation review]
  → lane-select
     ├── lane-a-genie → lane-a-annotations → [human gate: lane-a review]
     └── lane-b-defect-scan → lane-b-patch → [gh:pr gate] → [human gate: merge]
```

`bd ready` shows only unblocked, claimable work. Closing a bead automatically
unblocks its dependents — no re-planning needed.

### 11.3 Gates as governance

The key thesis — *the agent changes code, the human owns merge and deploy* — is
enforced by gates, not by promises:

| Gate | Type | Blocks | Who can resolve |
|---|---|---|---|
| Foundation review | `human` | Lane selection | Facilitator only (`bd gate resolve`) |
| Lane A review | `human` | End of lane A | Facilitator only |
| CI check | `gh:pr` | Merge gate | Auto-resolves when PR CI passes (`bd gate check`) |
| Merge | `human` | End of lane B | Human only — the agent cannot close this |

Agents can claim, investigate, patch, and close task beads. They cannot resolve
human gates. This is the machine-enforced boundary that replaces procedural
"don't merge" rules.

### 11.4 Seeded defect beads

Lane B participants claim seeded defect beads via `bd ready`. Each defect bead
describes a **symptom**, not the answer. The defect categories from §10.2 are
represented as separate beads:

| Defect bead | Category |
|---|---|
| Silver timezone not converted from AEST/AEDT | Timezone handling |
| Malformed rows silently dropped instead of quarantined | Quarantine bypass |
| Annotation CRUD missing identity check | Unsafe annotation access |
| Gold-to-Lakebase sync key mismatch | Gold-to-Lakebase key/reconciliation |

The exact defect locations and answers are kept in a separate organizer-controlled
artifact — not in the participant beads or repository.

### 11.5 Multi-agent coordination

Beads' hash-based IDs prevent collisions when multiple agents work concurrently.
For a 20–30 person workshop with teams of 2–3, each team pours its own molecule:

```bash
bd mol pour <proto-id> --var team=team01
bd mol pour <proto-id> --var team=team02
bd mol pour <proto-id> --var team=team03
# ...
```

All molecules share the same formula but have independent dependency graphs.
Facilitators can push new defects or updates via Dolt sync mid-workshop:

```bash
bd dolt push   # facilitator pushes updates
bd dolt pull   # teams pull new ready work
```

## 12. Validation contract

### 12.1 Common foundation checks

| Check | Description |
|---|---|
| Metadata schema validation | Every source entry conforms to the metadata contract |
| Deterministic fixture ingestion | Fixtures produce identical Bronze/Silver/Gold on repeated runs |
| Retry/idempotency behavior | Re-running acquisition does not duplicate Bronze rows |
| Bronze lineage/count checks | Bronze row count matches fixture file count; lineage to source file present |
| Silver type/dedup/key/timezone checks | Silver columns typed; duplicates resolved by natural key + watermark; NEM timezone explicit |
| Malformed-row quarantine with reason codes | Malformed rows isolated with reason code and source lineage |
| Gold grain/metric/freshness checks | Gold at documented grain; metrics computed; freshness metadata present |
| Live-source tests | Skip or fail clearly when network/credentials unavailable |

### 12.2 Lakebase checks

| Check | Description |
|---|---|
| Synced Gold key/row-count/freshness reconciliation | Synced table keys and row counts match Gold source; freshness marker current |
| Synced relations read-only to participants | Participant role cannot INSERT/UPDATE/DELETE on synced table |
| Native annotation create/read/update authorization | Annotator role can CRUD; reader role cannot write; audit fields populated |
| Audit fields | `created_at`, `updated_at`, `audit_version` present and correct |
| Logical referential integrity | Annotation keys resolve to Gold entities (logical check if physical FK unsupported) |
| End-to-end scenario | At least one scored scenario consumes both synced Gold and a native annotation |

### 12.3 Lane A checks

| Check | Description |
|---|---|
| Source/freshness context | Genie One answers include governed source and freshness context |
| Identity enforcement | Answers respect caller's UC permissions and row filters |
| Annotation workflow | At least one annotation created and joined to synced Gold |

### 12.4 Lane B checks

| Check | Description |
|---|---|
| Defect detection | Seeded defect classes detected |
| File/line evidence | Findings cite specific file and line numbers |
| Safe remediation | Patch does not write to production, exfiltrate secrets, or auto-merge |
| Tests | Updated or added tests pass |

### 12.5 Deployment/security checks (future scaffold)

| Check | Description |
|---|---|
| DAB schema/validate | Succeeds for documented targets |
| TODO variables | Fail clearly when unset |
| Secrets | Referenced, not committed |
| Permissions | Least privilege |

### 12.6 Documentation-phase checks (this phase)

| Check | Description |
|---|---|
| Tracked files | Exactly `README.md` and `docs/challenge-spec.md` |
| Links/headings | Render correctly |
| Required sections | All sections present (Overview through Stop Conditions) |
| TODO/preflight items | Searchable |
| Markdown/whitespace | Valid; no trailing whitespace issues |

### 12.7 Beads checks

| Check | Description |
|---|---|
| Formula validates | `bd formula show agentic-energy-challenge` succeeds with 13 steps |
| Molecule pours | `bd mol pour` creates the expected bead count per team |
| Ready frontier correct | `bd ready` shows only unblocked beads; blocked beads excluded |
| Gates block correctly | Human gates cannot be resolved by agents; `gh:pr` gates block until CI passes |
| Sync works | `bd dolt push` / `bd dolt pull` propagates changes between facilitator and teams |
| Defect beads claimable | Seeded defect beads appear in `bd ready` after lane-select closes |

## 13. Assumptions and defaults

The following defaults are approved for unanswered choices:

| Decision | Default |
|---|---|
| Weather enrichment | Open-Meteo (workshop default) |
| Starter repository | Future deployable repo with explicit TODOs |
| Code-review defects | Intentionally seeded, bounded, organizer-controlled key |
| Lane model | Common foundation first, then one lane choice; second lane optional stretch |
| Data sources | Bounded AEMO dispatch price/demand + 1–2 weather stations mapped to NEM regions |

## 14. Preflight decisions (unresolved)

The following require confirmation against current product documentation and
the target Agentic Energy tenant before any scaffold or integration work may begin:

| ID | Decision | Blocks |
|---|---|---|
| PF-1 | Genie One availability and surface in target workspace | Lane A scaffold |
| PF-2 | Genie Agent invocation, supported assets, citation behavior, permissions | Lane A scaffold |
| PF-3 | Select SharePoint or Confluence; verify connector type, tenant/site, consent, scopes, identity mapping, and cited fallback | Lane A context integration |
| PF-4 | Managed MCP endpoint availability, supported tools, caller identity, authorization, auditability | Lane A MCP edge |
| PF-5 | Identity propagation: UC principals, service principals, app registration/consent, per-user Microsoft OAuth | All scaffold |
| PF-6 | Network policy and permitted managed MCP endpoints | All scaffold |
| PF-7 | Lakebase autoscaling availability in target region | Lakebase scaffold |
| PF-8 | AEMO data use authorization and BOM feed terms compliance | Live acquisition |
| PF-9 | Coding assistant and repository host allowed by Agentic Energy policy; may source leave the tenant | Lane B |
| PF-10 | Participants create resources vs. modify bundle-managed definitions only | Scaffold permissions |

No document-connector, Genie, MCP, identity, deployment, or live-data scaffold work may
start until the relevant preflight decisions are verified.

## 15. Non-goals

- No full scaffold in this phase (specification only).
- No production SLA.
- No real-time market platform.
- No writeback into AEMO/NEMWEB.
- No production SharePoint or Confluence rollout.
- No unrestricted document search or copying selected context into Gold.
- No automatic code merge or deployment.
- No claim of verified Agentic Energy tenant capability.

## 16. Stop conditions

### 15.1 Repository stops (this phase)

- **Do not create the GitHub repository** if the authenticated principal cannot
  create under `dgokeeffe`, or if the repository name already exists with
  unexpected contents or ownership.
- **Do not publish** if private visibility cannot be guaranteed.
- Stop and remediate if visibility changes, unexpected files appear, secrets
  are detected, the remote target is wrong, or the working tree is not clean.

### 15.2 Downstream implementation stops (scaffold phase)

- No scaffold, resource provisioning, or integration testing until all
  applicable preflight decisions (PF-1 through PF-10) are resolved.
- Stop if AEMO data use is unauthorized.
- Stop if secrets or participant data cannot be kept out of Git.
- Stop if any request is made to make the repository public without explicit
  approval.

Failures must **stop**, not fall back to a personal namespace, public
visibility, guessed capabilities, or embedded credentials.

---

*This specification is the source of truth for the Agentic Energy Data Workshop.
It is deliberately specification-only. The scaffold phase will implement the
architecture described here once preflight decisions are resolved.*
