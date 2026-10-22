import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { readJson } from './n8n-harness.mjs';

function code(flow, name, items, extra = {}) {
  const body = flow.nodes.find(n => n.name === name).parameters.jsCode;
  return vm.runInNewContext(`(function(){${body}\n})()`, { items, $getWorkflowStaticData: () => ({}), $execution: { id: 'demo' }, ...extra }, { timeout: 2000 });
}

for (const file of ['entry-industry-news.json', 'entry-ai-news.json', 'entry-benchmark.json']) {
  const flow = readJson(`n8n/workflows/${file}`);
  const row = { fields: { target_base: 'demo-base', target_table: 'demo-table' } };
  test(`${file}: only a complete unique config may reach Catch`, () => {
    const run = (rows, more) => code(flow, 'Build Config Snapshot', [{ json: { code: 0, data: { items: rows, has_more: more } } }]);
    assert.throws(() => run([], false), /0 条/);
    assert.equal(run([row], false)[0].json.target_table, 'demo-table');
    assert.throws(() => run([row, row], false), /唯一|多条/);
    assert.throws(() => run([row], true), /唯一|分页|多条/);
  });
}

// SQLite is real. Only the better-sqlite3 module/path boundary is adapted for
// Node's built-in SQLite; this does not prove n8n task-runner compatibility.
function sqliteAdapter(filename) {
  return class Database {
    constructor() { this.db = new DatabaseSync(filename); }
    exec(sql) { this.db.exec(sql); return this; }
    prepare(sql) { return this.db.prepare(sql); }
    transaction(fn) {
      return (...args) => {
        this.db.exec('BEGIN IMMEDIATE');
        try { const result = fn(...args); this.db.exec('COMMIT'); return result; }
        catch (e) { this.db.exec('ROLLBACK'); throw e; }
      };
    }
    close() { this.db.close(); }
  };
}

for (const file of ['summary-news.json', 'summary-benchmark.json', 'metrics.json']) {
  for (const uncertainFrom of ['expired', 'response']) {
    test(`${file}: ${uncertainFrom} uncertainty blocks subsequent executions`, () => {
      const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ci-lock-'));
      try {
        const filename = path.join(dir, 'calls.sqlite');
        const flow = readJson(`n8n/workflows/${file}`);
        const extra = { require: name => { assert.equal(name, 'better-sqlite3'); return sqliteAdapter(filename); } };
        const item = { task_key: 'demo:v1:a1', article_id: 'a1', record_id: 'demo-record', run_id: 'r1', lock_until: Date.now() - 1, started_at: Date.now(), prompt_version: 'v1', model: 'demo', url: 'https://example.test/a1' };
        code(flow, 'Init SQLite', [{ json: item }], extra);
        const lock = run => code(flow, 'Atomic Lock', [{ json: { ...item, run_id: run } }], extra)[0].json.lock_result;
        assert.equal(lock('r1'), 'CLAIMED');
        if (uncertainFrom === 'expired') assert.equal(lock('r2'), 'LOCK_EXPIRED_REVIEW');
        else {
          const context = { ...extra, $: () => ({ first: () => ({ json: item }) }) };
          const response = file === 'metrics.json' ? { code: 503, msg: 'Synthetic timeout' } : { error: { status: 503, message: 'Synthetic timeout' } };
          const normalized = code(flow, file === 'metrics.json' ? 'Normalize Jizhile Result' : 'Normalize DeepSeek Result', [{ json: response }], context);
          code(flow, 'Write SQLite Non-Success', normalized, context);
        }
        assert.equal(lock('r3'), 'UNCERTAIN_REVIEW');
        assert.equal(lock('r4'), 'UNCERTAIN_REVIEW');
        const db = new DatabaseSync(filename);
        assert.equal(db.prepare(`SELECT count(*) AS n FROM ${file === 'metrics.json' ? 'metrics' : 'summary'}_call_log`).get().n, 1);
        db.close();
        execFileSync('python3', ['scripts/review_paid_calls.py', '--database', filename,
          '--stage', file === 'metrics.json' ? 'metrics' : 'summary', '--authorize-retry', '1',
          '--reason', 'Synthetic remote request settled; cost accepted', '--reviewer', 'demo-operator',
          '--confirm-remote-settled', '--accept-possible-charge']);
        assert.equal(lock('r5'), 'CLAIMED');
      } finally { fs.rmSync(dir, { recursive: true, force: true }); }
    });
  }
}
