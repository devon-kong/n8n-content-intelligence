# Python companion

[Portfolio](../README.md) · [Implementation comparison](../docs/implementation-comparison.md)

This process-style CLI implements the central-kitchen decomposition: configuration → catch → optional summary → optional metrics. It does not require a persistent Python server. An external scheduler can invoke it; no Hermes scheduler installation or acceptance is claimed.

## Setup and offline checks

Use Python 3.12+ and Node.js 22+ for the shared demonstration. The local release run used Python 3.14.7; CI uses Python 3.12. Direct dependencies are pinned in [requirements.txt](requirements.txt); this is not a full transitive lockfile.

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r python/requirements.txt
(cd python && python -m pytest -q)
python scripts/demo_python.py
python scripts/compare_demos.py
```

The fixture command uses synthetic data and calls no external clients. The Python test suite uses temporary databases and mocked HTTP responses. The comparison checks catch IDs/actions only, not complete summary or metrics equivalence.

## Live CLI configuration

Inside `python/`, copy [.env.example](.env.example) to `.env` and fill your own application, table and service values locally. The public Settings defaults do not contain configuration Base/table IDs.

```bash
cd python
cp .env.example .env
# Edit .env, then start with a read-only config check:
python -m article_catch config-show --pipeline industry_news

# These commands contact services and can write your configured target tables:
python -m article_catch run --pipeline industry_news
python -m article_catch run --pipeline industry_news,ai_news,benchmark
python -m article_catch catch --pipeline industry_news
```

Use a dedicated test table first. `config-show` is read-only; the other commands are not offline demos. Run `python -m article_catch --help` for individual summary/metric commands. Feed authentication uses the query parameter `k`, matching the n8n credential contract.

## Code map

```text
article_catch/
  cli.py                 arguments and exit codes
  flows/                 configuration and stage sequencing
  stages/                catch, summary, metrics
  ops/                   upsert, pending scans, visibility checks
  clients/               Feishu, feed, LLM, metrics HTTP boundaries
  store/                 SQLite call logs, locks and cache
  util/                  normalization, article IDs, field handling
```

The original port's feed-auth parameter and non-BMP Unicode hashing were corrected in this public copy with regression tests. Business rules otherwise remain the selected port's implementation. In particular, the benchmark's structured labeling is not implemented here, and orchestration is sequential. See the comparison before treating Python as a replacement.

Uncertain paid calls stay blocked across later runs and process restarts. Use the shared [local review procedure](../docs/paid-call-recovery.md) to inspect and explicitly authorize a retry; the review tool never calls a service.

Rollback: stop the external CLI schedule; retain SQLite state for investigation. Re-enabling an earlier n8n deployment is an independent operational decision. Neither this CLI nor the fixture tools modify your upstream service configuration. Do not publish raw live exceptions or API response bodies as portfolio evidence; review and redact operational logs separately.
