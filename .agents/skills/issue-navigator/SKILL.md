---
name: issue-navigator
description: Select and route one workshop-ready GitHub issue through the shared pair lifecycle.
---

# Issue navigator

1. List open GitHub issues carrying `workshop-ready`; do not invent local tickets.
2. The pair selects one issue and records its number and operator outcome.
3. Inspect the issue, `nemweb_foundation/`, and the named starter (`nemweb_app/`,
   `nemweb_ml/`, or `workshop/lakebase/`).
4. Continue in order through `understand-requirement`, `plan-change`, human
   approval, `implement-test`, `agentic-eval`, `adversarial-review`, and
   `prepare-pull-request`.
5. A person accepts, sends back, rejects, or stops. Agents never merge or deploy.

Keep one business responsibility and one engineering responsibility in the
pair. Participants may inspect `nemweb_foundation/`, but must not deploy,
provision, change grants, run jobs, enable live data, or change schedules.
