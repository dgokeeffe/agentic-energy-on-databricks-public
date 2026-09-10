# Draft issue: source_publication_basis is overwritten in Bronze

**Not yet filed.** This is a ready-to-file GitHub issue body, kept here so the
finding survives independently of pull request #28 — a note in a PR body dies
with the branch. Filing is outward-facing and needs authorisation.

Found while implementing registration coverage; see
[`../decisions/registration-coverage-metric.md`](../decisions/registration-coverage-metric.md)
for why that change had to guard around this defect rather than depend on the
field being truthful.

Every claim below was verified in the working tree at `d9927c8`. Two of them
correct the shorter description in the PR body: the blast radius is 8 Bronze
tables rather than the 3 registration ones, and a second fabrication upstream
means repairing `io.py:281` alone is not sufficient.

---

## Operator outcome

An operator can tell a real AEMO publication instant from one we fabricated from
our own download time. Today they cannot: every row in the Delta-landed Bronze
tables claims `source_publication_basis = 'listing_or_http'`, whether or not AEMO
ever gave us a publication timestamp.

`source_publication_at` is not null-safe provenance — it is either the instant
AEMO published the archive, or the instant *we* fetched it, and the only field
that distinguishes those two is the one being overwritten. A freshness or
coverage metric computed from `source_publication_at` therefore reads
**healthiest exactly when provenance is weakest**: when the lander had to invent
the publication instant from the retrieval event, the measured lag collapses
toward zero and the pipeline reports "current".

## The gap

The lander computes the basis correctly and Bronze then discards it. Each link
verified in the working tree at `d9927c8`:

1. **The lander gets it right.**
   `agentic_energy/nemweb/lander.py:432` writes into the immutable landing
   manifest:

   ```python
   "source_publication_basis": "listing_or_http" if archive.source_publication_at else "retrieval_fallback",
   ```

   with `lander.py:431` doing the paired `archive.source_publication_at or
   archive.retrieved_at` coalesce. So the manifest is honest about which of the
   two it wrote. Verified by running `land_snapshot` against
   `tests/fixtures/nemweb/v1`: all six manifest archives come out
   `retrieval_fallback`, publication instant equal to `retrieved_at`.

2. **`io.py` re-asserts it as a literal.**
   `agentic_energy/nemweb/pipeline/io.py:281`, inside `section_stream`
   (`io.py:232`), in the `subject_key` branch that begins at `io.py:260`:

   ```python
   F.lit("listing_or_http").alias("source_publication_basis"),
   ```

   The value is a constant. Nothing upstream can change it.

3. **The other branch of the same function does it correctly.** `section_stream`
   has two branches. The legacy `_nemweb_parsed_records` branch
   (`io.py:247-259`) inherits the real basis, because `read_parsed_records`
   projects it from the manifest — `io.py:95` declares
   `source_publication_basis` in `_MANIFEST_SCHEMA`, `io.py:131` reads
   `archive.source_publication_basis`, and `io.py:205` passes it through. The
   `subject_key` branch replaces that with the literal. **The correct
   passthrough already exists twenty lines above the defect.**

4. **The Delta landing tables have nowhere to carry it.** This is why the
   literal is there and why the fix is not a one-line edit. The
   `subject_key` branch reads `successful_run_records`
   (`agentic_energy/nemweb/delta_lander.py:188`), whose landing-table schema is
   `delta_lander.py:177` — it carries `source_publication_at TIMESTAMP,
   retrieved_at TIMESTAMP, landed_at TIMESTAMP` and **no basis column at all**.
   `LandingProvenance` (`delta_lander.py:25-33`) likewise has no basis field,
   and `delta_lander.py:123-127` never computes one. The basis is computed only
   on the Volume manifest path, and the Bronze read that matters uses the Delta
   path.

