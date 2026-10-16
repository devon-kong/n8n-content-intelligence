# Content Intelligence Automation

**Reusable n8n workflows for article monitoring, AI summaries and structured data — with a companion Python CLI.**

[![Portfolio checks](https://github.com/devon-kong/n8n-content-intelligence/actions/workflows/check.yml/badge.svg)](https://github.com/devon-kong/n8n-content-intelligence/actions/workflows/check.yml)
[中文介绍](README.zh-CN.md) · [n8n setup](n8n/README.md) · [Python setup](python/README.md) · [Validation](docs/validation.md)

![One shared processing core, three business pipelines, two implementations. Architecture illustration.](assets/diagrams/cover.svg)

## The business problem

A research or operations team monitors several groups of WeChat publishers. Each group needs its own destination table, time window and AI instructions. Copying a complete automation for every group makes changes expensive and repeated runs can create duplicate records or repeat paid API calls.

I designed a **shared processing core**: small entry workflows read business configuration, then reuse article collection and optional enrichment sub-workflows. The implementation connects **wechat2rss → n8n → Feishu Bitable → optional LLM / article metrics**.

WeChat is the source publishing platform. **wechat2rss is a separate upstream feed service**; this project builds the orchestration and processing around it. Feishu Bitable is the structured workspace database used here. Airtable, Notion and other destinations are not currently implemented.

## What I built

| Capability | Implementation | Practical value |
|---|---|---|
| Three configurable business pipelines | Industry news, AI news and benchmark entries | Reuse the core while varying sources, destinations and processing flags |
| Incremental article synchronization | Normalization, stable IDs, bulk existence checks, create / update / skip | Avoid unnecessary writes on stable reruns |
| Optional AI and metrics processing | Separate sub-workflows, SQLite call logs and cache | Keep paid enrichment separate from collection |
| Post-write verification | Article presence, content and URL checks | Expose missing output instead of relying only on successful requests |
| Companion Python implementation | CLI → flows → stages → reusable operations and clients | Demonstrate the same business decomposition in code |

This is an independent personal engineering project. It demonstrates reusable automation design and implementation, not a claimed client engagement.

## See the processing outcome

The checked-in demonstration uses **synthetic articles and simulated storage**, with no credentials or external requests. It executes the actual exported n8n Catch Code-node bodies and the Python catch functions against the same input.

![Synthetic catch demonstration: one create, one update, one skip in both implementations.](assets/diagrams/fixture-results.svg)

```bash
# Node.js 22+; no npm install required
node scripts/demo_n8n.mjs

# Python environment required; see python/README.md
python scripts/demo_python.py
python scripts/compare_demos.py
```

Results: [input scenario](examples/catch-scenario.json), [n8n Code-node output](assets/evidence/n8n-fixture-run.json), [Python output](assets/evidence/python-fixture-run.json).

**The Node harness is not an n8n engine execution.** Current public-release checks and historical live deployment are documented separately; fresh full n8n import and live integration remain pending.

## How the central kitchen works

![n8n architecture: three entry workflows reuse Catch and optionally call Summary and Metrics.](assets/diagrams/architecture.svg)

1. An **Entry** reads one enabled pipeline configuration: destination, time window, prompt/model and processing flags.
2. **Shared Catch** reads enabled accounts, fetches upstream JSON feeds, normalizes and deduplicates articles, writes six base fields, then verifies visibility.
3. **Summary** and **Metrics** run according to the entry's flags. They use their own pending criteria and SQLite records.

Only **seven current workflows** are included. The collection core is the latest selected 25-node revision; old experiments and production backups are excluded. The benchmark entry has separate summary/metrics branches after Catch; runtime parallelism depends on n8n's execution behavior.

[Explore the architecture and contracts →](docs/architecture.md)

## Three engineering decisions

**Configure business differences at the edge.** Entry workflows own configuration and routing. Catch owns collection and base-field synchronization. Changing a target or prompt does not require duplicating the processing core.

**Compare stable fields before writing.** Existing articles are compared by title, publication time, URL and account. Markdown formatting differences alone do not trigger an update. This is a deliberate trade-off: refreshing old article bodies needs a separate controlled operation.

**Treat paid enrichment and output verification explicitly.** SQLite call logs distinguish cached success, in-progress work and uncertain outcomes. Catch verifies that expected articles are visible. These mechanisms have specific scopes; they are not an end-to-end exactly-once guarantee.

## Why include Python?

The companion preserves the layered business model while replacing visual orchestration with a process-style CLI. It is useful evidence of code-based automation skills alongside n8n delivery.

It is **not a fully equivalent replacement**: benchmark enrichment fields differ and Python executes its stages sequentially. Shared catch-fixture IDs and decisions are checked; complete cross-implementation parity and live Python acceptance are not claimed.

[Implementation comparison →](docs/implementation-comparison.md) · [Run Python →](python/README.md)

## Validation and scope

Current local checks cover seven inactive exports, connection/reference integrity, Code-node syntax, catch fixture behavior, Python tests and bounded publication checks. CI reproduces the offline checks. See [validation](docs/validation.md) for commands, environments and remaining gates.

Live use requires your own upstream service, Feishu application, community nodes, optional paid-service credentials and an appropriate self-hosted n8n environment. Workflows are shipped inactive and contain configuration placeholders.

## My contribution and source availability

My work covers the business requirements, reusable workflow architecture, configuration model, incremental-write rules, integration decisions and acceptance-driven iteration, using AI-assisted development. The public snapshot includes the current workflow set and Python companion, with environment identifiers and runtime materials removed.

[Contribution and third-party boundaries](docs/contributions.md) · [Publication scope](NOTICE.md) · [Upwork portfolio copy](docs/portfolio.md)
