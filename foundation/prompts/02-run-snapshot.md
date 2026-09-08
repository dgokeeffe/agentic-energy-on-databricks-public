# Prompt 02 — run the snapshot

Use this prompt in a **fresh conversation**. This stage ends with deterministic
snapshot reconciliation. It does not enable live mode.

```text
This is a fresh conversation. You are assisting the workshop facilitator with the snapshot stage only. Read AGENTS.md, foundation/AGENTS.md, foundation/Instructions.md, PRE-REQUISITES.md, foundation/skills/01-snapshot-mode/SKILL.md, foundation/deployment-gates.md gates 1–4, and the reviewed deployment summary from stage one. Treat every nemweb_foundation link as facilitator-only; do not route participants there. Verify that nemweb_mode is snapshot, allow_live_nemweb is false, the target and both schedules are unchanged, and every workspace-aware command includes --profile daveok. Do not run the snapshot refresh unless the facilitator gives explicit current authorisation. If authorised, run only the named critical DAG without full refresh, capture the orchestration run ID, child lander result, pipeline ID, and exact pipeline update ID, then reconcile landed, Bronze, Silver, quarantine, and Gold results. Keep market time fixed AEST and processing timestamps UTC. Label every snapshot result live_evidence: false. Do not deploy, access live NEMWEB, unpause a schedule, publish analyst assets, expose a secret, or weaken a check. Return exact commands, exit codes, reconciliation results, failures, and the human decision, then stop so the next stage can start in a fresh conversation.
```
