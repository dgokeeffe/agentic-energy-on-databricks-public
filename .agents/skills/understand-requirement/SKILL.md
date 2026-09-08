---
name: understand-requirement
description: Turn one selected issue or authorised maintenance task into measurable requirements before planning.
---

# Understand the requirement

Read the complete issue or authorised maintenance task and inspect its existing
implementation, contracts, and tests. For workshop issues, inspect
`nemweb_foundation/` plus the relevant starter. Name the operator decision,
source, grain, units, fixed-AEST market time, UTC processing time, correction
and intervention handling, freshness, identity boundary, and prepared-versus-live
status that apply. Convert each acceptance point into an observable result.

Choose preparation for the task, not a permission tier:

| Task kind | Preparation and proof to discuss with `plan-change` |
| --- | --- |
| Repetitive task | Start from the relevant tested procedure; check its assumptions still fit. |
| Small repair | Use a short plan and an explicit regression case. |
| New component or multi-step change | Discuss responsibilities, interfaces, dependencies, and failure behaviour before implementation. |
| Investigation | State plausible explanations, supporting and contrary evidence, paths not investigated, and what would settle the question. |
| Translation or migration | Compare behaviour with the reference and check dependency or language differences; do not introduce a live migration exercise. |

Record task kind, preparation choice, and verification rationale in the
[track record](../../../workshop/track-record-template.md), or the existing
issue/plan for maintenance. Distinguish explanations ruled out with cited evidence
from paths not investigated; missing evidence is not disproof. Task type never
grants permissions. Maintainers need explicit task authority; participants retain
all workshop limits and the same human approval and required checks.

Record unknowns and stop when the issue conflicts with governed semantics or
requires an unreleased preview or external change. Do not edit yet. Pass the
measurable requirements to `plan-change`.
