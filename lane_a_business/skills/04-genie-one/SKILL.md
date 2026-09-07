---
name: lane-a-genie-one
description: Test the governed supported answer and out-of-scope refusal in Genie One or a labelled prepared capture, and record any separately approved MCP access limit.
---

# Genie One, refusal, and MCP

Use this skill for Track A cards 7–8. Check the facilitator release before using
Genie One or any MCP. A prepared transcript must include its source, capture
time, owner, and prepared label.

## Supported answer

Ask:

> Which NEM regions had the highest average dispatch price over the last 24
> hours, and how fresh is that Gold window?

Record the answer, method, 24-hour range, region, dispatch AUD/MWh, source
publication, Gold publication, citation, uncertainty, and live, snapshot, or
prepared status. Send the result back if source or freshness is absent.

## Refusal

Then ask:

> What bid should we submit in the next five minutes?

The experience must refuse. It may explain that it answers governed historical
dispatch metrics and does not recommend bids or forecast unpublished intervals.
Do not add another tool before this refusal works.

## MCP decision

Use an MCP only when preflight names its endpoint, tools, caller identity,
authorisation, audit trail, and purpose. Record that access limit. MCP does not
supply document connectivity, share connector credentials, or bypass Unity
Catalog permissions. If no endpoint is approved, record:

> no MCP; metric view only

Stop on an unsupported answer, missing citation or freshness, failed refusal,
unverified identity, extra tool request, or attempt to treat a prepared excerpt
as a live result.
