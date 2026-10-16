# n8n and Python: shared model, explicit differences

[Portfolio](../README.md) · [Python setup](../python/README.md)

The two implementations express the same business decomposition. They are not currently certified as interchangeable.

| Area | n8n | Python | Evidence / limit |
|---|---|---|---|
| Entry | Three visual workflows | `flows/central_kitchen.py` | Config-driven routing; source plus tests |
| Catch | Shared 25-node workflow | `stages/catch.py`, `ops/` | Shared synthetic fixture checks IDs and create/update/skip decisions |
| Feed auth | HTTP Query Auth named `k` | Query parameter `k` | Regression test corrects the original port's mismatch |
| Article ID | JS UTF-16 `charCodeAt` hash | Explicit UTF-16 code-unit port | Regression includes non-BMP Unicode; IDs are not cryptographic |
| Base fields | Six Catch-owned fields | Same six-field whitelist | Code-node fixture and Python tests |
| News summary | Dedicated visual workflow | Parameterized summary stage | Both write summary/status; live behavior not compared |
| Benchmark summary | Structured parsing and seven content/classification fields | Plain summary/status | **Known feature gap**; not full parity |
| Orchestration | Summary/metrics are separate branches after Catch for benchmark | Sequential stages | Different execution strategy |
| Paid-call state | `better-sqlite3` Code nodes | Python `sqlite3` store | Similar concepts; schema, state transitions and failure semantics not exhaustively compared |
| Scheduling | n8n Entry schedules | External invocation of CLI | No public Hermes deployment evidence |
| Current live acceptance | Historical source deployment records only | Original port had mock acceptance | Fresh public-package live acceptance remains pending for both |

## What the shared demo proves

Both paths use [the same synthetic feed](../examples/catch-scenario.json). The n8n harness executes exported normalization, deduplication, payload, decision, barrier and visibility Code nodes with supplied context and simulated storage. The Python demo calls normalization and upsert-decision functions. Their three article IDs and ordered create/update/skip decisions must match.

The n8n test suite additionally checks stable reruns, missing-record rejection and bucket isolation within one harness state. These are targeted behavioral checks. They do not execute community nodes, n8n's scheduler or paid providers.

## Why keep both implementations?

n8n is the primary visual automation deliverable: it makes routing and integrations inspectable. Python demonstrates the ability to express processing as reusable code, with testable HTTP boundaries and process-style execution. Selection depends on the client's operational environment; no unmeasured cost or memory comparison is claimed.
