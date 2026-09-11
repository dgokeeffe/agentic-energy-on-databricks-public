"""Offline checks spanning bundle, dataset declarations, publication and app reads.

These validate the authored graph and file contracts, not remote Spark execution.
"""
import ast
import json
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src/agentic_energy'


def resource(name):
    return yaml.safe_load((ROOT / 'resources' / name).read_text())['resources']


def declarations(path):
    result = {}
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in {'table', 'materialized_view', 'temporary_view'}:
                    name = next(ast.literal_eval(k.value) for k in dec.keywords if k.arg == 'name')
                    result[name] = dec.func.attr
    return result


def test_pipeline_libraries_have_unique_declarations_and_resolvable_imports():
    pipeline = resource('nemweb.pipeline.yml')['pipelines']['nemweb']
    assert pipeline['serverless'] is True
    assert (ROOT / 'resources' / pipeline['root_path']).resolve() == ROOT / 'src'
    names = {}
    paths = [(ROOT / 'resources' / library['file']['path']).resolve() for library in pipeline['libraries']]
    assert len(paths) == len(set(paths))
    for path in paths:
        defined = declarations(path)
        assert defined, f'Helper incorrectly included as library: {path}'
        assert not names.keys() & defined.keys(), f'Duplicate dataset in {path}'
        names.update(defined)
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('agentic_energy.'):
                imported = ROOT / 'src' / (node.module.replace('.', '/') + '.py')
                assert imported.is_file()
                assert imported not in paths, 'A library must not also execute on import'
    assert names['_nemweb_parsed_records'] == 'temporary_view'
    assert all(kind == 'table' for name, kind in names.items() if name.startswith('bronze_'))
    assert all(kind == 'materialized_view' for name, kind in names.items() if name.startswith(('silver_', 'gold_')))
    for path in paths:
        for table in re.findall(r'spark\.read(?:Stream)?\.table\(["\']([^"\']+)', path.read_text()):
            assert table in names, f'{path.name} reads undeclared {table}'
    assert set(paths) == {p for layer in ('bronze', 'silver', 'gold') for p in (SRC / layer).glob('*.py') if declarations(p)}


def test_root_targets_and_refresh_dependencies():
    bundle = yaml.safe_load((ROOT / 'databricks.yml').read_text())
    assert set(bundle['targets']) == {'dev', 'lab'}
    assert bundle['targets']['dev']['mode'] == 'development'
    assert bundle['targets']['lab']['mode'] == 'production'
    assert 'run_as' not in bundle['targets']['lab']
    for job in bundle['targets']['lab']['resources']['jobs'].values():
        assert job['run_as']['service_principal_name'] == '${var.runtime_service_principal}'
    assert bundle['targets']['lab']['resources']['pipelines']['nemweb']['run_as']['service_principal_name'] == '${var.runtime_service_principal}'
    for target in bundle['targets'].values():
        assert target['presets']['trigger_pause_status'] == 'PAUSED'
        assert '${var.deployment_id}' in target['workspace']['root_path']
    tasks = resource('refresh.job.yml')['jobs']['nemweb_refresh']['tasks']
    assert [t['run_job_task']['job_parameters']['scope'] for t in tasks[:-1]] == ['context', 'regional', 'critical']
    for previous, task in zip(tasks, tasks[1:]):
        assert task['depends_on'] == [{'task_key': previous['task_key']}]
    assert 'refresh_selection' not in tasks[-1]['pipeline_task']
    assert resource('refresh.job.yml')['jobs']['nemweb_refresh']['schedule']['pause_status'] == 'PAUSED'
    assert resource('context_refresh.job.yml')['jobs']['nemweb_context_refresh']['schedule']['pause_status'] == 'PAUSED'


def test_all_publications_match_sync_keys_and_api_tables():
    datasets = json.loads((ROOT / 'resources/lakebase/datasets.json').read_text())
    tasks = resource('publication.job.yml')['jobs']['nemweb_app_serving']['tasks']
    assert len(datasets) == len(tasks) == 3
    queries = (ROOT / 'app/server/db/serving.ts').read_text()
    for dataset, task in zip(datasets, tasks):
        path = (ROOT / 'resources' / task['sql_task']['file']['path']).resolve()
        sql = path.read_text()
        assert dataset['source'] == path.stem
        assert 'delta.enableChangeDataFeed' in sql
        assert 'MERGE WITH SCHEMA EVOLUTION' in sql
        assert 'WHEN NOT MATCHED THEN INSERT' in sql
        assert 'DELETE' not in sql.upper()
        assert 'DROP TABLE' not in sql.upper()
        for key in dataset['keys']:
            assert f'target.{key} = source.{key}' in sql
        assert f'FROM app_read.{dataset["target"]}' in queries
    assert queries.count('LIMIT ') == 3
    assert 'price_source_run_no' in queries and 'demand_source_run_no' in queries
    assert 'prediction' not in queries
    app = resource('app.app.yml')['apps']['app']
    assert [r['name'] for r in app['resources']] == ['postgres']
    assert app['lifecycle']['started'] is False


def test_resource_paths_exist():
    for path in (ROOT / 'resources').glob('*.yml'):
        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in {'path', 'python_file', 'source_code_path'} and isinstance(item, str) and item.startswith('../'):
                        assert (path.parent / item).exists(), (path, item)
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        walk(yaml.safe_load(path.read_text()))
