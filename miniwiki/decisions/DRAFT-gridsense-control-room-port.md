# DRAFT — Track C app: GridSense control-room port on governed data

**Status:** proposed, awaiting human approval. Nothing implemented.
**Supersedes, if approved:** [`app-value-capture-redesign.md`](app-value-capture-redesign.md)

## Decision requested

Rebuild the Track C app to look and behave like the GridSense Intelligence Hub
control room, while every displayed number continues to come from the governed
`gold_nem_*` layer published by `nemweb_foundation/`.

Four framing choices are already settled with the requester:

| Choice | Settled position |
|---|---|
| Narrative | GridSense look, governed data underneath |
| Synthetic data | Synthetic permitted (revised instruction). Labelled and mode-gated |
| Markets | NEM only. Japan, India, SEA and NZ dropped |
| Surfaces | LTAP six-step journey, plus a real NEM generator map |

## Correction: what GridSense actually renders

An earlier draft of this page described GridSense as an eight-tab command centre
and proposed porting its Digital Twin and Scenario Simulation. That description
was wrong, and the requester caught it.

`frontend/src/config/demo.ts` sets `LTAP_DEMO_MODE = true`, and
`frontend/src/App.tsx` line 169 returns early on it:

```text
LTAP_DEMO_MODE = true   →  Header + LiveGenerationLanding      (the whole app)
path === "/net-zero"    →  Header + NetZeroDebatePage          (separate page)
```

Under that flag the eight tabs, war room, shock injection, splash screen,
Digital Twin, Scenario Simulation **and `LiveNemTicker`** never mount. They are
dead code in the shipped configuration. The Net Zero debate page is the only
surface that is genuinely "off on its own", reached by a header link.

So the app to port is `LiveGenerationLanding`: a guided six-step journey.

| Step | Surface | Claim |
|---|---|---|
| 1–2 Observe | `GenerationOverTimeChart`, `LiveNemGenerationChart` | AEMO → Lakeflow → governed Delta gold; Lakebase synced-table reads |
| 3–4 Scale | `GenerationSyncPanel` | PLC/SCADA → Zerobus → Delta → Lakebase, LTAP write benchmark |
| 5 Reason | `DemoGeniePrompt` | governed Genie recommendation |
| 6 Learn | `ClosedLoopActions` | CDF decision history → analytics |

This maps almost one-to-one onto this repository, which is why it was chosen:
governed Gold reads, Lakebase writable state, and a CDF history contract all
already exist here.

## What the reference app actually is

`~/Repos/8-gridsense-intelligence-hub` is a 60-minute executive demo, not an
extensible starter. Measured, not assumed:

- `app.py` is 2,120 lines, FastAPI, 55 endpoints.
- Frontend is 163 `.tsx` files, ~44,500 lines, React 18 / Tailwind 3.
- Heavy visual dependencies: `deck.gl`, `three`, `@react-three/*`,
  `framer-motion`, `@xyflow/react`, `recharts`, `puppeteer`.
- **Zero governed reads.** `grep -c "statement_execution\|sql_query\|spark.sql"`
  on `app.py` returns `0`. There is no SQL warehouse call and no Unity Catalog
  read anywhere in the backend.
- Its data path is `AEMO NEMWEB --HTTP--> app.py --> UI`, polled every 30s.
- Non-AU markets are, in its own docstring, "deterministic synthetic prices
  seeded on 30-s intervals so numbers visibly update".
- It is internally inconsistent about its own target: `GOAL.md` names catalog
  `gridsense` and Genie space `01f16fe5…`; `app.yaml` names catalog `daveok`
  and Genie space `01f1a72b…`.

This matters because it is the exact inverse of what this repository teaches.
The foundation exists to prove landing → Bronze → correction-aware Silver →
five-minute Gold → app, with provenance on every value. A wholesale port of
GridSense's data layer would make `nemweb_foundation/` decorative.

## Real facility topology exists, so the map needs no fabrication

