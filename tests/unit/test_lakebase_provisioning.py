import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location('provision', Path(__file__).resolve().parents[2] / 'scripts/provision-lakebase.py')
provision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provision)


def test_existing_resource_is_reused_without_mutation(monkeypatch):
    cli = provision.Cli('chosen')
    calls = []
    def run(*args, **kwargs):
        calls.append(args)
        return {'name': 'projects/example'}
    monkeypatch.setattr(cli, 'run', run)
    assert cli.ensure(('postgres', 'get-project', 'projects/example'), ('postgres', 'create-project', 'example'), {}) == {'name': 'projects/example'}
    assert len(calls) == 1


def test_missing_resource_is_created_then_read(monkeypatch):
    cli = provision.Cli('chosen')
    calls = []
    responses = iter([None, {}, {'name': 'projects/example'}])
    monkeypatch.setattr(cli, 'run', lambda *args, **kwargs: (calls.append(args), next(responses))[1])
    assert cli.ensure(('postgres', 'get-project', 'projects/example'), ('postgres', 'create-project', 'example'), {})['name'] == 'projects/example'
    assert [call[1] for call in calls] == ['get-project', 'create-project', 'get-project']


def test_permission_error_never_becomes_missing_resource(monkeypatch):
    monkeypatch.setattr(provision.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=1, stderr='PERMISSION_DENIED', stdout=''))
    with pytest.raises(RuntimeError, match='PERMISSION_DENIED'):
        provision.Cli('chosen').run('postgres', 'get-project', 'projects/example', missing_ok=True)


def test_every_command_carries_explicit_profile(monkeypatch):
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout='{}', stderr='')
    monkeypatch.setattr(provision.subprocess, 'run', run)
    provision.Cli('chosen').run('postgres', 'create-project', 'example', body={'spec': {}})
    assert calls[0][calls[0].index('--profile') + 1] == 'chosen'
