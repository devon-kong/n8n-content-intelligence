"""Compare the actual n8n Code-node fixture output with the Python port."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
n8n = json.loads(subprocess.check_output(['node', 'scripts/demo_n8n.mjs'], cwd=ROOT))
python = json.loads(subprocess.check_output([sys.executable, '-B', 'scripts/demo_python.py'], cwd=ROOT))
if n8n['counts'] != python['counts'] or n8n['decisions'] != python['decisions']:
    raise SystemExit('FAIL: catch fixture outcomes differ between implementations')
for filename, current in [('n8n-fixture-run.json', n8n), ('python-fixture-run.json', python)]:
    saved = json.loads((ROOT / 'assets/evidence' / filename).read_text())
    if saved != current:
        raise SystemExit(f'FAIL: regenerate stale evidence {filename}')
print('PASS: same three article IDs and create/update/skip decisions. Scope: synthetic catch fixture only.')
