from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "grant-workshop-access.py"
# An explicit profile is part of every valid invocation. The repository mandates
# that one is named, not which one, so this fixture uses an arbitrary name.
BASE = [
    sys.executable,
    str(SCRIPT),
    "--catalog",
    "energy",
    "--schema",
    "nemweb",
    "--volume",
    "landing",
    "--warehouse-id",
    "abc123",
    "--profile",
    "any-operator-profile",
    "--dry-run",
]

# Same arguments without a profile, for the omission case.
BASE_WITHOUT_PROFILE = [argument for argument in BASE if argument not in {"--profile", "any-operator-profile"}]


def test_grant_script_dry_run_has_complete_idempotent_uc_chain() -> None:
    result = subprocess.run(
        [*BASE, "operator@example.com"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "GRANT USE CATALOG ON CATALOG `energy` TO `operator@example.com`" in result.stdout
    assert "GRANT USE SCHEMA ON SCHEMA `energy`.`nemweb`" in result.stdout
    assert "GRANT READ VOLUME, WRITE VOLUME ON VOLUME `energy`.`nemweb`.`landing`" in result.stdout

    reader = subprocess.run(
        [*BASE, "--readers", "reader group"], capture_output=True, text=True, check=False
    )
    assert reader.returncode == 0, reader.stderr
    assert "GRANT READ VOLUME ON VOLUME" in reader.stdout
    assert "WRITE VOLUME" not in reader.stdout


def test_grant_script_rejects_unsafe_principal_and_implicit_profile() -> None:
    unsafe = subprocess.run(
        [*BASE, "bad`principal"], capture_output=True, text=True, check=False
    )
    assert unsafe.returncode != 0
    assert "principal" in unsafe.stderr

    # Omitting --profile must fail, because the CLI would otherwise fall through
    # to whichever default profile the machine carries. This is the safety
    # property; the profile's name is not.
    implicit = subprocess.run(
        [*BASE_WITHOUT_PROFILE, "operator"], capture_output=True, text=True, check=False
    )
    assert implicit.returncode != 0
    assert "--profile" in implicit.stderr

    # An empty or whitespace profile is the same failure spelled differently.
    blank = subprocess.run(
        [*BASE_WITHOUT_PROFILE, "--profile", "   ", "operator"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert blank.returncode != 0
    assert "--profile" in blank.stderr


def test_grant_script_accepts_any_explicitly_named_profile() -> None:
    # No profile name is privileged. Two unrelated names must both work, so the
    # repository cannot drift back to mandating one operator's workspace.
    for profile in ("DEFAULT", "some-other-workspace"):
        result = subprocess.run(
            [*BASE_WITHOUT_PROFILE, "--profile", profile, "operator@example.com"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
