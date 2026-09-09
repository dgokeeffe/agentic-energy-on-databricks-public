# Workshop prerequisites

Complete this checklist before the workshop. The required participant path is
local-first. Workspace features are used only when the named preflight item has
current evidence and the facilitator releases that activity.

Never put tokens, passwords, client secrets, private workspace URLs, tenant
identifiers, or participant data in this repository, an AI-assistant prompt,
test output, screenshots, or a pair record.

## Responsibilities

### Workspace administrator

The workspace administrator must:

- provide the approved Databricks workspace, Unity Catalog catalog and schema,
  SQL warehouse, landing Volume name, and account-level principals;
- configure the participant and facilitator groups with the least permissions
  needed for the approved workshop path;
- confirm identity, network, data-use, repository-host, coding-assistant, and
  resource-creation policies;
- decide which optional Genie, MCP, Lakebase, live-data, and app capabilities
  may be used; and
- give the facilitator dated evidence for PF-1 through PF-10. An assertion that
  a feature should exist is not evidence.

The administrator must not provide credentials for inclusion in Git or chat.

### Facilitator

The facilitator must:

- record the current status and evidence for every applicable PF item in the
  table below;
- prepare the labelled substitutes in
  a labelled prepared substitute for any required
  surface that is not verified;
- confirm that each participant has chosen one track and knows where its
  `Instructions.md` is;
- provide a clean participant clone;
- keep workspace access validation-only during this preparation task; and
- stop rather than guess when the selected profile, target workspace, Unity
  Catalog resources, permissions, or policy do not match the approved setup.

Every workspace-aware facilitator command must select `--profile DEFAULT`
explicitly. Do not use an implicit profile, set a default profile as a
substitute, deploy the bundle, run jobs, or unpause schedules during
preparation.

### Participant

Each participant must:

- have Git, Python 3.10 or later, and `uv` available locally;
- use only a coding assistant and repository host approved under PF-9;
- join a cross-functional pair with named business outcome and engineering
  quality responsibilities;
- read [`QUICKSTART.md`](QUICKSTART.md) and the
  their chosen track's `Instructions.md`;
- be able to edit the pair record and run `make validate-local`; and
- avoid credentials, private tenant details, merge, deployment, live job runs,
  and schedule changes on the required workshop path.

Participants do not need Databricks administrator credentials. A facilitator
must release any workspace activity only after the relevant PF item passes.

## Local software check

Run these commands from the repository root:

```bash
git --version
python3 --version
uv --version
python3 scripts/validate-miniwiki.py
```

Each pair also confirms that the selected issue is labelled `workshop-ready`
and names deterministic tests. Do not edit before the exact plan is approved.

## Facilitator profile and bundle validation

First copy the placeholder file to the ignored local environment file and
replace every placeholder with an approved, non-secret value:

```bash
cp -f env.example .env
set -a
. ./.env
set +a
```

Keep `.env` local. Do not commit it. Databricks authentication belongs in the
local CLI configuration, not in `env.example`, `.env`, shell history, or a
workshop document.

The facilitator must then run only these validation commands, with the profile
shown on every workspace-aware command:

Substitute your own Databricks CLI profile name for `<profile>`. This repository
does not fix a profile name; it only requires that one is always named, so no
command runs against an implicit default workspace.

```bash
databricks auth describe --profile <profile>
(cd nemweb_foundation && databricks bundle validate --strict -t dev --profile <profile>)
```

Stop if the profile is absent, unauthenticated, points to an unexpected workspace,
or cannot validate the approved isolated development catalog, schema, and
Volume. Validation does not authorise `bundle deploy`, `jobs run-now`, pipeline
updates, live NEMWEB access, or schedule changes.

## PF-1 through PF-10

All items begin **unverified** for a new workshop or workspace. Replace the
status only after the facilitator records current, dated evidence. If an item
is not needed because its feature is omitted, record **not used** and use the
published prepared substitute where the required path calls for one.

| ID | Administrator decision | Facilitator evidence required | Initial status |
|---|---|---|---|
| PF-1 | Approve the SQL warehouse, Unity Catalog permissions, supported metric-view YAML version, and Genie compatibility over Gold. | Named-profile validation result, supported version, named warehouse, and permission check. | Unverified |
| PF-2 | Confirm Genie One availability and the supported surface for the selected agent and metric view. | Dated target-workspace capture or labelled prepared substitute. | Unverified |
| PF-3 | Confirm Genie Agent creation, supported assets, citation behaviour, and permissions. | Dated supported-answer and refusal captures with source and owner. | Unverified |
| PF-4 | Approve one Managed MCP endpoint, its tools, caller identity, authorisation, and audit trail, or approve no MCP. | Named approved endpoint and access limit, or recorded "no MCP" decision. | Unverified |
| PF-5 | Approve Unity Catalog principals, service principals, app registration and consent, and any per-user Microsoft OAuth. | Identity-flow record with no credentials or tokens. | Unverified |
| PF-6 | Approve network policy and permitted Managed MCP endpoints. | Named policy decision and connectivity validation using the named profile where Databricks is involved. | Unverified |
| PF-7 | Confirm whether Lakebase autoscaling is available in the target region. | Dated capability result or "not used"; Lakebase is optional. | Unverified |
| PF-8 | Approve AEMO data use and confirm compliance with applicable BOM feed terms. | Recorded approval and required attribution; otherwise snapshot-only. | Unverified |
| PF-9 | Approve the coding assistant and repository host, and decide whether source may leave the tenant. | Named tools, data-handling decision, and participant briefing. | Unverified |
| PF-10 | Decide whether participants may create resources or may only modify bundle-managed definitions. | Written permissions model and released activities. | Unverified |

No document connector, Genie, MCP, identity integration, deployment, or live-data
activity may start until its applicable PF items are verified. Use the
a labelled prepared substitute when the switching
trigger fires.
