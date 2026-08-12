"""Offline checks on the native annotation authorization boundary.

Scope and limits
----------------
These are **static assertions over the SQL artifact**, in the same style as the
control-plane artifact checks: they need no Database Instance, so they run from a
clean clone and in CI. They prove the DDL *declares* the boundary the challenge
spec requires (`docs/challenge-spec.md` sections 8.2 and 8.4).

They do **not** prove Postgres enforces it at runtime. Statements like "a
participant cannot update another author's note" can only be demonstrated
against a provisioned Lakebase endpoint; that belongs in dated evidence under
`docs/test-evidence/`, not here. Treating these as proof of enforcement would
overclaim — they are a guard against the boundary being silently dropped or
weakened by a later edit.
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = REPO_ROOT / "resources" / "lakebase" / "control_plane.sql"
SQL_RAW = SQL_PATH.read_text()


def _strip_comments(sql: str) -> str:
    """Drop `--` line comments.

    Grants and privileges must be asserted against effective SQL only. Scanning
    raw text let the prose in `-- No DELETE: ...` register as a DELETE grant,
    i.e. a comment explaining the boundary was read as a breach of it.
    """
    return "\n".join(re.sub(r"--.*$", "", line) for line in sql.splitlines())


SQL = _strip_comments(SQL_RAW)

SCHEMA = "agentic_energy"
TABLE = "operator_annotations"
QUALIFIED = f"{SCHEMA}.{TABLE}"

# Section 8.2 defines the audit/identity contract for the native table.
REQUIRED_COLUMNS = {
    "annotation_id",
    "gold_entity_key",
    "note",
    "status",
    "author_identity",
    "created_at",
    "updated_at",
    "audit_version",
}


def statement_containing(needle: str) -> str:
    """Return the single SQL statement containing `needle`."""
    for statement in SQL.split(";"):
        if needle in statement:
            return statement
    return ""


def annotations_ddl() -> str:
    return statement_containing(f"CREATE TABLE IF NOT EXISTS {QUALIFIED}")


def column_definition(column: str) -> str:
    """Return the line defining `column` inside the annotations DDL."""
    for line in annotations_ddl().splitlines():
        stripped = line.strip()
        if re.match(rf"^{column}\b", stripped):
            return stripped
    return ""


# --------------------------------------------------------------------------
# Section 8.2 — the native annotations table and its audit fields
# --------------------------------------------------------------------------


def test_native_annotations_table_is_declared():
    assert annotations_ddl(), (
        f"{QUALIFIED} is not declared in {SQL_PATH.name}; challenge-spec 8.2 "
        "requires a native, application-owned annotations table"
    )


@pytest.mark.parametrize("column", sorted(REQUIRED_COLUMNS))
def test_every_audit_and_identity_column_is_present(column):
    assert column_definition(column), (
        f"column {column!r} from challenge-spec 8.2 is missing from {QUALIFIED}"
    )


def test_author_identity_is_not_client_supplied():
    """Identity must be server-assigned.

    An `author_identity` a client can set is not an identity, it is a free-text
    field: any annotator could forge another principal's note and the audit
    trail would faithfully record the lie. Defaulting to `current_user` makes
    the database the authority.
    """
    definition = column_definition("author_identity")
    assert "NOT NULL" in definition.upper(), (
        "author_identity must be NOT NULL so a row cannot be written without "
        f"an attributable author; got: {definition!r}"
    )
    assert "DEFAULT CURRENT_USER" in definition.upper(), (
        "author_identity must default to current_user so the session identity, "
        f"not the caller's payload, decides authorship; got: {definition!r}"
    )


def test_audit_timestamps_and_version_are_server_defaulted():
    for column, expected in (
        ("created_at", "NOW()"),
        ("updated_at", "NOW()"),
        ("audit_version", "1"),
    ):
        definition = column_definition(column).upper()
        assert "NOT NULL" in definition, f"{column} must be NOT NULL"
        assert f"DEFAULT {expected}" in definition, (
            f"{column} must be server-defaulted to {expected} so audit context "
            f"cannot be omitted by the caller; got: {definition!r}"
        )


def test_annotation_status_is_constrained():
    """Status is a governed category, not arbitrary text."""
    definition = column_definition("status").upper()
    assert "CHECK" in definition, (
        "status must be CHECK-constrained to the governed categories from "
        f"challenge-spec 8.2; got: {definition!r}"
    )


def test_note_cannot_be_blank():
    definition = column_definition("note").upper()
    assert "CHECK" in definition and "NOT NULL" in definition, (
        f"note must be NOT NULL and reject blank content; got: {definition!r}"
    )


# --------------------------------------------------------------------------
# Section 8.4 — role separation, enforced in the database
# --------------------------------------------------------------------------


def test_row_level_security_is_enabled_and_forced():
    upper = SQL.upper()
    assert f"ALTER TABLE {QUALIFIED} ENABLE ROW LEVEL SECURITY".upper() in upper, (
        "row level security must be enabled on the annotations table, or the "
        "role grants alone let any annotator rewrite any author's row"
    )
    assert f"ALTER TABLE {QUALIFIED} FORCE ROW LEVEL SECURITY".upper() in upper, (
        "row level security must be FORCEd so the table owner is not exempt "
        "from the same boundary"
    )


def test_update_policy_restricts_writes_to_the_authoring_identity():
    """The core authorization check.

    Without a USING clause tied to the session identity, INSERT/UPDATE on the
    table is effectively 'any annotator may edit anyone's annotation', which is
    the unsafe-annotation-access failure mode.
    """
    policies = [s for s in SQL.split(";") if "CREATE POLICY" in s and TABLE in s]
    assert policies, f"no row policies declared for {QUALIFIED}"

    update_policies = [p for p in policies if re.search(r"\bFOR\s+UPDATE\b", p, re.I)]
    assert update_policies, "no FOR UPDATE policy: any author's row is rewritable"
    for policy in update_policies:
        assert re.search(r"\bUSING\b", policy, re.I), (
            "UPDATE policy needs a USING clause selecting only the caller's rows"
        )
        assert "author_identity" in policy and "current_user" in policy.lower(), (
            "UPDATE policy must compare author_identity against current_user; "
            f"got: {policy.strip()!r}"
        )


def test_authorship_cannot_be_reassigned_by_an_update():
    """A WITH CHECK clause is required, not just USING.

    USING decides which rows you may modify; WITH CHECK decides what they may
    become. With USING alone, an annotator can take a row they legitimately own
    and hand authorship to someone else, escaping their own audit trail.
    """
    for policy in [s for s in SQL.split(";") if "CREATE POLICY" in s and TABLE in s]:
        if re.search(r"\bFOR\s+(UPDATE|INSERT|ALL)\b", policy, re.I):
            assert re.search(r"WITH\s+CHECK", policy, re.I), (
                "write policy must carry WITH CHECK so a row cannot be "
                f"rewritten to another identity; got: {policy.strip()!r}"
            )


def test_insert_policy_binds_new_rows_to_the_caller():
    policies = [s for s in SQL.split(";") if "CREATE POLICY" in s and TABLE in s]
    insert_policies = [
        p for p in policies if re.search(r"\bFOR\s+(INSERT|ALL)\b", p, re.I)
    ]
    assert insert_policies, "no INSERT policy: authorship of new rows is unbound"
    assert any(
        "author_identity" in p and "current_user" in p.lower() for p in insert_policies
    ), "INSERT policy must bind author_identity to current_user"


def test_annotator_role_cannot_delete_or_touch_gold():
    """Section 8.4 grants the annotator INSERT/UPDATE only."""
    grants = [
        s for s in SQL.split(";")
        if "GRANT" in s.upper() and "annotator" in s.lower()
    ]
    assert grants, "no GRANT to an annotator role; role separation is undeclared"
    granted = " ".join(grants).upper()
    assert "INSERT" in granted and "UPDATE" in granted
    assert "DELETE" not in granted, (
        "annotator must not hold DELETE: annotations are audit records, and "
        "deletion destroys the trail rather than superseding it"
    )
    assert not re.search(r"\bALL\s+PRIVILEGES\b", granted), (
        "annotator must not hold ALL PRIVILEGES"
    )


# --------------------------------------------------------------------------
# Section 8.1 — synced Gold stays read-only, and annotations never mutate it
# --------------------------------------------------------------------------


def test_annotations_do_not_write_back_to_gold():
    """Spec 8.3: annotations must not mutate Gold or flow back to AEMO.

    Triggers on the annotations table are legitimate (audit maintenance); what
    is forbidden is a trigger *body* that writes to any other relation. So this
    inspects the function bodies rather than banning triggers outright.
    """
    gold_targets = ("market_weather", "synced", "gold", "source_metadata")
    for body in re.findall(r"\$\$(.*?)\$\$", SQL, re.S):
        if "operator_annotations" not in body and "NEW." not in body:
            continue
        for verb in ("INSERT INTO", "UPDATE", "DELETE FROM", "COPY"):
            for match in re.finditer(rf"{verb}\s+([\w.]+)", body, re.I):
                target = match.group(1).lower()
                assert not any(g in target for g in gold_targets), (
                    f"annotation trigger body writes to {target!r}; spec 8.3 "
                    "forbids annotations mutating Gold or flowing back upstream"
                )


def test_audit_trigger_makes_updated_at_and_version_move():
    """Server-side audit maintenance, not caller-supplied.

    Column defaults alone are stale-by-construction on UPDATE: `updated_at`
    would keep its insert value forever and `audit_version` would never leave
    1, while still looking authoritative.
    """
    bodies = " ".join(re.findall(r"\$\$(.*?)\$\$", SQL, re.S))
    assert re.search(r"NEW\.updated_at\s*:=\s*now\(\)", bodies, re.I), (
        "an UPDATE must refresh updated_at server-side"
    )
    assert re.search(r"NEW\.audit_version\s*:=\s*OLD\.audit_version\s*\+\s*1", bodies, re.I), (
        "an UPDATE must increment audit_version server-side"
    )
    assert re.search(r"BEFORE\s+UPDATE\s+ON\s+" + re.escape(QUALIFIED), SQL, re.I), (
        "the audit function must be wired to a BEFORE UPDATE trigger"
    )


def test_authorship_and_creation_time_are_immutable():
    """WITH CHECK stops handing a row to *another* identity, but an author
    could still rewrite their own created_at. Pin both server-side."""
    bodies = " ".join(re.findall(r"\$\$(.*?)\$\$", SQL, re.S))
    for column in ("author_identity", "created_at"):
        assert re.search(rf"NEW\.{column}\s*:=\s*OLD\.{column}", bodies, re.I), (
            f"{column} must be pinned to its OLD value on UPDATE so the audit "
            "trail cannot be rewritten"
        )


def test_gold_entity_key_is_validated_logically():
    """Spec 8.2: physical FKs to a synced relation are capability-dependent.

    A synced read-only relation may not accept a physical FK, so the key must
    still be constrained locally rather than left as unvalidated free text.
    """
    definition = column_definition("gold_entity_key").upper()
    assert "NOT NULL" in definition, "gold_entity_key must be NOT NULL"
    assert "CHECK" in definition or "REFERENCES" in definition, (
        "gold_entity_key needs logical validation (CHECK) when a physical FK to "
        f"the synced relation is unavailable; got: {definition!r}"
    )


# --------------------------------------------------------------------------
# Artifact hygiene — same invariants the scrubbed artifact tests enforced
# --------------------------------------------------------------------------


def test_annotation_ddl_is_idempotent():
    """The migration applies this artifact repeatedly."""
    for kind, rest in re.findall(r"^\s*CREATE\s+(TABLE|INDEX)(.*)$", SQL, re.M):
        assert "IF NOT EXISTS" in rest.upper(), (
            f"CREATE {kind}{rest.rstrip()} is not re-runnable"
        )
    # Policies and roles have no IF NOT EXISTS in PostgreSQL; they must be
    # guarded explicitly so a second apply does not error.
    if "CREATE POLICY" in SQL:
        assert "DROP POLICY IF EXISTS" in SQL, (
            "CREATE POLICY is not idempotent; pair it with DROP POLICY IF EXISTS"
        )


def test_gold_entity_key_constraint_accepts_real_pipeline_keys(tmp_path):
    """Tie the CHECK to actual Gold output, not to my assumption about it.

    A regex that looks reasonable but rejects the keys the pipeline really emits
    would block every legitimate annotation while passing a purely static test.
    So run the fixture pipeline and validate its Gold grain against the
    committed constraint.
    """
    from agentic_energy.pipeline import run_pipeline

    definition = column_definition("gold_entity_key")
    match = re.search(r"~\s*'([^']+)'", definition)
    assert match, f"no regex CHECK found on gold_entity_key: {definition!r}"
    # standard_conforming_strings is on by default, so backslashes reach the
    # regex engine as written.
    pattern = re.compile(match.group(1))

    out = tmp_path / "gold"
    run_pipeline(output_dir=out, mode="fixture")
    gold = [
        json.loads(line)
        for line in (out / "gold" / "market_weather.jsonl").read_text().splitlines()
        if line
    ]
    assert gold, "fixture run produced no Gold rows"
    for row in gold:
        key = f"{row['region']}|{row['interval_utc']}"
        assert pattern.match(key), (
            f"committed CHECK rejects a real Gold key {key!r}; the constraint "
            "would block every legitimate annotation for this row"
        )


def test_gold_entity_key_constraint_rejects_malformed_keys():
    definition = column_definition("gold_entity_key")
    pattern = re.compile(re.search(r"~\s*'([^']+)'", definition).group(1))
    for bad in (
        "NSW1",                          # no interval
        "NSW1|2024-01-14 23:00:00",      # not ISO-Z
        "NSW1|2024-01-14T23:00:00",      # missing Z, so not unambiguously UTC
        "|2024-01-14T23:00:00Z",         # no region
        "nsw1|2024-01-14T23:00:00Z",     # unnormalized region case
        "NSW1|not-a-time",
        "'; DROP TABLE agentic_energy.operator_annotations; --",
    ):
        assert not pattern.match(bad), f"CHECK should reject {bad!r}"


def test_roles_are_created_idempotently():
    """CREATE ROLE has no IF NOT EXISTS; a second apply must not error."""
    if re.search(r"CREATE\s+ROLE", SQL, re.I):
        assert "pg_roles" in SQL, (
            "guard CREATE ROLE with a pg_roles existence check so the artifact "
            "stays re-runnable"
        )


def test_artifact_contains_no_tenant_specific_identifiers():
    """resources/lakebase/README.md forbids committing environment detail."""
    lowered = SQL_RAW.lower()
    for forbidden in ("azuredatabricks.net", "dapi", "adb-", "bearer ", "password="):
        assert forbidden not in lowered, (
            f"{forbidden!r} looks like environment-specific detail in a "
            "committed artifact"
        )
