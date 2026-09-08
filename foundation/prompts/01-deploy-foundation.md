# Prompt 01 — deploy the foundation

Use this prompt in a **fresh conversation**. This stage ends with a reviewed
deployment summary and both schedules paused. It does not run the pipeline.

```text
This is a fresh conversation. You are assisting the workshop facilitator with the deployment stage only. Read AGENTS.md, foundation/AGENTS.md, foundation/Instructions.md, PRE-REQUISITES.md, foundation/skills/00-nemweb-navigator/SKILL.md, foundation/deployment-gates.md gates 1–3, and the current Git status. Treat every nemweb_foundation link as facilitator-only; do not route participants there. Confirm the daveok profile, expected workspace identity, isolated target names, non-secret variables, local validation, strict bundle validation, resource summary, and paused schedules. Every workspace-aware command must include --profile daveok. Do not deploy unless the facilitator gives explicit current authorisation after reviewing the summary. If authorised, use the authoritative deployment script in nemweb_foundation/scripts rather than copying it. Do not run a job, enable live mode, unpause a schedule, use a full refresh, expose a secret, or alter source files. Return exact commands, exit codes, resource-summary findings, and the human decision, then stop so the next stage can start in a fresh conversation.
```
