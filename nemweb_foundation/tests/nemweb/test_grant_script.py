from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "grant-workshop-access.py"
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
    "--dry-run",
]


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

    wrong_profile = subprocess.run(
        [*BASE, "--profile", "daveok", "operator"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert wrong_profile.returncode != 0
    assert "--profile DEFAULT" in wrong_profile.stderr
