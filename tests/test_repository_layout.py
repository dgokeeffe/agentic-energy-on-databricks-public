from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_foundation_app_ml_and_lakebase_structures_exist():
    for relative in ("nemweb_foundation", "nemweb_app", "nemweb_ml", "workshop/lakebase"):
        assert (ROOT / relative).is_dir(), relative


def test_app_analytics_identifier_is_fixed_to_the_regular_serving_table():
    query = (ROOT / "nemweb_app/config/queries/latest_region_status.sql").read_text()
    table = "agentic_energy_workshop.agentic_energy_workshop_d4_serving.gold_nem_app_region_status"
    assert "FROM IDENTIFIER(:region_status_table)" in query
    assert table in query  # type-generation-only sample value
    assert "FROM daveok." not in query
    assert "SERVING_TABLE" not in (ROOT / "nemweb_app/app.yaml").read_text()

    bundle = (ROOT / "nemweb_app/databricks.yml").read_text()
    assert "securable_full_name: ${var.region_status_table}" in bundle
    assert f"default: {table}" in bundle
    assert "securable_type: TABLE" in bundle
    assert "permission: SELECT" in bundle


def test_app_fuel_generation_read_is_fixed_and_separately_granted():
    """The value-capture read must be as constrained as the region-status read.

    It is a second governed surface with its own Unity Catalog grant, so a caller
    must not be able to choose the object and the privilege must be declared
    explicitly rather than inherited by widening an existing grant to the schema.
    """
    query = (ROOT / "nemweb_app/config/queries/latest_fuel_generation.sql").read_text()
    table = (
        "agentic_energy_workshop.agentic_energy_workshop_d4_serving"
        ".gold_nem_scada_generation_5min"
    )
    assert "FROM IDENTIFIER(:fuel_generation_table)" in query
    assert table in query  # type-generation-only sample value
    assert "FROM daveok." not in query

    bundle = (ROOT / "nemweb_app/databricks.yml").read_text()
    assert "securable_full_name: ${var.fuel_generation_table}" in bundle
    assert f"default: {table}" in bundle
    # A schema-level grant would hand the app every table in the serving schema.
    assert "securable_type: SCHEMA" not in bundle


def test_the_serving_table_can_gain_the_attribution_columns_on_an_existing_deploy():
    """A MERGE with UPDATE SET * needs both schemas to agree.

    The publication uses ``UPDATE SET *`` / ``INSERT *``, and ``CREATE TABLE IF NOT
    EXISTS`` is a no-op against a table that already exists, so new pipeline columns
    would fail the serving job on the first refresh after deploy. There is no
    ``autoMerge`` anywhere in this repository, and adding one would let any future
    pipeline column reach the serving surface unreviewed, so the columns are named
    in an idempotent ``ALTER TABLE``.

    Asserted rather than left to the comment, because the failure only appears
    against a previously-deployed table — never in a clean-schema test run.
    """
    serving = (ROOT / "nemweb_foundation/sql/app_serving/gold_nem_scada_generation_5min.sql").read_text()

    # Assert on executable SQL only, never the whole file. The prose above the MERGE
    # names both autoMerge and the rejected ALTER in order to explain why neither is
    # used, and a bare substring check would fail on that explanation — the same
    # over-broad assertion that would also have been satisfied by deleting it.
    statements = " ".join(
        line.split("--")[0] for line in serving.splitlines() if not line.strip().startswith("--")
    )

    # MERGE WITH SCHEMA EVOLUTION is per-statement: it evolves the target to match
    # this one reviewed source. Verified against the SQL engine — the previous
    # `ALTER TABLE ... ADD COLUMNS IF NOT EXISTS` returned PARSE_SYNTAX_ERROR at
    # 'EXISTS' (SQLSTATE 42601), because ADD COLUMNS has no IF NOT EXISTS clause.
    # Plain ADD COLUMNS parses but is not idempotent, and this job runs on every
    # refresh, so neither form is usable here.
    assert "MERGE WITH SCHEMA EVOLUTION" in statements, (
        "the serving MERGE must evolve the target schema, or new pipeline columns "
        "fail the publication against an already-deployed table"
    )
    assert "ADD COLUMNS IF NOT EXISTS" not in statements, (
        "ADD COLUMNS IF NOT EXISTS is not valid Databricks SQL (PARSE_SYNTAX_ERROR)"
    )
    assert "automerge" not in statements.lower(), (
        "schema evolution must stay per-statement, not a table-wide autoMerge property"
    )

    # The pipeline, the serving surface and the app read must name the same columns.
    # An asymmetry here is invisible locally: the app silently ignores a column it
    # does not select, so it could accumulate server-side while the client is blind
    # to it.
    gold = (ROOT / "nemweb_foundation/agentic_energy/nemweb/pipeline/gold_scada_generation.py").read_text()
    read = (ROOT / "nemweb_app/config/queries/latest_fuel_generation.sql").read_text()
    published = {
        "registration_effective_at",
        "registration_publication_at",
        "registration_coverage_seconds",
        "registration_coverage_basis",
    }
    for column in published:
        assert column in gold, f"{column} is expected in the Gold product but is not published there"

    # registration_effective_at is deliberately NOT read by the app: it is fixed-AEST
    # market time and the screen reports UTC coverage instead. Every other published
    # column must reach the app, and the app must read nothing that is not published.
    expected_in_app = published - {"registration_effective_at"}
    in_app = {column for column in published if column in read}
    assert in_app == expected_in_app, (
        f"serving and app read have drifted: published-and-unread "
        f"{sorted(expected_in_app - in_app)}, unexpected {sorted(in_app - expected_in_app)}"
    )

    # The reviewed read must stay pinned to one object.
    assert "FROM IDENTIFIER(:fuel_generation_table)" in read


