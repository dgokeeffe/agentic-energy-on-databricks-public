# Workshop fallback

Use prepared fixtures only when a required capability is unavailable or not
released by the checkpoint in the [run of show](workshop-run-of-show.md). Record
the missing capability, switch time, prepared artifact, and limitation in the
pair record. Do not claim that prepared output proves a workspace operation.

| Capability | Prepared path | Local check |
|---|---|---|
| NEMWEB foundation | versioned snapshot in `nemweb_foundation/` | `make foundation-snapshot` |
| AppKit Analytics | `nemweb_app/tests/fixtures/region-status.json` | `make app-test` |
| Lakebase synced table and CDF | `workshop/lakebase/fixtures/investigation-cdf.json` | `make lakebase-test` |
| Historical ML | `nemweb_ml/tests/fixtures/history.json` | `make ml-test` |
| Reviewer availability | a different person or read-only assistant reviews the issue, plan, diff, tests, and eval | record `REQUEST_CHANGES` or `PASS` with cited proof |

The fallback preserves the same domain types, source labels, identity boundary,
CDF ordering, and ML leakage contracts as integration mode. It does not create
or change a project, branch, database, synced table, CDF feed, App, grant,
schedule, model, or endpoint.

Continue through the shared skills:
[understand requirement](../../.agents/skills/understand-requirement/SKILL.md),
[plan change](../../.agents/skills/plan-change/SKILL.md),
[implement and test](../../.agents/skills/implement-test/SKILL.md),
[agentic eval](../../.agents/skills/agentic-eval/SKILL.md), and
[adversarial review](../../.agents/skills/adversarial-review/SKILL.md).
