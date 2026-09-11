#!/usr/bin/env python3
"""Render supported Postgres CLI sync requests, or inspect existing syncs."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATASETS = json.loads((ROOT / 'resources/lakebase/datasets.json').read_text())


def requests(args):
    for dataset in DATASETS:
        yield dataset['target'], {'spec': {
            'source_table_full_name': f'{args.catalog}.{args.serving_schema}.{dataset["source"]}',
            'primary_key_columns': dataset['keys'],
            'scheduling_policy': 'TRIGGERED',
            'branch': args.branch,
            'postgres_database': args.database,
            'create_database_objects_if_missing': True,
            'new_pipeline_spec': {'storage_catalog': args.catalog, 'storage_schema': args.storage_schema},
        }}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('render', 'status'))
    parser.add_argument('--profile', required=True)
    parser.add_argument('--lakebase-catalog', required=True)
    parser.add_argument('--catalog')
    parser.add_argument('--serving-schema')
    parser.add_argument('--storage-schema')
    parser.add_argument('--branch')
    parser.add_argument('--database', default='databricks_postgres')
    parser.add_argument('--output-dir', type=Path, default=ROOT / '.databricks/sync')
    args = parser.parse_args()
    if args.action == 'render':
        for key in ('catalog', 'serving_schema', 'storage_schema', 'branch'):
            if not getattr(args, key):
                parser.error(f'--{key.replace("_", "-")} is required for render')
        if not args.branch.startswith('projects/') or '/branches/' not in args.branch:
            parser.error('--branch must be an explicit projects/<id>/branches/<id> resource name')
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for target, request in requests(args):
            path = args.output_dir / f'{target}.json'
            path.write_text(json.dumps(request, indent=2) + '\n')
            # JSON array is deliberately reviewable, without shell interpolation.
            print(json.dumps(['databricks', 'postgres', 'create-synced-table',
                              f'{args.lakebase_catalog}.app_read.{target}', '--json', f'@{path}', '--profile', args.profile]))
    else:
        for dataset in DATASETS:
            result = subprocess.run(['databricks', 'postgres', 'get-synced-table',
                                     f'synced_tables/{args.lakebase_catalog}.app_read.{dataset["target"]}',
                                     '--profile', args.profile, '-o', 'json'], check=True, capture_output=True, text=True)
            state = json.loads(result.stdout)
            print(json.dumps(state, indent=2))
            # Keep the full status for the operator: readiness fields vary by API version.
            if not state.get('status'):
                raise RuntimeError(f'No sync status returned for {dataset["target"]}')


if __name__ == '__main__':
    main()
