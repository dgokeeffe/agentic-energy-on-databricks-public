# App redesign: fuel value capture

## Decision

Reframe the Track C app from **"can I trust this number?"** to **"where did the
value go?"** The screen now reports, per NEM region and fuel, how much of the
regional average price each fuel actually captured, and what negative-price
intervals cost.

Adopt the [Open Electricity](https://github.com/opennem/openelectricity) design
language — warm neutrals, its fuel-technology colour system, and its typographic
scale — replacing the AGL-inspired blue theme. Open Electricity is MIT licensed,
so the tokens may be reused with attribution.

## Why the previous framing did not work

The screen asked whether the latest five-minute price movement was trustworthy.
Three problems:

1. **Data quality was the subject rather than the discipline.** Correction
   provenance and source-to-Gold lag are means, not ends. Presented as the
   headline, they answer a question nobody's job depends on.
2. **The stated audience could not act.** It was framed for a wholesale trading
   desk making a five-minute decision, while the same page forbade bid and offer
   decisions and live market operation. A trading screen that may not trade
   reads as confused, because it is.
3. **Nothing was at stake.** "The number is trustworthy" has no magnitude. There
   was no quantity a reader could be right or wrong about.

The rigour was never the problem. It had no question to serve.

## Why fuel value capture

The commercially live question in the NEM is no longer "what is the price" but
"is each fuel capturing that price, or generating into value destruction?"
Midday, once premium, is now frequently negative.

Market context, all publicly citable:

- Utility-scale solar and wind curtailment in the NEM reached **over 7 TWh in
  2025, up more than 60% year-on-year**; solar was **52%** of it, and **38% of
  South Australia's utility-scale solar output was curtailed** ([PV Tech, on
  Rystad Energy analysis](https://www.pv-tech.org/utility-scale-solar-wind-curtailment-exceeds-7twh-nem-2025/)).
- Renewables supplied **51% of NEM electricity in the December 2025 quarter**
  (same source).
- In Western Australia's WEM, hours of negative prices **fell about 75% from a
  spring 2024 peak** as operational utility-scale battery capacity overtook
  utility-scale solar capacity — evidence that storage changes the exposure.

This matters to a gentailer audience such as AGL because the portfolio is
mid-transition from baseload coal towards firming and flexibility. Capture rate
per fuel is the measure that makes that transition legible: it is how you see a
coal unit's midday economics decay and a battery's spread capture improve, in the
same units, on the same axis.

### What the screen answers

| Question | Computation | Gold source |
|---|---|---|
| Which fuels captured the regional price, and which gave it away? | capture rate = revenue ÷ MWh, indexed to the region's time-weighted price | `gold_nem_scada_generation_5min` × `gold_nem_region_dispatch_5min` |
| What did negative-price intervals cost? | Σ MW × (5 ÷ 60) × RRP, restricted to RRP < 0 | as above |
| Did storage earn the spread rather than pay it? | signed MW against the interval price; charging is negative in the SCADA sum | as above |

### Why the governance work now earns its place

When AEMO re-runs a dispatch interval, the price changes, so **yesterday's
revenue changes**. Effective-run selection, correction provenance, and fixed-AEST
market time stop being hygiene and become the explanation for a moved dollar
figure. The screen states the restatement explicitly: *n* intervals re-run since
first publication, revenue restated by *$x*.

Identical rigour to the previous design, now with a reason for a reader to care.

## Grouping: region and fuel, not ownership

NEMWEB does not publish a DUID-to-owner mapping. Asserting one would mean
shipping an ownership claim we cannot source from AEMO, and attaching invented
financial figures to a named company.

`gold_nem_scada_generation_5min` is already aggregated at
`(interval_end, region_id, fuel_type)`, which is sufficient for every question
above and maps one-to-one onto the Open Electricity fuel palette. No portfolio
file, watchlist, or ownership inference is introduced.

## Design system

Borrowed from Open Electricity (MIT, © 2023-2026 Open Electricity), recorded here
so the provenance of each token is auditable.

**Neutrals and accent.** `#FAF9F6` light warm grey, `#F1F0ED` warm grey,
`#C6C6C6` mid warm grey, `#6A6A6A` mid grey, `#353535` dark grey, `#C74523` red,
`#963F29` dark red. Semantic: `#70D26E` success, `#FA6060` error.

**Fuel technologies.** `coal_black #121212`, `coal_brown #744A26`,
`gas_ccgt #FDB462`, `gas_ocgt #FFCD96`, `gas_steam #F48E1B`,
`gas_recip #F9DCBC`, `distillate #E15C34`, `hydro #5EA0C0`, `wind #2C7629`,
`solar_utility #FED500`, `battery_charging #577CFF`,
`battery_discharging #3245c9`, `bioenergy_biomass #1D7A7A`, plus `UNKNOWN`
rendered in mid grey.

**Type.** Open Electricity self-hosts DM Sans, Space Grotesk, and DM Mono. We
adopt its 10px-root rem scale and wide-tracked uppercase subheadings but **do not
self-host or fetch the fonts**, so no font binaries or third-party requests are
added. The stacks fall back to system sans and system mono. This loses some of
the source identity and is a deliberate trade.

### Fuel mapping is a real translation, not a rename

AEMO's `CO2E_ENERGY_SOURCE` values ("Black coal", "Natural Gas", "Wind") do not
match Open Electricity's finer token set. `gas_ccgt` and `gas_ocgt` are not
distinguishable from that field alone, so all gas maps to a single gas token
rather than guessing turbine technology. The mapping is explicit, tested, and
falls back to `UNKNOWN` rather than silently choosing a colour.

### Retiring the AGL-inspired theme

The previous theme approximated AGL's identity from public description because
the official palette is behind a registration gate, and carried a footer
disclaimer. Dropping it removes that trademark-adjacent risk entirely.

The app stays relevant to an AGL audience through the decision it supports, not
by resembling AGL's website. That is the stronger form of relevance.

## What this app must not be used for

- Bid or offer decisions, or any live market operation.
- Inferring unit availability. AEMO Current does not publish five-minute
  availability, so **curtailment cannot be quantified here** — we can show output
  and the price it earned, never the output that was withheld. This boundary is
  stated on screen, because the curtailment framing above makes it the first
  thing an informed reader will reach for.
- Summing market-wide constraint or interconnector values across regions.
- Settlement or financial reporting. Revenue here is five-minute SCADA output
  times the regional reference price: an indicative energy-value estimate that
  excludes FCAS, loss factors, contracts, and settlement adjustment.

## Status

Implemented: the theme, the fuel-capture domain module and its tests, the
redesigned screen, and the reviewed SQL read path.

### Dependency closed, dev deployment 2026-09-08

`gold_nem_scada_generation_5min` is now published into the app serving schema by
`nemweb_app_serving`, following the same reviewed pattern as
`gold_nem_app_region_status`, and granted separately in the app bundle so the
app's privileges stay enumerable.

Verified with the `daveok` profile against
`agentic_energy_workshop.agentic_energy_workshop_d4_serving`: job run
`354366776080686` SUCCESS on both publication tasks, the serving table reconciles
**22 rows to 22** against its pipeline source across 11 region/fuel pairs, and both
reviewed app SQL files execute against the warehouse. Schedules stayed PAUSED and
`nemweb.source_mode` stayed `snapshot` throughout.

### The run found a real defect in the fuel mapping

The mapping was written from guessed `CO2E_ENERGY_SOURCE` strings, and the local
fixture was built from the same guesses — so the tests confirmed the assumption
rather than the behaviour. Against real data, two fuels fell through to the unknown
bucket and displayed real generation as "Unattributed fuel":

```
Natural Gas (Pipeline) -> unknown   (should be gas)
Diesel oil             -> unknown   (should be distillate)
```

AEMO qualifies several sources in parentheses. Every distinct value observed in the
workspace is now mapped and pinned by a test, plus a second test asserting the
canonical initcap forms resolve identically to the raw AEMO casing, since
`gold_nem_scada_generation_5min` carries the canonicalised value while the
dimension carries the raw one.

**Remaining limit.** The snapshot holds two intervals per region/fuel pair, so the
screen renders correctly but the capture figures are not a realistic trading window.
The prepared local fixture remains the better teaching artefact. No live NEMWEB
claim is made: `allow_live_nemweb` stayed false and the mode stayed snapshot.

## Human review

- **Decision:** design direction approved in session; scenario, grouping, theme
  extent, and sequencing chosen by the repository owner.
- **Reviewer:** pending independent review of the implementation.
- **Evidence:** local fixture, unit tests, and the citations above. No live
  workspace evidence.
