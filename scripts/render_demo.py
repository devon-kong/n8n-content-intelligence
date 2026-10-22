"""Render the recorded synthetic engine output and a 60-second evidence video.

These are result illustrations, not Feishu UI captures or a live screencast.
Requires rsvg-convert and ffmpeg; no network calls.
"""
import html
import json
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'assets/demo'
DEST.mkdir(parents=True, exist_ok=True)
evidence = json.loads((ROOT / 'assets/evidence/n8n-engine-demo.json').read_text())
WIDTH, HEIGHT = 1600, 1000


def text(x, y, value, size=24, color='#142840', weight=400):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" font-family="Arial, sans-serif">{html.escape(str(value))}</text>'


def lines(x, y, value, chars, size=24, color='#42576f', limit=9):
    return ''.join(text(x, y + i * (size + 10), line, size, color) for i, line in enumerate(textwrap.wrap(value, chars)[:limit]))


def box(x, y, w, h, fill='#ffffff'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{fill}" stroke="#dbe4ec"/>'


def frame(title, subtitle, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}"><title>{html.escape(title)}</title>'
            '<rect width="1600" height="1000" fill="#f2f6fa"/>'
            '<rect width="1600" height="12" fill="#147d79"/>'
            + text(60, 65, 'CONTENT INTELLIGENCE  /  n8n + Python', 20, '#147d79', 700)
            + text(60, 130, title, 44, weight=700)
            + text(60, 177, subtitle, 24, '#53667c') + body
            + text(60, 945, 'SYNTHETIC DEMO · Real n8n engine; local mock connectors; authored model responses.', 20, '#53667c')
            + text(60, 977, 'Rendered evidence walkthrough · not a Feishu UI capture, live screencast or AI-quality evaluation.', 18, '#53667c') + '</svg>')


body = text(84, 235, 'ARTICLE / CLASSIFICATION', 18, '#147d79', 700) + text(600, 235, 'REVIEWABLE SUMMARY', 18, '#147d79', 700) + text(1130, 235, 'FACTS / FOLLOW-UP', 18, '#147d79', 700)
for i, row in enumerate(evidence['rows']):
    fields = row['fields']; y = 260 + i * 207
    facts = json.loads(fields['关键事实'])
    body += box(60, y, 1480, 188)
    body += lines(84, y + 37, fields['标题'], 34, size=25, color='#142840')
    body += text(84, y + 126, fields['文章类型'], 20, '#147d79', 700)
    body += text(84, y + 160, 'Source: example.com / fictional article', 17, '#65778b')
    body += lines(600, y + 37, fields['摘要'], 42, size=23)
    fact_text = ' · '.join(k.replace('_', ' ').capitalize() + ': ' + (', '.join(v) if isinstance(v, list) else str(v)) for k, v in facts.items())
    body += lines(1130, y + 37, fact_text, 27, size=22)
frames = [('result-board', frame('A daily research brief, ready to review', 'Three fictional articles become searchable summaries, categories and source-linked facts.', body), 20)]

article = evidence['rows'][1]['fields']
body = box(60, 235, 710, 600) + box(810, 235, 730, 600)
body += text(90, 290, '01  SOURCE MATERIAL', 22, '#147d79', 700)
body += lines(90, 350, article['markdown'], 43, 28)
body += text(90, 685, 'A missing date stays missing.', 29, '#142840', 700)
body += lines(90, 735, 'A researcher can identify what needs follow-up before relying on the brief.', 45, 23)
body += text(840, 290, '02  STORED STRUCTURED OUTPUT', 22, '#147d79', 700)
body += lines(840, 350, article['摘要'], 43, 28)
body += text(840, 575, 'Category: ' + article['文章类型'], 25, '#147d79', 700)
body += text(840, 630, 'Effective date: Not stated', 28, '#142840', 700)
body += lines(840, 700, 'This example checks parsing and writeback of an authored response. It does not measure model accuracy.', 48, 23)
frames.append(('source-to-result', frame('Keep the source and the uncertainty', 'Original article → benchmark parser → structured fields in the simulated destination.', body), 15))

body = ''
for i, run in enumerate(evidence['runs']):
    y = 235 + i * 153
    body += box(60, y, 1480, 130)
    label = {'first_run': 'FIRST EXECUTION', 'stable_rerun': 'STABLE RERUN', 'duplicate_config': 'DUPLICATE CONFIG', 'missing_output': 'MISSING OUTPUT'}[run['scenario']]
    body += text(90, y + 44, label, 23, '#147d79', 700)
    if run['scenario'] == 'first_run':
        detail = f"{run['created']} new records · {run['summary_fixture_calls']} scripted model calls · {run['summary_writes']} enriched rows"
    elif run['scenario'] == 'stable_rerun':
        detail = f"{run['created']} new records · {run['updated']} base updates · {run['summary_fixture_calls']} additional model calls"
    elif run['scenario'] == 'duplicate_config':
        detail = 'Stopped at configuration validation; no article processing'
    else:
        detail = 'Catch rejected an expected article missing from the destination'
    body += text(90, y + 91, detail, 29, '#142840')
frames.append(('execution-evidence', frame('Repeatable behavior. Visible failures.', 'Observed in n8n 2.19.5 with a secure JavaScript runner and local HTTP fixtures.', body), 15))

body = box(60, 245, 720, 570) + box(820, 245, 720, 570)
body += text(92, 305, 'MY CONTRIBUTION', 24, '#147d79', 700)
for i, line in enumerate(['Business requirements and field contracts', 'Shared Catch / optional enrichment design', 'Incremental write and review policies', 'Implementation with AI assistance', 'Tests, deployment notes and handover']):
    body += text(92, 380+i*73, line, 26)
body += text(852, 305, 'WHAT THIS EVIDENCE PROVES', 24, '#147d79', 700)
body += lines(852, 380, 'A representative workflow runs in the real n8n engine with synthetic service boundaries.', 43, 28)
body += lines(852, 535, 'Live provider compatibility, actual model quality and production concurrency still require dedicated acceptance.', 43, 26)
body += text(852, 742, 'Review source, tests and scope on GitHub.', 24, '#147d79', 700)
frames.append(('delivery-scope', frame('From business need to inspectable automation', 'Reusable n8n delivery, with Python available for code-based integration needs.', body), 10))

for name, source, duration in frames:
    (DEST / (name + '.svg')).write_text(source)
    subprocess.run(['rsvg-convert', '-o', str(DEST / (name + '.png')), str(DEST / (name + '.svg'))], check=True)
concat = ROOT / '.work/demo-frames.txt'
concat.parent.mkdir(exist_ok=True)
concat.write_text(''.join(f"file '{(DEST / (name + '.png')).as_posix()}'\nduration {duration}\n" for name, _, duration in frames) + f"file '{DEST / (frames[-1][0] + '.png')}'\n")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(concat),
                '-vf', 'fps=25,format=yuv420p', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                '-t', '60', '-movflags', '+faststart', str(DEST / 'walkthrough.mp4')], check=True)
print('Rendered four evidence illustrations and a silent 60-second walkthrough. Not a live screencast.')
