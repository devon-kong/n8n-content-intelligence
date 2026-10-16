# Upwork presentation draft

[Portfolio](../README.md)

## Title

**Reusable n8n Content Monitoring & AI Enrichment Workflows**

## Short description

I designed a configurable n8n system for monitoring WeChat articles, synchronizing them to Feishu Bitable, and running optional AI summaries and engagement metrics. Three business entries reuse one collection core with incremental writes, call-state tracking and output verification. A companion Python CLI demonstrates the same business decomposition. Includes sanitized workflows, source, synthetic demonstrations and clearly scoped validation evidence.

## Suggested capability labels

n8n · Workflow Automation · API Integration · Python · AI Integration

These are positioning suggestions, not a statement about the current platform's allowed tag names or limits.

## 60-second walkthrough

| Time | Show | Explain |
|---|---|---|
| 0–10s | Business problem and cover | Separate publisher groups need different destinations and AI rules |
| 10–25s | Central-kitchen diagram and seven workflow files | Thin entries reuse shared processing; configuration owns business differences |
| 25–40s | Run the synthetic demo | Three records take create/update/skip paths; outputs are inspectable |
| 40–50s | Python code map and comparison | The same business model can be expressed as a CLI; state known gaps |
| 50–60s | Validation page | Distinguish current offline evidence from pending live acceptance |

Use the [cover](../assets/diagrams/cover.svg) and [fixture graphic](../assets/diagrams/fixture-results.svg) as clearly labeled illustrations. An actual n8n UI capture and dedicated-table run would strengthen the demonstration later. Do not present generated graphics as a live execution screenshot or claim fabricated savings/success rates.
