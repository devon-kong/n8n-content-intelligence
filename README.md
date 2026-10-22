# n8n Content Intelligence — AI Research & Monitoring Automation

**Turn publisher feeds into a source-linked research brief: article synchronization, summaries, categories and key facts — with reusable n8n workflows and a Python companion.**

[![Portfolio checks](https://github.com/devon-kong/n8n-content-intelligence/actions/workflows/check.yml/badge.svg)](https://github.com/devon-kong/n8n-content-intelligence/actions/workflows/check.yml)
[中文介绍](README.zh-CN.md) · [n8n setup](n8n/README.md) · [Python setup](python/README.md) · [Validation](docs/validation.md)

## Architecture & Workflow Overview

**One shared collection core. Three configurable business pipelines.**

https://github.com/user-attachments/assets/292e2897-af19-499f-8ec5-c1fe630dc1c5

[Open or download the MP4](assets/demo/central-kitchen.mp4) · [Film and evidence boundaries](docs/video.md) · [Original evidence walkthrough](assets/demo/walkthrough.mp4)

## The business problem

A research or operations team monitors several groups of WeChat publishers. Each group needs its own destination table, time window and AI instructions. Copying a complete automation for every group makes changes expensive and repeated runs can create duplicate records or repeat paid API calls.

I designed a **shared processing core**: small entry workflows read business configuration, then reuse article collection and optional enrichment sub-workflows. The implementation connects **wechat2rss → n8n → Feishu Bitable → optional LLM / article metrics**.

WeChat is the source publishing platform. **wechat2rss is a separate upstream feed service**; this project builds the orchestration and processing around it. Feishu Bitable is the structured workspace database used here. Airtable, Notion and other destinations are not currently implemented.

## My role and what a client can reuse

I defined the monitoring requirements, field contracts, shared workflow architecture,
incremental-write rules and paid-call review policy, and implemented and tested the
system with AI assistance. The transferable delivery is a configurable monitoring
workflow, inspectable output, failure handling, setup instructions and handover.

For research and operations teams, the result is a brief they can filter by topic,
inspect for missing facts and trace back to a source. The synthetic example deliberately
keeps an unstated effective date as “Not stated”; that illustrates the intended review
workflow, not measured AI accuracy. New tools or destinations would be separately
scoped integrations. [Contribution and third-party boundaries](docs/contributions.md)

## What I built

| Capability | Implementation | Practical value |
|---|---|---|
| Three configurable business pipelines | Industry news, AI news and benchmark entries | Reuse the core while varying sources, destinations and processing flags |
| Incremental article synchronization | Normalization, stable IDs, bulk existence checks, create / update / skip | Avoid unnecessary writes on stable reruns |
| Optional AI and metrics processing | Separate sub-workflows, SQLite call logs, cache and persistent uncertainty review | Keep paid enrichment separate from collection; stop automatic retries when an outcome is unknown |
| Post-write verification | Article presence, content and URL checks | Expose missing output instead of relying only on successful requests |
| Companion Python implementation | CLI → flows → stages → reusable operations and clients | Demonstrate the same business decomposition in code |

This is an independent personal engineering project. It demonstrates reusable automation design and implementation, not a claimed client engagement.

## See the processing outcome

![Three synthetic research articles with structured summaries, classifications and key facts. Rendered from recorded engine output; not Feishu UI.](assets/demo/result-board.png)

The result board renders a **real n8n engine run with local mock connectors**. Its articles and model responses are authored synthetic fixtures. It demonstrates orchestration, parsing and writeback, without claiming actual LLM generation, Feishu integration or model accuracy. The film distinguishes the reported operating totals from these fixture examples.

The representative **Benchmark Entry → Catch → structured Summary** demo runs in
n8n 2.19.5 with a secure JavaScript runner. External connector nodes are explicitly
replaced by local HTTP fixtures in private copies; the original public exports stay
inactive. Seven original exports were accepted by CLI import with community nodes
disabled, which does not validate their connector compatibility.

| Observed scenario | Recorded result |
|---|---|
| First execution | 3 article creates, 3 scripted model responses, 3 enriched rows |
| Stable rerun | 0 creates, 0 base updates, 0 further model calls |
| Duplicate/paginated config | Rejected before article processing |
| Missing destination article | Rejected by Catch visibility verification |

[Bounded engine evidence](assets/evidence/n8n-engine-demo.json) · [Reproduce it](docs/demo.md)

A separate lightweight Catch fixture demonstrates **one create, one update and one
skip**, with matching IDs/actions in Python. It runs exported Code-node bodies in a
Node harness, independently of the n8n engine demonstration:

```bash
node scripts/demo_n8n.mjs
# After the Python setup below:
python scripts/demo_python.py
python scripts/compare_demos.py
```

[Catch input](examples/catch-scenario.json) · [n8n fixture output](assets/evidence/n8n-fixture-run.json) · [Python fixture output](assets/evidence/python-fixture-run.json)

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

**Treat paid enrichment and output verification explicitly.** SQLite call logs distinguish cached success, in-progress work and uncertain outcomes. Uncertain calls stay blocked across runs until an operator explicitly reviews them; [retry approval](docs/paid-call-recovery.md) is audited and makes no remote call. Catch verifies that expected articles are visible. These mechanisms have specific scopes; they are not an end-to-end exactly-once guarantee.

## Why include Python?

The companion preserves the layered business model while replacing visual orchestration with a process-style CLI. It is useful evidence of code-based automation skills alongside n8n delivery.

It is **not a fully equivalent replacement**: benchmark enrichment fields differ and Python executes its stages sequentially. Shared catch-fixture IDs and decisions are checked; complete cross-implementation parity and live Python acceptance are not claimed.

[Implementation comparison →](docs/implementation-comparison.md) · [Run Python →](python/README.md)

## 15 days of continuous collection

**883 article records collected across three business pipelines during a reported 15-day period of continuous operation.**

| Pipeline | Articles collected |
|---|---:|
| AI news | 273 |
| Benchmark | 508 |
| Industry news | 102 |
| **Combined pipeline count** | **883** |

Stable collection is supported by a shared Catch core: normalize and deduplicate
incoming articles, create or update changed records, skip unchanged records, and
verify that expected output arrived. Business-specific configuration keeps the
three pipelines on the same collection logic. Optional enrichment has separate
responsibilities and review rules.

These are [operator-reported aggregate results](assets/evidence/operator-reported-collection.json),
provided by Devon on 22 October 2026. The 15 days describe system operation, not
the articles' publication window. The total sums the three pipeline counts;
independent public-package tests are documented separately in the [validation record](docs/validation.md).

## Validation and scope

Current checks cover inactive exports, references, Code-node behavior, real SQLite lock/review transitions, Python tests and bounded publication checks. CI reproduces the offline checks; the engine demo is a separate opt-in local run. Live service compatibility, model quality and production concurrency remain untested in this public package. See [validation](docs/validation.md).

Live use requires your own upstream service, Feishu application, community nodes, optional paid-service credentials and an appropriate self-hosted n8n environment. Workflows are shipped inactive and contain configuration placeholders.

## My contribution and source availability

My work covers the business requirements, reusable workflow architecture, configuration model, incremental-write rules, integration decisions and acceptance-driven iteration, using AI-assisted development. The public snapshot includes the current workflow set and Python companion, with environment identifiers and runtime materials removed.

[Contribution and third-party boundaries](docs/contributions.md) · [Publication scope](NOTICE.md) · [Upwork portfolio copy](docs/portfolio.md)
