---
name: lane-a-genie-agent
description: Define or inspect a Genie Agent limited to released governed assets, caller permissions, fixed market semantics, freshness disclosure, and refusal rules.
---

# Genie Agent

Use this skill for the Agent setup within card 7. Verify the applicable
preflight before touching a workspace. If it has not passed, use only the
facilitator's timestamped prepared capture or stop.

## Record the Agent contract

- owner and business purpose;
- caller identity and confirmed permissions;
- released governed assets, centred on `nem_region_dispatch_metrics`;
- fixed-AEST interval-ending semantics;
- effective intervention-run policy;
- dispatch price in AUD/MWh versus demand in MW;
- source publication and Gold publication as separate freshness fields;
- valid negative price handling;
- query time range and citation expectations; and
- refusal of bid recommendations, forecasts, or unpublished intervals.

The Agent must not imply access to other tables, documents, Lakebase, MCP tools,
or identities. End-user filters and permissions still apply. A serialized or
prepared definition is not evidence of a deployed, callable Agent.

## Evidence

Record the source or capture, capture time, live or prepared status, owner,
asset list, instructions, caller limit, expected supported question, expected
refusal, and human decision. Do not ask the questions in this stage; the next
stage tests behaviour separately.

Stop if the invocation method, assets, permissions, citations, or instructions
have not been verified, or if widening access is proposed as a workaround.