def test_the_registration_staleness_threshold_is_the_same_in_both_languages():
    """The pipeline and the screen must not disagree about what "stale" means.

    ``STALE_REGISTRATION_AFTER_SECONDS`` is written twice — once in Python for the
    governed contract, once in TypeScript for the screen — because the repository
    has no cross-language constant sharing. Nothing else couples them, and an
    independent review found the drift is silent: changing only the TypeScript side
    from 45 to 40 days passes all 97 app tests and all 343 foundation tests,
    because no test straddles the gap between the two values.

    A pipeline that considers a load fresh while the screen calls it stale, or the
    reverse, is the divergence this branch exists to prevent. Rather than trust a
    comment to keep them aligned, read both declarations and compare.

    An earlier version matched four literal factors with a regex, and an independent
    review showed that broke on refactors carrying no semantic change at all —
    ``45 * 86400``, ``(45) * (24) * (60) * (60)``, a line continuation, or a
    ``_DAY`` constant. A guard that fails on a no-op teaches maintainers to delete
    it. Both sides are now evaluated as arithmetic, so the test couples the value
    rather than its spelling.
    """
    import ast
    import re

    def evaluate(expression: str, path: str) -> int:
        """Evaluate a literal arithmetic expression, refusing anything else.

        ``ast.literal_eval`` rejects ``45 * 24``, so walk the tree instead. Only
        integer literals, multiplication and addition are permitted — enough for any
        honest spelling of a duration, and not enough to execute anything.
        """

        def value(node: ast.AST) -> int:
            if isinstance(node, ast.Constant) and isinstance(node.value, int):
                return node.value
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mult, ast.Add)):
                left, right = value(node.left), value(node.right)
                return left * right if isinstance(node.op, ast.Mult) else left + right
            raise AssertionError(
                f"{path} declares the threshold as an expression this test cannot "
                f"evaluate ({expression!r}). Keep it literal integer arithmetic, or "
                f"update this guard deliberately."
            )

        return value(ast.parse(expression.strip(), mode="eval").body)

    def threshold(path: str, pattern: str) -> int:
        text = (ROOT / path).read_text()
        # MULTILINE, so ``^`` anchors each declaration to its own line rather than
        # to the start of the file.
        match = re.search(pattern, text, re.MULTILINE)
        assert match, (
            f"STALE_REGISTRATION_AFTER_SECONDS not found in {path}. If it was "
            f"renamed or moved, update both sides and this guard together."
        )
        return evaluate(match.group(1), path)

    python_seconds = threshold(
        "nemweb_foundation/agentic_energy/nemweb/quality.py",
        r"^STALE_REGISTRATION_AFTER_SECONDS\s*=\s*(.+?)\s*$",
    )
    typescript_seconds = threshold(
        "nemweb_app/client/src/domain/fuelCapture.ts",
        r"^export const STALE_REGISTRATION_AFTER_SECONDS\s*=\s*(.+?);\s*$",
    )

    assert python_seconds == typescript_seconds, (
        f"registration staleness threshold has drifted: "
        f"quality.py says {python_seconds}s, fuelCapture.ts says {typescript_seconds}s"
    )
    # A monthly archive is up to 31 days apart by definition, so a threshold at or
    # below that alarms every ordinary month in both layers at once.
    assert python_seconds > 31 * 24 * 60 * 60


