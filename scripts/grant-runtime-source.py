#!/usr/bin/env python3
"""Grant the configured lab runtime read access to this bundle's source and wheels."""
import argparse
import json
import subprocess

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
principal = bundle['variables']['runtime_service_principal'].get('value')
if args.target == 'lab' and principal:
    root = bundle['workspace']['root_path'].rstrip('/') + '/'
    for key in ('file_path', 'artifact_path'):
        path = bundle['workspace'][key]
        if not path.startswith(root):
            raise ValueError('Runtime source grant must remain inside the isolated bundle root')
        directory = cli('workspace', 'get-status', path)
        cli('permissions', 'update', 'directories', str(directory['object_id']), body={
            'access_control_list': [{'service_principal_name': principal, 'permission_level': 'CAN_READ'}],
        })
        print(f'Runtime CAN_READ: {path}')
