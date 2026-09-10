from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def test_mock_and_integration_app_modes_share_domain_contract():
    interface = (ROOT / "nemweb_app/client/src/data/regionStatusRepository.ts").read_text()
    mock = (ROOT / "nemweb_app/client/src/data/mockRegionStatusRepository.ts").read_text()
    integration = (ROOT / "nemweb_app/client/src/data/integrationRegionStatusRepository.ts").read_text()
    assert "interface RegionStatusRepository" in interface
    assert "implements RegionStatusRepository" in mock
    assert "implements RegionStatusRepository" in integration
