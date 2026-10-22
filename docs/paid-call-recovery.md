# Review an uncertain paid call

[Portfolio](../README.md) · [Architecture](architecture.md)

A timeout, incomplete model response or expired processing lock does not prove
that a remote request failed. Summary and Metrics retain `uncertain` rows and
return `UNCERTAIN_REVIEW` on later lock attempts, including after restart. They
do not automatically reclaim these calls. A successful cached result can still
be reused without making a new paid request.

## Inspect and decide

1. Pause every Entry or CLI schedule sharing this database. Let in-flight work
   finish; pausing a schedule does not cancel an existing request.
2. Run the read-only command on the actual persistent database (or inspect a
   backup first). The tool uses only Python's standard library and contacts no
   service:

   ```bash
   python3 scripts/review_paid_calls.py --database .work/calls.sqlite --stage summary
   # Use --stage metrics for the metrics log.
   ```

3. Match the row to the original request in your private provider records. If
   its outcome is still unknown, leave it blocked. If the result already exists,
   reconcile it with the destination before considering a new call. This tool
   does not retrieve remote results or certify that no charge occurred.
4. Only after the remote request is settled, explicitly accept the possible
   cost of another request and authorize a particular row for retry:

   ```bash
   python3 scripts/review_paid_calls.py \
     --database .work/calls.sqlite --stage summary --authorize-retry 7 \
     --reviewer operator --reason 'Checked remote outcome; retry cost accepted' \
     --confirm-remote-settled --accept-possible-charge
   ```

The example path and row number are placeholders. Use the database actually
mounted in the n8n runner or configured for Python; editing a detached copy
does not unblock the running system. Keep reasons, databases and raw logs
private, with no credentials in command arguments or reasons.

## What approval changes

In one SQLite transaction, approval records stage, row ID, reason, reviewer and
time in `paid_call_review`, then changes only that `uncertain` row to `skipped`
with `REVIEW_RETRY_APPROVED`. Original payload and timing fields are retained.
It rejects active/successful/already-reviewed rows and never creates a missing
database. Any other uncertain row for the same task still blocks acquisition.

Approval does not call a provider. A later normal execution may acquire a new
lock if the record remains pending. Inspect that execution before re-enabling
schedules. No exactly-once or no-double-charge guarantee is claimed.

The tool supports the n8n and Python schemas shipped here. Lock keys retain
their existing article/model/prompt-version scope; this is not tenant isolation.
