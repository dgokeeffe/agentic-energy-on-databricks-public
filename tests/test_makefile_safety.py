from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_makefile_contains_only_local_or_read_only_targets():
    text = (ROOT / "Makefile").read_text()
    for command in (
        "bundle deploy", "bundle run", "apps deploy", "postgres create",
        "postgres delete", "unpause", "git push", "git merge", "issue close",
    ):
        assert command not in text.lower()
    targets = set(re.findall(r"^([a-z][a-z0-9-]*):", text, re.M))
    assert {"validate-local", "validate-readonly", "bundle-validate", "app-test", "ml-test", "lakebase-test"} <= targets


def test_workspace_validation_refuses_missing_or_wrong_profile():
    completed = subprocess.run(
        ["make", "bundle-validate", "PROFILE=wrong"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert completed.returncode != 0
    assert "PROFILE=DEFAULT is required" in completed.stderr
