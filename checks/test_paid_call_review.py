"""Recovery must release exactly one reviewed uncertain row and retain an audit."""
from contextlib import closing
import importlib.util
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class PaidCallReviewTests(unittest.TestCase):
    def test_review_is_explicit_audited_and_cannot_release_active_work(self):
        spec = importlib.util.spec_from_file_location('review_paid_calls', ROOT / 'scripts/review_paid_calls.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'calls.sqlite'
            with closing(sqlite3.connect(path)) as db, db:
                for stage in ('summary', 'metrics'):
                    db.execute(f'CREATE TABLE {stage}_call_log (id INTEGER PRIMARY KEY, status TEXT, error_code TEXT)')
                    db.executemany(f'INSERT INTO {stage}_call_log VALUES (?, ?, ?)', [(1, 'uncertain', 'TIMEOUT'), (2, 'processing', None), (3, 'uncertain', 'TIMEOUT')])
            for flags in ([], ['--confirm-remote-settled'], ['--accept-possible-charge']):
                result = subprocess.run([sys.executable, str(ROOT / 'scripts/review_paid_calls.py'),
                    '--database', str(path), '--stage', 'summary', '--authorize-retry', '1',
                    '--reason', 'Checked', '--reviewer', 'operator', *flags], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                with closing(sqlite3.connect(path)) as db:
                    self.assertEqual(db.execute('SELECT status FROM summary_call_log WHERE id=1').fetchone()[0], 'uncertain')
            for stage in ('summary', 'metrics'):
                with self.assertRaises(ValueError):
                    module.approve_retry(path, stage, 1, '', 'operator')
                with self.assertRaises(ValueError):
                    module.approve_retry(path, stage, 2, 'Remote request settled', 'operator')
                module.approve_retry(path, stage, 1, 'Remote request settled; retry cost accepted', 'operator')
                with self.assertRaises(ValueError):
                    module.approve_retry(path, stage, 1, 'Duplicate approval', 'operator')
                with closing(sqlite3.connect(path)) as db, db:
                    self.assertEqual(db.execute(f'SELECT id,status FROM {stage}_call_log ORDER BY id').fetchall(), [(1, 'skipped'), (2, 'processing'), (3, 'uncertain')])
                    row = db.execute('SELECT call_id,action,reason,reviewer FROM paid_call_review WHERE stage=?', (stage,)).fetchone()
                    self.assertEqual(row, (1, 'authorize_retry', 'Remote request settled; retry cost accepted', 'operator'))
            with self.assertRaises(FileNotFoundError):
                module.approve_retry(Path(temp) / 'missing.sqlite', 'summary', 1, 'Checked', 'operator')
