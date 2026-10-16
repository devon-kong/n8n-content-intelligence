# Contribution and third-party boundaries

[Portfolio](../README.md) · [Publication scope](../NOTICE.md)

## Personal contribution

This is Devon's personal automation project. The work covers defining the monitoring use cases, separating Entry/Catch/Summary/Metric responsibilities, selecting the configuration and destination model, specifying field ownership and incremental-write rules, integration decisions, and iterating from execution feedback.

Implementation and this portfolio preparation use AI-assisted development. That assistance is not an independent human audit, and this repository does not claim every line was manually typed by the author. The value presented is responsibility for requirements, architecture, implementation decisions and acceptance boundaries.

The public release curates the latest selected seven n8n workflows and an existing Python port. It removes private identifiers, credential references, runtime state and internal development records. Two compatibility fixes were made in the public Python copy: `k` query authentication and UTF-16 hashing for non-BMP Unicode.

## What belongs to other projects

- **n8n** supplies the orchestration platform and built-in nodes. This repository contains workflow definitions, not a replacement implementation of n8n.
- **wechat2rss** supplies the upstream article feeds. The crawler/feed service is not authored or bundled here. Its [deployment documentation](https://wechat2rss.xlab.app/deploy/) governs that integration.
- **Feishu / Bitable**, **DeepSeek** and the metrics provider supply their respective hosted services.
- `n8n-nodes-feishu-lite`, `n8n-nodes-deepseek`, `better-sqlite3` and Python packages are separate dependencies. Their licenses and service terms remain applicable; compatible community-node versions still need fresh acceptance.
- Architecture illustrations and synthetic examples in this public package were prepared for the portfolio. They are not product UI screenshots or historical production data.

No third-party application source, private provider credentials, real article corpus or production service is bundled. The API paths in the code describe integration points, not an endorsement or availability guarantee.
