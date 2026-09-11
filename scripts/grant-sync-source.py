#!/usr/bin/env python3
"""Grant the explicitly selected sync operator SELECT on the three serving sources."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--target', choices=('dev', 'lab'), required=True)
    args = parser.parse_args()

    def cli(*command, body=None):
        cmd = ['databricks', *command, '--profile', args.profile, '-o', 'json']
        if body is not None:
            cmd += ['--json', json.dumps(body)]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return json.loads(result.stdout) if result.stdout.strip() else {}

    bundle = cli('bundle', 'summary', '--target', args.target)
    catalog = bundle['variables']['catalog']['value']
    schema = bundle['variables']['app_serving_schema']['value']
    operator = cli('current-user', 'me')['userName']
    for dataset in json.loads((ROOT / 'resources/lakebase/datasets.json').read_text()):
        table = f'{catalog}.{schema}.{dataset["source"]}'
        cli('grants', 'update', 'table', table, body={
            'changes': [{'principal': operator, 'add': ['SELECT']}],
        })
        print(f'Sync operator SELECT: {table}')


if __name__ == '__main__':
    main()
