#!/usr/bin/env python3
"""Provision isolated Lakebase resources and write private bundle configuration.

Uses only the supported Postgres CLI. Existing resources are read and reused;
this command never replaces branches, drops databases, or deletes projects.
"""
import argparse
import configparser
import os
from urllib.parse import urlencode
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


class Cli:
    def __init__(self, profile):
        self.profile = profile

    def run(self, *args, body=None, missing_ok=False):
        command = ['databricks', *args, '--profile', self.profile, '-o', 'json']
        if body is not None:
            command += ['--json', json.dumps(body)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            if missing_ok and any(code in result.stderr for code in ('NOT_FOUND', 'does not exist', 'not found', 'not_found')):
                return None
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def ensure(self, get_args, create_args, body):
        value = self.run(*get_args, missing_ok=True)
        if value is None:
            print('Creating ' + ' '.join(create_args), flush=True)
            self.run(*create_args, body=body)
            value = self.run(*get_args)
        return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--catalog', required=True)
    parser.add_argument('--account-id', help='Account ID; otherwise read from the explicitly selected CLI profile')
    parser.add_argument('--deployment-id', required=True)
    parser.add_argument('--target', choices=('dev', 'lab'), required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,17}', args.deployment_id):
        parser.error('deployment-id must be a lowercase identifier of at most 18 characters')
    directory = ROOT / '.databricks/bundle' / args.target
    path = directory / 'variable-overrides.json'
    existing = json.loads(path.read_text()) if path.exists() else {}
    expected = {'catalog': args.catalog, 'deployment_id': args.deployment_id,
                'schema_suffix': args.deployment_id.replace('-', '_'),
                'lakebase_project_id': f'energy-{args.deployment_id}', 'postgres_branch_id': args.target}
    if any(key in existing and existing[key] != value for key, value in expected.items()):
        raise ValueError(f'Refusing to replace the existing isolation configuration in {path}')
    cli = Cli(args.profile)
    cli.run('catalogs', 'get', args.catalog)
    project_id = f'energy-{args.deployment_id}'
    project = f'projects/{project_id}'
    branch = f'{project}/branches/{args.target}'
    lakebase_catalog = f'energy_{args.deployment_id.replace("-", "_")}_{args.target}_lb'
    cli.ensure(('postgres', 'get-project', project), ('postgres', 'create-project', project_id), {'spec': {
        'display_name': f'Energy baseline {args.deployment_id}',
        'default_endpoint_settings': {'autoscaling_limit_min_cu': 0.5, 'autoscaling_limit_max_cu': 1, 'suspend_timeout_duration': '300s'},
    }})
    cli.ensure(('postgres', 'get-branch', branch), ('postgres', 'create-branch', project, args.target), {'spec': {
        'source_branch': f'{project}/branches/production', 'no_expiry': True,
    }})
    endpoint = cli.ensure(('postgres', 'get-endpoint', f'{branch}/endpoints/primary'),
                         ('postgres', 'create-endpoint', branch, 'primary'), {'spec': {
        'endpoint_type': 'ENDPOINT_TYPE_READ_WRITE',
        'autoscaling_limit_min_cu': 0.5, 'autoscaling_limit_max_cu': 1, 'suspend_timeout_duration': '300s',
    }})
    databases = cli.run('postgres', 'list-databases', branch)
    if isinstance(databases, dict):
        databases = databases.get('databases', [])
    database = next(db for db in databases if db.get('status', {}).get('postgres_database') == 'databricks_postgres')
    registered = cli.ensure(('postgres', 'get-catalog', f'catalogs/{lakebase_catalog}'),
                           ('postgres', 'create-catalog', lakebase_catalog), {'spec': {
        'postgres_database': 'databricks_postgres', 'branch': branch,
    }})
    binding = registered.get('spec', registered.get('status', {}))
    if binding.get('branch') and binding['branch'] != branch:
        raise ValueError('Existing Lakebase catalog points to another branch')
    values = {
        'catalog': args.catalog, 'deployment_id': args.deployment_id,
        'schema_suffix': args.deployment_id.replace('-', '_'),
        'lakebase_project_id': project_id, 'postgres_branch_id': args.target,
        'postgres_database_id': database['name'].rsplit('/', 1)[-1],
    }
    if args.target == 'lab':
        name = f'energy-{args.deployment_id}-runtime'
        principals = cli.run('service-principals', 'list', '--filter', f'displayName eq "{name}"')
        if isinstance(principals, dict):
            principals = principals.get('Resources', [])
        if len(principals) > 1:
            raise ValueError('Runtime display name is not unique')
        principal = principals[0] if principals else cli.run('service-principals', 'create', body={'displayName': name, 'active': True})
        values['runtime_service_principal'] = principal['applicationId']
        config = configparser.ConfigParser()
        config.read(os.environ.get('DATABRICKS_CONFIG_FILE', str(Path.home() / '.databrickscfg')))
        account_id = args.account_id or config.get(args.profile, 'account_id', fallback=None)
        if not account_id:
            raise ValueError('lab provisioning requires --account-id or account_id in the selected profile')
        user = cli.run('current-user', 'me')
        member = f'users/{user["userName"]}'
        rule_name = f'accounts/{account_id}/servicePrincipals/{principal["applicationId"]}/ruleSets/default'
        endpoint_path = '/api/2.0/preview/accounts/access-control/rule-sets'
        rules = cli.run('api', 'get', endpoint_path + '?' + urlencode({'name': rule_name, 'etag': ''}))
        grants = rules.get('grant_rules', [])
        role = 'roles/servicePrincipal.user'
        if not any(g['role'] == role and member in g.get('principals', []) for g in grants):
            grants.append({'role': role, 'principals': [member]})
            cli.run('api', 'put', endpoint_path, body={
                'name': rule_name, 'rule_set': {'name': rule_name, 'etag': rules['etag'], 'grant_rules': grants},
            })
        # Runtime can resolve this catalog; object permissions are scoped by the bundle.
        cli.run('grants', 'update', 'catalog', args.catalog, body={'changes': [
            {'principal': principal['applicationId'], 'add': ['USE_CATALOG']},
        ]})
    directory = ROOT / '.databricks/bundle' / args.target
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'variable-overrides.json'
    existing = json.loads(path.read_text()) if path.exists() else {}
    for key, value in values.items():
        if key in existing and existing[key] != value:
            raise ValueError(f'Refusing to replace existing {key} in {path}')
    path.write_text(json.dumps({**existing, **values}, indent=2) + '\n')
    (directory / 'lakebase.json').write_text(json.dumps({
        'project': project, 'branch': branch, 'endpoint': endpoint['name'],
        'database': database['name'], 'lakebase_catalog': lakebase_catalog,
    }, indent=2) + '\n')
    print(f'Configured {args.target}: {path}\nLakebase catalog: {lakebase_catalog}', flush=True)


if __name__ == '__main__':
    main()
