#!/usr/bin/env python3
"""Prove the learner checkpoint fails for the intended missing implementation."""
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = 'NotImplementedError: Initial-supply exercise: implement the regional SCADA summary'


def main():
    with tempfile.TemporaryDirectory(prefix='energy-learner-') as directory:
        report = Path(directory) / 'results.xml'
        result = subprocess.run(['uv', 'run', '--frozen', 'pytest',
            'workshop/initial-supply/test_behaviour.py', '--junitxml', str(report)],
            cwd=ROOT, capture_output=True, text=True)
        if not report.exists():
            raise RuntimeError('pytest did not produce a report: ' + result.stderr)
        cases = ET.parse(report).findall('.//testcase')
        scenarios = json.loads((ROOT / 'workshop/initial-supply/scenarios.json').read_text())
        names = {case.attrib['name'].split('[', 1)[-1].removesuffix(']') for case in cases}
        valid = result.returncode == 1 and len(cases) == len(scenarios) and names == {s['name'] for s in scenarios}
        valid = valid and all(case.find('failure') is not None and
            EXPECTED in case.find('failure').attrib.get('message', '') for case in cases)
        if not valid:
            raise RuntimeError('Not the intended learner failures:\n' + result.stdout + result.stderr)
        print(f'{len(cases)} scenarios failed at the intended learner stub; checkpoint verified')


if __name__ == '__main__':
    main()
