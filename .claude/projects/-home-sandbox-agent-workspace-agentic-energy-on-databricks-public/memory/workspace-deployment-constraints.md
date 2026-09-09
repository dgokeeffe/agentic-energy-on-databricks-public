---
name: workspace-deployment-constraints
description: Deployment constraints for the Azure australiaeast workshop workspace
metadata:
  type: project
---

Workshop deployed to the approved Azure `australiaeast` workspace on 2026-09-09.
The workspace ID, host, and account ID are deliberately omitted: they are tenant
identifiers and must not enter Git. Read them from the selected CLI profile with
`databricks auth describe`.

Constraints discovered that are not derivable from the repo:

- **Catalog creation is impossible via API/SQL.** The account has Default Storage
  enabled, so `catalogs create`, `CREATE CATALOG`, and `CREATE CATALOG ... MANAGED
  LOCATION` all fail with "Please use the UI to create a catalog with Default
  Storage." A catalog must be created by a human in the UI first.
- Deployment therefore targets catalog `edp_entdata_exp_dev_landing`, where the
  `App-DG-ENTDATA-Engineer` group holds `ALL_PRIVILEGES` + `MANAGE`. The repo's
  original `agentic_energy_workshop` catalog does not exist here.
- Only the `DEFAULT` CLI profile exists; the repo originally hardcoded `daveok`.
- `gh` CLI is **not installed** on this sandbox and there is no `~/.config/gh`.
  Git authenticates through a Databricks credential helper, so a PR cannot be
  opened from this box without installing and authenticating `gh` first.

See [[minutes-trigger-cli-warning-is-stale]].
