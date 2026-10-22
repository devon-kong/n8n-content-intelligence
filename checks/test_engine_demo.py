"""The engine demo must isolate all external boundaries and disclose changes."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class EngineDemoTests(unittest.TestCase):
    def test_variants_are_inactive_and_only_use_local_http(self):
        spec = importlib.util.spec_from_file_location('engine_demo', ROOT / 'scripts/demo_engine.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            paths, changes = module.prepare_variants(Path(temp), 'http://127.0.0.1:18766')
            self.assertEqual(len(paths), 7)
            self.assertTrue(changes)
            for path in paths:
                flow = json.loads(path.read_text())
                original = json.loads((ROOT / 'n8n/workflows' / path.name).read_text())
                self.assertFalse(flow['active'])
                self.assertEqual(flow['connections'], original['connections'])
                for node in flow['nodes']:
                    self.assertNotIn('credentials', node)
                    self.assertNotIn('feishu-lite', node['type'])
                    self.assertNotIn('deepseek', node['type'])
                    if node['type'] == 'n8n-nodes-base.httpRequest':
                        self.assertTrue(node['parameters']['url'].startswith('http://127.0.0.1:18766/'))
            with self.assertRaises(ValueError):
                module.prepare_variants(Path(temp), 'https://example.com')

    def test_execution_summary_requires_engine_result(self):
        spec = importlib.util.spec_from_file_location('engine_demo', ROOT / 'scripts/demo_engine.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with self.assertRaises(ValueError):
            module.execution_summary('runner failed before execution')
        result = module.execution_summary('runner ready\n' + json.dumps({'status': 'error', 'data': {'resultData': {'lastNodeExecuted': 'Build Config Snapshot', 'error': {'message': 'Synthetic failure'}}}}))
        self.assertEqual(result, {'status': 'error', 'last_node': 'Build Config Snapshot', 'error_message': 'Synthetic failure'})

    def test_stable_rerun_must_finish_and_make_no_writes(self):
        spec = importlib.util.spec_from_file_location('engine_demo', ROOT / 'scripts/demo_engine.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        good = dict(scenario='stable_rerun', exit_code=0, status='success', error_message=None,
                    last_node='Check Metric Enabled', created=0, updated=0, summary_fixture_calls=0, summary_writes=0)
        module.validate_successful_run(good)
        for change in [dict(last_node='Read Pipeline Config'), dict(status='error'), dict(error_message='Failed'), dict(summary_writes=1)]:
            with self.assertRaises(ValueError):
                module.validate_successful_run({**good, **change})