5. **A second, independent fabrication in the deployed entrypoint.**
   `scripts/land_nemweb_delta.py:49` does:

   ```python
   item.get("source_publication_at") or item["retrieved_at"],
   ```

   This coalesce happens when building `ArchiveInput`, i.e. **before**
   `lander.py:432` ever runs. `ArchiveInput.source_publication_at` is therefore
   never `None` on this path, so the lander's conditional cannot take its
   `retrieval_fallback` arm. Verified empirically: replicating
   `land_nemweb_delta.py:37-50` over the registration fixture (whose manifest
   entries have no `source_publication_at` key) and landing it produces
   `source_publication_basis = listing_or_http`, whereas `land_snapshot` —
   which passes `item.get("source_publication_at")` through *uncoalesced* at
   `lander.py:532` — produces `retrieval_fallback` for the same fixture.

   **So even repairing `io.py:281` alone would not fix this.** On the deployed
   job (`resources/nemweb_lander.job.yml`, task `land_nemweb_files`, which runs
   `scripts/land_nemweb_delta.py`) the manifest itself would still say
   `listing_or_http`. Both `land_nemweb_delta.py:49` and `io.py:281` must be
   repaired for the basis to be true.

6. **The column is validated for shape, not for truth.** `COMMON_VALIDITY_SQL`
   at `io.py:58` requires:

   ```
   source_publication_basis IN ('listing_or_http', 'retrieval_fallback')
   ```

   A hardcoded literal satisfies that enum perfectly and always. This is the
   same class of defect as the tautological expectation noted against issue #2:
   a check that the wrong code passes by construction.

7. **The fallback path is the default, not an edge case.** All six artifacts in
   the governed snapshot manifest
   (`agentic_energy/resources/nemweb_snapshot/v1/manifest.json`) **omit the
   `source_publication_at` key entirely** — dispatchis x2, dispatch_scada x2,
   next_day_dispatch, registration. The test fixture
   (`tests/fixtures/nemweb/v1/manifest.json`) is the same. Under snapshot mode,
   which is the mode participants and the current deployment run, the
   fabricated-publication path is taken for **100% of rows**. Every one of them
   is stamped `listing_or_http`.

   For live mode the timestamp is genuinely optional: it comes from a listing
   scrape at `lander.py:636` (`_publication_by_url`) and is applied at
   `lander.py:651`, so an unparsed listing legitimately yields `None`. The
   fallback is real in both modes; snapshot just makes it universal.

## Blast radius

Not registration-only. Grepping `section_stream` across
`agentic_energy/nemweb/pipeline/` and classifying each call by branch (AST, on
`keywords`):

**Affected — `subject_key` branch, hits `io.py:281` (8 Bronze tables):**

| Table | Call site |
|---|---|
| `bronze_nem_genunits` | `bronze_registration.py:24` |
| `bronze_nem_dudetail` | `bronze_registration.py:43` |
| `bronze_nem_dualloc` | `bronze_registration.py:62` |
| `bronze_nem_dispatch_price` | `bronze_dispatchis.py:40` |
| `bronze_nem_dispatch_region_sum` | `bronze_dispatchis.py:67` |
| `bronze_nem_dispatch_constraint` | `bronze_dispatchis.py:94` |
| `bronze_nem_dispatch_interconnector_res` | `bronze_dispatchis.py:121` |
| `bronze_nem_dispatch_unit_scada` | `bronze_scada.py:21` |

All three registration tables are affected, as expected — but so is the entire
app-critical dispatch and SCADA path. That is 8 of the 9 tables in
`CRITICAL_TABLES` (`tests/nemweb/test_bronze_contracts.py:35-44`); the ninth,
`bronze_nem_dispatch_unit_solution_t1`, uses the legacy branch.

**Unaffected — legacy `_nemweb_parsed_records` branch, basis is correct:**
`bronze_unit_solution.py:44`, `bronze_bids.py:60`, `bronze_bids.py:80`,
`bronze_trading.py:28`, `bronze_settlement.py:47`, `bronze_settlement.py:67`.

This also means the column is currently **inconsistent across Bronze**: the same
column name means "real, from the manifest" on six tables and "always the
literal `listing_or_http`" on eight.

## Why it matters concretely

PR #28 (issue #7) added a registration coverage metric. Its provenance guard has
two legs, and **the correct leg is inert because of this defect**:

- `agentic_energy/nemweb/quality.py:216-218` checks
  `source_publication_basis == 'retrieval_fallback'`. This is the right signal.
  It can never fire for the registration Bronze tables, and the docstring at
  `quality.py:187-191` says so explicitly.
