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
    """Tracks A and B stay local or read-only.

    Track C is excluded deliberately: the attendee-isolation decision authorises a
    Track C attendee to deploy their own app against their own Lakebase branch.
    That exception is asserted separately, and narrowly, below.
    """
    text = "\n".join((ROOT / path).read_text() for path in (
        "QUICKSTART.md",
        "lane_a_business/Instructions.md",
        "lane_b_engineering/Instructions.md",
        "workshop/track-record-template.md",
    ))
    forbidden = re.compile(r"databricks\s+(?:bundle\s+deploy|bundle\s+run|postgres\s+(?:create|delete)|apps\s+deploy)", re.I)
    assert not forbidden.search(text)


def test_track_c_may_deploy_its_app_and_bootstrap_its_endpoint_only():
    """Track C's external permissions are real but bounded.

    It may deploy from nemweb_app and create its own endpoint through the
    endpoint helper. It must never deploy the foundation bundle, run its jobs,
    or delete a Lakebase project or branch.
    """
    text = (ROOT / "workshop/track_c_app/Instructions.md").read_text()

    # The one permitted external action, and only from the app directory.
    assert "databricks bundle deploy" in text
    assert "cd nemweb_app" in text
    assert "provision-attendee-endpoint.sh" in text
    assert "CAN_MANAGE" in text

    # Destructive or foundation-level operations must not appear at all.
    forbidden = re.compile(
        r"databricks\s+(?:postgres\s+delete|bundle\s+run)"
        r"|deploy\.sh"
        r"|DROP\s+SCHEMA",
        re.I,
    )
    assert not forbidden.search(text)

    # It must state the ordering rule that prevents the 42501 ownership failure.
    assert "42501" in text


def test_mock_and_integration_app_modes_share_domain_contract():
    interface = (ROOT / "nemweb_app/client/src/data/regionStatusRepository.ts").read_text()
    mock = (ROOT / "nemweb_app/client/src/data/mockRegionStatusRepository.ts").read_text()
    integration = (ROOT / "nemweb_app/client/src/data/integrationRegionStatusRepository.ts").read_text()
    assert "interface RegionStatusRepository" in interface
    assert "implements RegionStatusRepository" in mock
    assert "implements RegionStatusRepository" in integration
