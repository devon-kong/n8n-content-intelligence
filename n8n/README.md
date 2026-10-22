# Run the n8n implementation

[Portfolio](../README.md) · [Architecture](../docs/architecture.md) · [Validation](../docs/validation.md)

## Current workflow set

| File | Role | Nodes |
|---|---|---:|
| [catch.json](workflows/catch.json) | Shared collection and synchronization | 25 |
| [summary-news.json](workflows/summary-news.json) | News summaries | 23 |
| [summary-benchmark.json](workflows/summary-benchmark.json) | Structured benchmark summaries | 23 |
| [metrics.json](workflows/metrics.json) | Article engagement metrics | 24 |
| [entry-industry-news.json](workflows/entry-industry-news.json) | Industry-news entry | 8 |
| [entry-ai-news.json](workflows/entry-ai-news.json) | AI-news entry | 8 |
| [entry-benchmark.json](workflows/entry-benchmark.json) | Benchmark entry | 11 |

[manifest.json](manifest.json) contains the portable IDs, node counts and SHA-256 identities of the selected source artifacts. A hash identifies a source; it does not prove successful execution.

## Dependencies

The source deployment was documented against **self-hosted n8n 2.19.5**. The seven inactive exports have now been accepted by CLI import in an isolated 2.19.5 instance with community nodes disabled. A representative path also ran with explicitly substituted local mock connectors. This does not establish original community-node compatibility or live integration. [Exact engine-demo scope](../docs/demo.md). Newer versions require their own acceptance run.

- Community node packages: `n8n-nodes-feishu-lite`, `n8n-nodes-deepseek`. The source records do not pin their installed versions; select and record compatible versions in your test instance.
- `better-sqlite3` must be installed and permitted in the **Code-node execution environment**. The historical setup used `NODE_FUNCTION_ALLOW_EXTERNAL=better-sqlite3`; external task runners also need the module available in their own environment. Do not assume setting a variable alone installs the module. The isolated demo used version 12.4.1 and an explicit native-binding path in its private copies because default addon discovery failed in the secure runner. Validate your own runner packaging; do not disable runner security to copy the demo.
- A persistent writable SQLite path, currently `/home/node/.n8n/wechat_monitor_paid_calls.sqlite`, shared by the relevant summary/metrics workflows.
- A reachable, separately operated wechat2rss service. Catch currently uses the example Docker-network hostname `http://wechat2rss:8080`; change `Normalize Accounts` if your topology differs.
- A Feishu application with access to the configuration and article tables; optional DeepSeek and metrics-provider accounts.

The fixtures do not require these services. The full workflow set is not advertised as compatible with a default n8n Cloud installation.

## Configure your own copy

1. Copy [n8n-install-config.json](../examples/n8n-install-config.json) into `.work/install.json` at the repository root. Replace the three placeholder values with your configuration Base, account table and pipeline table identifiers.
2. Generate private copies without editing the public templates:

   ```bash
   mkdir -p .work
   cp examples/n8n-install-config.json .work/install.json
   # Edit .work/install.json, then:
   python3 scripts/prepare_n8n.py --config .work/install.json
   ```

   Generated files stay under git-ignored `.work/n8n-configured/`. The tool refuses existing output directories. `values` can also contain the four credential-ID placeholders, **credential reference IDs only, never actual tokens**. `workflow_ids` optionally maps the portable IDs in the manifest to IDs from an instance-specific import process.
3. Create credentials in n8n's own UI:

   | Placeholder | Credential type | Configuration |
   |---|---|---|
   | `FEISHU_CREDENTIAL_ID` | Feishu Credentials API | Your Feishu app credentials |
   | `DEEPSEEK_CREDENTIAL_ID` | DeepSeek API | Your provider key |
   | `FEED_QUERY_CREDENTIAL_ID` | HTTP Query Auth | Name `k`; value supplied privately |
   | `METRICS_CREDENTIAL_ID` | HTTP Custom Auth | Provider's private `verifycode` body value |

4. Prepare the tables using [the field contract](../docs/architecture.md) and [example pipeline rows](../examples/pipeline-config.json). Example identifiers are not working tables. The benchmark prompt must match its structured output fields; a generic free-text prompt is insufficient.

## Import and bind

1. Import **Catch, both Summary workflows and Metrics first**, then the three Entries, from the configured copies. All exports are inactive.
2. Bind credentials on each applicable node. A placeholder credential reference is not an installed credential.
3. In every Entry's **Execute Catch / Execute Summary / Execute Metric** node, select the imported child workflow. **UI imports may assign different workflow IDs**; the portable references are not proof of correct binding. Industry/AI entries use News Summary; Benchmark uses Benchmark Summary.
4. For CLI/scheduled execution in 2.19.5, publish the child workflow versions after binding and reviewing them; merely importing an inactive child is insufficient. Keep scheduled Entries inactive during acceptance. Review schedules and timezone before activation. Imported schedule nodes retain the selected source design; keep every Entry inactive until acceptance is complete.
5. Run one Entry manually using a dedicated test target. Inspect Catch's `Verify Count`, write actions and downstream outcomes. Repeat with the same input to inspect skip behavior and paid-call reuse. Test optional metrics separately if you enable it.

Local checks cannot establish that your credentials, node-package versions or target schemas are compatible. Record that import/manual-execution gate in your environment before scheduling live use.

## Troubleshooting and rollback

- **Unknown node type:** install/enable the required community package and verify its version.
- **Child workflow not found:** reselect the imported workflow in each Execute node.
- **Module not allowed / SQLite unavailable:** inspect the actual runner's module installation, allowlist and filesystem permissions.
- **Table not found / field error:** verify app access, configured identifiers, field names and types. Chinese field names are part of the contract.
- **`UNCERTAIN_REVIEW` / expired paid-call lock:** pause related schedules and follow the [review and recovery procedure](../docs/paid-call-recovery.md). Repeated runs do not release uncertain calls.
- **Configuration not unique:** keep exactly one enabled row per pipeline; a paginated response is rejected rather than selecting a partial result.
- **Visibility failure:** inspect missing IDs/content/URLs and write responses; do not bypass verification merely to obtain a green execution.
- **More than 100 enabled accounts:** the selected Catch intentionally fails fast; account-list pagination is not implemented.

Rollback: deactivate the three imported Entries to stop new schedules. The export does not alter the upstream feed service or prior workflows. Retain your own pre-import backup and SQLite backup before any live migration. Deactivation does not undo previously written rows or paid calls; review any data cleanup separately.