def test_app_states_the_availability_and_settlement_boundaries_on_screen():
    """A capture screen invites a curtailment reading, so the denial must be visible.

    AEMO Current publishes no five-minute availability, and the revenue figure is
    an indicative energy value rather than a settlement figure. Both boundaries are
    asserted here so they cannot be lost to a later copy edit.
    """
    purpose = (ROOT / "nemweb_app/client/src/components/AppPurpose.tsx").read_text()
    shell = (ROOT / "nemweb_app/client/src/components/RegionalOperationsShell.tsx").read_text()
    assert "no five-minute availability" in purpose
    # JSX prose is line-wrapped, so assert fragments that survive the wrapping
    # rather than a sentence that spans a newline and two indents.
    assert "Curtailment is not" in shell
    assert "AEMO Current publishes no five-minute availability" in shell
    assert "excluding FCAS, loss factors, contracts, and settlement adjustment" in shell
    # The borrowed design system is MIT licensed and must stay attributed.
    assert "Open Electricity" in shell
    assert "MIT licensed" in shell


def test_app_mock_smoke_does_not_start_workspace_plugins():
    playwright = (ROOT / "nemweb_app/playwright.config.ts").read_text()
    makefile = (ROOT / "Makefile").read_text()
    assert "vite preview" in playwright
    assert "npm start" not in playwright
    assert "VITE_DATA_MODE=mock npx vite" in makefile


def test_no_script_mandates_one_hardcoded_databricks_profile_name():
    """The guardrail is an explicit profile, not a particular profile.

    miniwiki/guardrails.md: "Use an explicitly named Databricks profile; never
    select a workspace implicitly." Equality checks against one hardcoded name go
    further than that and cause real breakage: they embed one operator's
    workspace in a public repository, and they make every script unusable on a
    machine whose CLI has no profile of that name.

    This has already regressed once, renamed from "daveok" to "DEFAULT" rather
    than removed, so it is asserted rather than trusted. Runnable examples in
    prose may still name a profile to stay copy-pasteable; executable guards may
    not.
    """
    scripts = [
        *(ROOT / "nemweb_foundation/scripts").glob("*.py"),
        *(ROOT / "workshop/lakebase/scripts").glob("*.py"),
        *(ROOT / "workshop/lakebase/scripts").glob("*.sh"),
        ROOT / "nemweb_foundation/agentic_energy/nemweb/evidence.py",
    ]
    offenders = []
    for script in scripts:
        if not script.is_file():
            continue
        for number, line in enumerate(script.read_text().splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Python equality guard, e.g. `if args.profile != "DEFAULT":`
            python_guard = "profile" in stripped and "!=" in stripped and '"' in stripped
            # Shell equality guard, e.g. `if [[ "$PROFILE" != "daveok" ]]`
            shell_guard = "$PROFILE" in stripped and "!=" in stripped
            if python_guard or shell_guard:
                offenders.append(f"{script.relative_to(ROOT)}:{number}: {stripped}")
    assert not offenders, (
        "scripts must require an explicitly named profile without mandating which "
        "name:\n" + "\n".join(offenders)
    )


def test_app_analytics_query_parameters_are_referentially_stable():
    app = (ROOT / "nemweb_app/client/src/App.tsx").read_text()
    assert "const EMPTY_QUERY_PARAMETERS" in app
    assert "useMemo(() => ({" in app
    assert "useAnalyticsQuery('latest_region_status', regionParameters)" in app
    assert "useAnalyticsQuery('latest_fuel_generation', fuelParameters)" in app
    assert "sql.string(servingTableParameters.region_status_table)" in app
    assert "sql.string(servingTableParameters.fuel_generation_table)" in app
