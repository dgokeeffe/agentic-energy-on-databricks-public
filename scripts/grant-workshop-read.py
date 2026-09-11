#!/usr/bin/env python3
"""Grant the selected facilitator SELECT on exactly four workshop Gold products."""
import argparse
import json
import re
import subprocess

TABLES = ('gold_nem_initial_supply_5min', 'gold_nem_scada_generation_5min',
          'gold_nem_region_dispatch_5min', 'gold_nem_unit_dispatch_5min')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('profile', 'catalog', 'deployment-id'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--target', choices=('dev', 'lab'), required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,17}', args.deployment_id) or args.deployment_id.startswith('baseline'):
        parser.error('Use the new isolated workshop deployment ID')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', args.catalog):
        parser.error('Expected a simple catalog identifier')
    def cli(*command, body=None):
        cmd = ['databricks', *command, '--profile', args.profile, '-o', 'json']
        if body is not None:
            cmd += ['--json', json.dumps(body)]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return json.loads(result.stdout) if result.stdout.strip() else {}
    operator = cli('current-user', 'me')['userName']
    schema = f'energy_{args.target}_{args.deployment_id.replace("-", "_")}'
    for name in TABLES:
        table = f'{args.catalog}.{schema}.{name}'
        cli('grants', 'update', 'table', table, body={
            'changes': [{'principal': operator, 'add': ['SELECT']}]})
        print('Facilitator SELECT:', table)


if __name__ == '__main__':
    main()