`data/nem_facility_coordinates.csv` in the reference repository holds **572
DUIDs across 435 facilities** with WGS84 coordinates, exported from
[OpenElectricity](https://github.com/opennem/openelectricity). Commit `428ecaa`
added it precisely because the earlier map had only 11 hand-typed stations and
silently dropped 487 units.

Its `duid` column is the join key to this repository's
`gold_nem_unit_dispatch_5min`, which carries per-DUID `actual_generation_mw`,
`region_id`, `fuel_type` and `registered_capacity_mw`.

A real generator map is therefore available with **no invented topology and no
invented output**. This supersedes both the `REGION_TWINS` port and the
interconnector-graph substitute proposed earlier, and it makes the requester's
fabrication authorisation unnecessary for this surface.

Retained caveat: `actual_generation_mw` is output, never a dispatch target, and
AEMO Current publishes no five-minute availability. The map must not imply
curtailment or availability.

## Recommended stack: keep AppKit, port the design

**Do not replatform to FastAPI.** Port GridSense's design language and chosen
surfaces onto the existing Node/AppKit app.

Rationale:

1. AppKit is what performs the governed read. `nemweb_app/databricks.yml`
   declares per-table `SELECT` on `gold_nem_app_region_status` and
   `gold_nem_scada_generation_5min` as least-privilege app resources.
   Replatforming to Python means rebuilding that governed read path, and its
   grant model, from nothing — to reach the same place.
2. Lakebase `app_write.investigations` and the CDF contract already work.
3. Attendee isolation (`attendee_slug` → app name + Lakebase branch) is already
   wired through the bundle.
4. Existing vitest and Playwright coverage stays meaningful.

What is genuinely portable from GridSense is the part that was admired: the
design tokens, typography, card/KPI/pill primitives, dark mode, header with
region switcher, and the live ticker. That is ~650 lines across the chosen
landing surfaces, and it is stack-agnostic CSS and JSX.

The cost of this recommendation: React 19 / Tailwind 4 here versus React 18 /
Tailwind 3 there, so ported components need small adjustments, and
`@databricks/appkit-ui` primitives replace GridSense's hand-rolled ones.

### Revised instruction on synthetic data

The requester subsequently authorised fabricated topology and synthetic
generation, superseding the earlier "real data or explicit empty state"
position. This unblocks the Digital Twin.

The repository already treats prepared data as first-class:
`MockRegionStatusRepository`, `MockFuelGenerationRepository`,
`tests/fixtures/*.json` and `make app-dev-mock` under `VITE_DATA_MODE=mock`.
Synthetic data is therefore consistent with existing practice.

The retained constraint, absent further instruction: a synthetic value carries a
visible prepared or modelled label and stays behind the mock data mode. It is
not presented as a governed read in integration mode. This preserves the
"prepared material is not live evidence" rule in `AGENTS.md` without reducing
anything on screen.

## The Digital Twin conflict, and the proposed resolution

`frontend/src/components/twin/twinConfig.ts` defines `REGION_TWINS` as a
hardcoded literal. Australia has 9 nodes and 9 edges. Station names are real
(Bayswater, Loy Yang A, Hornsdale, Snowy 2.0, Torrens Island). Every
`riskPct`, `flowPct`, `capacityMw`, `x`/`y` and `voltageKv` is invented.

The foundation has no substation topology, no coordinates, no line ratings and
no asset health. Verified by grep across `nemweb_foundation/`; the only hits
were inside `.venv`.

With synthetic topology now authorised, the Digital Twin can be ported in full.
The design below is still preferred, because it makes the dynamic values real
where the foundation can supply them and synthetic only where it cannot:

**NEM interconnector network view.** Five NEM regions as nodes, the governed
interconnectors as edges, from:

| Field | Source |
|---|---|
| `mw_flow`, `metered_mw_flow` | `gold_nem_interconnector_flows_5min` |
| `export_limit_mw`, `import_limit_mw` | same |
| `mw_losses`, `marginal_value`, `violation_degree` | same |
| binding constraint detail | `gold_nem_binding_constraints_5min` |
| regional price and demand | `gold_nem_region_dispatch_5min` |
| generation by fuel | `gold_nem_scada_generation_5min` |

Edge utilisation becomes flow ÷ limit, which is a real number rather than a
literal `flowPct`. A violated interconnector is real. A binding constraint is
real.

Static topology is fabricated, in three tiers, so the label on each value is
accurate:

| Tier | Example | Treatment |
|---|---|---|
| Public fact | station names, coordinates, registered capacity, interconnector identifiers | fabricated into a fixture, but publicly checkable |
| Governed dynamic | interconnector flow, limits, violation, price, demand, generation by fuel | read from `gold_nem_*` when published |
| Synthetic dynamic | per-asset risk percentage, asset health | generated, labelled modelled |

Only the third tier is invention with no external referent, and it is the tier
that carries the label.

Known limitation to carry forward: `gold_nem_app_region_status` repeats
market-wide interconnector and constraint summaries per region, and there is no
governed interconnector-to-region mapping. The network view must therefore read
`gold_nem_interconnector_flows_5min` directly and must not derive per-region
attribution, nor sum the repeated summary values across regions.

## Scenario Simulation, scoped honestly

Counterfactuals computed from governed data and labelled as modelled are
legitimate; they are not synthetic evidence. Proposed to keep, relabelled:

- Interconnector limit counterfactual: consequence when a real flow approaches
  a real `export_limit_mw`.
- Time-travel over actual history, using correction-aware Silver so a restated
  interval is visible as restated.

Proposed to drop:

- **OPF Solver Race** (450 lines) and its 155× CPLEX speedup claim. No
  supporting evidence exists in either repository.
- DER orchestration, regulatory STPIS exposure, outage cascade. These depend on
  asset and regulatory data the foundation does not publish.

## Sequence

1. Design tokens and primitives: port GridSense `index.css` variables,
   `tailwind.config.ts` theme, `.card`/`.pill`/`live-dot`, Inter, dark mode.
2. Shell: header, region switcher, live NEM ticker, KPI row, on existing
   governed reads. This alone delivers most of the visual change.
3. Add governed reads for interconnector flows and binding constraints:
   reviewed SQL in `nemweb_app/config/queries/`, plus matching `uc_securable`
   grants in `nemweb_app/databricks.yml`. Build against a mock repository first,
   behind the same interface, so no surface is blocked on publication.
4. Real NEM generator map: facility coordinates joined to per-DUID dispatch.
5. Zerobus/LTAP scale step and the CDF decision-history step.
6. Rewrite `workshop/track_c_app/Instructions.md` and re-cut the twelve draft
   exercises in `workshop/exercises/` against the new app.

Steps 1–2 are independently valuable and reversible. Because every new surface
is built against a mock repository behind the existing repository interface, no
step is blocked on a facilitator publishing tables; publication upgrades a
surface from prepared to governed without a code change.

## Done criteria

- `make app-install`, `make app-test`, `make app-dev-mock` all pass.
- No synthetic value renders without an explicit prepared or modelled label.
- Every governed value traces to a reviewed SQL file and a declared UC grant.
- No write to a synced table; Lakebase remains the only writable state.
- `databricks bundle validate --profile DEFAULT` passes.
- Track C instructions match the app a participant actually sees.

## Test consequences

`nemweb_app/tests/smoke.spec.ts` asserts the value-capture screen in detail:
headings such as "Solar (utility) captured 0.20× of the SA1 average price",
"What each fuel earned in SA1", and a light-theme guard requiring every body
background channel above 200. Adding GridSense's dark mode will fail that guard
by design.

These tests are therefore rewritten to assert the new intended behaviour. That
is a rewrite, not a relaxation: no assertion is deleted to obtain a pass, and
the accessibility, focus-return, mobile-overflow and negative-price assertions
are all carried across to the new surfaces.

## Open questions for the requester

1. Confirm the AppKit recommendation over the FastAPI replatform.
2. Confirm dropping the OPF solver race and its unevidenced 155× claim.
3. Confirm synthetic values stay labelled and mode-gated rather than silent.
4. Eventually, who publishes `gold_nem_interconnector_flows_5min` and
   `gold_nem_binding_constraints_5min` into
   `agentic_energy_workshop_d4_serving`, to upgrade prepared surfaces to
   governed ones?
