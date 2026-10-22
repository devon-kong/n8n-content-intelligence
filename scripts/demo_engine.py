"""Execute explicit boundary-substituted copies in a private n8n CLI instance.

Imports the seven unmodified exports first. All connector nodes in the execution
copies use loopback HTTP fixtures; all Code bodies/routing remain unchanged
except the feed hostname, SQLite path and explicit native binding. No credentials or production calls.
Raw runner output stays under .work; only bounded summaries are published.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / 'n8n/workflows'


def prepare_variants(work: Path, base_url: str, runtime: Path | None = None):
    parsed = urlparse(base_url)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.username or parsed.password:
        raise ValueError('Demo endpoints must be loopback HTTP')
    runtime = runtime or ROOT / '.work/n8n-runtime'
    binding = runtime / 'node_modules/better-sqlite3/build/Release/better_sqlite3.node'
    dest = work / 'variants'
    dest.mkdir(parents=True, exist_ok=True)
    originals = [json.loads(p.read_text()) for p in sorted(WORKFLOWS.glob('*.json'))]
    ids = {flow['id']: 'demo' + flow['id'] for flow in originals}
    paths, changes = [], []
    for path, original in zip(sorted(WORKFLOWS.glob('*.json')), originals):
        flow = copy.deepcopy(original)
        flow['id'] = ids[flow['id']]
        flow['name'] = 'SYNTHETIC DEMO · ' + flow['name']
        for node in flow['nodes']:
            node.pop('credentials', None)
            if node['type'] in ('n8n-nodes-feishu-lite.feishuNode', 'n8n-nodes-deepseek.deepSeek', 'n8n-nodes-base.httpRequest'):
                before = node['type']
                params = node['parameters']
                body = params.get('body', '={{ JSON.stringify($json) }}')
                # The mock server receives the actual exported Feishu write/search
                # payload; reference IDs travel separately for update fixtures.
                if 'feishu' in before:
                    body = '={{ JSON.stringify({ payload: (' + body.removeprefix('={{').removesuffix('}}').strip() + '), record_id: (' + params.get('record_id', "={{ '' }}").removeprefix('={{').removesuffix('}}').strip() + ') }) }}'
                node['type'] = 'n8n-nodes-base.httpRequest'
                node['typeVersion'] = 4.2
                node['parameters'] = {'method': 'POST', 'url': base_url + '/node/' + quote(node['name'], safe=''),
                                      'sendBody': True, 'specifyBody': 'json', 'jsonBody': body,
                                      'options': {'timeout': 10000}}
                changes.append({'workflow': path.name, 'node': node['name'], 'substitution': before + ' -> local HTTP fixture'})
            if node['type'] == 'n8n-nodes-base.code':
                old = node['parameters']['jsCode']
                new = old.replace('http://wechat2rss:8080', base_url).replace('/home/node/.n8n/wechat_monitor_paid_calls.sqlite', str(work / 'calls.sqlite'))
                new = new.replace("new Database('" + str(work / 'calls.sqlite') + "')", "new Database(" + json.dumps(str(work / 'calls.sqlite')) + ", { nativeBinding: " + json.dumps(str(binding)) + " })")
                node['parameters']['jsCode'] = new
                if new != old:
                    changes.append({'workflow': path.name, 'node': node['name'], 'substitution': 'local feed hostname / private SQLite path / explicit native binding for secure runner'})
            if node['type'] == 'n8n-nodes-base.executeWorkflow':
                node['parameters']['workflowId']['value'] = ids[node['parameters']['workflowId']['value']]
            if node['type'] == 'n8n-nodes-base.scheduleTrigger':
                node['type'] = 'n8n-nodes-base.manualTrigger'
                node['typeVersion'] = 1
                node['parameters'] = {}
                changes.append({'workflow': path.name, 'node': node['name'], 'substitution': 'inactive schedule -> manual CLI entry'})
        target = dest / path.name
        target.write_text(json.dumps(flow, ensure_ascii=False, indent=2) + '\n')
        paths.append(target)
    return paths, changes


class DemoState:
    def __init__(self):
        self.fixture = json.loads((ROOT / 'examples/business-demo.json').read_text())
        self.rows = []
        self.phase = 'first_run'
        self.events = []
        self.published = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    def respond(self, name, body):
        self.events.append({'phase': self.phase, 'node': name})
        payload = body.get('payload', body)
        if isinstance(payload, str):
            payload = json.loads(payload)
        if name == 'Read Pipeline Config':
            return {'code': 0, 'data': {'has_more': self.phase == 'duplicate_config', 'items': [{'fields': {
                'target_base': 'demo-base', 'target_table': 'demo-articles', 'window_days': '7',
                'summary_enabled': True, 'metric_enabled': False, 'process_mode': 'benchmark',
                'summary_prompt': 'Extract only stated facts as the documented benchmark JSON object.',
                'summary_version': 'synthetic-v1', 'model': 'scripted-fixture'}}]}}
        if name == 'Get Enabled Accounts From Feishu':
            return {'code': 0, 'data': {'has_more': False, 'items': [{'fields': {'biz_id': 'demo-account', '账号名称': 'Synthetic Research Desk'}}]}}
        if name == 'Get Account JSON Feed':
            return {'title': 'Authored synthetic feed', 'items': [{'title': a['title'], 'url': a['url'], 'date_published': self.published, 'content_html': '<p>' + a['body'] + '</p>'} for a in self.fixture['articles']]}
        if name in ('Feishu Search Existing Records', 'Feishu Visibility Search', 'Read Feishu Pending'):
            rows = self.rows
            if name == 'Read Feishu Pending':
                rows = [r for r in rows if not r['fields'].get('摘要') and r['fields'].get('markdown')]
            if name == 'Feishu Visibility Search' and self.phase == 'missing_output':
                rows = rows[1:]
            return {'code': 0, 'data': {'items': rows, 'has_more': False}}
        if name == 'Create New Feishu Record':
            row = {'record_id': f'demo-record-{len(self.rows)+1}', 'fields': payload['fields']}
            self.rows.append(row)
            return {'code': 0, 'data': {'record': row}}
        if name in ('Update Stage1 Fields', 'Write Feishu Summary'):
            row = next(r for r in self.rows if r['record_id'] == body['record_id'])
            row['fields'].update(payload['fields'])
            return {'code': 0, 'data': {'record': row}}
        if name == 'Call DeepSeek':
            article = next(a for a in self.fixture['articles'] if a['body'] in body['markdown'])
            return {'choices': [{'message': {'content': json.dumps(article['model_response'])}, 'finish_reason': 'stop'}]}
        raise ValueError('Unexpected mock endpoint: ' + name)


def serve(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
                result = state.respond(unquote(self.path.removeprefix('/node/')), body)
                encoded = json.dumps(result, ensure_ascii=False).encode()
                self.send_response(200)
            except Exception as exc:
                encoded = json.dumps({'error': type(exc).__name__}).encode()
                self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(encoded)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def execution_summary(output):
    for offset, character in enumerate(output):
        if character != '{' or (offset and output[offset - 1] != '\n'):
            continue
        try:
            result, _ = json.JSONDecoder().raw_decode(output[offset:])
        except ValueError:
            continue
        data = result.get('data', {}).get('resultData')
        if data is not None:
            return {'status': result.get('status'), 'last_node': data.get('lastNodeExecuted'),
                    'error_message': (data.get('error') or {}).get('message')}
    raise ValueError('No complete n8n execution result; not evidence of a controlled failure')


def validate_successful_run(run):
    if (run['exit_code'] != 0 or run['status'] != 'success'
            or run['error_message'] is not None or run['last_node'] != 'Check Metric Enabled'):
        raise ValueError('Engine did not successfully finish the representative path')
    expected = (3, 0, 3, 3) if run['scenario'] == 'first_run' else (0, 0, 0, 0)
    counts = tuple(run[key] for key in ['created', 'updated', 'summary_fixture_calls', 'summary_writes'])
    if counts != expected:
        raise ValueError('Unexpected writes or model-fixture calls')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=ROOT / '.work/n8n-runtime')
    parser.add_argument('--node-bin', type=Path, default=ROOT / '.work/node-runtime/node_modules/.bin')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    work = ROOT / '.work' / ('engine-demo-' + stamp)
    work.mkdir(parents=True, exist_ok=False)
    state = DemoState()
    server = serve(state)
    base = f'http://127.0.0.1:{server.server_port}'
    runtime = args.runtime.resolve()
    inherited = {key: value for key, value in os.environ.items() if key in {'PATH', 'HOME', 'TMPDIR', 'LANG', 'LC_ALL'}}
    env = {**inherited, 'PATH': str(args.node_bin.resolve()) + os.pathsep + os.environ['PATH'],
           'N8N_USER_FOLDER': str(work), 'N8N_DIAGNOSTICS_ENABLED': 'false', 'N8N_VERSION_NOTIFICATIONS_ENABLED': 'false',
           'N8N_TEMPLATES_ENABLED': 'false', 'N8N_RUNNERS_ENABLED': 'true', 'N8N_RUNNERS_MODE': 'internal',
           'NODE_FUNCTION_ALLOW_EXTERNAL': 'better-sqlite3', 'N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS': 'true',
           'N8N_COMMUNITY_PACKAGES_ENABLED': 'false'}
    version = json.loads((runtime / 'node_modules/n8n/package.json').read_text())['version']
    if version != '2.19.5':
        raise ValueError('This demonstration requires n8n 2.19.5')
    cli = str(runtime / 'node_modules/n8n/bin/n8n')
    def run(label, *arguments):
        result = subprocess.run(['node', cli, *arguments], env=env, cwd=runtime, capture_output=True, text=True, timeout=120)
        (work / (label + '.log')).write_text(result.stdout + result.stderr)
        print(label + ': exit ' + str(result.returncode), flush=True)
        return result
    try:
        imported = run('import-originals', 'import:workflow', '--separate', '--input=' + str(WORKFLOWS))
        if imported.returncode:
            raise RuntimeError('Original import failed; inspect private import log')
        _, changes = prepare_variants(work, base, runtime)
        imported_demo = run('import-variants', 'import:workflow', '--separate', '--input=' + str(work / 'variants'))
        if imported_demo.returncode:
            raise RuntimeError('Variant import failed; inspect private import log')
        # CLI sub-workflow execution uses published child versions in n8n 2.19.5.
        # Only private mock-boundary children are published; all Entries stay inactive.
        for child in ['demociCatchMain00001', 'demociSummaryBench01']:
            if run('publish-' + child, 'publish:workflow', '--id=' + child).returncode:
                raise RuntimeError('Private demo child publication failed')
        runs = []
        for phase in ['first_run', 'stable_rerun', 'duplicate_config', 'missing_output']:
            state.phase = phase
            result = run(phase, 'execute', '--id=demociEntryBench001', '--rawOutput')
            events = [e['node'] for e in state.events if e['phase'] == phase]
            counts = {key: events.count(node) for key, node in {'created': 'Create New Feishu Record', 'updated': 'Update Stage1 Fields', 'summary_fixture_calls': 'Call DeepSeek', 'summary_writes': 'Write Feishu Summary'}.items()}
            runs.append({'scenario': phase, 'exit_code': result.returncode, **execution_summary(result.stdout), **counts})
            if phase == 'first_run':
                if result.returncode or len(state.rows) != 3 or counts['summary_writes'] != 3:
                    raise RuntimeError('First engine execution did not produce three enriched rows; inspect private log')
            if phase in ('first_run', 'stable_rerun'):
                validate_successful_run(runs[-1])
        if runs[1]['exit_code'] or runs[1]['created'] or runs[1]['updated'] or runs[1]['summary_fixture_calls']:
            raise RuntimeError('Stable rerun failed')
        if (not runs[2]['exit_code'] or runs[2]['last_node'] != 'Build Config Snapshot'
                or '唯一' not in (runs[2]['error_message'] or '')
                or not runs[3]['exit_code'] or '未在飞书找到' not in (runs[3]['error_message'] or '')):
            raise RuntimeError('Controlled failure was not rejected')
        for article, row in zip(state.fixture['articles'], state.rows):
            if row['fields'].get('摘要') != article['model_response']['summary_v2']:
                raise RuntimeError('Summary output does not match authored fixture')
            if json.loads(row['fields'].get('关键事实', '{}')) != article['model_response']['key_facts']:
                raise RuntimeError('Structured output does not match authored fixture')
        evidence = {'recorded_at_utc': datetime.now(timezone.utc).isoformat(), 'mode': 'n8n_engine_with_mock_connectors',
                    'n8n_version': version, 'node_version': subprocess.check_output(['node', '--version'], env=env, text=True).strip(),
                    'better_sqlite3_version': json.loads((runtime / 'node_modules/better-sqlite3/package.json').read_text())['version'],
                    'runner': 'internal JavaScript runner, secure mode; explicit native SQLite binding in demo copies',
                    'community_nodes': 'disabled; original exports imported but community-node execution not tested',
                    'private_child_versions': 'Catch and Benchmark Summary published in isolated demo instance only', 'original_import': 'seven inactive exports accepted by CLI import',
                    'scope': 'Real n8n CLI and Code nodes; connector nodes replaced by local HTTP fixtures. Authored model responses, no actual LLM/Feishu/feed calls. No original community-node execution or live integration claim.',
                    'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(WORKFLOWS.glob('*.json'))},
                    'substitutions': changes, 'runs': runs, 'rows': state.rows}
        (ROOT / 'assets/evidence/n8n-engine-demo.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
        print('PASS: bounded engine demonstration recorded; live integration remains untested.', flush=True)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
