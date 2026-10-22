# Architecture and business contracts

[Portfolio](../README.md) · [n8n setup](../n8n/README.md)

![Shared processing architecture](../assets/diagrams/architecture.svg)

## Responsibility boundaries

| Component | Owns | Does not own |
|---|---|---|
| Entry | Read exactly one enabled pipeline config; route optional processors | Article collection or writes to the config table |
| Catch | Read enabled accounts; feed requests; window filtering; normalization; deduplication; base-field upsert and visibility | Reading pipeline config, calling Summary/Metric or writing their statuses |
| News Summary | Pending records, free-text summary, SQLite call state and writeback | Collection or metrics |
| Benchmark Summary | Structured summary parsing and benchmark fields | Collection or metrics |
| Metrics | Pending records, provider request, 24-hour success cache and writeback | Deciding business eligibility |

The three entries use `industry_news`, `ai_news` and `benchmark`. Their shared Catch receives:

```text
pipeline_key, target_base, target_table, window_days
```

The n8n Summary sub-workflows receive `target_base, target_table, summary_prompt_template, prompt_version, model`. Each Entry's `Prepare Summary Inputs` maps configuration fields `summary_prompt` → `summary_prompt_template` and `summary_version` → `prompt_version`. The Python stage keeps `summary_prompt` / `summary_version` as its argument names. Metrics receives only `target_base, target_table`.

Summary is enabled by `summary_enabled`. Metrics eligibility is **summary_enabled AND process_mode=benchmark AND metric_enabled**. In the n8n benchmark entry, the checks are separate branches after Catch, not a dependency on summary success. Python runs the stages in sequence.

## Data contracts

Field names remain Chinese where they are API schema keys. The English explanations below do not rename the exported node parameters.

**Accounts table**

| Field | Type | Meaning |
|---|---|---|
| `账号名称` | Text | Display name |
| `biz_id` | Text | Upstream account identifier |
| `是否启用` | Checkbox | Include this account |
| `pipeline_key` | Single select | One of the three business keys |

Use one pipeline assignment per account in this version. The account query fails fast if it has more than 100 results; it does not paginate the account list.

**Pipeline Config**

Use the rows in [pipeline-config.json](../examples/pipeline-config.json) as a template, not as an API import payload. Configure `pipeline_key`, `target_base`, `target_table`, `summary_prompt` and `summary_version` as text; flags as checkboxes; `model`, `process_mode` and `window_days` as text or compatible single-select values. Exactly one enabled matching row must exist. n8n Entry queries request up to two rows and reject multiple matches or `has_more=true`, so a paginated response cannot silently establish uniqueness. The selected Entry does not update `last_run`.

**Article table: six Catch-owned fields**

| Field | Suggested field type | Meaning |
|---|---|---|
| `article_id` | Text | Stable `wx_…` identifier derived by this implementation |
| `标题` | Text | Title |
| `markdown` | Multiline text | Cleaned article body |
| `发布时间` | Date/time | Epoch-millisecond write payload |
| `地址` | URL-compatible field | Link object; verify the selected node's serialization |
| `账号` | Text | Account display name |

Summary adds `摘要` (text) and `summary_status` (single select containing `summarized`). Metrics adds six number fields: `阅读`, `点赞`, `在看`, `转发`, `收藏`, `评论数`, plus `metric_status` containing `data_fetched`.

The current **n8n Benchmark Summary** also writes `文章类型`, `类型原因`, `政策对象`, `主题标签`, `企业类型`, `关键事实`. The parser serializes its array/object values as JSON strings, so text fields are appropriate for a new demo table. Do not assume they are native multi-select payloads.

Its model response is a JSON object with non-empty `summary_v2`; additional fields are `article_type`, `type_reason`, `policy_entity` (array), `topic_tags_v2` (array), `target_company_type` (array) and `key_facts` (object). The synthetic config includes a matching basic prompt. Model availability, output quality and the destination schema still need live acceptance.

## Incremental writes

Catch computes article IDs, deduplicates them and searches existing records in groups of up to 50 IDs. It compares title, publication time, URL and account. New IDs create records; stable-field changes update records; unchanged records skip writes. Markdown is excluded from the comparison and existing-record projection to avoid formatting-driven rewrites.

The trade-off is intentional: a body-only correction is not refreshed automatically. Also, article IDs are lightweight non-cryptographic hashes, not collision-free identities or security boundaries.

## Call state, completion and limits

Summary/Metric use SQLite call logs and atomic lock decisions to reuse successes and avoid blindly repeating uncertain paid calls. Lock expiry changes the old call to `uncertain` and stops that attempt. Later attempts return `UNCERTAIN_REVIEW` while any uncertain row for the same key remains, including after restart. This is a review condition, not proof that a remote request never executed. An explicit [local review](paid-call-recovery.md) can authorize retry of a selected row and atomically preserve an audit record; it makes no remote request. Cache/task keys are primarily article/model/prompt-version based; arbitrary cross-table and multi-tenant isolation is not guaranteed. Use distinct prompt versions and controlled account ownership, then validate your actual table-sharing design.

The selected N8N Catch retains an execution-ID bucket barrier because the historical deployment reported issues with loop completion routing. The harness tests interleaved buckets in one JavaScript state. That is **not proof of safe persistence across real concurrent n8n executions**; the historical workaround must be revalidated in the chosen runtime.

After processing, Catch queries expected article IDs and checks visibility/content/URLs. It does not establish transactionality across upstream, Feishu and paid APIs. External response bodies may appear in application errors; operational logs need their own redaction before sharing.
