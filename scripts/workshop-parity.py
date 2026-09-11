#!/usr/bin/env python3
"""Verify full-column parity of all three unchanged workshop serving contracts.

Reads only. Export bounds must contain the entire isolated snapshot, otherwise
verification fails. Timestamp JSON preserves six fractional digits and offsets.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('profile', 'deployment-id', 'catalog', 'warehouse-id', 'output-dir'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--target', choices=('dev', 'lab'), required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,17}', args.deployment_id) or args.deployment_id.startswith('baseline'):
        parser.error('Use the new isolated workshop deployment ID')
    output = Path(args.output_dir).resolve()
    if not output.is_relative_to(ROOT / '.databricks') or output.exists():
        parser.error('Use a new output directory within ignored .databricks')
    output.mkdir(parents=True)
    query = load('workshop_query', ROOT / 'scripts/workshop-query.py')
    verify = load('verify_sync', ROOT / 'scripts/verify-sync.py')
    catalog = query.identifier(args.catalog)
    schema = f'energy_{args.target}_{args.deployment_id.replace("-", "_")}_serving'
    endpoint = f'projects/energy-{args.deployment_id}/branches/{args.target}/endpoints/primary'
    evidence = {}
    for dataset in json.loads((ROOT / 'resources/lakebase/datasets.json').read_text()):
        table = f'{catalog}.{schema}.{dataset["source"]}'
        properties = query.cli(args.profile, 'tables', 'get', table).get('properties', {})
        if properties.get('delta.enableChangeDataFeed') != 'true':
            raise ValueError(f'CDF not enabled: {table}')
        order = ','.join(dataset['keys'])
        sql_file = output / (dataset['target'] + '.sql')
        sql_file.write_text("SELECT to_json(struct(*), map('ignoreNullFields','false',"
            "'timestampFormat','yyyy-MM-dd HH:mm:ss.SSSSSSXXX','timeZone','UTC')) AS row_json "
            f"FROM (SELECT *, COUNT(*) OVER () AS _workshop_export_count FROM {table} ORDER BY {order} LIMIT 2000)")
        statement_file = output / (dataset['target'] + '-statement.json')
        subprocess.run([sys.executable, str(ROOT / 'scripts/workshop-query.py'),
            '--profile', args.profile, '--warehouse-id', args.warehouse_id,
            '--catalog', catalog, '--schema', schema, '--sql-file', str(sql_file),
            '--output', str(statement_file)], check=True, stdout=subprocess.DEVNULL)
        source = [json.loads(row['row_json']) for row in query.rows(json.loads(statement_file.read_text()))]
        if not source or any(int(row.pop('_workshop_export_count')) != len(source) for row in source):
            raise ValueError('Source empty or export does not contain the entire isolated snapshot')
        target = 'app_read.' + dataset['target']
        sql = f"SET timezone='UTC'; SELECT json_build_object('count',(SELECT COUNT(*) FROM {target}), 'rows', (SELECT COALESCE(json_agg(t),'[]') FROM (SELECT * FROM {target} ORDER BY {order} LIMIT 2000) t));"
        result = subprocess.run(['databricks', 'psql', endpoint, '--profile', args.profile, '--',
            '-d', 'databricks_postgres', '-qAt', '-v', 'ON_ERROR_STOP=1', '-c', sql],
            capture_output=True, text=True, check=True)
        synced = json.loads(result.stdout.strip())
        if int(synced['count']) != len(synced['rows']):
            raise ValueError('Postgres export does not contain the entire isolated snapshot')
        (output / (dataset['target'] + '-source.json')).write_text(json.dumps(source, indent=2) + '\n')
        (output / (dataset['target'] + '-postgres.json')).write_text(json.dumps(synced['rows'], indent=2) + '\n')
        count = verify.compare(source, synced['rows'], dataset['keys'])
        evidence[dataset['target']] = {'identical_rows': count, 'cdf': True}
        print(dataset['target'], count, 'identical full-column rows', flush=True)
    (output / 'parity.json').write_text(json.dumps(evidence, indent=2) + '\n')


if __name__ == '__main__':
    main()
