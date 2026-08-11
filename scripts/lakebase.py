#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["psycopg[binary]>=3.1"]
# ///
"""Lakebase control plane: project, per-developer branches, roles, schema.

Lakebase Autoscaling (`databricks postgres`) — projects, copy-on-write branches,
compute endpoints, scale-to-zero. The retired Provisioned tier
(`databricks database`, instances, CU_1-CU_8) must not be used: it is being
migrated away with no customer action, and its `database` CLI group is absent
from newer CLIs.

Why branches instead of one control plane per developer: a branch is
copy-on-write off the parent, so twenty developers get twenty isolated Postgres
databases that share storage and cost nothing extra until they diverge. Each gets
its own `source_metadata` rows without colliding, and a wrecked branch is deleted
and recreated in seconds. That is strictly better than either sharing one
database or paying for twenty projects.

    scripts/lakebase.py up                          # project + production branch + schema
    scripts/lakebase.py branch                      # a branch named after you
    scripts/lakebase.py branch --branch bugfix-123  # ...or named explicitly
    scripts/lakebase.py role <sp-application-id>    # let a job identity connect
    scripts/lakebase.py role me@example.com --identity-type USER
    scripts/lakebase.py migrate --branch <b>        # (re)apply control_plane.sql
    scripts/lakebase.py verify  --branch <b>        # connect + round-trip a row
    scripts/lakebase.py psql    --branch <b>        # print a psql invocation
    scripts/lakebase.py list
    scripts/lakebase.py down --branch <b> --yes     # delete a branch
    scripts/lakebase.py down --project --yes        # delete the whole project

Authentication is OAuth only. There is no Postgres password anywhere in this
project: the project is created with native password login disabled, the Postgres
role name IS the Databricks identity, and the credential is a bearer token minted
per connection with a ~1 hour lifetime. Nothing is stored in a file, an env var,
a secret scope or a connection string.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import psycopg

SCRIPTS = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS.parent
SQL_PATH = REPO_ROOT / "resources" / "lakebase" / "control_plane.sql"

SCHEMA = "agentic_energy"
DEFAULT_PROJECT = "agentic-energy"
DEFAULT_BRANCH = "production"
DEFAULT_ENDPOINT = "primary"
PG_DATABASE = "databricks_postgres"

# Tables control_plane.sql defines; asserted after every apply so a schema change
# cannot silently escape the check. Kept in step by tests/test_lakebase_artifacts.py.
EXPECTED_TABLES = {
    "source_metadata",
    "metadata_versions",
    "pipeline_runs",
    "pipeline_run_sources",
}

_CLI: str | None = None


def cli_bin() -> str:
    """Resolve a CLI that has the `postgres` command group (Lakebase needs >= 0.294).

    A host can have several `databricks` binaries at different versions (a
    wrapper, a user install, a system install). When an old one wins, every
    command fails with `unknown command "postgres"`, which says nothing about
    versions. Probe instead of trusting PATH order.
    """
    global _CLI
    if _CLI is not None:
        return _CLI
    candidates = [os.environ["DATABRICKS_CLI"]] if os.environ.get("DATABRICKS_CLI") else []
    candidates += [
        p
        for p in (
            shutil.which("databricks"),
            str(Path.home() / ".local/bin/databricks"),
            "/usr/local/bin/databricks",
        )
        if p
    ]
    tried = []
    for candidate in dict.fromkeys(candidates):
        if not Path(candidate).exists():
            continue
        if subprocess.run(
            [candidate, "postgres", "-h"], capture_output=True, text=True
        ).returncode == 0:
            _CLI = candidate
            return _CLI
        version = subprocess.run(
            [candidate, "--version"], capture_output=True, text=True
        ).stdout.strip()
        tried.append(f"  {candidate} ({version or 'unknown version'})")
    sys.exit(
        "no databricks CLI found with the `postgres` command group (Lakebase "
        "Autoscaling needs CLI >= 0.294.0).\nTried:\n"
        + "\n".join(tried)
        + "\nUpgrade the CLI, or point DATABRICKS_CLI at a newer binary."
    )


def cli(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run([cli_bin(), *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        sys.exit(f"databricks {' '.join(args)} failed:\n{proc.stderr.strip()}")
    return proc


def cli_json(*args: str, check: bool = True):
    proc = cli(*args, "-o", "json", check=check)
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout or "null")


def identity() -> str:
    return cli_json("current-user", "me")["userName"]


def slug(value: str) -> str:
    """RFC 1123 id: lowercase alphanumerics and hyphens, starting with a letter."""
    token = re.sub(r"[^a-z0-9]+", "-", value.split("@")[0].lower()).strip("-")
    if not token or not token[0].isalpha():
        token = f"b-{token}"
    return token[:63]


def branch_path(project: str, branch: str) -> str:
    return f"projects/{project}/branches/{branch}"


def endpoint_path(project: str, branch: str, endpoint: str = DEFAULT_ENDPOINT) -> str:
    return f"{branch_path(project, branch)}/endpoints/{endpoint}"


def endpoint_host(project: str, branch: str) -> str:
    """Resolve the branch's read-write endpoint host.

    A new branch gets its own endpoint; do not assume the parent's host, or every
    branch will silently read and write the parent's data.
    """
    endpoints = cli_json("postgres", "list-endpoints", branch_path(project, branch))
    for ep in endpoints or []:
        host = (ep.get("status") or {}).get("hosts", {}).get("host")
        if host:
            return host
    sys.exit(f"no endpoint with a host on {branch_path(project, branch)}")


def connect(project: str, branch: str) -> psycopg.Connection:
    """Direct PostgreSQL connection, OAuth only — no username/password.

    The token occupies the libpq password field because that is the only slot the
    wire protocol offers a bearer credential; it is minted here, used once, and
    never written down. Native Postgres passwords are disabled on the project.
    """
    if os.environ.get("PGPASSWORD"):
        sys.exit(
            "PGPASSWORD is set. This control plane authenticates with short-lived "
            "OAuth tokens only — remove it rather than configuring a password."
        )
    endpoint = endpoint_path(project, branch)
    token = cli_json("postgres", "generate-database-credential", endpoint)["token"]
    return psycopg.connect(
        host=endpoint_host(project, branch),
        dbname=PG_DATABASE,
        user=identity(),  # the Databricks identity, not a database username
        password=token,  # short-lived OAuth bearer token, never persisted
        sslmode="require",
        connect_timeout=30,
    )


def ensure_project(project: str) -> None:
    existing = cli_json("postgres", "get-project", f"projects/{project}", check=False)
    if existing:
        status = existing.get("status", {})
        print(f"project {project} exists (pg {status.get('pg_version')})")
        if status.get("enable_pg_native_login"):
            print(
                "  warning: native Postgres password login is ENABLED on this "
                "project; this control plane expects OAuth-only",
                file=sys.stderr,
            )
        return
    print(f"creating project {project}")
    created = cli_json(
        "postgres",
        "create-project",
        project,
        "--json",
        json.dumps({"spec": {"display_name": f"{project} control plane"}}),
    )
    status = created.get("status", {})
    print(
        f"  created: pg {status.get('pg_version')}, "
        f"default branch {status.get('default_branch')}, "
        f"native password login {status.get('enable_pg_native_login')}"
    )


# A project allows only 10 unarchived branches, so branch-per-developer does not
# reach 20 people in one project. Above this, give each developer their own
# project (the workspace limit is 1000) and let branches serve their features and
# CI runs.
MAX_BRANCHES = 10


def ensure_branch(project: str, branch: str, ttl_seconds: int | None) -> None:
    path = branch_path(project, branch)
    if cli_json("postgres", "get-branch", path, check=False):
        print(f"branch {branch} exists")
        return
    branches = cli_json("postgres", "list-branches", f"projects/{project}") or []
    if len(branches) >= MAX_BRANCHES:
        sys.exit(
            f"project {project} already has {len(branches)} branches "
            f"(limit {MAX_BRANCHES}). Delete an unused branch, or give this "
            f"developer their own project: --project agentic-energy-<name>"
        )
    # An expiration policy is mandatory: the API rejects a branch with neither
    # ttl nor no_expiry. A TTL is the right default for developer branches — it
    # garbage-collects abandoned work instead of accumulating cost.
    spec = {"source_branch": branch_path(project, DEFAULT_BRANCH)}
    if ttl_seconds:
        spec["ttl"] = f"{ttl_seconds}s"
        print(
            f"creating branch {branch} (copy-on-write from {DEFAULT_BRANCH}, "
            f"expires in {ttl_seconds // 86400}d)"
        )
    else:
        spec["no_expiry"] = True
        print(f"creating branch {branch} (copy-on-write from {DEFAULT_BRANCH}, no expiry)")
    cli(
        "postgres",
        "create-branch",
        f"projects/{project}",
        branch,
        "--json",
        json.dumps({"spec": spec}),
    )


def apply_schema(project: str, branch: str) -> int:
    sql = SQL_PATH.read_text()
    with connect(project, branch) as conn:
        with conn.cursor() as cur:
            # One transaction: a half-applied control plane is worse than none,
            # and every statement in the artifact is idempotent.
            cur.execute(sql)
        conn.commit()
        print(f"applied {SQL_PATH.relative_to(REPO_ROOT)} to {branch}")
        with conn.cursor() as cur:
            cur.execute(
                "select table_name from information_schema.tables "
                "where table_schema = %s",
                (SCHEMA,),
            )
            found = {row[0] for row in cur.fetchall()}
    missing = EXPECTED_TABLES - found
    for table in sorted(EXPECTED_TABLES):
        print(f"  {'ok  ' if table in found else 'MISS'} {SCHEMA}.{table}")
    if missing:
        print(f"missing tables: {', '.join(sorted(missing))}", file=sys.stderr)
        return 1
    return 0


def verify(project: str, branch: str) -> int:
    """Prove the branch is usable, not merely present: write, read back, clean up."""
    probe = f"verify-probe-{slug(identity())}"
    with connect(project, branch) as conn, conn.cursor() as cur:
        cur.execute("select current_user, current_database()")
        who, db = cur.fetchone()
        print(f"  connected to {branch} as {who} (database {db})")
        cur.execute(
            f"""insert into {SCHEMA}.metadata_versions
                (snapshot_id, source_ids, metadata_payload, status)
                values (%s, %s::jsonb, %s::jsonb, 'validated')
                on conflict (snapshot_id) do nothing""",
            (probe, "[]", json.dumps({"verify_probe": True})),
        )
        cur.execute(
            f"select created_by from {SCHEMA}.metadata_versions where snapshot_id = %s",
            (probe,),
        )
        row = cur.fetchone()
        if row is None:
            print("  probe row missing after insert", file=sys.stderr)
            return 1
        print(f"  wrote and read back a row (created_by = {row[0]})")
        cur.execute(
            f"delete from {SCHEMA}.metadata_versions where snapshot_id = %s", (probe,)
        )
        conn.commit()
        print("  probe row removed")
    return 0


def cmd_up(args) -> int:
    ensure_project(args.project)
    if args.branch != DEFAULT_BRANCH:
        ensure_branch(args.project, args.branch, args.ttl)
    rc = apply_schema(args.project, args.branch)
    return rc or verify(args.project, args.branch)


def cmd_branch(args) -> int:
    branch = args.branch if args.branch != DEFAULT_BRANCH else slug(identity())
    ensure_branch(args.project, branch, args.ttl)
    rc = apply_schema(args.project, branch)
    rc = rc or verify(args.project, branch)
    print(
        f"\nbranch {branch} ready. Delete it when done:\n"
        f"  scripts/lakebase.py down --branch {branch} --yes"
    )
    return rc


def grant_schema_privileges(project: str, branch: str, role: str) -> None:
    """Give a registered role the Postgres privileges to actually use the schema.

    Registering the identity only gets it *logged in*. Without these grants the
    connection succeeds and then every statement fails with
    `permission denied for schema agentic_energy` — a second, separate failure
    that looks nothing like an auth problem.

    ALTER DEFAULT PRIVILEGES covers tables added by a later migration, so a new
    control-plane table does not silently become unwritable for job identities.
    """
    with connect(project, branch) as conn, conn.cursor() as cur:
        # psycopg cannot parameterise identifiers; the role name comes from the
        # registered role list, and is quoted.
        quoted = '"' + role.replace('"', '""') + '"'
        for statement in (
            f"GRANT USAGE ON SCHEMA {SCHEMA} TO {quoted}",
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {SCHEMA} TO {quoted}",
            f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {SCHEMA} TO {quoted}",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {quoted}",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} "
            f"GRANT USAGE, SELECT ON SEQUENCES TO {quoted}",
        ):
            cur.execute(statement)
        conn.commit()
    print(f"  granted {SCHEMA} privileges to {role} on {branch}")


def cmd_role(args) -> int:
    """Register a Databricks identity as a Postgres role, then grant it the schema.

    The role must be created through this API with an identity_type and
    auth_method. Creating it in SQL (`CREATE ROLE ... WITH LOGIN`) appears to work
    but produces a role with no link to a Databricks identity, which can never
    satisfy an OAuth login — and the failure reads `password authentication
    failed`, despite OAuth using no password.

    Roles live on a branch and are inherited by branches created from it, so
    registering on the default branch before branching covers every later branch.
    """
    path = branch_path(args.project, args.branch)
    existing = cli_json("postgres", "list-roles", path) or []
    if any(
        (role.get("status") or {}).get("postgres_role") == args.principal
        for role in existing
    ):
        print(f"role {args.principal} already registered on {args.branch}")
    else:
        print(f"registering {args.principal} ({args.identity_type}) on {args.branch}")
        cli(
            "postgres",
            "create-role",
            path,
            "--role-id",
            args.principal,
            "--json",
            json.dumps(
                {
                    "spec": {
                        "identity_type": args.identity_type,
                        "postgres_role": args.principal,
                        "auth_method": "LAKEBASE_OAUTH_V1",
                    }
                }
            ),
        )
    grant_schema_privileges(args.project, args.branch, args.principal)
    for role in cli_json("postgres", "list-roles", path) or []:
        status = role.get("status") or {}
        print(
            f"  {status.get('postgres_role') or role['name'].rsplit('/', 1)[-1]}"
            f"  {status.get('identity_type') or ''}  {status.get('auth_method') or ''}"
        )
    return 0


def cmd_psql(args) -> int:
    """Emit a psql invocation with a freshly minted token, for interactive use.

    Printed as an environment assignment rather than embedded in a URL so the
    token does not land in shell history or a process list.
    """
    endpoint = endpoint_path(args.project, args.branch)
    token = cli_json("postgres", "generate-database-credential", endpoint)["token"]
    print(
        f"PGPASSWORD='{token}' \\\n"
        f"  psql 'host={endpoint_host(args.project, args.branch)} "
        f"dbname={PG_DATABASE} user={identity()} sslmode=require'"
    )
    print("\n# token expires in ~1 hour; re-run this command for a fresh one",
          file=sys.stderr)
    return 0


def cmd_list(args) -> int:
    projects = cli_json("postgres", "list-projects") or []
    if not projects:
        print("no Lakebase projects in this workspace")
        return 0
    for project in projects:
        pid = project.get("project_id")
        print(f"{pid}  (owner {project.get('status', {}).get('owner')})")
        for branch in cli_json("postgres", "list-branches", f"projects/{pid}") or []:
            name = branch["name"].rsplit("/", 1)[-1]
            parent = (branch.get("spec") or {}).get("parent", {}).get("branch", "")
            suffix = f"  <- {parent.rsplit('/', 1)[-1]}" if parent else ""
            print(f"  branch {name}{suffix}")
    return 0


def cmd_down(args) -> int:
    if not args.yes:
        sys.exit("refusing to delete without --yes")
    if args.project_scope:
        cli("postgres", "delete-project", f"projects/{args.project}")
        print(f"deleted project {args.project}")
        return 0
    if args.branch == DEFAULT_BRANCH:
        sys.exit(
            f"refusing to delete the default branch {DEFAULT_BRANCH}; "
            "pass --project to delete the whole project"
        )
    cli("postgres", "delete-branch", branch_path(args.project, args.branch))
    print(f"deleted branch {args.branch}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    sub = parser.add_subparsers(dest="command", required=True)

    # 7 days matches the skill's "feature development" guidance; branches may not
    # exceed 30 days.
    parser.add_argument(
        "--ttl",
        type=int,
        default=604800,
        metavar="SECONDS",
        help="branch lifetime, max 2592000 (30d). 0 means no expiry.",
    )

    sub.add_parser("up", help="project + branch + schema + verify").set_defaults(
        func=cmd_up
    )
    sub.add_parser(
        "branch", help="copy-on-write branch for one developer"
    ).set_defaults(func=cmd_branch)

    role = sub.add_parser("role", help="register an identity as a Postgres role")
    role.add_argument("principal", help="SP application ID, user email, or group")
    role.add_argument(
        "--identity-type",
        default="SERVICE_PRINCIPAL",
        choices=["SERVICE_PRINCIPAL", "USER", "GROUP"],
    )
    role.set_defaults(func=cmd_role)

    sub.add_parser("migrate", help="(re)apply control_plane.sql").set_defaults(
        func=lambda a: apply_schema(a.project, a.branch)
    )
    sub.add_parser("verify", help="connect and round-trip a row").set_defaults(
        func=lambda a: verify(a.project, a.branch)
    )
    sub.add_parser("psql", help="print a psql invocation with a fresh token").set_defaults(
        func=cmd_psql
    )
    sub.add_parser("list", help="list projects and branches").set_defaults(func=cmd_list)

    down = sub.add_parser("down", help="delete a branch or the project")
    down.add_argument("--yes", action="store_true")
    down.add_argument(
        "--project",
        dest="project_scope",
        action="store_true",
        help="delete the whole project rather than one branch",
    )
    down.set_defaults(func=cmd_down)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
