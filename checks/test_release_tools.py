"""Release checks must catch known leaks without echoing their values."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('release_check', Path(__file__).resolve().parents[1] / 'scripts/check_public.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReleaseChecks(unittest.TestCase):
    def test_secret_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / '.env').write_text('EXAMPLE=not-a-real-secret')
            errors, _ = module.scan(root)
            self.assertTrue(any('runtime/secret' in e for e in errors))

    def test_known_identifier_scan_only_returns_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / '.work').mkdir()
            (root / '.work/source-identifiers.json').write_text('["synthetic-sensitive-marker"]')
            (root / 'example.md').write_text('synthetic-sensitive-marker')
            errors, _ = module.scan(root)
            self.assertEqual(errors, ['example.md: original environment identifier'])

    def test_broken_link_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'README.md').write_text('[Guide](missing.md)')
            errors, _ = module.scan(root)
            self.assertTrue(any('missing/outside' in e for e in errors))

    def test_reviewable_video_is_allowed_but_other_binary_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'walkthrough.mp4').write_bytes(b'\x00\x00\x00\x18ftypmp42\xff')
            errors, _ = module.scan(root)
            self.assertEqual(errors, [])
            (root / 'unknown.bin').write_bytes(b'\xff\xfe')
            errors, _ = module.scan(root)
            self.assertTrue(any('unexpected binary' in error for error in errors))

    def test_blank_environment_template_is_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / '.env.example').write_text('TOKEN=\n')
            errors, _ = module.scan(root)
            self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
