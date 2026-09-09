from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def _executable_lines(text: str) -> str:
    """Strip comments and blank lines so a scan tests code, not prose.

    Both this file's guards describe the very verbs they forbid ("never
    unpauses a schedule"), so a naive substring scan over the whole file would
    flag its own documentation. Only what actually runs is of interest.
    """
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(line.split(" #", 1)[0] if " #" in line else line)
    return "\n".join(lines)


def test_makefile_delegates_every_mutating_command_to_the_deploy_script():
    """No mutating command string may live in the Makefile itself.

    The deploy-* targets exist and do change the workspace, but each one shells
    out to scripts/deploy-workshop.sh. Keeping the literal commands out of this
    file preserves the original guarantee that reading the Makefile cannot
    mislead an operator about what a target will mutate, and keeps a single
    audited place where deployment happens.
    """
    text = (ROOT / "Makefile").read_text()
    executable = _executable_lines(text).lower()
    for command in (
        "bundle deploy", "bundle run", "apps deploy", "postgres create",
        "postgres delete", "unpause", "git push", "git merge", "issue close",
    ):
        assert command not in executable, command
    targets = set(re.findall(r"^([a-z][a-z0-9-]*):", text, re.M))
    assert {"validate-local", "validate-readonly", "bundle-validate", "app-test", "ml-test", "lakebase-test"} <= targets


def test_deploy_targets_delegate_to_the_single_audited_script():
    text = (ROOT / "Makefile").read_text()
    for target in ("deploy-plan", "deploy-all", "deploy-foundation", "deploy-app"):
        assert re.search(rf"^{target}:", text, re.M), target
    # Each mutating target must route through the one reviewed script.
    assert text.count("bash scripts/deploy-workshop.sh") == 4
    assert "--dry-run" in text


def test_deploy_script_never_unpauses_a_schedule_or_enables_live_nemweb():
    """The deployment path must not be able to start cadence or live ingestion.

    Both require a separate human decision, so neither may appear as an action in
    the script. `pause_status` is still read for verification, which is why the
    assertion targets the mutating verbs rather than the field name.
    """
    text = _executable_lines((ROOT / "scripts/deploy-workshop.sh").read_text()).lower()
    # Mutation verbs only. The script legitimately READS pause_status and reports
    # an "UNPAUSED SCHEDULE(S)" failure, so bare "unpause" would flag its own
    # guard; what must be absent is any command that changes those states.
    for forbidden in (
        "jobs update", "jobs reset", "pause_status: unpaused",
        '"pause_status": "unpaused"', "update-schedule",
        "allow_live_nemweb=true", "nemweb_mode=live",
        "delete-branch", "drop schema", "drop table", "delete-project",
        "--replace-existing", "reset-branch",
        "git push", "git commit", "git merge",
    ):
        assert forbidden not in text, forbidden


def test_workspace_validation_refuses_an_empty_profile():
    """A profile must always be explicit, but its name is workspace-specific.

    The former assertion required the literal name daveok. That prevented the
    repository from being validated in any workspace without a profile of that
    name, so the requirement is now that a profile is named, not which one.
    """
    completed = subprocess.run(
        ["make", "bundle-validate", "PROFILE="], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert completed.returncode != 0
    assert "PROFILE is required" in completed.stderr
