// Executes the checked-in Code-node bodies. This is NOT an n8n engine.
import fs from 'node:fs';
import vm from 'node:vm';

export const root = new URL('../', import.meta.url);
export const readJson = path => JSON.parse(fs.readFileSync(new URL(path, root), 'utf8'));
export const catchFlow = readJson('n8n/workflows/catch.json');
export const scenario = readJson('examples/catch-scenario.json');
const epoch = Date.parse(scenario.as_of);
class FixtureDate extends Date {
  constructor(...args) { super(...(args.length ? args : [epoch])); }
  static now() { return epoch; }
}

export function executeNode(name, items, outputs = {}, staticData = {}, executionId = 'synthetic-run') {
  const node = catchFlow.nodes.find(n => n.name === name);
  if (!node || node.type !== 'n8n-nodes-base.code') throw new Error(`Missing Code node: ${name}`);
  const sandbox = {
    items, $json: items[0]?.json ?? {}, Date: FixtureDate,
    $execution: { id: executionId }, $getWorkflowStaticData: () => staticData,
    $: key => ({
      all: () => outputs[key] ?? [],
      first: () => outputs[key]?.[0] ?? { json: {} },
    }),
  };
  const result = vm.runInNewContext(`(function(){${node.parameters.jsCode}\n})()`, sandbox, { timeout: 1000 });
  return JSON.parse(JSON.stringify(result));
}

export function runCatchScenario() {
  const outputs = {
    'Execute Sub-workflow Trigger': [{ json: { window_days: scenario.window_days } }],
    'Normalize Accounts': [{ json: scenario.account }],
  };
  const normalized = executeNode('Normalize And Filter Articles', [{ json: scenario.feed }], outputs);
  const deduped = executeNode('Deduplicate Articles by article_id', normalized, outputs);
  const prepared = executeNode('Prepare Feishu Base Payload', deduped, outputs);
  outputs['Prepare Feishu Base Payload'] = prepared;
  // Two synthetic existing records: one changed title; one markdown-only difference.
  const existing = prepared.slice(1).map((item, i) => ({
    record_id: `demo-record-${i + 1}`,
    fields: { ...item.json.feishu_update_fields },
  }));
  existing[0].fields['标题'] = 'Previous export outlook';
  existing[1].fields.markdown = 'Different stored markdown formatting';
  const decisions = executeNode('Aggregate Existing Map And Decide', [{ json: { data: { items: existing } } }], outputs);
  outputs['Aggregate Existing Map And Decide'] = decisions;
  const barrier = executeNode('Upsert Done Barrier', decisions, outputs);
  const visibilityInputs = executeNode('Prepare Visibility Check', barrier, outputs);
  outputs['Prepare Visibility Check'] = visibilityInputs;
  // Simulated storage boundary: no HTTP calls or credentials.
  const rows = prepared.map(item => ({ fields: item.json.feishu_create_fields }));
  const verification = executeNode('Verify Count', [{ json: { data: { items: rows } } }], outputs)[0].json;
  return { outputs, prepared, decisions, verification };
}

export function demoResult() {
  const { decisions, verification } = runCatchScenario();
  return {
    mode: 'synthetic_fixture',
    runtime: 'exported n8n Code nodes in a Node.js harness; external storage simulated',
    as_of: scenario.as_of,
    counts: Object.fromEntries(['create', 'update', 'skip'].map(a => [a, decisions.filter(i => i.json.action === a).length])),
    decisions: decisions.map(i => ({ article_id: i.json.article_id, title: i.json.title, action: i.json.action })),
    visibility_check: verification.visibility_check,
  };
}
