import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare', ROOT / 'scripts/prepare_n8n.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PrepareExports(unittest.TestCase):
    def setUp(self):
        # Ignored local state is absent in a fresh clone / CI checkout.
        (ROOT / '.work').mkdir(exist_ok=True)

    def config(self):
        return {'values': {'CONFIG_BASE_ID': 'demo-base', 'ACCOUNTS_TABLE_ID': 'demo-accounts', 'PIPELINES_TABLE_ID': 'demo-pipelines'}, 'workflow_ids': {'ciCatchMain00001': 'demo-imported-catch'}}

    def test_remaps_subworkflow_references_without_touching_templates(self):
        output = ROOT / '.work/test-prepare-remap'
        try:
            self.assertEqual(module.prepare(self.config(), output), 7)
            catch = json.loads((output / 'catch.json').read_text())
            entry = json.loads((output / 'entry-ai-news.json').read_text())
            self.assertEqual(catch['id'], 'demo-imported-catch')
            calls = [n for n in entry['nodes'] if n['type'] == 'n8n-nodes-base.executeWorkflow']
            self.assertEqual(calls[0]['parameters']['workflowId']['value'], 'demo-imported-catch')
            raw = (ROOT / 'n8n/workflows/catch.json').read_text()
            self.assertIn('CONFIG_BASE_ID', raw)
            self.assertNotIn('CONFIG_BASE_ID', (output / 'catch.json').read_text())
        finally:
            shutil.rmtree(output, ignore_errors=True)

    def test_refuses_export_outside_ignored_work_directory(self):
        with self.assertRaises(ValueError):
            module.prepare(self.config(), ROOT / 'n8n/unsafe-export')

    def test_refuses_existing_output_directory(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.work') as d:
            with self.assertRaises(FileExistsError):
                module.prepare(self.config(), Path(d))


if __name__ == '__main__':
    unittest.main()