- `quality.py:220-224` therefore adds a **timing heuristic**: publication
  instant within `MINIMUM_PUBLICATION_TO_LANDING_SECONDS` (60,
  `quality.py:107`) of `landed_at`. Its Spark twin is
  `agentic_energy/nemweb/pipeline/silver_facilities.py:60-71`, whose docstring
  at `silver_facilities.py:55-57` records the same reason.

That heuristic is a substitute for provenance, not provenance. It only works
because the fabricated timestamp happens to derive from the same retrieval event
as `landed_at`; it produces a false positive on a genuinely fast-landed real
publication, and a false negative on any fabrication that does not collapse onto
`landed_at`. `quality.py:192-196` states this in the source. The heuristic is
load-bearing today and should not be removed by this fix — but it should stop
being the *only* thing that fires.

## Required change

Carry the basis through from the landing record instead of re-asserting it in
Bronze. Concretely, all three of:

1. Stop fabricating the timestamp before the basis is decided.
   `scripts/land_nemweb_delta.py:49` must pass the manifest value through
   unchanged (as `lander.py:532` already does), leaving the
   `or retrieved_at` coalesce to `lander.py:431`, which is where the paired
   basis decision lives. The two lines must stay adjacent so they cannot drift
   apart again.
2. Give the Delta landing path a basis column: add it to `LandingProvenance`
   (`delta_lander.py:25-33`), populate it at `delta_lander.py:123-127` using the
   *same* expression as `lander.py:432` (extract it to one shared helper — two
   copies of this conditional is how the defect survives), and add it to the
   landing-table DDL at `delta_lander.py:177` and to `landing_nem_files` at
   `delta_lander.py:184` if the file-level summary is to stay consistent.
3. Replace `io.py:281` with a projection of that column, so both branches of
   `section_stream` derive the basis from landed provenance rather than one
   deriving and one asserting.

Must **not** be done:

- Do not paper over it in consumers. Leave `quality.py:220-224` and
  `silver_facilities.py:60-71` in place — the heuristic is the current
  protection and a fix that only strengthens the heuristic has not fixed the
  defect. Equally, do not "fix" this by deleting the basis leg because it never
  fires.
- Do not drop or filter rows. `retrieval_fallback` is a legitimate, expected
  value — `COMMON_VALIDITY_SQL` at `io.py:58` already admits it. A row with a
  fabricated publication instant must land, correctly labelled, not be
  quarantined.
- Do not widen or weaken `COMMON_VALIDITY_SQL` to make a migration easier.
- Do not re-cut the governed snapshot manifest as part of this fix. Adding real
  `source_publication_at` values to
  `agentic_energy/resources/nemweb_snapshot/v1/manifest.json` would hide the
  defect rather than repair it, and snapshot provenance is a separate
  facilitator decision (tracked as E2 in
  `miniwiki/decisions/registration-coverage-metric.md`).

## Deterministic tests

- Landing an archive with **no** `source_publication_at` yields
  `retrieval_fallback` in the manifest **and** in the Delta landing row, through
  `scripts/land_nemweb_delta.py`'s input construction — not only through
  `land_snapshot`. This is the test that would have caught the second link, and
  the current suite has no equivalent.
- Landing an archive **with** a `source_publication_at` distinct from
  `retrieved_at` yields `listing_or_http`, and the two timestamps stay distinct.
- The basis surviving into Bronze is the landed value, asserted structurally:
  `F.lit("listing_or_http")` no longer appears in `io.py`, and both branches of
  `section_stream` project the same column name from provenance. Assert on the
  projection, not on whole-file substrings — three of four mutants in the PR #28
  mutation run survived because of over-broad substring assertions
  (`miniwiki/decisions/registration-coverage-metric.md`).
- `registration_coverage` reports `DEGRADED_RETRIEVAL_FALLBACK` from the **basis
  leg alone**, with `landed_at` set far enough from the publication instant that
  the timing heuristic cannot fire. This proves the correct leg is live. Extend
  the existing case at
  `tests/nemweb/test_registration_coverage.py:145` rather than duplicating it.
- The timing heuristic still fires independently, so a future regression in the
  basis passthrough is still caught:
  `tests/nemweb/test_registration_coverage.py:165` must stay green.
- The eight affected tables and the six unaffected ones agree on the meaning of
  the column, so `source_publication_basis` means one thing across Bronze.
