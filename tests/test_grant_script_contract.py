"""Contract tests for the Unity Catalog grant script.

Two failures motivated these. First, `docs/deployment.md` referenced
`scripts/grant-workshop-access.sh` while the script was absent from the tree, so
following the documented deployment procedure failed at the grant step. Second,
publishing governed tables added a `CREATE_TABLE` requirement that the original
volume-only script did not grant, and that gap fails *late* — after a run has
already written its Volume evidence.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "grant-workshop-access.sh"


def test_documented_scripts_exist():
    """Every scripts/*.sh path named in the docs must be present and executable."""
    import re

    docs = (REPO_ROOT / "docs" / "deployment.md").read_text()
    referenced = set(re.findall(r"scripts/[A-Za-z0-9_.-]+\.sh", docs))
    assert referenced, "expected the deployment doc to reference at least one script"
    for relative in sorted(referenced):
        path = REPO_ROOT / relative
        assert path.exists(), f"docs/deployment.md references missing {relative}"


def test_grant_script_covers_the_table_publication_chain():
    script = SCRIPT.read_text()
    # Publication needs CREATE_TABLE; consumers need SELECT. Both are schema-level.
    assert "CREATE_TABLE" in script
    assert "SELECT" in script
    for privilege in ("USE_CATALOG", "USE_SCHEMA", "WRITE_VOLUME", "READ_VOLUME"):
        assert privilege in script


def test_readers_get_select_but_never_create_table():
    """Business consumers query the Gold tables; they must not create them."""
    script = SCRIPT.read_text()
    reader_branch = script.split('if [ "${1:-}" = "--readers" ]; then')[1].split("fi")[0]
    assert "SELECT" in reader_branch
    assert "CREATE_TABLE" not in reader_branch
    assert "WRITE_VOLUME" not in reader_branch


def test_grant_script_is_valid_bash():
    import subprocess

    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)
