"""Run offline checks and record bounded results without publishing raw logs."""
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'assets/evidence/validation.json'
REPORT.write_text(json.dumps({'status': 'recording'}) + '\n')
steps = [
    ('public_files', [sys.executable, '-B', 'scripts/check_public.py'], ROOT),
    ('release_tools', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'checks', '-p', 'test_*.py'], ROOT),
    ('exported_code_nodes', ['node', '--test', *[str(p.relative_to(ROOT)) for p in sorted((ROOT / 'checks').glob('*.test.mjs'))]], ROOT),
    ('python_suite', [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider'], ROOT / 'python'),
    ('catch_fixture_comparison', [sys.executable, '-B', 'scripts/compare_demos.py'], ROOT),
]
results = []
for name, command, cwd in steps:
    run = subprocess.run(command, cwd=cwd, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, text=True, capture_output=True)
    print(f'{name}: {"PASS" if run.returncode == 0 else "FAIL"}')
    results.append({'check': name, 'command': ['python' if x == sys.executable else x for x in command], 'cwd': '.' if cwd == ROOT else 'python', 'exit_code': run.returncode})
    if run.returncode:
        # Detailed diagnostics stay local; the public report records no raw traces.
        (ROOT / '.work').mkdir(exist_ok=True)
        (ROOT / '.work/validation-failure.log').write_text(run.stdout + run.stderr)
        REPORT.write_text(json.dumps({'status': 'failed', 'checks': results}, indent=2) + '\n')
        raise SystemExit('Check failed. Inspect .work/validation-failure.log locally.')

sys.path.insert(0, str(ROOT / 'scripts'))
from check_public import public_files
hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(public_files(ROOT)) if p != REPORT}
report = {
    'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'status': 'offline_checks_passed',
    'environment': {'python': platform.python_version(), 'node': subprocess.check_output(['node', '--version'], text=True).strip(), 'platform': platform.system()},
    'scope': 'Static exports, exported Code-node fixtures and real SQLite regression tests, Python mocked/unit tests, recovery/demo tool tests and public-file checks. Not an n8n engine/import or live integration result.',
    'checks': results,
    'artifact_sha256': hashes,
    'pending': ['Original community-node execution', 'Live service integration and actual AI output quality', 'Other Entry/News Summary/Metrics engine coverage', 'Real n8n concurrent persistence', 'Python structured benchmark parity', 'Live Feishu visuals'],
    'separate_engine_evidence': 'assets/evidence/n8n-engine-demo.json',
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print('Recorded successful offline checks and artifact hashes; live gates remain pending.')
