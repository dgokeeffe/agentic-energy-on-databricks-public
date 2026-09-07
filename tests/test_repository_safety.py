from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_repository_safety_validator_passes():
    completed = subprocess.run(
        [sys.executable, "scripts/validate-repository-safety.py"], cwd=ROOT,
        text=True, capture_output=True, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_participant_docs_do_not_provision_or_delete_external_resources():
    text = "\n".join((ROOT / path).read_text() for path in (
        "QUICKSTART.md", "docs/participant/workshop-playbook.md",
        "docs/participant/workshop-pair-record.md", "docs/participant/pilot-canvas.md",
    ))
    forbidden = re.compile(r"databricks\s+(?:bundle\s+deploy|bundle\s+run|postgres\s+(?:create|delete)|apps\s+deploy)", re.I)
    assert not forbidden.search(text)


def test_mock_and_integration_app_modes_share_domain_contract():
    interface = (ROOT / "nemweb_app/client/src/data/regionStatusRepository.ts").read_text()
    mock = (ROOT / "nemweb_app/client/src/data/mockRegionStatusRepository.ts").read_text()
    integration = (ROOT / "nemweb_app/client/src/data/integrationRegionStatusRepository.ts").read_text()
    assert "interface RegionStatusRepository" in interface
    assert "implements RegionStatusRepository" in mock
    assert "implements RegionStatusRepository" in integration