- Fixed-AEST market time and UTC processing timestamps unchanged. The basis
  describes lineage only; it must not touch `interval_end` or any market
  instant.

## Blast radius / migration

**Forward-only is not sufficient, and I cannot determine the backfill scope from
the repository alone.** Being explicit about what is and is not established:

- **Established:** every existing row in the eight tables above carries
  `source_publication_basis = 'listing_or_http'` regardless of truth, because
  the value is a literal. Under snapshot mode every one of those rows also has a
  fabricated `source_publication_at`, since all six governed manifest artifacts
  omit the key. So the currently-landed rows are not merely unverified — for
  snapshot mode they are known to be **wrong**.
- **Established:** the Bronze tables are append-only
  (`delta.appendOnly` on the landing tables, `dp.expect_or_drop` and no
  `dropDuplicates` in Bronze — `tests/nemweb/test_bronze_contracts.py:152-160`),
  so a correcting rewrite is not an ordinary operation here.
- **Not established:** whether any deployed table currently holds rows, and how
  many. `miniwiki/decisions/registration-coverage-metric.md` records that as of
  2026-09-10 the serving table did not yet carry the PR #28 coverage columns at
  all, which suggests the deployed state is behind `main` — but I have not
  queried the workspace and this task does not authorise doing so. **A
  facilitator must check row counts before deciding.**

Given that, the honest recommendation: implement the fix forward-only, and treat
the pre-fix rows as **basis-unknown rather than as `listing_or_http`**. Since the
enum admits only two values, "unknown" cannot be expressed in the existing
column, so one of these has to be chosen deliberately by a human:

- accept that historical rows over-claim, and rely on the timing heuristic for
  them (it does correctly flag the collapsed-timestamp snapshot rows);
- or truncate and re-land in the non-production workshop schema, which is
  cheaper here than in a real deployment and may be the right call given the
  data is synthetic snapshot data;
- or widen the enum with a third `unknown` value, which changes
  `COMMON_VALIDITY_SQL` and every consumer, and is almost certainly
  disproportionate.

I have not chosen between these. Whichever is chosen must be recorded before
merge, because a fix that leaves wrong historical rows silently
indistinguishable from right new ones reproduces the defect at a different
layer.

## Evidence required

Plan, changed files, red/green tests (the red must fail on the *current* code —
a test that passes before the fix has not demonstrated the defect), the basis
value distribution per affected table before and after, confirmation that the
timing heuristic in `quality.py` and `silver_facilities.py` still fires
independently, the migration decision above with its author, independent review,
remaining uncertainty, and a pull request linked to this issue.

## Limits

No deployment, no schedule change, no unpausing, no live-NEMWEB enablement, no
grant change, and no job run without explicit authorisation in the task that
does it. No re-cutting the governed snapshot manifest under this issue. No
weakening or deletion of `COMMON_VALIDITY_SQL` or of the existing provenance
tests to obtain a pass. Treat snapshot and prepared material as non-live
evidence. Keep tokens, private workspace details, and participant data out of
issues, commits, screenshots, and pull requests.

Where a Databricks CLI command is approved, name the profile explicitly:

```bash
databricks auth describe --profile DEFAULT
```

## Verification notes

Every file:line above was read in the working tree at `d9927c8` on branch
`feat/registration-attribution-freshness`. The two lander paths were executed
against `tests/fixtures/nemweb/v1` to confirm they disagree
(`land_snapshot` → `retrieval_fallback`; the `land_nemweb_delta.py:49`
construction → `listing_or_http`). `section_stream` call sites were classified
by parsing each `bronze_*.py` with `ast` rather than by reading them.

Two things stated as uncertain rather than fact: the deployed row counts, and
therefore the backfill decision. No severity label is asserted — this issue
carries no severity claim, in line with the other issues in this repository,
which use `difficulty:` and `area:` labels only.

Related: PR #28 / issue #7 (the metric whose basis leg this defect makes inert);
issue #2 (the same silent-plausible-value failure class); issue #5 (separating
source publication delay from pipeline freshness, which depends on this column
being true). Recorded as "E1" in
`miniwiki/decisions/registration-coverage-metric.md:148-153`, which is the
open-item note this issue formalises — note that the miniwiki entry says "every
Bronze table using `section_stream`", which is not exact: six of the fourteen
call sites are on the correct branch.
