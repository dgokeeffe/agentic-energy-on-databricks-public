---
name: minutes-trigger-cli-warning-is-stale
description: The MINUTES trigger-unit warning from Databricks CLI v1.7.0 is a stale enum, not a YAML defect
metadata:
  type: reference
---

`nemweb_foundation/resources/nemweb_refresh.job.yml` sets
`trigger.periodic.unit: MINUTES`. Databricks CLI v1.7.0 warns `invalid value
"MINUTES" for enum field. Valid values are [DAYS HOURS WEEKS]`.

**The warning is wrong.** Verified 2026-09-09: after deploying, reading the job
back from the Jobs API returns `{'interval': 5, 'unit': 'MINUTES'}` stored
verbatim. The five-minute cadence is deliberate and documented at length in that
file, so the YAML must not be "fixed" to satisfy the CLI.

**Consequence:** `nemweb_foundation/scripts/deploy.sh` hardcodes `--strict`, and
strict mode rejects all warnings, so that script cannot run in this environment.
Use `bundle validate` (non-strict) then `bundle deploy`, which is what
`scripts/deploy-workshop.sh` does. Either pin an older CLI or relax `--strict` in
`deploy.sh` to fix it properly.

See [[workspace-deployment-constraints]].
