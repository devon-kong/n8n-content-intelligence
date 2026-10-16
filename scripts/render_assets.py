"""Generate architecture/fixture illustrations. These are not UI screenshots."""
import html
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'assets/diagrams'


def text(x, y, value, size=20, color='#e8eef9', weight=400):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" font-family="Arial, sans-serif">{html.escape(str(value))}</text>'


def box(x, y, w, h, fill='#17243b', stroke='#30425e'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" stroke="{stroke}"/>'


def svg(body, height):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img"><title>Content Intelligence Automation — architecture or synthetic fixture illustration</title><rect width="1200" height="{height}" rx="24" fill="#0c1628"/>{body}</svg>'


cover = text(50, 60, 'CONTENT INTELLIGENCE AUTOMATION', 16, '#75d7cf', 700)
cover += text(50, 116, 'One shared core. Three business pipelines.', 37, weight=700)
cover += text(50, 154, 'n8n workflow architecture + companion Python CLI', 22, '#b3c4dc')
for x, title in [(50, 'Industry news'), (295, 'AI news'), (540, 'Benchmark')]:
    cover += box(x, 195, 220, 55) + text(x + 21, 230, title, 20)
cover += '<path d="M160 250 V275 H405 M405 250 V295 M650 250 V275 H405" fill="none" stroke="#6781a4" stroke-width="3"/>'
cover += box(50, 295, 710, 115, '#392834', '#ec866f')
cover += text(78, 333, 'n8n · SHARED CATCH', 16, '#f2ad98', 700)
cover += text(78, 371, 'Normalize → Deduplicate → Create / Update / Skip', 24, weight=700)
cover += text(78, 395, 'Six base fields · output visibility verification', 16, '#d1c6cf')
cover += box(820, 195, 330, 215, '#122f39', '#4caa9d')
cover += text(846, 235, 'PYTHON COMPANION', 17, '#75d7cf', 700)
cover += text(846, 276, 'CLI → Flow → Stages', 23, weight=700)
cover += text(846, 313, 'Reusable clients and operations', 18, '#b3c4dc')
cover += text(846, 346, 'Shared catch fixture checks', 18, '#b3c4dc')
cover += text(846, 378, 'Known differences documented', 17, '#b3c4dc')
cover += text(50, 455, 'Optional AI Summary + Metrics  →  Feishu Bitable', 24, '#b3c4dc')
cover += text(50, 502, 'Architecture illustration · no credentials or real business data · not an n8n UI capture', 15, '#8a9db9')
(DEST / 'cover.svg').write_text(svg(cover, 530))

a = json.loads((ROOT / 'assets/evidence/n8n-fixture-run.json').read_text())
b = json.loads((ROOT / 'assets/evidence/python-fixture-run.json').read_text())
body = text(50, 59, 'SYNTHETIC CATCH DEMONSTRATION', 16, '#75d7cf', 700)
body += text(50, 108, 'Same input. Matching article IDs and decisions.', 32, weight=700)
body += text(50, 146, 'External storage is simulated. No live n8n engine, LLM or provider call.', 20, '#b3c4dc')
for y, title, data in [(188, 'Exported n8n Code nodes · Node.js harness', a), (333, 'Python normalization + upsert functions', b)]:
    body += box(50, y, 1100, 120)
    body += text(76, y + 35, title, 20, weight=700)
    for x, key, color in [(76, 'create', '#75d7cf'), (420, 'update', '#ffd296'), (770, 'skip', '#abbbff')]:
        body += text(x, y + 88, f"{data['counts'][key]}  {key.upper()}", 32, color, 700)
body += text(50, 496, 'Actual fixture output is committed as JSON; this graphic is a rendered results illustration.', 17, '#8a9db9')
(DEST / 'fixture-results.svg').write_text(svg(body, 530))
for name in ['cover', 'fixture-results']:
    subprocess.run(['rsvg-convert', '-o', str(DEST / f'{name}.png'), str(DEST / f'{name}.svg')], check=True)
print('Rendered two SVG/PNG illustrations from architecture and recorded synthetic results.')
