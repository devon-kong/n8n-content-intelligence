import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { readJson, root, executeNode, runCatchScenario, scenario } from './n8n-harness.mjs';

test('all seven exports are disabled, self-contained and syntactically valid', () => {
  const manifest = readJson('n8n/manifest.json');
  assert.equal(manifest.workflows.length, 7);
  const ids = new Set(manifest.workflows.map(f => f.id));
  assert.equal(ids.size, 7);
  for (const entry of manifest.workflows) {
    const j = readJson(`n8n/workflows/${entry.file}`);
    assert.equal(j.id, entry.id);
    assert.equal(j.active, false);
    assert.equal(j.staticData, null);
    assert.deepEqual(j.pinData, {});
    const names = new Set(j.nodes.map(n => n.name));
    assert.equal(names.size, j.nodes.length);
    assert.equal(j.nodes.length, entry.nodes);
    for (const [from, ports] of Object.entries(j.connections)) {
      assert.ok(names.has(from), from);
      for (const branches of Object.values(ports)) for (const edges of branches) for (const edge of edges) assert.ok(names.has(edge.node), edge.node);
    }
    for (const n of j.nodes) {
      if (n.parameters.jsCode) new vm.Script(`(function(){${n.parameters.jsCode}\n})`);
      if (n.type === 'n8n-nodes-base.executeWorkflow') assert.ok(ids.has(n.parameters.workflowId.value));
      for (const c of Object.values(n.credentials ?? {})) assert.match(c.id, /^[A-Z_]+_CREDENTIAL_ID$/);
    }
  }
});

test('actual catch nodes yield create/update/skip and exclude old articles', () => {
  const { prepared, decisions, verification } = runCatchScenario();
  assert.equal(prepared.length, 3);
  assert.deepEqual(decisions.map(i => i.json.action), scenario.expected_actions);
  assert.equal(verification.visibility_check, 'passed');
  assert.equal(verification.expected, 3);
  const allowed = ['标题', 'markdown', '发布时间', '地址', '账号', 'article_id'].sort();
  for (const i of prepared) assert.deepEqual(Object.keys(i.json.feishu_create_fields).sort(), allowed);
});

test('a stable rerun skips every record, including markdown-only changes', () => {
  const { prepared, outputs } = runCatchScenario();
  const records = prepared.map((i, idx) => ({ record_id: `demo-${idx}`, fields: { ...i.json.feishu_create_fields, markdown: 'Formatting changed' } }));
  const decisions = executeNode('Aggregate Existing Map And Decide', [{ json: { data: { items: records } } }], outputs);
  assert.deepEqual(decisions.map(i => i.json.action), ['skip', 'skip', 'skip']);
});

test('visibility verification rejects missing articles', () => {
  const { prepared, outputs } = runCatchScenario();
  assert.throws(() => executeNode('Verify Count', [{ json: { data: { items: prepared.slice(1).map(i => ({ fields: i.json.feishu_create_fields })) } } }], outputs), /未在飞书找到/);
});

test('barrier buckets isolate interleaved IDs within one harness state', () => {
  const { decisions, outputs } = runCatchScenario();
  const state = {};
  assert.deepEqual(executeNode('Upsert Done Barrier', decisions.slice(0, 1), outputs, state, 'A'), []);
  assert.deepEqual(executeNode('Upsert Done Barrier', decisions.slice(1), outputs, state, 'B'), []);
  assert.equal(executeNode('Upsert Done Barrier', decisions.slice(1), outputs, state, 'A')[0].json.processed, 3);
  assert.equal(executeNode('Upsert Done Barrier', decisions.slice(0, 1), outputs, state, 'B')[0].json.processed, 3);
  assert.deepEqual(executeNode('Upsert Done Barrier', decisions, outputs, state, 'A'), []);
});
