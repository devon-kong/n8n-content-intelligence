# Upwork presentation copy and walkthrough

[Portfolio](../README.md) · [Evidence and reproduction](demo.md)

## Title

**n8n AI Research & Content Monitoring Automation**

## Role

Workflow architecture, API integration, data contracts and acceptance testing

## Short description

I built a configurable n8n workflow that turns publisher feeds into source-linked research briefs with summaries, categories and key facts. Three business entries share one collection core with incremental writes, output checks and explicit review of uncertain paid calls. I owned the requirements, architecture and testing, using AI-assisted development. Includes a Python companion, setup and handover documentation, and a real n8n engine demo with clearly labeled synthetic service boundaries. Live service acceptance remains environment-specific.

## Suggested skills

n8n · Workflow Automation · API Integration · Python · AI Integration

These are capability suggestions; check the platform's current selectable tags
and field limits when publishing. This file is a draft and does not publish a
profile or imply a client engagement.

## Media ready for review

- [Result board](../assets/demo/result-board.png): structured output rendered from
  recorded simulated destination rows; not Feishu UI.
- [Source and structured result](../assets/demo/source-to-result.png): an example
  of preserving missing information for human follow-up.
- [Execution outcomes](../assets/demo/execution-evidence.png): first run, stable
  rerun and two rejected failure cases.
- [Actual n8n editor capture](../assets/demo/n8n-catch-editor.png): the private
  synthetic Catch workflow loaded in the real editor.
- [60-second video](../assets/demo/walkthrough.mp4): a silent evidence walkthrough
  using these rendered frames; not a live screencast.

All article facts and model responses are authored synthetic fixtures. Do not
call the video a live model demonstration or use it as an accuracy benchmark.

## Result-first 60-second script

| Time | Show | Suggested narration |
|---|---|---|
| 0–20s | Final research brief | “A research team needs more than a list of links. This workflow organizes articles into summaries, categories and facts that can be reviewed against a source.” |
| 20–35s | Source → structured output | “In this synthetic example, the effective date is missing. The structured output preserves that gap for follow-up. The response is authored; this checks parsing and writeback.” |
| 35–50s | Recorded engine outcomes | “The n8n engine created and enriched three records. Repeating the run made no further writes or model calls. Duplicate configuration and missing output were rejected.” |
| 50–60s | Role and delivery scope | “I designed the workflow and acceptance rules with AI-assisted implementation. Similar delivery includes configuration, integrations, tests and handover; actual services require their own acceptance.” |

## A concise proposal connection

“I can apply this shared-workflow pattern to your monitoring and research process:
clarify sources and output fields, build the integration, verify reruns and failure
handling, and document the handover. My portfolio shows the implementation and
its validation boundaries; your requested tools would be scoped and tested in
your dedicated environment.”

Choose one target connector only when the actual project requires it. Airtable,
Notion and Google Sheets are not current implemented destinations. Avoid claims
about hours saved, cost reduction or production success rates without measurements.
