# Genie preparation for evidence review

Audience: workshop analysts and engineers inspecting a prepared NEM snapshot.
Purpose: inspect actual observations and their limits after the initial-supply
exercise, then record a human-reviewed finding in the existing investigation UI.
This package prepares the data context and reference answers. It does not connect
Genie to the app, create a live Genie space, or claim a Conversation API evaluation.

Use the three named Gold materialized views in the facilitator's isolated schema.
They have concrete interval-level observations rather than new reusable KPI
formulas. No metric view, T+1 availability dataset or legacy bundle is required.
The table and column meanings below come from the retained contracts and the
exercise's explicitly provisional definition of supply.

| Question | Source | Reference SQL | Answer requirements |
|---|---|---|---|
| What actual signed output was observed in each region at 00:05 and 00:10 AEST on 1 July 2026? | `gold_nem_initial_supply_5min` | `sql/01_observed_supply.sql` | MW, observed DUID count, attribution gaps; not total market supply |
| What corrected effective prices and demand are available for those intervals? | `gold_nem_region_dispatch_5min` | `sql/02_effective_prices.sql` | Filter `is_effective_run`; retain run numbers; state NSW-only price coverage |
| What signed fuel output and registration coverage were observed in those intervals? | `gold_nem_scada_generation_5min` | `sql/03_signed_fuel.sql` | Preserve signed MW and UNKNOWN; distinguish missing registration coverage from zero |
| How much capacity was available or curtailed? | Unsupported | No SQL | Explain that these SCADA observations and registered capacities do not establish five-minute availability or curtailment |

The third reference returns all fuel rows in the two intervals so reviewers can
check negative and incomplete observations in context. Empty filtered findings
must not turn into a claim of complete attribution or no charging across the NEM.

## Data context to prepare

- **Interval:** interval-ending fixed AEST (UTC+10), no daylight-saving shift.
  SQL timestamp literals carry `+10:00`; results may display in the SQL session's
  timezone. Convert for presentation without changing the instant.
- **Supply/output:** signed observed actual MW; negative storage values are kept.
  Summing across time does not yield MW. These questions request interval rows.
- **Observed count:** DUIDs represented in the input, not total registered fleet.
- **Attribution:** `partially_enriched_unit_count` or fuel counterpart reports
  incomplete region/fuel matching. UNKNOWN observations remain visible.
- **Freshness:** source and processing publication fields are UTC instants, while
  the July snapshot interval is intentionally old. Neither the snapshot nor
  recently processed snapshot rows constitute live evidence.
- **Price:** AUD/MWh; demand: MW. `is_effective_run` selects one intervention row
  per region/interval. The retained table includes non-effective audit rows.
- **Registration coverage:** signed nullable UTC publication-time lag, not an
  interval-time comparison, availability estimate or zero when missing.

For a facilitator-created Genie space, attach only these three tables, provide
these descriptions on the relevant columns, and offer the three concrete sample
questions above. Do not attach native investigation notes or landing payloads.
Avoid inferred joins; each question can be answered from one governed product.

## Validate and retain reference answers

After the isolated pipeline passes, use its bundle warehouse and explicit
catalog/schema. Run each query with a fresh ignored output path:

```sh
python3 scripts/workshop-query.py --profile <profile> --warehouse-id <warehouse-id> \
  --catalog <catalog> --schema <isolated-schema> \
  --sql-file workshop/genie/sql/01_observed_supply.sql \
  --output .databricks/workshop/genie-01.json
# Repeat for 02_effective_prices.sql and 03_signed_fuel.sql with distinct outputs.
```

The command prints its statement ID before polling. An observation timeout leaves
that handle saved; use `--resume <statement-id>` with the same arguments. An
existing evidence file cannot silently be overwritten by a new submission.
Results over the bound or incomplete chunks are errors, never a passing benchmark.

Record actual rows and expected limitations before creating a space. When a
facilitator explicitly approves a concrete space configuration, use the installed
CLI's current `genie create-space --help`/serialized schema, not a generated DAB
guide. Capture the created space ID and warehouse, then ask each question through
the Conversation API or UI and retain generated SQL, results and full response.
Score: source/filter/values correct; signed output intact; UTC/AEST meaning intact;
coverage and non-live caveats explicit; unsupported claims declined. Every item
must pass before calling Genie behavior verified. Reference SQL execution alone
is data readiness evidence, not an LLM evaluation.
