"""Explicit local review of uncertain paid calls; never contacts a provider.

Works with the shared n8n/Python SQLite schema. Keep the database and reasons
private. Pause related schedules and settle remote requests before approval.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path

TABLES = {'summary': 'summary_call_log', 'metrics': 'metrics_call_log'}


def approve_retry(database: Path, stage: str, call_id: int, reason: str, reviewer: str) -> None:
    if stage not in TABLES or call_id < 1 or not reason.strip() or not reviewer.strip():
        raise ValueError('A valid stage, row ID, review reason and reviewer are required')
    database = Path(database).resolve()
    if not database.is_file():
        raise FileNotFoundError('Existing call-log database required')
    # mode=rw never silently creates a replacement database.
    with closing(sqlite3.connect(database.as_uri() + '?mode=rw', uri=True)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute(f'SELECT status FROM {TABLES[stage]} WHERE id=?', (call_id,)).fetchone()
        if not row or row[0] != 'uncertain':
            raise ValueError('Only an existing uncertain row can be reviewed; no change made')
        db.execute('''CREATE TABLE IF NOT EXISTS paid_call_review (
            id INTEGER PRIMARY KEY AUTOINCREMENT, stage TEXT NOT NULL,
            call_id INTEGER NOT NULL, action TEXT NOT NULL, reason TEXT NOT NULL,
            reviewer TEXT NOT NULL, reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('INSERT INTO paid_call_review(stage,call_id,action,reason,reviewer) VALUES (?,?,?,?,?)',
                   (stage, call_id, 'authorize_retry', reason.strip(), reviewer.strip()))
        db.execute(f"UPDATE {TABLES[stage]} SET status='skipped', error_code='REVIEW_RETRY_APPROVED' WHERE id=? AND status='uncertain'", (call_id,))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--stage', required=True, choices=TABLES)
    parser.add_argument('--authorize-retry', type=int, metavar='ROW_ID')
    parser.add_argument('--reason', default='')
    parser.add_argument('--reviewer', default='')
    parser.add_argument('--confirm-remote-settled', action='store_true')
    parser.add_argument('--accept-possible-charge', action='store_true')
    args = parser.parse_args()
    try:
        if args.authorize_retry is not None:
            if not args.confirm_remote_settled or not args.accept_possible_charge:
                parser.error('Retry approval requires --confirm-remote-settled and --accept-possible-charge')
            approve_retry(args.database, args.stage, args.authorize_retry, args.reason, args.reviewer)
            print(json.dumps({'stage': args.stage, 'row_id': args.authorize_retry, 'action': 'retry_authorized', 'remote_calls': 0}))
        else:
            with closing(sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True)) as db:
                db.row_factory = sqlite3.Row
                rows = db.execute(f"SELECT id,article_id,status,started_at,error_code FROM {TABLES[args.stage]} WHERE status='uncertain' ORDER BY id").fetchall()
                print(json.dumps([dict(row) for row in rows], indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f'Review failed: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
