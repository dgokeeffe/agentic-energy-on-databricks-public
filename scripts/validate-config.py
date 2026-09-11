#!/usr/bin/env python3
"""Check isolation values before authenticated bundle validation."""
import argparse
import json
import os
from pathlib import Path
import re


def validate(target, values):
    for key in ('deployment_id', 'schema_suffix', 'catalog', 'lakebase_project_id', 'postgres_branch_id'):
        if not values.get(key):
            raise ValueError(f'Missing {key}: set BUNDLE_VAR_{key} or the target variable-overrides.json')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,17}', values['deployment_id']):
        raise ValueError('deployment_id must start with a lowercase letter and use at most 18 lowercase letters, digits or hyphens')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', values['schema_suffix']):
        raise ValueError('schema_suffix must be a SQL identifier')
    if target == 'lab' and not values.get('runtime_service_principal'):
        raise ValueError('lab requires an explicit runtime_service_principal')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=('dev', 'lab'), required=True)
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / '.databricks/bundle' / args.target / 'variable-overrides.json'
    values = json.loads(path.read_text()) if path.exists() else {}
    # Bundle variable precedence: environment values override local overrides.
    values.update({key.removeprefix('BUNDLE_VAR_'): value for key, value in os.environ.items() if key.startswith('BUNDLE_VAR_')})
    validate(args.target, values)
