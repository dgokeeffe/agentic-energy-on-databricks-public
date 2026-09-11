#!/usr/bin/env python3
"""Verify an explicitly named workshop app; optionally test temporary native writes."""
import argparse
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--app', required=True)
    parser.add_argument('--deployment-id', required=True)
    parser.add_argument('--exercise-writes', action='store_true')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.app not in {f'energy-dev-{args.deployment_id}', f'energy-lab-{args.deployment_id}'}:
        parser.error('App must match the explicitly selected deployment identifier')
    if args.deployment_id.startswith('baseline'):
        parser.error('Baseline resources are not workshop rehearsal targets')
    root = Path(__file__).resolve().parents[1]
    if not args.output.resolve().is_relative_to(root / '.databricks'):
        parser.error('Keep runtime evidence inside ignored .databricks')
    if args.output.exists():
        parser.error('Choose a fresh output path to preserve earlier evidence')
    def cli(*command):
        return json.loads(subprocess.run(['databricks', *command, '--profile', args.profile, '-o', 'json'],
                                        capture_output=True, text=True, check=True).stdout)
    app = cli('apps', 'get', args.app)
    token = cli('auth', 'token')['access_token']
    def api(method, route, body=None):
        request = urllib.request.Request(app['url'] + route, method=method,
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
            data=None if body is None else json.dumps(body).encode())
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()
                return response.status, json.loads(data) if data else None
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode()
    evidence = {'app': args.app, 'reads': {}, 'native_writes': 'not requested'}
    for route, bound in [('region-status', 100), ('fuel-generation', 1000), ('unit-dispatch', 1800)]:
        status, rows = api('GET', '/api/' + route)
        if status != 200 or not isinstance(rows, list) or not 0 < len(rows) <= bound:
            raise ValueError(f'{route}: invalid read status/count: {status}')
        evidence['reads'][route] = len(rows)
        if route == 'region-status':
            region = rows[0]
    if args.exercise_writes:
        status, created = api('POST', '/api/investigations', {
            'nemEventKey': 'workshop-rehearsal-' + str(uuid.uuid4()),
            'regionId': region['region_id'], 'intervalEnd': region['interval_end'],
            'teamIdentifier': 'workshop-rehearsal', 'status': 'open',
            'decision': 'Temporary workshop verification; removed after check.', 'evidenceReference': None})
        if status != 201:
            raise ValueError(f'Create failed: {status}')
        record_id = created['investigation_id']
        # Record the exact test-owned ID immediately, including if later cleanup fails.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({'cleanup_record_id': record_id, 'app': args.app}))
        try:
            status, listed = api('GET', '/api/investigations')
            if status != 200 or not any(r['investigation_id'] == record_id for r in listed):
                raise ValueError('Created investigation missing from list')
            update = {'expectedVersion': int(created['version']), 'status': 'reviewing',
                      'decision': 'Native persistence verified.'}
            status, updated = api('PATCH', '/api/investigations/' + record_id, update)
            if status != 200 or int(updated['version']) != int(created['version']) + 1:
                raise ValueError('Versioned update failed')
            status, _ = api('PATCH', '/api/investigations/' + record_id, update)
            if status != 404:
                raise ValueError('Stale version was not rejected with the established 404 contract')
            evidence['native_writes'] = {'create': 201, 'list': 200, 'update': 200, 'stale_version': 404}
        finally:
            status, _ = api('DELETE', '/api/investigations/' + record_id)
            if status != 204:
                raise ValueError(f'Cleanup failed; remove test-owned investigation {record_id}')
        evidence['native_writes']['delete'] = 204
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
