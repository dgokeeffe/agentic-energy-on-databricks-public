import hashlib
import json
from pathlib import Path

from agentic_energy.ingestion.parser import parse_zip_bytes

ROOT = Path(__file__).resolve().parents[2] / 'src/agentic_energy/resources/nemweb_snapshot/v2'


def test_application_snapshot_has_aligned_market_intervals_and_valid_checksums():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    intervals = {'dispatchis': set(), 'dispatch_scada': set()}
    assert manifest['required_families'] == ['dispatchis', 'dispatch_scada', 'registration']
    for item in manifest['artifacts']:
        data = (ROOT / item['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == item['sha256']
        parsed = parse_zip_bytes(data, item['report_family'])
        assert not [issue for issue in parsed.issues if issue.severity == 'error']
        if item['report_family'] in intervals:
            for row in parsed.records:
                if row.values.get('SETTLEMENTDATE'):
                    intervals[item['report_family']].add(row.values['SETTLEMENTDATE'])
    assert len(intervals['dispatchis']) == 2
    assert intervals['dispatchis'] == intervals['dispatch_scada']


def test_application_snapshot_lands_all_required_families(tmp_path):
    import importlib.util
    from agentic_energy.ingestion.lander import land_archives

    script = ROOT.parents[4] / "scripts/land_nemweb_delta.py"
    spec = importlib.util.spec_from_file_location("land_nemweb_delta", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scope in ("context", "critical"):
        archives = module._snapshot_inputs(ROOT, "snapshot", scope)
        result = land_archives(
            archives, tmp_path, run_id=scope, source_mode="snapshot",
            required_families=tuple(sorted({a.report_family for a in archives})),
        )
        assert result.status == "success"
